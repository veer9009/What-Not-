from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import select

from app.models import ProductImage
from test_authentication import auth_client
from test_authorization import bearer


def picture(format='PNG'):
    stream = BytesIO()
    Image.new('RGB', (12, 9), 'red').save(stream, format=format)
    return stream.getvalue()


@pytest.fixture
def images_client(auth_client, tmp_path):
    auth_client.app.state.settings.image_local_directory = tmp_path / 'private'
    return auth_client


def test_upload_reload_replace_primary_remove_and_revoke_delivery(images_client, records, db):
    client = images_client
    pid = records['product'].id
    headers = bearer(records['seller_user'].id)
    path = f'/api/v1/products/{pid}/images'
    first = client.post(path, content=picture(), headers=headers)
    assert first.status_code == 201
    image = first.json()['images'][0]
    assert image['is_primary'] is True
    assert first.json()['image_url'] == image['image_url']
    assert client.get(image['image_url']).status_code == 200
    assert client.get(image['image_url'].split('?')[0]).status_code == 404
    assert client.get(image['image_url'] + 'tampered').status_code == 404
    echoed = client.patch(f'/api/v1/products/{pid}', headers=headers,
        json={'name': 'Legacy client edit', 'image_url': first.json()['image_url']})
    assert echoed.status_code == 200
    from app.storage.product_images import image_key
    assert image_key(records['product'].images[0].image_url) is not None
    assert client.get(echoed.json()['image_url']).status_code == 200
    reloaded = client.get('/api/v1/sellers/me/products', headers=headers).json()[0]
    assert reloaded['images'][0]['id'] == image['id']
    second = client.post(path, content=picture('JPEG'), headers=headers)
    assert second.status_code == 201
    other = second.json()['images'][1]
    primary = client.post(f"{path}/{other['id']}/primary", json={}, headers=headers)
    assert primary.status_code == 200
    assert [i['id'] for i in primary.json()['images'] if i['is_primary']] == [other['id']]
    replaced = client.post(f"{path}/{image['id']}/replace", content=picture('WEBP'), headers=headers)
    assert replaced.status_code == 200
    assert client.get(image['image_url']).status_code == 404
    new_image = next(i for i in replaced.json()['images'] if i['id'] == image['id'])
    assert client.get(new_image['image_url']).status_code == 200
    removed = client.post(f"{path}/{other['id']}/remove", json={}, headers=headers)
    assert removed.status_code == 200
    assert len(removed.json()['images']) == 1
    assert removed.json()['images'][0]['is_primary'] is True
    assert client.get(other['image_url']).status_code == 404
    assert len(list(db.scalars(select(ProductImage)))) == 1


