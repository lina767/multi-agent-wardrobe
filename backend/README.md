# Fashion Multi-Agent API (Single-User v1)

FastAPI backend with **rule-based** specialist agents (Color, Style, Wardrobe, Context), an **Orchestrator**, and an **evidence layer** tying adjustments to documented research citations.

## Quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API base: `http://127.0.0.1:8000/v1`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Frontend (Inventory UI): `http://127.0.0.1:8000/`
- SQLite file: `backend/data/wardrobe.db` (created automatically)

No authentication — a single local user `default_user` is bootstrapped on startup.

## Main endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | Liveness |
| GET/POST | `/v1/wardrobe/items` | List / create wardrobe items |
| PATCH/DELETE | `/v1/wardrobe/items/{id}` | Update / delete |
| POST | `/v1/wardrobe/items/{id}/image` | Bild für Item hochladen |
| POST | `/v1/recommendations` | Top-3 outfits + agent + evidence trace |
| POST/GET | `/v1/feedback` | Store / list feedback |

## Tests

```bash
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing
```

Tests use **in-memory SQLite** with `StaticPool` so Lifespan + request sessions share one database.

## Configuration

Environment variables (prefix `WARDROBE_`):

- `WARDROBE_DATABASE_URL` — override DB URL (default: SQLite file under `backend/data/`)
- `WARDROBE_CORS_ORIGINS` — JSON list (optional; defaults include localhost)
- `WARDROBE_LOG_LEVEL` — e.g. `INFO`, `DEBUG`
- `WARDROBE_STORAGE_BACKEND` — `local` (default) or `supabase`
- `WARDROBE_SUPABASE_URL` — project URL, e.g. `https://xyzcompany.supabase.co`
- `WARDROBE_SUPABASE_SERVICE_KEY` — service role key for upload/delete
- `WARDROBE_SUPABASE_BUCKET` — storage bucket name (default: `wardrobe-images`)

## Inventory Datenbank aufsetzen

```bash
cd backend
source .venv/bin/activate
python scripts/init_inventory_db.py
python scripts/import_inventory_csv.py
```

- Beispiel-Importdatei: `backend/data/inventory_sample.csv`
- Import unterstützt die Felder: `name`, `category`, `color_families`, `formality`, `season_tags`, `is_available`, `style_tags`, `brand`, `size_label`, `material`, `quantity`, `purchase_price`, `notes`
