CREATE TABLE IF NOT EXISTS users (
    id serial PRIMARY KEY NOT NULL,
    user_id BIGINT UNIQUE NOT NULL,
    "order" JSONB DEFAULT '[]'::jsonb,
    cost INT DEFAULT 0,
    datetime TIMESTAMP DEFAULT NOW() NOT NULL
);
