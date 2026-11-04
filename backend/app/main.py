from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, health, orders, products, addresses, sellers, discovery
from app.api.routes import notifications, properties, creative
from app.api.errors import install_error_handlers
from app.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application):
        try:
            yield
        finally:
            if application.state.database_engine is not None:
                application.state.database_engine.dispose()
                application.state.database_engine = None

    application = FastAPI(
        title="What Not? API", version="0.1.0",
        description="Controlled-beta marketplace: Homemade orders, sale properties and Creative Services. Locality discovery; exact delivery eligibility at checkout. No payments are collected.",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.database_engine = None
    application.state.database_engine_lock = Lock()
    install_error_handlers(application)

    @application.middleware('http')
    async def private_api_cache_policy(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    application.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Idempotency-Key"],
    )
    for router in (health.router, auth.router, products.router, orders.router, admin.router, addresses.router, sellers.router, discovery.router, notifications.router, properties.router, creative.router):
        application.include_router(router, prefix="/api/v1")
    return application


app = create_app()
