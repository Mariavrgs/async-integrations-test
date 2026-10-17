import uuid

CORRELATION_HEADER = "X-Correlation-ID"


def new_correlation_id(prefix: str = "test") -> str:
    """Um id único por teste/ação. Todo evento, linha de banco e chamada externa carrega esse id,
    então cada teste só olha para os dados que ele mesmo gerou (sem race entre testes paralelos)."""
    return f"{prefix}-{uuid.uuid4()}"
