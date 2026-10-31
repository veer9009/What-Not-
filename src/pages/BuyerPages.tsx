import { ArrowLeft, BadgeCheck, Check, MapPin, Search, ShieldCheck, ShoppingBag } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CartIcon, DashboardShell, EmptyState, PageTop, ProductCard, RadiusSelector, Rating } from '../components/Shared';
import { DemoNotice } from '../components/ApiStates';
import { ExploreVerticals } from '../components/ExploreVerticals';
import { useAuth } from '../state/AuthContext';
import { useDemo } from '../state/DemoContext';
import { filterProducts, isBuyerEligible } from '../utils/products';

const categories = [
  ['All', 'All Homemade'], ['Homemade Food', 'Homemade Food'], ['Handmade', 'Handmade'],
  ['Home Decor', 'Home Decor'], ['Gifts', 'Handmade Gifts'], ['Fashion', 'Handmade Bags'],
  ['Jewellery', 'Jewellery'], ['Crafts', 'Crafts'],
];
export function BuyerDashboard() {
  const { state } = useDemo();
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('All');
  const [radius, setRadius] = useState(3);
  const visible = useMemo(() => filterProducts(state.products.filter(product => !product.backend), query, category, radius), [state.products, query, category, radius]);
  const reset = () => { setQuery(''); setCategory('All'); setRadius(3); };
  return <DashboardShell role="buyer"><DemoNotice/>
    <PageTop eyebrow={`Hello, ${user?.name}`} title="Discover What Not?" action={<Link to="/buyer/cart" className="cart-link"><CartIcon count={state.cart.reduce((a,b)=>a+b.quantity,0)}/><span>Cart</span></Link>}/>
    <ExploreVerticals/>
    <section id="homemade-catalogue" aria-labelledby="homemade-catalogue-heading">
      <div className="section-heading"><div><p className="eyebrow">Food, handmade products & crafts</p><h2 id="homemade-catalogue-heading">Homemade samples</h2></div></div>
      <div className="location-bar"><div><MapPin/><span><small>Sample location</small><b>Indiranagar, Bengaluru</b></span></div><button disabled title="Geographic location selection is deferred">Location unavailable</button></div>
      <section className="discover-controls"><div className="search-box"><Search/><input aria-label="Search products" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search homemade food, crafts or local makers..."/></div>
        <div className="filter-row"><div className="chips" role="group" aria-label="Homemade sample categories">{categories.map(([value, label])=><button key={value} aria-pressed={category===value} className={category===value?'active':''} onClick={()=>setCategory(value)}>{label}</button>)}</div><RadiusSelector value={radius} onChange={setRadius}/></div>
      </section>
      <div className="results-head"><p><b>{visible.length} Homemade samples</b> within {radius} km (sample distance)</p><span>Closest first · sample</span></div>
      {visible.length?<div className="product-grid buyer-grid">{visible.map(p=><ProductCard key={p.id} product={p}/>)}</div>:<EmptyState title="No Homemade samples match that" action={reset}/>}
    </section>
  </DashboardShell>;
}

export function ProductDetailsPage() {
  const { id } = useParams();
  const { state, dispatch } = useDemo();
  const product = state.products.find(p => p.id === id && !p.backend);
  const [notice, setNotice] = useState('');
  if (!product || !isBuyerEligible(product)) return <DashboardShell role="buyer"><DemoNotice/><EmptyState title="That product is unavailable" description="Only approved, active products in stock and within your delivery area can be viewed."/><Link className="btn btn-primary back-btn" to="/buyer">Return to discovery</Link></DashboardShell>;
  const quantity = state.cart.find(item => item.productId === product.id)?.quantity ?? 0;
  const add = () => {
    if (quantity >= product.stock) { setNotice('All available stock is already in your cart.'); return; }
    dispatch({ type: 'cart/add', id: product.id }); setNotice('Added to your cart');
  };
  return <DashboardShell role="buyer"><DemoNotice/><Link className="inline-back" to="/buyer"><ArrowLeft size={16}/> Back to Homemade samples</Link><div className="product-detail"><div className="detail-image"><img src={product.image} alt={product.name}/><span>Homemade sample</span></div><div className="detail-copy"><p className="eyebrow">{product.category} · {product.distance} km away (sample)</p><h1>{product.name}</h1><div className="seller-detail"><span>{product.seller}</span>{product.verified&&<b><BadgeCheck size={16}/> Sample verification</b>}</div><Rating value={product.rating}/><strong className="detail-price">₹{product.price.toLocaleString('en-IN')}</strong><p className="detail-description">{product.description}</p><div className="detail-facts"><span><small>Sample availability</small><b>{product.stock} in stock</b></span><span><small>Sample selling radius</small><b>{product.radius} KM</b></span><span><small>Sample distance</small><b>{product.distance} km away</b></span></div><div className="eligible"><Check/> Sample distance falls inside the sample selling area</div><div className="detail-actions"><button className="btn btn-primary" onClick={add} disabled={quantity>=product.stock}><ShoppingBag size={18}/> Add to Cart</button><button className="btn btn-dark" disabled>Checkout unavailable</button><button className="btn btn-outline" disabled>Contact unavailable for samples</button></div>{notice&&<p className="success-note" role="status">{notice} · <Link to="/buyer/cart">View cart</Link></p>}<p className="safe-note"><ShieldCheck/> Sample basket only · Ordering and payments are unavailable</p></div></div></DashboardShell>;
}

export { CartPage } from './CartPage';
