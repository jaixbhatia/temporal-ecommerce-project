-- Initial schema migration
CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR PRIMARY KEY,
    state VARCHAR NOT NULL,
    address_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR PRIMARY KEY,
    order_id VARCHAR NOT NULL REFERENCES orders(id),
    status VARCHAR NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR NOT NULL REFERENCES orders(id),
    type VARCHAR NOT NULL,
    payload_json JSONB,
    ts TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance, if we scale up later
-- CREATE INDEX IF NOT EXISTS idx_orders_state ON orders(state);
-- CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
-- CREATE INDEX IF NOT EXISTS idx_events_order_id ON events(order_id);
-- CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
