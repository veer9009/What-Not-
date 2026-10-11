from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, health, orders, products
from app.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    application = FastAPI(
        title="What Not? API", version="0.1.0",
        description="Phase 2 foundation. Health works; marketplace endpoints are explicitly not implemented.",
    )
    application.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    for router in (health.router, auth.router, products.router, orders.router, admin.router):
        application.include_router(router, prefix="/api/v1")
    return application


app = create_app()
