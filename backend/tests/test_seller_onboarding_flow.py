"""Real service/SQL onboarding checks using an isolated, disposable SQLite database.

This checks persisted service behavior, not PostgreSQL locks, concurrency or migrations.
Only private table copies receive SQLite DDL compatibility changes.
"""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, CheckConstraint, Integer, MetaData, create_engine, event, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Product, ProductImage, SellerProfile, User
from app.models.events import AuditEvent
from app.schemas.discovery import DiscoveryQuery
from app.schemas.location import Coordinate
from app.schemas.marketplace import seller_response
from app.schemas.product import ProductCreate
from app.schemas.public_discovery import PublicDiscoveryConfirmation, PUBLIC_DISCOVERY_CONSENT_VERSION
from app.services.discovery import DiscoveryService
from app.services.inputs import SellerCreate
from app.services.moderation import ModerationService
from app.services.products import ProductService
from app.services.sellers import SellerService


@pytest.fixture
def onboarding_engine():
    metadata = MetaData()
    for model in (User, SellerProfile, Product, ProductImage, AuditEvent):
        table = model.__table__.to_metadata(metadata)
        # SQLite autoincrement requires the literal INTEGER PRIMARY KEY type.
        table.c.id.type = Integer()
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint) and "::numeric" in str(constraint.sqltext):
                constraint.sqltext = text(str(constraint.sqltext).replace("::numeric", ""))
        for index in table.indexes:
            predicate = index.dialect_options["postgresql"].get("where")
            if predicate is not None:
                index.dialect_options["sqlite"]["where"] = predicate

    engine = create_engine("sqlite://", poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def sqlite_functions(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.create_function("clock_timestamp", 0,
            lambda: datetime.now(timezone.utc).replace(tzinfo=None).isoformat(" "))

    try:
        metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()


def public_consent():
    # The intentionally different public point must not replace dispatch data.
    return PublicDiscoveryConfirmation(latitude="12.975000", longitude="77.595000",
        consent=True, consent_version=PUBLIC_DISCOVERY_CONSENT_VERSION)


def test_saved_seller_two_products_moderation_discovery_and_consent(onboarding_engine):
    with Session(onboarding_engine) as session, session.begin():
        session.add_all(User(id=id_, name=f"Synthetic {role}", email=f"{role.lower()}@example.test",
            phone=f"synthetic-{id_}", password_hash="synthetic-unused-hash", role=role,
            is_active=True) for id_, role in ((101, "SELLER"), (102, "BUYER"), (103, "ADMIN")))
        session.flush()
        profile = SellerService(session).create(101, SellerCreate(shop_name="Synthetic crafts",
            phone="synthetic-shop", latitude="12.971600", longitude="77.594600"))
        profile_id = profile.id
        assert profile.dispatch_location_confirmed_at is None
        assert profile.public_discovery_consent_version is None

    # Reopening the session ensures subsequent forms reuse the persisted profile.
    with Session(onboarding_engine) as session, session.begin():
        sellers = SellerService(session)
        profile = sellers.get_by_user(101)
        assert profile.id == profile_id
        products = [ProductService(session).create(101, profile.id, ProductCreate(
            name=name, description="Synthetic handmade listing", price="125.00", stock_quantity=2,
            category="Crafts", delivery_radius_km=3)) for name in ("Synthetic vase", "Synthetic basket")]
        product_ids = [product.id for product in products]
        assert all(product.status == "PENDING" for product in products)
        assert {product.seller_id for product in products} == {profile_id}
        assert session.scalar(select(func.count()).select_from(SellerProfile)) == 1

        discovery = DiscoveryService(session)
        query = DiscoveryQuery(location=Coordinate(latitude="12.975000", longitude="77.595000"))
        assert discovery.list(102, query) == []

        sellers.set_dispatch_location(101, Coordinate(latitude="12.971600", longitude="77.594600"))
        sellers.set_public_discovery(101, public_consent())
        assert discovery.list(102, query) == []  # Consent does not bypass PENDING moderation.
        for product_id in product_ids:
            ModerationService(session).approve(103, product_id)

    with Session(onboarding_engine) as session, session.begin():
        discovery = DiscoveryService(session)
        visible = discovery.list(102, query)
        assert {product.id for product in visible} == set(product_ids)
        assert {product.seller_id for product in visible} == {profile_id}
        assert session.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == "PRODUCT_APPROVED", AuditEvent.actor_id == 103)) == 2
        private_fields = {"latitude", "longitude", "phone", "user_id", "dispatch_location_confirmed_at",
            "public_discovery_latitude", "public_discovery_longitude", "public_discovery_confirmed_at",
            "public_discovery_consent_version"}
        assert all(private_fields.isdisjoint(product.model_dump()) for product in visible)
        owner_view = seller_response(SellerService(session).get_by_user(101))
        assert owner_view.latitude == Decimal("12.971600")
        assert owner_view.public_discovery_latitude == Decimal("12.975000")

        sellers = SellerService(session)
        revoked = sellers.set_public_discovery(101, None)
        assert revoked.public_discovery_confirmed_at is None
        assert discovery.list(102, query) == []
        sellers.set_public_discovery(101, public_consent())
        assert len(discovery.list(102, query)) == 2
        moved = sellers.set_dispatch_location(101, Coordinate(latitude="12.972000", longitude="77.595000"))
        assert moved.dispatch_location_confirmed_at is not None
        assert all(getattr(moved, field) is None for field in (
            "public_discovery_latitude", "public_discovery_longitude", "public_discovery_confirmed_at",
            "public_discovery_consent_version"))
        assert discovery.list(102, query) == []

    with Session(onboarding_engine) as session:
        saved = SellerService(session).get_by_user(101)
        assert saved.id == profile_id
        assert saved.latitude == Decimal("12.972000")
        assert saved.public_discovery_consent_version is None
        assert DiscoveryService(session).list(102, query) == []

    # Private fixture compatibility changes must never alter production model metadata.
    assert isinstance(Product.__table__.c.id.type, BigInteger)
    assert any("::numeric" in str(constraint.sqltext) for constraint in Product.__table__.constraints
        if isinstance(constraint, CheckConstraint))
