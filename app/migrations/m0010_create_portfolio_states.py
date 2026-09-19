from app.container import container

container.database.add_migration(
    version=10,
    sql="""
    CREATE TABLE portfolio_states (
        user_id TEXT NOT NULL REFERENCES users(id),
        day TEXT NOT NULL,
        hour INTEGER NOT NULL,
        cash REAL NOT NULL,
        holdings TEXT NOT NULL,
        total_value REAL NOT NULL,
        recorded_at TEXT NOT NULL,
        PRIMARY KEY (user_id, day, hour)
    );
    """,
)
