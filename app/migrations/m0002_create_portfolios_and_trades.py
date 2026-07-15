from app.container import container

container.database.add_migration(
    version=2,
    sql="""
    CREATE TABLE portfolios (
        user_id TEXT PRIMARY KEY REFERENCES users(id),
        data TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE requested_trades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        requested_at TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
    );

    CREATE TABLE executed_trades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        executed_at TEXT NOT NULL
    );
    """,
)
