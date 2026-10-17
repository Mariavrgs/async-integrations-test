"""Cliente do serviço de stub (sample_system/stub_server.py), que roda dentro do Compose e
substitui APIs externas de terceiros: respostas controladas e chamadas registradas."""
import httpx


class ExternalApiStub:
    def __init__(self, base_url: str):
        self._client = httpx.Client(base_url=base_url, timeout=10)

    def reset(self) -> None:
        self._client.delete("/__control/reset").raise_for_status()

    def stub(self, method: str, path: str, *, status: int = 200, json: dict | None = None, delay_ms: int = 0):
        spec = {"method": method.upper(), "path": path, "status": status, "json": json or {}, "delay_ms": delay_ms}
        self._client.post("/__control/stubs", json=spec).raise_for_status()

    def requests(self, path: str | None = None) -> list[dict]:
        data = self._client.get("/__control/requests").json()
        return [r for r in data if path is None or r["path"] == path]

    def close(self) -> None:
        self._client.close()
