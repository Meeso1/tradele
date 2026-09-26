from app.container import container

container.database.add_migration(
    version=11,
    sql="""
    CREATE TABLE tutorial_completions (
        user_id TEXT PRIMARY KEY,
        completed_at TEXT NOT NULL
    );
    """,
)
