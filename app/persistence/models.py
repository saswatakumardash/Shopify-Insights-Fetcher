from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    site_url = Column(String(500), unique=True, nullable=False)
    site_name = Column(String(255))
    domain = Column(String(255))
    about_text = Column(Text)

    products = relationship("ProductORM", back_populates="store", cascade="all, delete-orphan")


class ProductORM(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    external_id = Column(String(255))
    handle = Column(String(255))
    title = Column(String(512))
    url = Column(String(1000))
    price = Column(String(64))
    currency = Column(String(16))
    available = Column(Boolean)
    vendor = Column(String(255))
    product_type = Column(String(255))

    store = relationship("Store", back_populates="products")
