"""itf - Integration Test Framework: ambiente efêmero, polling por estado, correlation_id e stubs."""
from itf.correlation import CORRELATION_HEADER, new_correlation_id
from itf.polling import PollingTimeout, UnexpectedTransition, wait_for_state_sequence, wait_until

__all__ = [
    "CORRELATION_HEADER",
    "new_correlation_id",
    "PollingTimeout",
    "UnexpectedTransition",
    "wait_until",
    "wait_for_state_sequence",
]
