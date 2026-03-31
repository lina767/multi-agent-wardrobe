# Deployment: Vercel + Railway

## 1) Railway (Backend API)

Deploy the `backend/` folder on Railway.

### Start command

Railway uses `backend/Procfile`:

`web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

### Required env vars

- `WARDROBE_DATABASE_URL`  
  Example with Railway Postgres:
  `postgresql+psycopg://...`
- `WARDROBE_CORS_ORIGINS`  
  JSON array, e.g.:
  `["https://your-frontend.vercel.app","http://localhost:3000"]`
- `WARDROBE_LOG_LEVEL` (optional), e.g. `INFO`

### Supabase Storage (recommended for images)

Create a public bucket in Supabase, e.g. `wardrobe-images`, then set:

- `WARDROBE_STORAGE_BACKEND=supabase`
- `WARDROBE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co`
- `WARDROBE_SUPABASE_SERVICE_KEY=...` (service role key)
- `WARDROBE_SUPABASE_BUCKET=wardrobe-images`

If these vars are not set, backend falls back to local file storage.

## 2) Vercel (Frontend)

Deploy the `frontend/` folder as a static project.

Before deploy, set API base in `frontend/index.html` by adding this small script before the main `<script>` block:

```html
<script>
  window.__API_BASE__ = "https://YOUR-RAILWAY-BACKEND.up.railway.app";
</script>
```

Then deploy:

- Root directory: `frontend`
- Build command: none
- Output directory: `.`

## 3) Local sanity checks

- Backend local: `http://127.0.0.1:8000`
- Local frontend via backend: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`
