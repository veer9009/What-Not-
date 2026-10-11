import { ArrowLeft, BadgeCheck, Check, Minus, Plus, MapPin, Search, ShieldCheck, ShoppingBag, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CartIcon, DashboardShell, EmptyState, PageTop, ProductCard, RadiusSelector, Rating } from '../components/Shared';
import { useDemo } from '../state/DemoContext';
import { filterProducts, isBuyerEligible } from '../utils/products';
import { createSellerOrders } from '../utils/orders';

const categories=['All','Handmade','Home Decor','Gifts','Fashion','Jewellery','Crafts'];
export function BuyerDashboard(){const {state}=useDemo();const[query,setQuery]=useState('');const[category,setCategory]=useState('All');const[radius,setRadius]=useState(3);const visible=useMemo(()=>filterProducts(state.products,query,category,radius),[state.products,query,category,radius]);const reset=()=>{setQuery('');setCategory('All');setRadius(3)};return <DashboardShell role="buyer"><PageTop eyebrow="Good morning, Aanya" title="Products Near You" action={<Link to="/buyer/cart" className="cart-link"><CartIcon count={state.cart.reduce((a,b)=>a+b.quantity,0)}/><span>My cart</span></Link>}/><div className="location-bar"><div><MapPin/><span><small>Your location</small><b>Indiranagar, Bengaluru</b></span></div><button>Change</button></div><section className="discover-controls"><div className="search-box"><Search/><input aria-label="Search products" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search handmade products or local makers..."/></div><div className="filter-row"><div className="chips">{categories.map(c=><button key={c} className={category===c?'active':''} onClick={()=>setCategory(c)}>{c}</button>)}</div><RadiusSelector value={radius} onChange={setRadius}/></div></section><div className="results-head"><p><b>{visible.length} local finds</b> within {radius} km</p><span>Closest first</span></div>{visible.length?<div className="product-grid buyer-grid">{visible.map(p=><ProductCard key={p.id} product={p}/>)}</div>:<EmptyState title="No local finds match that" action={reset}/>}</DashboardShell>}

export function ProductDetailsPage() {
  const { id } = useParams();
  const { state, dispatch } = useDemo();
  const product = state.products.find(p => p.id === id);
  const [notice, setNotice] = useState('');
  if (!product || !isBuyerEligible(product)) return <DashboardShell role="buyer"><EmptyState title="That product is unavailable" description="Only approved, active products in stock and within your delivery area can be viewed."/><Link className="btn btn-primary back-btn" to="/buyer">Return to discovery</Link></DashboardShell>;
  const quantity = state.cart.find(item => item.productId === product.id)?.quantity ?? 0;
  const add = () => {
    if (quantity >= product.stock) { setNotice('All available stock is already in your cart.'); return; }
    dispatch({ type: 'cart/add', id: product.id }); setNotice('Added to your cart');
  };
  return <DashboardShell role="buyer"><Link className="inline-back" to="/buyer"><ArrowLeft size={16}/> Back to nearby finds</Link><div className="product-detail"><div className="detail-image"><img src={product.image} alt={product.name}/><span>Handmade nearby</span></div><div className="detail-copy"><p className="eyebrow">{product.category} · {product.distance} km away</p><h1>{product.name}</h1><div className="seller-detail"><span>{product.seller}</span>{product.verified&&<b><BadgeCheck size={16}/> Admin Verified</b>}</div><Rating value={product.rating}/><strong className="detail-price">₹{product.price.toLocaleString('en-IN')}</strong><p className="detail-description">{product.description}</p><div className="detail-facts"><span><small>Availability</small><b>{product.stock} in stock</b></span><span><small>Selling radius</small><b>{product.radius} KM</b></span><span><small>Distance</small><b>{product.distance} km away</b></span></div><div className="eligible"><Check/> You're inside this maker's selling area</div><div className="detail-actions"><button className="btn btn-primary" onClick={add} disabled={quantity>=product.stock}><ShoppingBag size={18}/> Add to Cart</button><button className="btn btn-dark" onClick={add} disabled={quantity>=product.stock}>Buy Now</button><a className="btn btn-outline" href="https://wa.me/918080098882" target="_blank" rel="noreferrer">Contact Seller</a></div>{notice&&<p className="success-note" role="status">{notice} · <Link to="/buyer/cart">View cart</Link></p>}<p className="safe-note"><ShieldCheck/> Demo purchase · No real payment will be collected</p></div></div></DashboardShell>;
}

export function CartPage() {
  const { state, dispatch } = useDemo();
  const groups = createSellerOrders(state.products, state.cart, 'preview');
  const [error, setError] = useState('');
  const checkout = () => {
    if (!createSellerOrders(state.products, state.cart, 'check').length) { setError('Some items are unavailable or exceed current stock. Update your cart before checkout.'); return; }
    dispatch({ type: 'checkout', id: crypto.randomUUID() }); setError('');
  };
  const subtotal = groups.reduce((sum, o) => sum + o.subtotal, 0);
  const delivery = groups.reduce((sum, o) => sum + o.delivery, 0);
  return <DashboardShell role="buyer"><PageTop eyebrow="Your local basket" title="Shopping Cart" action={<Link className="text-link" to="/buyer">Continue shopping</Link>}/>
    {error && <p className="form-error" role="alert">{error}</p>}
    {state.cart.length ? groups.length ? <div className="cart-layout"><div className="cart-list">
      <p className="approval-help">{groups.length} separate seller {groups.length === 1 ? 'order' : 'orders'}. Delivery is ₹49 per seller order.</p>
      {groups.map(group => <section className="seller-order-group" key={group.seller}><h2>{group.seller}</h2>{group.items.map(({ product, quantity }) => <article className="cart-item" key={product.id}>
        <img src={product.image} alt={product.name}/><div><p className="eyebrow">{product.seller}</p><h3>{product.name}</h3><span>{product.distance} km away</span></div>
        <div className="quantity"><button aria-label={`Decrease ${product.name} quantity`} disabled={quantity <= 1} onClick={() => dispatch({ type: 'cart/quantity', id: product.id, quantity: quantity - 1 })}><Minus/></button><b>{quantity}</b><button aria-label={`Increase ${product.name} quantity`} disabled={quantity >= product.stock} onClick={() => dispatch({ type: 'cart/quantity', id: product.id, quantity: quantity + 1 })}><Plus/></button></div>
        <strong>₹{(product.price * quantity).toLocaleString('en-IN')}</strong><button className="trash" aria-label={`Remove ${product.name}`} onClick={() => dispatch({ type: 'cart/remove', id: product.id })}><Trash2/></button>
      </article>)}<p className="seller-order-total">Seller subtotal ₹{group.subtotal.toLocaleString('en-IN')} + delivery ₹{group.delivery} = ₹{group.total.toLocaleString('en-IN')}</p></section>)}
    </div><aside className="order-card"><p className="eyebrow">Order summary</p><h2>Almost yours</h2><div><span>Subtotal</span><b>₹{subtotal.toLocaleString('en-IN')}</b></div><div><span>Local delivery ({groups.length} {groups.length === 1 ? 'seller' : 'sellers'})</span><b>₹{delivery}</b></div><div className="total"><span>Total</span><b>₹{(subtotal + delivery).toLocaleString('en-IN')}</b></div><button className="btn btn-primary wide" onClick={checkout}>Proceed to checkout</button><small>Demo orders only. No payment will be processed.</small></aside></div>
      : <section className="panel"><p className="form-error" role="alert">Some cart items are no longer eligible or exceed current stock. Remove them or adjust quantities before checkout.</p>{state.cart.map(item => <div className="unavailable-cart-item" key={item.productId}><span>{state.products.find(p => p.id === item.productId)?.name ?? 'Unavailable product'}</span><button className="btn btn-outline btn-sm" onClick={() => dispatch({ type: 'cart/remove', id: item.productId })}>Remove</button></div>)}</section>
      : <EmptyState title="Your local basket is empty" description="Discover nearby products and add your favourites to your basket."/>}
    {state.orders.length > 0 && <section className="panel order-confirmation"><h2>Demo orders placed</h2><p className="success-note" role="status">Your seller orders were created. No payment was processed.</p>{state.orders.map(order => <article className="seller-order-receipt" key={order.id}><h3>{order.seller}</h3><small>Order {order.id}</small>{order.items.map(item => <p key={item.product.id}>{item.product.name} × {item.quantity}</p>)}<b>Order total: ₹{order.total.toLocaleString('en-IN')}</b></article>)}</section>}
  </DashboardShell>;
}
