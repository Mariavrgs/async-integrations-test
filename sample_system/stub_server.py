"""Stub de API externa. Controle: POST /__control/stubs, GET /__control/requests, DELETE /__control/reset.
Qualquer outra rota responde conforme o stub cadastrado (404 se não houver) e registra a chamada."""
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
STUBS: dict[tuple[str, str], dict] = {}
RECEIVED: list[dict] = []


@app.get("/__control/requests")
async def requests_log():
    return RECEIVED


@app.post("/__control/stubs")
async def add_stub(spec: dict):
    STUBS[(spec["method"], spec["path"])] = spec
    return {"ok": True}


@app.delete("/__control/reset")
async def reset():
    STUBS.clear()
    RECEIVED.clear()
    return {"ok": True}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(path: str, request: Request):
    full = "/" + path
    body = (await request.body()).decode() or None
    RECEIVED.append(
        {"method": request.method, "path": full, "body": body, "headers": dict(request.headers)}
    )
    spec = STUBS.get((request.method, full))
    if not spec:
        return JSONResponse({"error": "stub não cadastrado"}, status_code=404)
    if spec["delay_ms"]:
        await asyncio.sleep(spec["delay_ms"] / 1000)
    return JSONResponse(spec["json"], status_code=spec["status"])
