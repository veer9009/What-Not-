from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, health, orders, products, addresses, sellers
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
        description="Phase 5 authentication and ownership-protected marketplace operations. Buyer discovery and checkout await geography.",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.database_engine = None
    application.state.database_engine_lock = Lock()
    install_error_handlers(application)
    application.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    for router in (health.router, auth.router, products.router, orders.router, admin.router, addresses.router, sellers.router):
        application.include_router(router, prefix="/api/v1")
    return application


app = create_app()
