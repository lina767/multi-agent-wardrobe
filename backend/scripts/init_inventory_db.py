import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import init_db
from app.db.session import SessionLocal
from app.bootstrap import ensure_default_user
from app.db.migrate import ensure_inventory_schema


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        ensure_inventory_schema(db)
        user = ensure_default_user(db)
        print(f"Inventory DB initialized. default_user_id={user.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
