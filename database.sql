CREATE TABLE urls (id BIGINT GENERATED ALWAYS AS IDENTITY, name VARCHAR(255) UNIQUE, created_at TIMESTAMP);