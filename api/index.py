"""Vercel Python Function entrypoint.

Vercel serves this module's ASGI ``app`` for every ``/api/*`` request
(see the rewrite in vercel.json).
"""

from backend.main import app  # noqa: F401
