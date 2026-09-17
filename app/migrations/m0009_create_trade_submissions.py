from app.container import container

# Records the time of each user's most recent trade submission, so the
# once-per-day rule no longer has to be inferred from active trades
# (which cancel-only submissions would bypass). The latest timestamp is
# kept as a single row per user.
container.database.add_migration(
    version=9,
    sql="""
    CREATE TABLE trade_submissions (
        user_id TEXT PRIMARY KEY REFERENCES users(id),
        last_submitted_at TEXT NOT NULL
    );
    """,
)