def test_image_limits_and_hosted_url_preservation(images_client, records, db):
    client = images_client
    pid = records['product'].id
    headers = bearer(records['seller_user'].id)
    legacy = ProductImage(product=records['product'], image_url='https://example.test/legacy.jpg', is_primary=True)
    db.add(legacy); db.flush()
    path = f'/api/v1/products/{pid}/images'
    for _ in range(4):
        assert client.post(path, content=picture(), headers=headers).status_code == 201
    denied = client.post(path, content=picture(), headers=headers)
    assert denied.status_code == 409
    listed = client.get(path, headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 5
    assert listed.json()[0]['image_url'] == 'https://example.test/legacy.jpg'
    replaced = client.post(f'{path}/{legacy.id}/replace', content=picture(), headers=headers)
    assert replaced.status_code == 200
    assert len(replaced.json()['images']) == 5


@pytest.mark.parametrize('actor,status', [(None,401),('buyer',403)])
def test_image_mutations_require_seller(images_client, records, actor, status):
    headers = bearer(records[actor].id) if actor else {}
    assert images_client.post(f"/api/v1/products/{records['product'].id}/images", content=picture(), headers=headers).status_code == status


def test_other_seller_and_other_product_image_access_are_denied(images_client, records, db):
    from app.models import User, Product, SellerProfile
    other = User(name='Other', email='other-images@example.test', phone='other-images', password_hash='hash', role='SELLER')
    seller = SellerProfile(user=other, shop_name='Other', phone='other-images', latitude=0, longitude=0)
    product = Product(seller=seller, name='Other', description='Other', price=1, stock_quantity=1, category='Crafts', delivery_radius_km=1)
    db.add(product); db.flush()
    own = bearer(records['seller_user'].id)
    path = f"/api/v1/products/{records['product'].id}/images"
    uploaded = images_client.post(path, content=picture(), headers=own).json()['images'][0]
    for suffix, body in [('',picture()),(f"/{uploaded['id']}/replace",picture()),(f"/{uploaded['id']}/remove",b'{}'),(f"/{uploaded['id']}/primary",b'{}')]:
        payload = {'json': {}} if suffix.endswith(('/remove', '/primary')) else {'content': body}
        assert images_client.post(path+suffix, **payload, headers=bearer(other.id)).status_code == 403
    assert images_client.get(path, headers=bearer(other.id)).status_code == 403
    assert images_client.post(f"/api/v1/products/{product.id}/images/{uploaded['id']}/remove", json={}, headers=bearer(other.id)).status_code == 404


@pytest.mark.parametrize('body,status', [(b'not an image',422),(b'<svg/>',422),(b'x'*(5*1024*1024+1),413)], ids=['malformed','svg','oversize'])
def test_bad_uploads_are_sanitized_and_do_not_attach(images_client, records, body, status):
    response = images_client.post(f"/api/v1/products/{records['product'].id}/images", content=body, headers=bearer(records['seller_user'].id))
    assert response.status_code == status
    assert 'Traceback' not in response.text
    assert records['product'].images == []


def test_image_edit_requires_renewed_moderation_and_suspended_owner_loses_delivery(images_client, records, db):
    records['product'].status = 'APPROVED'; db.flush()
    response = images_client.post(f"/api/v1/products/{records['product'].id}/images", content=picture(), headers=bearer(records['seller_user'].id))
    assert response.status_code == 201
    assert response.json()['status'] == 'PENDING'
    url = response.json()['image_url']
    records['seller_user'].is_active = False; db.flush()
    assert images_client.get(url).status_code == 404


def test_storage_failure_is_sanitized_and_does_not_attach_an_image(images_client, records, monkeypatch):
    from app.services import product_images
    from app.storage.product_images import ImageStorageError
    def unavailable(settings):
        raise ImageStorageError('private provider diagnostic')
    monkeypatch.setattr(product_images, 'get_image_storage', unavailable)
    response = images_client.post(f"/api/v1/products/{records['product'].id}/images", content=picture(), headers=bearer(records['seller_user'].id))
    assert response.status_code == 503
    assert response.json() == {'detail':'Image storage is unavailable; please retry later'}
    assert records['product'].images == []


def test_concurrent_uploads_cannot_exceed_five(fresh_database_url, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from alembic import command
    from fastapi import HTTPException
    from sqlalchemy import create_engine, func
    from sqlalchemy.orm import Session
    from conftest import migration_config
    from app.core.config import Settings
    from app.models import User, SellerProfile, Product
    from app.services.product_images import ProductImageService

    command.upgrade(migration_config(fresh_database_url), 'head')
    engine = create_engine(fresh_database_url, connect_args={'options':'-c statement_timeout=20000 -c lock_timeout=15000'})
    settings = Settings(_env_file=None, environment='test', image_local_directory=tmp_path/'concurrent')
    try:
        with Session(engine) as session, session.begin():
            user = User(name='Parallel',email='parallel-images@example.test',phone='parallel-images',password_hash='test-only',role='SELLER')
            seller = SellerProfile(user=user,shop_name='Parallel',phone='parallel-images',latitude=0,longitude=0)
            product = Product(seller=seller,name='Parallel',description='Parallel',price=1,stock_quantity=1,category='Crafts',delivery_radius_km=1)
            product.images = [ProductImage(image_url=f'https://example.test/{i}.jpg',is_primary=i==0,sort_order=i) for i in range(4)]
            session.add(product); session.flush()
            uid, pid = user.id, product.id
        barrier = Barrier(2)
        def upload_one():
            try:
                with Session(engine) as session, session.begin():
                    barrier.wait(timeout=15)
                    ProductImageService(session,settings).upload(uid,pid,picture())
                return 201
            except HTTPException as exc:
                return exc.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(upload_one) for _ in range(2)]
            assert sorted(f.result(timeout=40) for f in futures) == [201,409]
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(ProductImage)) == 5
            assert session.scalar(select(func.count()).select_from(ProductImage).where(ProductImage.is_primary.is_(True))) == 1
    finally:
        engine.dispose()
