CREATE TABLE urls (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(255) UNIQUE,
    created_at TIMESTAMP
);
CREATE TABLE url_checks (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url_id BIGINT REFERENCES urls(id),
    status_code VARCHAR(255),
    h1 text,
    title text,
    description text,
    created_at timestamp
);

SELECT url_checks.created_at, url_checks.status_code FROM url_checks
INNER JOIN urls on urls.id=url_checks.url_id
ORDER BY url_checks.url_id DESC
LIMIT 1;