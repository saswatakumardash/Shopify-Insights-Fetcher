# Shopify Store Insights-Fetcher (FastAPI)

A Python FastAPI service that fetches insights from a given Shopify storefront URL (without using the official Shopify API) and returns a well-structured JSON Brand Context.

It collects:
- Whole product catalog (via /products.json with pagination when available)
- Hero products (from the homepage)
- Policies (Privacy, Refund/Return, Terms, Shipping)
- FAQs (various patterns, including accordions and article pages)
- Social handles
- Contact details
- Brand about text
- Important links (order tracking, contact us, blog)

Bonus-ready:
- Optional SQL persistence via SQLAlchemy (MySQL recommended via DATABASE_URL)

## Quick start

### Prerequisites
- Python 3.10+

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open UI: http://localhost:8000/
Open docs: http://localhost:8000/docs

### Usage

- GET /health -> health check
- POST /api/insights -> JSON body: `{ "website_url": "https://examplestore.com" }`

Example curl:

```bash
curl -X POST http://localhost:8000/api/insights \
  -H 'Content-Type: application/json' \
  -d '{"website_url":"https://memy.co.in"}'
```

### Environment

- `REQUEST_TIMEOUT_SECONDS` (default: 12)
- `MAX_PAGES_TO_SCAN` (default: 3) for secondary FAQ/article crawling
- `USER_AGENT` (default set)
- `DATABASE_URL` (optional; e.g., `mysql+pymysql://user:pass@localhost:3306/shopify_insights`)
- `PERSIST_ENABLED` (optional; `true`/`false`) enables DB persistence if `DATABASE_URL` provided

### Notes
- If /products.json is blocked by a store, the service best-effort parses product cards on the site. Product coverage may be partial.
- 401 is returned if the website is not found or unreachable (per assignment requirement). 500 for internal errors.

## Project structure

```
app/
  main.py           # FastAPI app & routes
  schemas.py        # Pydantic models
  scraper.py        # Shopify-oriented scraping logic
  utils.py          # Helpers (URL normalization, fetchers)
  config.py         # Settings
  persistence/
    __init__.py
    db.py           # SQLAlchemy engine/session (optional)
    models.py       # ORM models (optional)
requirements.txt
README.md
site/
  index.html        # Static UI that can be hosted anywhere; configure API base in UI
```

## Testing

```bash
pytest -q
```

Includes a few unit tests for URL normalization and model validation (network-free).
GitHub Actions CI runs tests on pushes/PRs to main.

## MySQL persistence (bonus)

- Install MySQL server and create a database.
- Set `DATABASE_URL` to a valid SQLAlchemy URL, e.g. `mysql+pymysql://user:pass@localhost:3306/shopify_insights`.
- Set `PERSIST_ENABLED=true` to enable writes.

Migration is not required for this demo; models use `create_all`.

## Troubleshooting

- Some Shopify stores restrict their JSON product feeds. The service still returns partial insights by parsing HTML.
- If a site uses heavy JS, consider enabling the optional Playwright plugin in future work.

## Deployment

### Docker

```bash
docker build -t shopify-insights .
docker run -p 8000:8000 shopify-insights
```

Open http://localhost:8000/

### Docker Compose (with MySQL)

```bash
docker compose up --build
```

API: http://localhost:8000/ (persists to MySQL at localhost:3306)

### Render/Heroku-like

- Use the provided `Procfile`.
- Set environment variables as needed (DATABASE_URL, PERSIST_ENABLED).

### Static hosting for UI (optional)

The current UI is rendered by FastAPI with Jinja2. For a pure static site, copy `app/templates/index.html` as `index.html` and replace `endpoint` URLs with your deployed API base.
Alternatively, use the ready-made static UI at `site/index.html` and set the API base from the UI (stored in localStorage).

## License

MIT
