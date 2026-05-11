# Narranomics Macro Sentiment Dashboard

Standalone read-only dashboard for presenting macro narrative sentiment data to external contacts. Connects to the shared Supabase instance.

## Deploy to Render

1. Create a new GitHub repo and push this code
2. In Render, create a new Web Service pointing to the repo
3. Set environment variables:

| Variable | Value |
|---|---|
| `SUPABASE_URL` | `https://jriduffggpmmjcgwsqxj.supabase.co` |
| `SUPABASE_KEY` | (your Supabase anon key) |
| `DASH_USERNAME` | (login username for DJ contacts) |
| `DASH_PASSWORD` | (login password, comma-separated for multiple) |
| `SECRET_KEY` | (auto-generated or set manually) |

4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`
6. Free plan is fine for demo usage

## Data Source

Reads from `dj_macro_daily_summary` table in Supabase. Schema:

- `date` (DATE)
- `category` (TEXT) — Central Banks, US Economic, Equities, Key Regions
- `composite_score` (INTEGER, 0-100)
- `article_count` (INTEGER)
- `summary_text` (TEXT)

Unique constraint on `(date, category)`.

## Stack

- Flask + Gunicorn
- Chart.js for visualisation
- Supabase REST API (proxied through Flask, keys never exposed to client)
