from app.container import container

container.database.add_migration(
    version=3,
    sql="""
    DROP TABLE requested_trades;
    DROP TABLE executed_trades;

    CREATE TABLE active_trades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity REAL NOT NULL,
        requested_at TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        active_from_hour INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
    );

    CREATE TABLE historical_trades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL,
        closed_at TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """,
)
