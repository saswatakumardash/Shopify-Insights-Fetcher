from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .config import settings
from .schemas import BrandContext, ContactInfo, FAQItem, Link, Policy, Product
from .utils import (
    absolutize,
    find_emails,
    find_phones,
    find_social_links,
    normalize_url,
    text_of,
    unique,
)


@dataclass
class FetchResult:
    url: str
    status: int
    text: str


class ShopifyScraper:
    def __init__(self, base_url: str):
        self.base_url = normalize_url(base_url)
        self.root = self.base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/json,application/xhtml+xml",
            },
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    async def fetch(self, path_or_url: str) -> FetchResult:
        url = path_or_url if path_or_url.startswith("http") else urljoin(self.root + "/", path_or_url.lstrip("/"))
        try:
            r = await self.client.get(url)
            return FetchResult(url=url, status=r.status_code, text=r.text or "")
        except httpx.RequestError:
            return FetchResult(url=url, status=0, text="")

    async def get_home(self) -> BeautifulSoup | None:
        res = await self.fetch(self.root)
        if res.status != 200:
            return None
        return BeautifulSoup(res.text, "lxml")

    async def get_products_json(self) -> list[Product]:
        products: list[Product] = []
        page = 1
        while True:
            path = f"/products.json?limit=250&page={page}"
            res = await self.fetch(path)
            if res.status != 200:
                break
            try:
                data = json.loads(res.text)
            except json.JSONDecodeError:
                break
            raw_products = data.get("products") or []
            if not raw_products:
                break
            for p in raw_products:
                prod = Product(
                    id=p.get("id"),
                    handle=p.get("handle"),
                    title=p.get("title") or p.get("handle") or "",
                    url=urljoin(self.root + "/", f"/products/{p.get('handle')}") if p.get("handle") else None,
                    images=[img.get("src") for img in (p.get("images") or []) if img.get("src")],
                    tags=unique((p.get("tags") or "").split(", ") if isinstance(p.get("tags"), str) else (p.get("tags") or [])),
                    vendor=p.get("vendor"),
                    product_type=p.get("product_type"),
                    available=None,
                )
                # try to extract price from variants
                variants = p.get("variants") or []
                if variants:
                    try:
                        price = float(variants[0].get("price")) if variants[0].get("price") is not None else None
                    except (ValueError, TypeError):
                        price = None
                    prod.price = price
                products.append(prod)
            page += 1
        return products

    async def parse_products_from_html(self, soup: BeautifulSoup) -> list[Product]:
        products: list[Product] = []
        selectors = [
            ".grid-product", ".product-card", ".product-item", ".product-grid-item",
            "[data-product]", "article.product"
        ]
        for sel in selectors:
            for card in soup.select(sel):
                title_el = card.select_one(".product-title, .card__heading, .grid-product__title, a[title]")
                title = text_of(title_el)
                url = title_el.get("href") if title_el else (card.get("href") if card.has_attr("href") else None)
                url = absolutize(self.root, url)
                if not title and not url:
                    continue
                img_el = card.select_one("img")
                img = img_el.get("src") or img_el.get("data-src") if img_el else None
                products.append(Product(title=title or url or "", url=img and url, images=[img] if img else []))
        # de-duplicate by url/title
        seen = set()
        deduped = []
        for p in products:
            key = (p.url or "", p.title)
            if key not in seen:
                seen.add(key)
                deduped.append(p)
        return deduped

    async def extract_hero_products(self, soup: BeautifulSoup) -> list[str]:
        hero = []
        for a in soup.select("section a[href*='/products/'], .hero a[href*='/products/']"):
            href = absolutize(self.root, a.get("href"))
            if href:
                hero.append(href)
        return unique(hero)

    async def extract_policies(self, soup: BeautifulSoup) -> list[Policy]:
        policies: list[Policy] = []
        keywords = [
            ("Privacy Policy", "privacy"),
            ("Refund Policy", "refund"),
            ("Return Policy", "return"),
            ("Shipping Policy", "shipping"),
            ("Terms of Service", "terms"),
        ]
        links = soup.select("a[href]")
        for title, key in keywords:
            candidate = None
            for a in links:
                href = a.get("href", "").lower()
                text = text_of(a)
                if key in href or key in text.lower():
                    candidate = a
                    break
            if candidate:
                url = absolutize(self.root, candidate.get("href"))
                if url:
                    page = await self.fetch(url)
                    content_excerpt = None
                    if page.status == 200:
                        page_soup = BeautifulSoup(page.text, "lxml")
                        content = text_of(page_soup.select_one("main, .rte, .content, article")) or text_of(page_soup)
                        content_excerpt = content[:400]
                    policies.append(Policy(name=title, url=url, content_excerpt=content_excerpt))
        return policies

    async def extract_faqs(self, soup: BeautifulSoup) -> list[FAQItem]:
        faqs: list[FAQItem] = []
        # Common FAQ patterns: details/summary, accordions, headings followed by content
        for d in soup.select("details"):  # native disclosure
            q = text_of(d.select_one("summary"))
            a = text_of(d)
            if q:
                faqs.append(FAQItem(question=q, answer=a))
        # accordions
        for qel in soup.select(".accordion__title, .faq__question, h3, h4"):
            q = text_of(qel)
            if not q or len(q) > 160:
                continue
            # answer might be the next sibling or within parent
            ans_candidates = [qel.find_next_sibling(), qel.parent]
            answer = None
            for c in ans_candidates:
                if not c:
                    continue
                t = text_of(c)
                if t and len(t) > len(q) + 10:
                    answer = t
                    break
            if q and answer:
                faqs.append(FAQItem(question=q, answer=answer))
        # If few found, search potential FAQ pages
        if len(faqs) < 3:
            more_links = []
            for a in soup.select("a[href]"):
                href = a.get("href", "").lower()
                if any(k in href for k in ["faq", "help", "support"]):
                    u = absolutize(self.root, a.get("href"))
                    if u:
                        more_links.append(u)
            more_links = unique(more_links)[: settings.max_pages_to_scan]
            for url in more_links:
                page = await self.fetch(url)
                if page.status != 200:
                    continue
                psoup = BeautifulSoup(page.text, "lxml")
                faqs.extend(await self.extract_faqs(psoup))
        # dedupe by question
        final: dict[str, FAQItem] = {}
        for f in faqs:
            if f.question not in final:
                final[f.question] = f
        return list(final.values())

    async def extract_about_and_links(self, soup: BeautifulSoup) -> tuple[str | None, list[Link]]:
        about = None
        links: list[Link] = []
        # Try footer and about page
        for a in soup.select("a[href]"):
            text = text_of(a)
            href = a.get("href", "")
            low = text.lower()
            if any(k in low for k in ["about", "our story", "story"]) and len(text) <= 30:
                u = absolutize(self.root, href)
                if u:
                    links.append(Link(title=text, url=u))
                    page = await self.fetch(u)
                    if page.status == 200 and not about:
                        psoup = BeautifulSoup(page.text, "lxml")
                        about = text_of(psoup.select_one("main, article, .rte, .content"))[:800] or None
        # Important links
        important_keys = {
            "Order Tracking": ["track", "order status"],
            "Contact Us": ["contact"],
            "Blog": ["blog"],
        }
        for a in soup.select("a[href]"):
            text = text_of(a)
            href = a.get("href", "")
            low = text.lower()
            for title, keys in important_keys.items():
                if any(k in low or k in href.lower() for k in keys):
                    u = absolutize(self.root, href)
                    if u:
                        links.append(Link(title=title if title != "Contact Us" else text or title, url=u))
        # de-duplicate by url
        uniq: dict[str, Link] = {}
        for link in links:
            if isinstance(link.url, str) and link.url not in uniq:
                uniq[link.url] = link
        return about, list(uniq.values())

    async def extract_contact(self, soup: BeautifulSoup) -> ContactInfo:
        text = text_of(soup)
        emails = find_emails(text)
        phones = find_phones(text)
        # try to find address or contact page
        contact_page = None
        for a in soup.select("a[href]"):
            href = a.get("href", "").lower()
            if any(k in href for k in ["contact", "support"]):
                contact_page = absolutize(self.root, a.get("href"))
                break
        return ContactInfo(emails=emails, phones=phones, address=None, contact_page_url=contact_page)

    async def scrape(self) -> BrandContext:
        errors: list[str] = []
        home = await self.get_home()
        if not home:
            raise FileNotFoundError("Website not reachable")

        site_name = text_of(home.select_one("title")) or None
        domain = urlparse(self.root).netloc

        # Parallel tasks
        products_task = asyncio.create_task(self.get_products_json())
        hero_task = asyncio.create_task(self.extract_hero_products(home))
        policies_task = asyncio.create_task(self.extract_policies(home))
        faqs_task = asyncio.create_task(self.extract_faqs(home))
        about_task = asyncio.create_task(self.extract_about_and_links(home))
        contact_task = asyncio.create_task(self.extract_contact(home))

        products = await products_task
        if not products:
            # fallback parse homepage collections
            try:
                products = await self.parse_products_from_html(home)
            except Exception as e:  # noqa: BLE001
                errors.append(f"product_parse_error: {e}")

        hero = await hero_task
        policies = await policies_task
        faqs = await faqs_task
        about_text, important_links = await about_task
        contact = await contact_task

        ctx = BrandContext(
            site_url=self.root,
            site_name=site_name,
            domain=domain,
            catalog_count=len(products) or None,
            products=products,
            hero_products=hero,
            policies=policies,
            faqs=faqs,
            social_handles=find_social_links(home, self.root),
            contact=contact,
            about_text=about_text,
            important_links=important_links,
            errors=errors,
        )

        return ctx


async def get_insights(url: str) -> BrandContext:
    scraper = ShopifyScraper(url)
    try:
        return await scraper.scrape()
    finally:
        await scraper.close()
