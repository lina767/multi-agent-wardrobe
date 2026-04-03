import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.bootstrap import get_default_user_id
from app.db.models import WardrobeItem
from app.db.session import SessionLocal, init_db
from app.domain.enums import ItemStatus


def parse_list(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def to_float(value: str):
    if value is None or value == "":
        return None
    return float(value)


def to_int(value: str, default: int = 1) -> int:
    if value is None or value == "":
        return default
    return int(value)


def to_datetime(value: str):
    if value is None or value == "":
        return None
    return datetime.fromisoformat(value)


def main(csv_path: str = "data/inventory_sample.csv") -> None:
    init_db()
    db = SessionLocal()
    try:
        uid = get_default_user_id(db)
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")

        inserted = 0
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = WardrobeItem(
                    user_id=uid,
                    name=row["name"],
                    category=row["category"],
                    color_families_json=parse_list(row.get("color_families", "")),
                    formality=row.get("formality", "casual"),
                    season_tags_json=parse_list(row.get("season_tags", "")),
                    is_available=to_bool(row.get("is_available", "true")),
                    status=row.get("status", ItemStatus.CLEAN.value) or ItemStatus.CLEAN.value,
                    style_tags_json=parse_list(row.get("style_tags", "")),
                    brand=row.get("brand") or None,
                    size_label=row.get("size_label") or None,
                    fit_type=row.get("fit_type", "regular") or "regular",
                    material=row.get("material") or None,
                    wear_frequency=row.get("wear_frequency", "sometimes") or "sometimes",
                    last_worn_at=to_datetime(row.get("last_worn_at", "")),
                    condition=row.get("condition", "good") or "good",
                    quantity=to_int(row.get("quantity", "1"), 1),
                    purchase_price=to_float(row.get("purchase_price", "")),
                    notes=row.get("notes") or None,
                )
                db.add(item)
                inserted += 1

        db.commit()
        print(f"Imported {inserted} inventory items from {path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
