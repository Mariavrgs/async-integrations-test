"""Consumidor: PENDING -> PROCESSING -> (chama gateway de pagamento externo) -> PAID | FAILED."""
import asyncio
import json
import os

import asyncpg
import httpx
from aiokafka import AIOKafkaConsumer

TOPIC = "orders.created"
PAYMENTS_URL = os.environ["PAYMENTS_URL"]


async def set_state(pool, order_id: str, cid: str, state: str) -> None:
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute("UPDATE orders SET state = $2 WHERE id = $1::uuid", order_id, state)
        await conn.execute(
            "INSERT INTO order_state_history (order_id, correlation_id, state) VALUES ($1::uuid, $2, $3)",
            order_id, cid, state,
        )


async def handle(msg, pool, http: httpx.AsyncClient) -> None:
    data = json.loads(msg.value)
    cid = dict(msg.headers)["correlation_id"].decode()
    await set_state(pool, data["order_id"], cid, "PROCESSING")
    try:
        resp = await http.post(
            f"{PAYMENTS_URL}/payments",
            json={"order_id": data["order_id"], "amount": data["amount"]},
            headers={"X-Correlation-ID": cid},
        )
        resp.raise_for_status()
        final = "PAID"
    except httpx.HTTPError:
        final = "FAILED"
    await set_state(pool, data["order_id"], cid, final)


async def main() -> None:
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=5)
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=os.environ["KAFKA_BOOTSTRAP"],
        group_id="order-processor",
        auto_offset_reset="earliest",  # evita perder mensagens publicadas antes do consumidor entrar no grupo
    )
    await consumer.start()
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            async for msg in consumer:
                await handle(msg, pool, http)
    finally:
        await consumer.stop()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
