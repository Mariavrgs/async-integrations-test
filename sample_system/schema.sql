CREATE TABLE orders (
    id             UUID PRIMARY KEY,
    correlation_id TEXT NOT NULL,
    amount         NUMERIC(12,2) NOT NULL,
    state          TEXT NOT NULL
);

-- Cada mudança de estado vira uma linha: é isso que o polling do teste observa.
CREATE TABLE order_state_history (
    id             BIGSERIAL PRIMARY KEY,
    order_id       UUID NOT NULL,
    correlation_id TEXT NOT NULL,
    state          TEXT NOT NULL,
    at             TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ON order_state_history (correlation_id, id);
