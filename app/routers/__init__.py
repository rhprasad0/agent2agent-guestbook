"""API routers for A2A Guestbook."""

from app.routers.a2a import router as a2a_router
from app.routers.public import router as public_router

__all__ = ["a2a_router", "public_router"]
