import { ListingImage } from '../components/ListingImage';
import { useCallback, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { DashboardShell, EmptyState, PageTop, RadiusSelector } from '../components/Shared';
import { ErrorNotice, Loading } from '../components/ApiStates';
import { LocationPicker } from '../components/LocationPicker';
import { ExploreVerticals } from '../components/ExploreVerticals';
import { addressesApi } from '../api/addresses';
import { discoveryApi } from '../api/discovery';
import { useDiscovery } from '../state/DiscoveryContext';
import { useResource } from '../state/useResource';
import { useDemo } from '../state/DemoContext';
import { identifier } from '../api/client';

function BuyerLocation(){
  const {source,choose,radius,setRadius}=useDiscovery();const addresses=useResource(addressesApi.list);
  const [pin,setPin]=useState('');
  const matchingAddresses=addresses.data?.filter(address=>!pin||address.pincode===pin.trim());
  return <section className="panel discovery-location" aria-label="Discovery location"><h2>Discovery location</h2><p className="discovery-location-status" role="status">{source?'Location available for discovery':'Location not set'}</p><p>Choose where you want to discover nearby products. Your device location is requested only when you press the button.</p><LocationPicker onDraftChange={()=>choose(null)} onConfirm={async point=>choose({location:point})} confirmLabel="Use for discovery"/>
    <div className="discovery-radius"><h3>Discovery radius</h3><RadiusSelector label="Discovery radius" value={radius} onChange={setRadius}/><p>Within {radius} km of sellers' confirmed public business points. Browser location is approximate, especially near a boundary. Delivery is confirmed at checkout.</p></div>
    <div className="discovery-saved-address"><h3>Use a saved address</h3><label>PIN code<input aria-label="PIN code" aria-describedby="discovery-pin-help" name="pincode" inputMode="numeric" maxLength={6} value={pin} onChange={event=>{setPin(event.target.value);choose(null);}}/></label><p id="discovery-pin-help">Enter a PIN code to find one of your saved addresses, then select it. A PIN code alone does not identify an exact location.</p>{addresses.loading?<Loading/>:addresses.error?<ErrorNotice message={addresses.error} retry={()=>void addresses.reload()}/>:matchingAddresses?.length?<div className="discovery-address-actions">{matchingAddresses.map(address=><button type="button" className="btn btn-outline" key={address.id} onClick={()=>choose({address_id:address.id})}>Use {address.label} for discovery</button>)}</div>:<p>{pin?'No saved address matches this PIN code.':'No saved addresses.'} <Link to="/buyer/addresses">Add an address</Link></p>}</div>
    {source&&<div className="discovery-clear-action"><button type="button" className="btn btn-outline" onClick={()=>choose(null)}>Clear discovery location</button></div>}
  </section>;
}
export function BuyerDiscoveryPage(){
  return <DashboardShell role="buyer"><PageTop eyebrow="Your neighbourhood" title="Discover What Not?"/><ExploreVerticals live/><div className="discovery-layout"><BuyerLocation/><section id="homemade-catalogue" aria-labelledby="homemade-catalogue-heading"><h2 id="homemade-catalogue-heading">Nearby Homemade products</h2><p>Approved, active products near your chosen location. Checkout confirms delivery eligibility. Delivery is free. Pay the seller by COD or direct UPI; What Not? does not collect funds. Food-specific listing tools are coming soon.</p><DiscoveryResults/></section></div></DashboardShell>;
}
function DiscoveryResults(){
  const {source,radius}=useDiscovery();
  return source?<LocatedResults key={`${radius}:${JSON.stringify(source)}`}/>:<EmptyState title="Choose your discovery location" description="Use your device, enter coordinates, or choose a saved address to see nearby products."/>;
}
function LocatedResults(){
  const {source,radius}=useDiscovery();
  const load=useCallback(()=>discoveryApi.list(source!,radius),[source,radius]);const result=useResource(load);
  const [query,setQuery]=useState('');
  if(result.loading)return <Loading/>;
  if(result.error)return <ErrorNotice message={result.error} retry={()=>void result.reload()}/>;
  const products=(result.data??[]).filter(p=>`${p.name} ${p.category} ${p.shop_name}`.toLowerCase().includes(query.toLowerCase()));
  return <><div className="search-box"><input aria-label="Search products" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search nearby products"/></div><p>Up to 100 nearby locality products. Exact delivery eligibility is confirmed at checkout.</p>{products.length?<div className="product-grid buyer-grid">{products.map(p=><article className="product-card" key={p.id}><div className="product-image"><ListingImage src={p.image_url} alt={p.name}/></div><div className="product-body"><p>{p.category} · Nearby locality</p><h3>{p.name}</h3><p>{p.shop_name}{p.is_verified?' · Verified seller':''}</p><div className="price-row"><strong>₹{p.price}</strong><Link className="text-link" to={`/buyer/products/${p.id}`}>View {p.name}</Link></div></div></article>)}</div>:<EmptyState title="No products nearby" description="No eligible products match this location and search. Try another location or refresh."/>}<button className="btn btn-outline btn-sm" onClick={()=>void result.reload()}>Refresh nearby products</button></>;
}
export function DiscoveryDetailPage(){
  const {source,radius}=useDiscovery();const {id}=useParams();
  return <DashboardShell role="buyer"><Link className="inline-back" to="/buyer">Back to discovery</Link>{source?<LocatedDetail key={`${id}:${radius}:${JSON.stringify(source)}`} id={id!}/>:<EmptyState title="Choose your discovery location" description="Return to discovery to select the location used for availability."/>}</DashboardShell>;
}
function LocatedDetail({id}:{id:string}){
  const {source,radius}=useDiscovery();const load=useCallback(()=>discoveryApi.detail(id,source!,radius),[id,source,radius]);const result=useResource(load);
  const {state,dispatch}=useDemo();const [added,setAdded]=useState(false);
  if(result.loading)return <Loading/>;
  if(result.error)return <ErrorNotice message={result.error} retry={()=>void result.reload()}/>;
  const p=result.data!;
  let orderable=true;try{identifier(p.id);identifier(p.seller_id);}catch{orderable=false;}
  const item=state.cart.find(item=>item.productId===`backend:${p.id}`);
  const recovering=state.placements?.some(attempt=>attempt.cartIds.includes(`backend:${p.id}`));
  return <div className="product-detail"><div className="detail-image"><ListingImage src={p.image_url} alt={p.name}/></div><div className="detail-copy"><p className="eyebrow">{p.category} · Nearby locality</p><h1>{p.name}</h1><p>{p.shop_name}{p.is_verified?' · Verified seller':''}</p><strong className="detail-price">₹{p.price}</strong><details className="product-description"><summary>Description and product details</summary><p>{p.description}</p></details><p>{p.stock_quantity} in stock · {p.delivery_radius_km} km delivery radius</p><p>This listing is in a nearby locality. Delivery eligibility is confirmed at checkout using your selected saved address.</p><button className="btn btn-primary" disabled={!orderable||recovering||item?.placementUncertain||(item?.quantity??0)>=p.stock_quantity} onClick={()=>{dispatch({type:'cart/add-discovered',product:p});setAdded(true);}}>Add to Cart</button>{added&&<p className="success-note" role="status">Added to your cart. <Link to="/buyer/cart">View cart</Link></p>}<p>Choose a saved delivery address in your cart to place an order. Delivery is Free (₹0). No payment is collected.</p>{!orderable&&<p role="alert">This product is missing valid ordering identifiers and cannot be added.</p>}</div></div>;
}
