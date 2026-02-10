"""Paste-ready GlitchTip integration snippet for FastAPI services."""

import os

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

sentry_sdk.init(
    dsn=os.getenv("GLITCHTIP_DSN"),
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "production"),
    release=os.getenv("APP_VERSION", "unknown"),
)


def install_glitchtip(app):
    """Attach Sentry/GlitchTip ASGI middleware to FastAPI app."""
    app.add_middleware(SentryAsgiMiddleware)
