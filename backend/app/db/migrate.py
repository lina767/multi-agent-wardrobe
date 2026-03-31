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
}

_OUTFIT_LOG_COLUMNS: dict[str, str] = {
    "item_ids_json": "TEXT",
    "context_json": "JSON",
    "worn_at": "DATETIME",
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
