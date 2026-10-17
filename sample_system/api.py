"""API do sistema de exemplo: cria o pedido (PENDING) e publica no Kafka com correlation_id."""
import json
import os
import uuid
from contextlib import asynccontextmanager

import asyncpg
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, Header, Request
from pydantic import BaseModel

TOPIC = "orders.created"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=5)
    app.state.producer = AIOKafkaProducer(bootstrap_servers=os.environ["KAFKA_BOOTSTRAP"])
    await app.state.producer.start()
    try:
        yield
    finally:
        await app.state.producer.stop()
        await app.state.pool.close()


app = FastAPI(lifespan=lifespan)


class OrderIn(BaseModel):
    amount: float


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/orders", status_code=202)
async def create_order(order: OrderIn, request: Request, x_correlation_id: str | None = Header(None)):
    cid = x_correlation_id or str(uuid.uuid4())
    order_id = uuid.uuid4()
    async with request.app.state.pool.acquire() as conn, conn.transaction():
        await conn.execute(
            "INSERT INTO orders (id, correlation_id, amount, state) VALUES ($1, $2, $3, 'PENDING')",
            order_id, cid, order.amount,
        )
        await conn.execute(
            "INSERT INTO order_state_history (order_id, correlation_id, state) VALUES ($1, $2, 'PENDING')",
            order_id, cid,
        )
    await request.app.state.producer.send_and_wait(
        TOPIC,
        json.dumps({"order_id": str(order_id), "amount": order.amount}).encode(),
        headers=[("correlation_id", cid.encode())],
    )
    return {"order_id": str(order_id), "correlation_id": cid}
