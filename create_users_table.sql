CREATE TABLE IF NOT EXISTS users (
    id serial PRIMARY KEY NOT NULL,
    user_id BIGINT UNIQUE NOT NULL,
    user_url TEXT UNIQUE,
    "order" JSONB DEFAULT '[]'::jsonb,
    cost INT DEFAULT 0,
    is_user_admin BOOL DEFAULT FALSE,
    is_order_accepted BOOL DEFAULT TRUE,
    status INT DEFAULT 1,
    order_id INT DEFAULT -1
);
