from __future__ import annotations

import re
import urllib.parse
from typing import Iterable, Optional

from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\-()\s]{6,}\d")


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    normalized = parsed._replace(fragment="").geturl()
    return normalized


def absolutize(base: str, href: str | None) -> Optional[str]:
    if not href:
        return None
    return urllib.parse.urljoin(base, href)


def text_of(el) -> str:
    if not el:
        return ""
    return " ".join(el.get_text(" ", strip=True).split())


def find_emails(text: str) -> list[str]:
    return sorted(set(EMAIL_RE.findall(text or "")))


def find_phones(text: str) -> list[str]:
    return sorted(set(PHONE_RE.findall(text or "")))


def find_social_links(soup: BeautifulSoup, base: str) -> dict[str, str]:
    socials = {}
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        label = text_of(a).lower()
        u = absolutize(base, href)
        if not u:
            continue
        host = urllib.parse.urlparse(u).netloc.lower()
        if any(k in host for k in ["instagram.com", "instagr.am"]):
            socials.setdefault("instagram", u)
        elif "facebook.com" in host:
            socials.setdefault("facebook", u)
        elif "tiktok.com" in host:
            socials.setdefault("tiktok", u)
        elif "twitter.com" in host or "x.com" in host:
            socials.setdefault("twitter", u)
        elif "youtube.com" in host or "youtu.be" in host:
            socials.setdefault("youtube", u)
        elif "pinterest.com" in host:
            socials.setdefault("pinterest", u)
        elif "linkedin.com" in host:
            socials.setdefault("linkedin", u)
        elif "snapchat.com" in host:
            socials.setdefault("snapchat", u)
    return socials


def unique(seq: Iterable[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for s in seq:
        if s and s not in seen:
            out.append(s)
            seen.add(s)
    return out
