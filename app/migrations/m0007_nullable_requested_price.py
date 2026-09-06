from app.container import container

# Market orders have no requested price, so the column must be nullable.
# SQLite can't alter a column's constraints in place, so the tables are rebuilt.
container.database.add_migration(
    version=7,
    sql="""
    CREATE TABLE active_trades_new (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        kind TEXT NOT NULL,
        requested_price REAL,
        quantity REAL NOT NULL,
        requested_at TEXT NOT NULL,
        active_from_day TEXT NOT NULL,
        active_from_hour INTEGER NOT NULL
    );
    INSERT INTO active_trades_new SELECT * FROM active_trades;
    DROP TABLE active_trades;
    ALTER TABLE active_trades_new RENAME TO active_trades;

    CREATE TABLE historical_trades_new (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        kind TEXT NOT NULL,
        requested_price REAL,
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
    INSERT INTO historical_trades_new SELECT * FROM historical_trades;
    DROP TABLE historical_trades;
    ALTER TABLE historical_trades_new RENAME TO historical_trades;
    """,
)
