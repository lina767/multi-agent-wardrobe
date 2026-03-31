# Database migrations (v1)

Single-user v1 uses **SQLAlchemy `create_all`** on application startup (`init_db()` in lifespan) against SQLite.

For production upgrades later, adopt Alembic and replace `create_all` with versioned revisions. Schema version is implied by deployed code; optional: add a `schema_migrations` table.

## v1 tables

- `users` — single `default_user` row
- `wardrobe_items`
- `feedback_events`
- `outfit_logs` — optional history for style agent signals
