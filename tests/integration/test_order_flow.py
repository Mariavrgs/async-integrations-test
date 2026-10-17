"""Testes de integração do fluxo API -> Kafka -> consumidor -> gateway externo (stub) -> Postgres.

Sem `sleep` fixo: o teste espera as transições de estado reais no banco.
Sem race entre testes: cada um filtra pelo próprio correlation_id.
"""
from concurrent.futures import ThreadPoolExecutor

import pytest

from itf import CORRELATION_HEADER, new_correlation_id, wait_for_state_sequence

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_db")]


def states_of(db, cid):
    def fetch():
        rows = db.execute(
            "SELECT state FROM order_state_history WHERE correlation_id = %s ORDER BY id", (cid,)
        ).fetchall()
        return [r[0] for r in rows]

    return fetch


def create_order(api, amount=100.0):
    cid = new_correlation_id()
    r = api.post("/orders", json={"amount": amount}, headers={CORRELATION_HEADER: cid})
    assert r.status_code == 202
    return cid


def test_payment_approved_flow(api, db, stub):
    stub.stub("POST", "/payments", status=200, json={"approved": True})
    cid = create_order(api)

    wait_for_state_sequence(states_of(db, cid), ["PENDING", "PROCESSING", "PAID"])

    calls = stub.requests("/payments")
    assert len(calls) == 1
    assert calls[0]["headers"]["x-correlation-id"] == cid  # o id atravessou todo o pipeline


def test_gateway_error_marks_order_failed(api, db, stub):
    stub.stub("POST", "/payments", status=500, json={"error": "gateway indisponível"})
    cid = create_order(api)
    wait_for_state_sequence(states_of(db, cid), ["PENDING", "PROCESSING", "FAILED"])


def test_slow_gateway_still_completes(api, db, stub):
    stub.stub("POST", "/payments", status=200, json={"approved": True}, delay_ms=500)
    cid = create_order(api)
    wait_for_state_sequence(states_of(db, cid), ["PENDING", "PROCESSING", "PAID"], timeout=20)


def test_concurrent_orders_do_not_interfere(api, db, stub):
    stub.stub("POST", "/payments", status=200, json={"approved": True})
    with ThreadPoolExecutor(max_workers=10) as pool:
        cids = list(pool.map(lambda _: create_order(api), range(20)))

    for cid in cids:
        wait_for_state_sequence(states_of(db, cid), ["PENDING", "PROCESSING", "PAID"], timeout=30)

    seen = [c["headers"]["x-correlation-id"] for c in stub.requests("/payments")]
    assert sorted(seen) == sorted(cids)  # exatamente 1 chamada externa por pedido
