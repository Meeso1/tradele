from app.container import container

container.database.add_migration(
    version=1,
    sql="""
    CREATE TABLE users (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL
    );
    """,
)
