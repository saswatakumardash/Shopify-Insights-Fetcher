from __future__ import annotations

from sqlalchemy import select

from ..schemas import BrandContext
from .db import get_session
from .models import Store, ProductORM


async def save_brand_context(ctx: BrandContext):
    # Using a sync session inside async path; simple demo. For production, use async engine.
    session = get_session()
    try:
        store = session.execute(select(Store).where(Store.site_url == str(ctx.site_url))).scalar_one_or_none()
        if not store:
            store = Store(site_url=str(ctx.site_url), site_name=ctx.site_name, domain=ctx.domain, about_text=ctx.about_text)
            session.add(store)
            session.flush()
        else:
            store.site_name = ctx.site_name
            store.domain = ctx.domain
            store.about_text = ctx.about_text
        # naive replace of products for demo
        session.query(ProductORM).filter(ProductORM.store_id == store.id).delete()
        for p in ctx.products[:1000]:  # limit
            session.add(
                ProductORM(
                    store_id=store.id,
                    external_id=str(p.id) if p.id is not None else None,
                    handle=p.handle,
                    title=p.title,
                    url=str(p.url) if p.url else None,
                    price=str(p.price) if p.price is not None else None,
                    currency=p.currency,
                    available=p.available,
                    vendor=p.vendor,
                    product_type=p.product_type,
                )
            )
        session.commit()
    finally:
        session.close()
