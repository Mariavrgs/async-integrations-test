"""Fixtures reutilizáveis. Ative com `pytest_plugins = ["itf.fixtures"]` no conftest.py."""
import os

import httpx
import psycopg
import pytest

from itf.compose import EphemeralEnvironment
from itf.polling import wait_until
from itf.stubs import ExternalApiStub


def pytest_addoption(parser):
    parser.addoption("--keep-env", action="store_true", help="não destrói o ambiente no final (debug)")


@pytest.fixture(scope="session")
def env(request):
    compose_file = os.getenv("ITF_COMPOSE_FILE", "docker-compose.yml")
    environment = EphemeralEnvironment(compose_file)
    environment.up()
    try:
        yield environment
    finally:
        if request.config.getoption("--keep-env"):
            print(f"\nAmbiente mantido: docker compose -p {environment.project} down -v")
        else:
            environment.down()


@pytest.fixture(scope="session")
def api(env):
    port = env.port("api", 8000)
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
        wait_until(lambda: client.get("/health").status_code, lambda s: s == 200, description="API saudável")
        yield client


@pytest.fixture(scope="session")
def db(env):
    port = env.port("postgres", 5432)
    with psycopg.connect(
        f"host=127.0.0.1 port={port} user=app password=app dbname=app", autocommit=True
    ) as conn:
        yield conn


@pytest.fixture(scope="session")
def stub_server(env):
    port = env.port("stub", 9000)
    client = ExternalApiStub(f"http://127.0.0.1:{port}")
    wait_until(lambda: client.requests(), lambda _: True, description="stub no ar")
    yield client
    client.close()


@pytest.fixture
def stub(stub_server):
    stub_server.reset()
    yield stub_server


@pytest.fixture(autouse=False)
def clean_db(db):
    """Isolamento entre testes: esvazia as tabelas antes de cada teste que pedir esta fixture."""
    db.execute("TRUNCATE order_state_history, orders")
    yield
