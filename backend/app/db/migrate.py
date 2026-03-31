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
    "item_ids": "JSON",
    "occasion": "TEXT",
    "mood": "TEXT",
    "weather_temp": "REAL",
    "weather_condition": "TEXT",
    "created_at": "DATETIME",
    "rating": "INTEGER",
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
    db.commit()
