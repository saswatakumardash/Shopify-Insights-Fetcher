from __future__ import annotations

import asyncio
import urllib.parse
from typing import List

import httpx

from .config import settings
from .scraper import get_insights


def _domain(url: str) -> str:
    u = urllib.parse.urlparse(url)
    return u.netloc.lower()


async def discover_competitors(website_url: str, limit: int = 5) -> list[str]:
    if not settings.bing_search_api_key:
        return []
    domain = _domain(website_url)
    q = f"competitors of {domain}"
    headers = {"Ocp-Apim-Subscription-Key": settings.bing_search_api_key}
    params = {"q": q, "count": max(10, limit * 3)}
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        r = await client.get("https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params)
        if r.status_code != 200:
            return []
        data = r.json()
    urls = []
    for item in (data.get("webPages", {}).get("value", []) if isinstance(data, dict) else []):
        u = item.get("url")
        if not u:
            continue
        d = _domain(u)
        if d and d != domain:
            urls.append(f"https://{d}")
    # de-duplicate preserve order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            out.append(u)
            seen.add(u)
        if len(out) >= limit:
            break
    return out


async def discover_and_fetch(website_url: str, limit: int = 5) -> list[dict]:
    comps = await discover_competitors(website_url, limit)
    if not comps:
        return []
    results = await asyncio.gather(*[get_insights(u) for u in comps], return_exceptions=True)
    out = []
    for url, res in zip(comps, results):
        if isinstance(res, Exception):
            out.append({"url": url, "error": str(res)})
        else:
            out.append({"url": url, "data": res})
    return out
