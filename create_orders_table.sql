CREATE TABLE IF NOT EXISTS orders (
    id serial PRIMARY KEY NOT NULL,
    order_name TEXT UNIQUE,
    "order" JSONB DEFAULT '[]'::jsonb,
    cost INT DEFAULT 0,
    order_status INT DEFAULT -1,
    address TEXT,
    full_order_name TEXT
);