# app/handlers/__init__.py
from aiogram import Router
from app.handlers import start, free, premium


def setup_routers() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(free.router)
    router.include_router(premium.router)
    return router