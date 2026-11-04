"""Explicit browser smoke test; run from backend via pytest, never application DB.

Requires the existing production build, Node 24+ and installed Microsoft Edge.
Uses the same generated PostgreSQL fixture as backend tests. Does not install tools.
"""
from pathlib import Path
import json
import secrets
import socket
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
sys.path.insert(0,str(ROOT/'backend/tests/persistence'))
from conftest import isolated_cluster, migrated_engine  # noqa: F401


def test_real_edge_beta_workflows(migrated_engine):
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi import HTTPException
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine
    import uvicorn
    from app.main import create_app
    from app.core.config import Settings
    from app.core.security import hash_password
    from app.models import User,Address,SellerProfile,Product,Order,OrderItem
    from app.models.property import PropertyListing,PropertyProfile
    from app.models.creative import CreativeProvider,CreativeListing
    from datetime import datetime,timedelta,timezone
    password=secrets.token_urlsafe(24)
    with Session(migrated_engine) as session,session.begin():
        users=[]
        for name,role in [('Buyer','BUYER'),('OtherBuyer','BUYER'),('Seller','SELLER'),('OtherSeller','SELLER'),('Admin','ADMIN')]:
            user=User(name=name,email=name.lower()+'@browser.example.com',phone='browser-'+name,
                role=role,password_hash=hash_password(password));session.add(user);users.append(user)
        session.flush();buyer,other,seller,other_seller,admin=users
        address=Address(user_id=buyer.id,label='Browser home',address_line1='Synthetic delivery lane',city='Pune',state='MH',pincode='411001',latitude=19,longitude=72)
        shop=SellerProfile(user_id=seller.id,shop_name='Browser Maker',phone=seller.phone,latitude=19,longitude=72,dispatch_location_confirmed_at=datetime.now(timezone.utc))
        session.add_all([address,shop]);session.flush()
        product=Product(seller_id=shop.id,name='Browser vase',description='Synthetic clay',price=100,stock_quantity=10,category='Crafts',delivery_radius_km=1,status='APPROVED')
        session.add(product);session.flush();order_ids=[]
        for _ in range(2):
            order=Order(buyer_id=buyer.id,seller_id=shop.id,address_id=address.id,status='PLACED',subtotal=100,delivery_fee=0,total_amount=100)
            session.add(order);session.flush();session.add(OrderItem(order_id=order.id,product_id=product.id,seller_id=shop.id,product_name=product.name,quantity=1,unit_price=100));order_ids.append(str(order.id))
        profile=PropertyProfile(user_id=seller.id,display_name='Browser Owner',capacity='OWNER',share_contact=False)
        prop=PropertyListing(creator_id=seller.id,capacity='OWNER',title='Browser sale home',description='Synthetic home',category='Residential',price=500,locality='Pune',private_address='Synthetic private property lane',status='APPROVED',reconfirmed_at=datetime.now(timezone.utc),expires_at=datetime.now(timezone.utc)+timedelta(days=30))
        provider=CreativeProvider(user_id=seller.id,display_name='Browser Studio',bio='Video editing')
        session.add_all([profile,prop,provider]);session.flush()
        listing=CreativeListing(provider_id=provider.id,title='Browser video edit',description='Synthetic creative work',category='Video Editing',pricing='FIXED',amount=100,currency='INR',remote=True,portfolio=[],status='APPROVED')
        session.add(listing);session.flush()
        fixture=dict(password=password,orders=order_ids,property=str(prop.id),listing=str(listing.id),address=str(address.id))
    app=create_app(Settings(_env_file=None,environment='test',jwt_secret_key='browser-test-only-'+'x'*40))
    app.state.database_engine=create_engine(migrated_engine.url)
    app.mount('/assets',StaticFiles(directory=ROOT/'dist/assets'),name='assets')
    @app.get('/{path:path}')
    def spa(path:str):
        if path.startswith('api/'):raise HTTPException(404)
        return FileResponse(ROOT/'dist/index.html')
    listener=socket.socket()
    # The built frontend's default local API URL is port 8000. Refuse an occupied
    # port; never inspect, stop or reuse another application listener.
    listener.bind(('127.0.0.1',8000));listener.listen(128)
    server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
    try:
        deadline=time.monotonic()+15
        while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.05)
        assert server.started,'Isolated browser API failed to start'
        completed=subprocess.run(['node',str(ROOT/'scripts/beta_browser_smoke.mjs')],
            input=json.dumps(fixture),text=True,capture_output=True,timeout=180,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
        assert completed.returncode==0,completed.stdout+'\n'+completed.stderr
        print(completed.stdout)
    finally:
        server.should_exit=True;thread.join(timeout=15);listener.close()
        assert not thread.is_alive(),'Isolated browser API shutdown failed'
