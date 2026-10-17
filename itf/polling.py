"""Polling inteligente: em vez de `time.sleep(5)` fixo, consulta o estado real do sistema
com backoff e falha rápido se o sistema entrar num estado inesperado."""
import time
from typing import Any, Callable, Sequence


class PollingTimeout(AssertionError):
    pass


class UnexpectedTransition(AssertionError):
    pass


def wait_until(
    fetch: Callable[[], Any],
    predicate: Callable[[Any], bool] = bool,
    *,
    timeout: float = 15.0,
    interval: float = 0.05,
    max_interval: float = 1.0,
    backoff: float = 1.5,
    description: str = "condição",
) -> Any:
    """Chama `fetch()` até `predicate(valor)` ser verdadeiro. Retorna o último valor.

    O intervalo cresce de `interval` até `max_interval` (backoff), então o teste é rápido quando o
    sistema responde logo e não martela o banco quando demora. Se `predicate` levantar exceção,
    ela sobe imediatamente (usado para falhar rápido).
    """
    deadline = time.monotonic() + timeout
    delay = interval
    attempts = 0
    while True:
        value = fetch()
        attempts += 1
        if predicate(value):
            return value
        if time.monotonic() + delay > deadline:
            raise PollingTimeout(
                f"Timeout de {timeout}s esperando {description} "
                f"({attempts} tentativas). Último valor observado: {value!r}"
            )
        time.sleep(delay)
        delay = min(delay * backoff, max_interval)


def wait_for_state_sequence(
    fetch_states: Callable[[], Sequence[str]],
    expected: Sequence[str],
    **kwargs: Any,
) -> list[str]:
    """Espera o histórico de estados chegar exatamente em `expected`, na ordem.

    - Estados parciais que são prefixo de `expected` são normais (o sistema ainda está andando).
    - Qualquer desvio (estado fora de ordem, estado extra, estado terminal errado) falha NA HORA com
      o histórico completo, sem esperar o timeout.
    """
    expected = list(expected)

    def check(states: Sequence[str]) -> bool:
        states = list(states)
        if states != expected[: len(states)]:
            raise UnexpectedTransition(
                f"Transição inesperada. Esperado (prefixo de) {expected}, observado {states}"
            )
        return states == expected

    wait_until(
        lambda: list(fetch_states()),
        check,
        description=f"sequência de estados {expected}",
        **kwargs,
    )
    return expected
