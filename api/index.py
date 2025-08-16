# Vercel serverless entry for FastAPI using asgi adapter
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

# Reuse app from our package
from app.main import app as fastapi_app  # noqa: E402

# On Vercel Python, export a module-level variable named `app`
app = fastapi_app
