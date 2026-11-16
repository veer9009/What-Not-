"""Buyer eligibility rules; geography always precedes public pagination."""
from app.repositories.products import ProductRepository
from app.schemas.discovery import BuyerProduct, DiscoveryQuery, DiscoverySource
from app.schemas.location import Coordinate
from app.services.addresses import AddressService
from app.services.errors import ProductNotFound
from app.services.geography import distance_km, within_radius
from app.services.users import require_user
from app.services.mappers import safe_product_image_url
from app.schemas.public_discovery import PUBLIC_DISCOVERY_CONSENT_VERSION
import math


def locality_center(latitude, longitude):
    # A stable ~1.1 km cell. All sellers in a cell have identical discovery
    # membership; arbitrary query locations cannot recover their private point.
    return (min(90, math.floor(float(latitude) * 100) / 100 + .005),
            min(180, math.floor(float(longitude) * 100) / 100 + .005))


class DiscoveryService:
    def __init__(self, session, settings=None):
        self.session = session
        self.settings = settings
        self.repository = ProductRepository(session)

    def _location(self, actor_id, source):
        require_user(self.session, actor_id, role='BUYER')
        if source.address_id is not None:
            address = AddressService(self.session).get(actor_id, source.address_id)
            return Coordinate(latitude=address.latitude, longitude=address.longitude)
        return source.location

    def _eligible_view(self, product, location, radius_km=3):
        seller = product.seller
        if (seller.public_discovery_latitude is None or seller.public_discovery_longitude is None
                or seller.public_discovery_confirmed_at is None
                or seller.public_discovery_consent_version != PUBLIC_DISCOVERY_CONSENT_VERSION):
            return None
        try:
            public_distance = distance_km(location.latitude, location.longitude,
                seller.public_discovery_latitude, seller.public_discovery_longitude)
        except ValueError:
            # Invalid legacy public points are excluded, never fabricated.
            return None
        if not within_radius(public_distance, radius_km) or not within_radius(public_distance, product.delivery_radius_km):
            return None
        latitude, longitude = locality_center(seller.latitude, seller.longitude)
        distance = distance_km(location.latitude, location.longitude, latitude, longitude)
        # 0.8 km bounds the displacement to the cell centre at the equator.
        # Discovery is a locality candidate list; checkout alone confirms delivery.
        if distance > product.delivery_radius_km + .8:
            return None
        return BuyerProduct(id=product.id, seller_id=product.seller_id, name=product.name, description=product.description,
            price=product.price, stock_quantity=product.stock_quantity, category=product.category,
            delivery_radius_km=product.delivery_radius_km,
            image_url=safe_product_image_url(next((i.image_url for i in product.images if i.is_primary), None), self.settings),
            shop_name=seller.shop_name, is_verified=seller.is_verified)

    def list(self, actor_id: int, query: DiscoveryQuery) -> list[BuyerProduct]:
        query = DiscoveryQuery.model_validate(query)
        location = self._location(actor_id, query)
        results, eligible_count, after_id = [], 0, 0
        while True:
            batch = self.repository.discovery_candidates(after_id, 100)
            if not batch:
                return results
            for product in batch:
                view = self._eligible_view(product, location, query.radius_km)
                if view is not None:
                    if eligible_count >= query.offset:
                        results.append(view)
                        if len(results) == query.limit:
                            return results
                    eligible_count += 1
            after_id = batch[-1].id

    def get(self, actor_id: int, product_id: int, source: DiscoverySource) -> BuyerProduct:
        source = DiscoverySource.model_validate(source)
        location = self._location(actor_id, source)
        product = self.repository.eligible_detail(product_id)
        view = self._eligible_view(product, location, source.radius_km) if product is not None else None
        if view is None:
            raise ProductNotFound('Product is unavailable')
        return view
