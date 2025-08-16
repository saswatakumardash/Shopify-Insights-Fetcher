from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, Field


class Link(BaseModel):
    title: str
    url: AnyHttpUrl | str


class Policy(BaseModel):
    name: str
    url: AnyHttpUrl | str | None = None
    content_excerpt: str | None = None


class FAQItem(BaseModel):
    question: str
    answer: str | None = None


class ContactInfo(BaseModel):
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    address: str | None = None
    contact_page_url: AnyHttpUrl | str | None = None


class Product(BaseModel):
    id: str | int | None = None
    handle: str | None = None
    title: str
    url: AnyHttpUrl | str | None = None
    price: float | None = None
    currency: str | None = None
    images: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    available: bool | None = None
    vendor: str | None = None
    product_type: str | None = None


class BrandContext(BaseModel):
    site_url: AnyHttpUrl | str
    site_name: str | None = None
    domain: str | None = None

    catalog_count: int | None = None
    products: list[Product] = Field(default_factory=list)
    hero_products: list[str] = Field(default_factory=list)

    policies: list[Policy] = Field(default_factory=list)
    faqs: list[FAQItem] = Field(default_factory=list)

    social_handles: dict[str, str] = Field(default_factory=dict)
    contact: ContactInfo = Field(default_factory=ContactInfo)

    about_text: str | None = None
    important_links: list[Link] = Field(default_factory=list)

    errors: list[str] = Field(default_factory=list)


class InsightsRequest(BaseModel):
    website_url: AnyHttpUrl | str


class InsightsResponse(BaseModel):
    data: BrandContext
