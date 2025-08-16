from __future__ import annotations

import asyncio
import urllib.parse

import httpx

from .config import settings
from .scraper import get_insights


def _domain(url: str) -> str:
    u = urllib.parse.urlparse(url)
    return u.netloc.lower()


async def discover_competitors(website_url: str, limit: int = 5) -> list[str]:
    # Prefer Bing when key is present; else try Gemini if configured
    if settings.bing_search_api_key:
        return await _discover_bing(website_url, limit)
    if settings.gemini_api_key:
        return await _discover_gemini(website_url, limit)
    return []

async def _discover_bing(website_url: str, limit: int = 5) -> list[str]:
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


async def _discover_gemini(website_url: str, limit: int = 5) -> list[str]:
    # Use Gemini to suggest competitor domains. This uses a simple prompt and expects a JSON list response.
    # We avoid adding a heavy SDK; call the REST API directly.
    if not settings.gemini_api_key:
        return []
    import json as _json
    domain = _domain(website_url)
    prompt = (
        "Return a JSON array of up to " + str(limit) +
        " Shopify or D2C competitor homepage URLs (https://...) for the brand at domain: " + domain +
        ". Only output the JSON array, no extra text."
    )
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": settings.gemini_api_key}
    body = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        r = await client.post(endpoint, headers=headers, params=params, json=body)
        if r.status_code != 200:
            return []
        data = r.json()
    # Parse text candidates
    text = ""
    try:
        candidates = data.get("candidates", [])
        for c in candidates:
            parts = c.get("content", {}).get("parts", [])
            for p in parts:
                if p.get("text"):
                    text += p["text"]
    except Exception:
        text = ""
    urls: list[str] = []
    try:
        arr = _json.loads(text)
        if isinstance(arr, list):
            urls = [str(u) for u in arr if isinstance(u, str)]
    except Exception:
        urls = []
    # clean & de-dup
    cleaned = []
    seen = set()
    for u in urls:
        d = _domain(u)
        if not d or d == domain or u in seen:
            continue
        cleaned.append("https://" + d if not u.startswith("http") else u)
        seen.add(u)
        if len(cleaned) >= limit:
            break
    return cleaned


async def discover_and_fetch(website_url: str, limit: int = 5) -> list[dict]:
    comps = await discover_competitors(website_url, limit)
    if not comps:
        return []
    results = await asyncio.gather(*[get_insights(u) for u in comps], return_exceptions=True)
    out = []
    for url, res in zip(comps, results, strict=True):
        if isinstance(res, Exception):
            out.append({"url": url, "error": str(res)})
        else:
            out.append({"url": url, "data": res})
    return out
