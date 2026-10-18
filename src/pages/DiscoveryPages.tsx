import { useCallback, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { DashboardShell, EmptyState, PageTop } from '../components/Shared';
import { ErrorNotice, Loading } from '../components/ApiStates';
import { LocationPicker } from '../components/LocationPicker';
import { ExploreVerticals } from '../components/ExploreVerticals';
import { addressesApi } from '../api/addresses';
import { discoveryApi } from '../api/discovery';
import { useDiscovery } from '../state/DiscoveryContext';
import { useResource } from '../state/useResource';

function BuyerLocation(){
  const {source,choose}=useDiscovery();const addresses=useResource(addressesApi.list);
  return <section className="panel" aria-label="Discovery location"><h2>Discovery location</h2><p>{source?'Location available for discovery':'Location not set'}</p><p>Choose where you want to discover nearby products. Your device location is requested only when you press the button.</p><LocationPicker onDraftChange={()=>choose(null)} onConfirm={async point=>choose({location:point})} confirmLabel="Use for discovery"/>
    <h3>Use a saved address</h3>{addresses.loading?<Loading/>:addresses.error?<ErrorNotice message={addresses.error} retry={()=>void addresses.reload()}/>:addresses.data?.length?<div className="form-actions">{addresses.data.map(address=><button className="btn btn-outline btn-sm" key={address.id} onClick={()=>choose({address_id:address.id})}>Use {address.label} for discovery</button>)}</div>:<p>No saved addresses. <Link to="/buyer/addresses">Add an address</Link></p>}
    {source&&<button className="text-link" onClick={()=>choose(null)}>Clear discovery location</button>}
  </section>;
}
export function BuyerDiscoveryPage(){
  return <DashboardShell role="buyer"><PageTop eyebrow="Your neighbourhood" title="Discover What Not?"/><ExploreVerticals live/><BuyerLocation/><section id="homemade-catalogue" aria-labelledby="homemade-catalogue-heading"><h2 id="homemade-catalogue-heading">Nearby Homemade products</h2><p>Products shown are approved, active, in stock and within the seller's delivery radius. Food-specific listing tools are coming soon. Checkout remains unavailable.</p><DiscoveryResults/></section></DashboardShell>;
}
function DiscoveryResults(){
  const {source}=useDiscovery();
  return source?<LocatedResults key={JSON.stringify(source)}/>:<EmptyState title="Choose your discovery location" description="Use your device, enter coordinates, or choose a saved address to see nearby products."/>;
}
function LocatedResults(){
  const {source}=useDiscovery();
  const load=useCallback(()=>discoveryApi.list(source!),[source]);const result=useResource(load);
  const [query,setQuery]=useState('');
  if(result.loading)return <Loading/>;
  if(result.error)return <ErrorNotice message={result.error} retry={()=>void result.reload()}/>;
  const products=(result.data??[]).filter(p=>`${p.name} ${p.category} ${p.shop_name}`.toLowerCase().includes(query.toLowerCase()));
  return <><div className="search-box"><input aria-label="Search products" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search nearby products"/></div><p>Up to 100 eligible products in listing order. Distances are approximate.</p>{products.length?<div className="product-grid buyer-grid">{products.map(p=><article className="product-card" key={p.id}>{p.image_url&&<div className="product-image"><img src={p.image_url} alt={p.name} referrerPolicy="no-referrer"/></div>}<div className="product-body"><p>{p.category} · Approximately {p.distance_km.toFixed(2)} km away</p><h3>{p.name}</h3><p>{p.shop_name}{p.is_verified?' · Verified seller':''}</p><div className="price-row"><strong>₹{p.price}</strong><Link className="text-link" to={`/buyer/products/${p.id}`}>View {p.name}</Link></div></div></article>)}</div>:<EmptyState title="No products nearby" description="No eligible products match this location and search. Try another location or refresh."/>}<button className="btn btn-outline btn-sm" onClick={()=>void result.reload()}>Refresh nearby products</button></>;
}
export function DiscoveryDetailPage(){
  const {source}=useDiscovery();const {id}=useParams();
  return <DashboardShell role="buyer"><Link className="inline-back" to="/buyer">Back to discovery</Link>{source?<LocatedDetail key={`${id}:${JSON.stringify(source)}`} id={id!}/>:<EmptyState title="Choose your discovery location" description="Return to discovery to select the location used for availability."/>}</DashboardShell>;
}
function LocatedDetail({id}:{id:string}){
  const {source}=useDiscovery();const load=useCallback(()=>discoveryApi.detail(id,source!),[id,source]);const result=useResource(load);
  if(result.loading)return <Loading/>;
  if(result.error)return <ErrorNotice message={result.error} retry={()=>void result.reload()}/>;
  const p=result.data!;
  return <div className="product-detail">{p.image_url&&<div className="detail-image"><img src={p.image_url} alt={p.name} referrerPolicy="no-referrer"/></div>}<div className="detail-copy"><p className="eyebrow">{p.category} · Approximately {p.distance_km.toFixed(2)} km away</p><h1>{p.name}</h1><p>{p.shop_name}{p.is_verified?' · Verified seller':''}</p><strong className="detail-price">₹{p.price}</strong><p>{p.description}</p><p>{p.stock_quantity} in stock · {p.delivery_radius_km} km delivery radius</p><p>Available for your selected discovery location at the time of this check. Location and distance are approximate.</p><button className="btn btn-primary" disabled>Checkout unavailable</button><p>Ordering and payments are not available yet.</p></div></div>;
}
