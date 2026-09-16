from app.container import container

# Value-based orders have no quantity, and quantity-based orders have no
# value, so `quantity` must become nullable and a nullable `value` column
# is added. SQLite can't alter a column's constraints in place, so the
# tables are rebuilt (same approach as m0007).
container.database.add_migration(
    version=8,
    sql="""
    CREATE TABLE active_trades_new (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        kind TEXT NOT NULL,
        requested_price REAL,
        quantity REAL,
        value REAL,
        requested_at TEXT NOT NULL,
        active_from_day TEXT NOT NULL,
        active_from_hour INTEGER NOT NULL
    );
    INSERT INTO active_trades_new
        (id, user_id, symbol, kind, requested_price, quantity, requested_at, active_from_day, active_from_hour)
    SELECT id, user_id, symbol, kind, requested_price, quantity, requested_at, active_from_day, active_from_hour
    FROM active_trades;
    DROP TABLE active_trades;
    ALTER TABLE active_trades_new RENAME TO active_trades;

    CREATE TABLE historical_trades_new (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        symbol TEXT NOT NULL,
        kind TEXT NOT NULL,
        requested_price REAL,
        quantity REAL,
        value REAL,
        requested_at TEXT NOT NULL,
        active_from_day TEXT NOT NULL,
        active_from_hour INTEGER NOT NULL,
        fill_price REAL,
        closed_at TEXT NOT NULL,
        closed_at_hour_day TEXT NOT NULL,
        closed_at_hour_hour INTEGER NOT NULL,
        status TEXT NOT NULL
    );
    INSERT INTO historical_trades_new
        (id, user_id, symbol, kind, requested_price, quantity, requested_at, active_from_day, active_from_hour, fill_price, closed_at, closed_at_hour_day, closed_at_hour_hour, status)
    SELECT id, user_id, symbol, kind, requested_price, quantity, requested_at, active_from_day, active_from_hour, fill_price, closed_at, closed_at_hour_day, closed_at_hour_hour, status
    FROM historical_trades;
    DROP TABLE historical_trades;
    ALTER TABLE historical_trades_new RENAME TO historical_trades;
    """,
)
