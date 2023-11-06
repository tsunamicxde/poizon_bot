CREATE TABLE IF NOT EXISTS paid_orders (
    id serial PRIMARY KEY NOT NULL,
    order_name TEXT,
    "order" JSONB DEFAULT '[]'::jsonb,
    cost INT DEFAULT 0,
    address TEXT,
    full_order_name TEXT
);