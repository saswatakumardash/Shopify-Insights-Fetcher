# Vercel serverless entry for FastAPI using asgi adapter
from __future__ import annotations

# Reuse app from our package
from app.main import app

# Export for Vercel
__all__ = ["app"]
