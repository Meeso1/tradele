from app.container import container

container.database.add_migration(
    version=4,
    sql="""
    DROP TABLE active_trades;
    DROP TABLE historical_trades;

    CREATE TABLE active_trades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        kind TEXT NOT NULL,
        requested_price REAL NOT NULL,
        quantity REAL NOT NULL,
        requested_at TEXT NOT NULL,
        active_from_day TEXT NOT NULL,
        active_from_hour INTEGER NOT NULL
    );

    CREATE TABLE historical_trades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        kind TEXT NOT NULL,
        requested_price REAL NOT NULL,
        quantity REAL NOT NULL,
        requested_at TEXT NOT NULL,
        active_from_day TEXT NOT NULL,
        active_from_hour INTEGER NOT NULL,
        fill_price REAL,
        closed_at TEXT NOT NULL,
        closed_at_hour_day TEXT NOT NULL,
        closed_at_hour_hour INTEGER NOT NULL,
        status TEXT NOT NULL
    );
    """,
)
