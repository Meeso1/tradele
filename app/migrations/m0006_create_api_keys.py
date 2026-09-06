from app.container import container

container.database.add_migration(
    version=6,
    sql="""
    ALTER TABLE users ADD COLUMN is_service_account INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE users ADD COLUMN allowed_auth_methods TEXT NOT NULL DEFAULT '["token","api_key"]';

    CREATE TABLE api_keys (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL,
        created_by_key TEXT,
        created_at TEXT NOT NULL,
        deactivated_at TEXT
    );

    CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
    """,
)
