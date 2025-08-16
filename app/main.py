from __future__ import annotations

import asyncio
import contextlib

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .competitors import discover_and_fetch
from .config import settings
from .schemas import InsightsRequest, InsightsResponse
from .scraper import get_insights

try:
    from .persistence.db import Base, get_engine
    from .persistence.save import save_brand_context
    _persistence_available = True
except Exception:  # pragma: no cover - optional
    _persistence_available = False

app = FastAPI(title="Shopify Insights-Fetcher", default_response_class=ORJSONResponse)
templates = Jinja2Templates(directory="app/templates")
app.mount("/assets", StaticFiles(directory="site/assets"), name="assets")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index_standalone.html", {"request": request})


@app.post("/api/insights", response_model=InsightsResponse)
async def insights(req: InsightsRequest):
    try:
        ctx = await get_insights(req.website_url)
        # optional persistence
        if settings.persist_enabled and settings.database_url and _persistence_available:
            with contextlib.suppress(Exception):
                await save_brand_context(ctx)
        return {"data": ctx}
    except FileNotFoundError as e:
        raise HTTPException(status_code=401, detail="website not found or unreachable") from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.on_event("startup")
async def _startup():  # pragma: no cover - side-effectful
    if settings.persist_enabled and settings.database_url and _persistence_available:
        # initialize tables
        engine = get_engine()
        Base.metadata.create_all(bind=engine)


@app.post("/api/insights/competitors", response_model=dict)
async def insights_competitors(payload: dict):
    """Bonus: Accepts { website_url: str, competitor_urls?: [str], auto_discover?: bool, limit?: int }
    - If competitor_urls provided, uses them.
    - Else if auto_discover true and Bing or Gemini key set, discovers via Bing/Gemini and fetches.
    - Else returns empty with a note.
    """
    website_url = payload.get("website_url")
    competitor_urls = payload.get("competitor_urls") or []
    auto_discover = bool(payload.get("auto_discover"))
    limit = int(payload.get("limit") or 5)
    if not website_url:
        raise HTTPException(status_code=422, detail="website_url required")

    results = []
    if not competitor_urls:
        if auto_discover and (settings.bing_search_api_key or settings.gemini_api_key):
            results = await discover_and_fetch(website_url, limit=limit)
            return {"website_url": website_url, "competitors": results, "discovered": True}
        return {"website_url": website_url, "competitors": results, "note": "Provide competitor_urls or set auto_discover=true with Bing or Gemini key."}

    # fetch in parallel
    tasks = [get_insights(u) for u in competitor_urls]
    try:
        contexts = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:  # defensive
        raise HTTPException(status_code=500, detail=str(e)) from e

    for url, ctx in zip(competitor_urls, contexts, strict=True):
        if isinstance(ctx, Exception):
            results.append({"url": url, "error": str(ctx)})
        else:
            results.append({"url": url, "data": ctx})

    return {"website_url": website_url, "competitors": results}
