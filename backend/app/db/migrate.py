from sqlalchemy import text
from sqlalchemy.orm import Session


_INVENTORY_COLUMNS: dict[str, str] = {
    "brand": "TEXT",
    "size_label": "TEXT",
    "material": "TEXT",
    "quantity": "INTEGER DEFAULT 1",
    "purchase_price": "REAL",
    "notes": "TEXT",
    "image_path": "TEXT",
    "weather_tags_json": "JSON",
    "status": "TEXT DEFAULT 'clean'",
    "processed_image_path": "TEXT",
    "vision_status": "TEXT DEFAULT 'pending'",
    "vision_error": "TEXT",
    "dominant_colors_json": "JSON",
}

_OUTFIT_LOG_COLUMNS: dict[str, str] = {
    "item_ids_json": "TEXT",
    "context_json": "JSON",
    "worn_at": "DATETIME",
}

_USER_COLUMNS: dict[str, str] = {
    "supabase_user_id": "TEXT",
    "email": "TEXT",
    "email_verified_at": "DATETIME",
    "last_login_at": "DATETIME",
    "is_active": "BOOLEAN DEFAULT 1",
}


def _existing_columns(db: Session, table: str) -> set[str]:
    rows = db.execute(text(f"PRAGMA table_info({table})")).all()
    return {str(r[1]) for r in rows}


def ensure_inventory_schema(db: Session) -> None:
    cols = _existing_columns(db, "wardrobe_items")
    for col, sql_type in _INVENTORY_COLUMNS.items():
        if col in cols:
            continue
        db.execute(text(f"ALTER TABLE wardrobe_items ADD COLUMN {col} {sql_type}"))
    db.execute(text("UPDATE wardrobe_items SET status = 'clean' WHERE status IS NULL OR status = ''"))
    db.execute(text("UPDATE wardrobe_items SET vision_status = 'pending' WHERE vision_status IS NULL OR vision_status = ''"))
    db.commit()


def ensure_user_schema(db: Session) -> None:
    cols = _existing_columns(db, "users")
    for col, sql_type in _USER_COLUMNS.items():
        if col in cols:
            continue
        db.execute(text(f"ALTER TABLE users ADD COLUMN {col} {sql_type}"))
    db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_supabase_user_id_unique ON users(supabase_user_id)"))
    db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_unique ON users(email)"))
    db.commit()


def ensure_agent_schema(db: Session) -> None:
    try:
        cols = _existing_columns(db, "outfit_logs")
    except Exception:
        cols = set()
    if cols:
        for col, sql_type in _OUTFIT_LOG_COLUMNS.items():
            if col in cols:
                continue
            db.execute(text(f"ALTER TABLE outfit_logs ADD COLUMN {col} {sql_type}"))

        # Backfill from older schema names when present.
        if "item_ids_json" in _OUTFIT_LOG_COLUMNS and "item_ids_json" not in cols and "item_ids" in cols:
            db.execute(text("UPDATE outfit_logs SET item_ids_json = item_ids WHERE item_ids_json IS NULL"))
        if "worn_at" in _OUTFIT_LOG_COLUMNS and "worn_at" not in cols and "created_at" in cols:
            db.execute(text("UPDATE outfit_logs SET worn_at = created_at WHERE worn_at IS NULL"))

        legacy_context_cols = {"occasion", "mood", "weather_temp", "weather_condition"}
        if "context_json" in _OUTFIT_LOG_COLUMNS and "context_json" not in cols and legacy_context_cols.issubset(cols):
            db.execute(
                text(
                    """
                    UPDATE outfit_logs
                    SET context_json = json_object(
                        'occasion', occasion,
                        'mood', mood,
                        'weather_temp', weather_temp,
                        'weather_condition', weather_condition
                    )
                    WHERE context_json IS NULL
                    """
                )
            )
    db.commit()


def ensure_temporal_schema(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                schema_version TEXT DEFAULT 'v1',
                life_phase TEXT,
                role_transition TEXT,
                body_change_note TEXT,
                fit_confidence REAL,
                style_goals_json JSON,
                context_weights_json JSON,
                effective_from DATETIME,
                created_at DATETIME
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS color_feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source TEXT DEFAULT 'user',
                predicted_season TEXT NOT NULL,
                predicted_undertone TEXT,
                predicted_contrast_level TEXT,
                predicted_confidence REAL,
                corrected_season TEXT,
                corrected_undertone TEXT,
                corrected_contrast_level TEXT,
                note TEXT,
                created_at DATETIME
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_state_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                state_key TEXT DEFAULT 'current',
                features_json JSON,
                source_signal_ids_json JSON,
                confidence REAL DEFAULT 0.5,
                created_at DATETIME
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS preference_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                window_days INTEGER DEFAULT 30,
                embedding_json JSON,
                stability_score REAL DEFAULT 0.0,
                updated_at DATETIME
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS style_signal_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                signal_type TEXT NOT NULL,
                source TEXT DEFAULT 'system',
                payload_json JSON,
                weight REAL DEFAULT 0.5,
                occurred_at DATETIME
            )
            """
        )
    )
    # Backfill a baseline state row for users without history.
    db.execute(
        text(
            """
            INSERT INTO user_state_timeline (user_id, state_key, features_json, source_signal_ids_json, confidence, created_at)
            SELECT u.id, 'baseline', json('{}'), json('[]'), 0.3, CURRENT_TIMESTAMP
            FROM users u
            WHERE NOT EXISTS (
                SELECT 1 FROM user_state_timeline s WHERE s.user_id = u.id
            )
            """
        )
    )
    db.commit()
