from app.container import container

container.database.add_migration(
    version=5,
    sql="""
    CREATE TABLE market_data_cache (
        symbol TEXT NOT NULL,
        day TEXT NOT NULL,
        hour INTEGER NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        fetched_at TEXT NOT NULL,
        PRIMARY KEY (symbol, day, hour)
    );
    """,
)
