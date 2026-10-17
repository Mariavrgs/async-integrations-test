import pytest

from itf import PollingTimeout, UnexpectedTransition, wait_for_state_sequence, wait_until
from itf.correlation import new_correlation_id


def test_wait_until_returns_when_condition_becomes_true():
    values = iter([0, 0, 3])
    assert wait_until(lambda: next(values), lambda v: v == 3, interval=0.001) == 3


def test_wait_until_times_out_with_last_value_in_message():
    with pytest.raises(PollingTimeout) as exc:
        wait_until(lambda: "PENDING", lambda v: v == "PAID", timeout=0.05, interval=0.01, description="pagamento")
    assert "PENDING" in str(exc.value) and "pagamento" in str(exc.value)


def test_state_sequence_accepts_progressive_history():
    history = [
        [],
        ["PENDING"],
        ["PENDING", "PROCESSING"],
        ["PENDING", "PROCESSING", "PAID"],
    ]
    it = iter(history)
    wait_for_state_sequence(lambda: next(it), ["PENDING", "PROCESSING", "PAID"], interval=0.001)


def test_state_sequence_fails_fast_on_wrong_terminal_state():
    it = iter([["PENDING"], ["PENDING", "PROCESSING"], ["PENDING", "PROCESSING", "FAILED"]])
    with pytest.raises(UnexpectedTransition) as exc:
        wait_for_state_sequence(lambda: next(it), ["PENDING", "PROCESSING", "PAID"], timeout=30, interval=0.001)
    assert "FAILED" in str(exc.value)


def test_state_sequence_fails_on_out_of_order():
    with pytest.raises(UnexpectedTransition):
        wait_for_state_sequence(lambda: ["PROCESSING"], ["PENDING", "PROCESSING"], interval=0.001)


def test_correlation_ids_are_unique():
    assert len({new_correlation_id() for _ in range(1000)}) == 1000
