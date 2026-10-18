"""Buyer eligibility rules; geography always precedes public pagination."""
from app.repositories.products import ProductRepository
from app.schemas.discovery import BuyerProduct, DiscoveryQuery, DiscoverySource
from app.schemas.location import Coordinate
from app.services.addresses import AddressService
from app.services.errors import ProductNotFound
from app.services.geography import distance_km, within_radius
from app.services.users import require_user


class DiscoveryService:
    def __init__(self, session):
        self.session = session
        self.repository = ProductRepository(session)

    def _location(self, actor_id, source):
        require_user(self.session, actor_id, role='BUYER')
        if source.address_id is not None:
            address = AddressService(self.session).get(actor_id, source.address_id)
            return Coordinate(latitude=address.latitude, longitude=address.longitude)
        return source.location

    def _eligible_view(self, product, location):
        seller = product.seller
        distance = distance_km(location.latitude, location.longitude, seller.latitude, seller.longitude)
        if not within_radius(distance, product.delivery_radius_km):
            return None
        return BuyerProduct(id=product.id, name=product.name, description=product.description,
            price=product.price, stock_quantity=product.stock_quantity, category=product.category,
            delivery_radius_km=product.delivery_radius_km,
            image_url=next((i.image_url for i in product.images if i.is_primary), None),
            shop_name=seller.shop_name, is_verified=seller.is_verified, distance_km=round(distance, 2))

    def list(self, actor_id: int, query: DiscoveryQuery) -> list[BuyerProduct]:
        query = DiscoveryQuery.model_validate(query)
        location = self._location(actor_id, query)
        results, eligible_count, after_id = [], 0, 0
        while True:
            batch = self.repository.discovery_candidates(after_id, 100)
            if not batch:
                return results
            for product in batch:
                view = self._eligible_view(product, location)
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
        view = self._eligible_view(product, location) if product is not None else None
        if view is None:
            raise ProductNotFound('Product is unavailable')
        return view
