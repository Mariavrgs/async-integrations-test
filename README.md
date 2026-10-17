# Async Integration Tests

Framework de testes de integração para sistemas **assíncronos** (API → Kafka → consumidor → banco → API externa), feito com **Pytest** e **Docker Compose**, focado em eliminar testes instáveis (*flaky*).

## Por que testes assíncronos ficam instáveis

| Causa típica | Como o framework trata |
|---|---|
| `time.sleep(5)` fixo: ora é pouco, ora é demais | **Polling inteligente** (`itf/polling.py`): consulta o estado real do banco com backoff e falha rápido em transição inesperada |
| Testes se atropelam (dados e mensagens misturados) | **`correlation_id` único por teste**, propagado em header HTTP → mensagem Kafka → banco → chamada externa. Cada teste só olha para o que ele gerou |
| Estado sujo de execuções anteriores | **Ambiente efêmero** (`itf/compose.py`): a suíte sobe um projeto Compose com nome único e o destrói com `down -v` no final |
| APIs de terceiros fora do ar, lentas ou imprevisíveis | **Stub server** dentro do Compose: respostas, erros e atrasos controlados pelo teste, com registro das chamadas |

## Como funciona

```
pytest ──► fixture `env` ──► docker compose -p itf-<id> up -d --wait
   │                         (kafka, postgres, api, consumer, stub — portas aleatórias)
   │
   ├─ stub.stub("POST", "/payments", status=500)     # define o comportamento da API externa
   ├─ api.post("/orders", headers={X-Correlation-ID})# dispara o fluxo
   └─ wait_for_state_sequence(                        # espera PENDING → PROCESSING → FAILED
         fetch_estados(correlation_id), [...])
   └─ ao final da suíte: docker compose down -v
```

O `wait_for_state_sequence` aceita estados parciais (o sistema ainda está andando) mas **falha na hora** se o histórico sair do esperado, mostrando o histórico completo, sem esperar o timeout.

## Rodando

Pré-requisitos: Python 3.12+ e Docker com Compose v2.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest tests/unit                       # rápido, sem Docker
pytest tests/integration -m integration # sobe e destrói o ambiente sozinho
pytest tests/integration --keep-env     # mantém o ambiente para depurar
```

## Estrutura

```
itf/                framework reutilizável
  compose.py        ambiente efêmero (up/down, descoberta de portas, logs em caso de falha)
  polling.py        wait_until e wait_for_state_sequence
  correlation.py    correlation_id
  stubs.py          cliente do stub de APIs externas
  fixtures.py       fixtures pytest (env, api, db, stub, clean_db)
sample_system/      sistema de exemplo que os testes exercitam (API, consumidor, stub)
tests/unit/         testes do próprio framework (sem Docker)
tests/integration/  cenários: aprovado, erro no gateway, gateway lento, 20 pedidos concorrentes
.github/workflows/  CI (unit → integration)
```

## Usando no seu projeto

1. Copie a pasta `itf/` e o `conftest.py`.
2. Aponte `ITF_COMPOSE_FILE` para o seu `docker-compose.yml` (com `healthcheck` nos serviços e portas `"0:PORTA"`).
3. Ajuste as fixtures `api`, `db` e `stub_server` em `itf/fixtures.py` para os seus serviços.
4. Use `new_correlation_id()` e `wait_for_state_sequence()` nos testes.

## Métricas de cobertura e estabilidade

Este repositório mostra a técnica num sistema de exemplo pequeno; ele **não** traz números de cobertura de um sistema real. Para medir no seu projeto:

```bash
pip install pytest-cov
pytest --cov=meu_pacote --cov-report=term-missing
```

Para checar flakiness, rode a suíte várias vezes (`pytest --count=20` com `pytest-repeat`) e registre a taxa de falhas antes e depois.
