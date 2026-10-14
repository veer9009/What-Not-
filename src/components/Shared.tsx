import { BadgeCheck, HelpCircle, MapPin, Menu, MessageCircle, ShoppingBag, Star, X } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../state/AuthContext';
import type { Product, ProductStatus } from '../types';

export function Logo({ light = false }: { light?: boolean }) {
  return <Link className={`logo ${light ? 'logo-light' : ''}`} to="/"><span className="logo-mark">N</span><span>What Not?<small>discover local possibilities</small></span></Link>;
}
export function PublicHeader() {
  const [open,setOpen]=useState(false);
  return <header className="public-header"><Logo/><button className="menu-btn" onClick={()=>setOpen(!open)} aria-label="Toggle navigation" aria-expanded={open} aria-controls="public-navigation">{open?<X/>:<Menu/>}</button><nav id="public-navigation" aria-label="Main navigation" className={open?'open':''} onClick={()=>setOpen(false)}>
    <a href="/#homemade">Homemade</a><a href="/#real-estate">Real Estate</a><a href="/#creative-services">Creative Services</a><Link to="/login/seller">Become a Seller</Link><Link className="btn btn-dark btn-sm" to="/login">Login</Link>
  </nav></header>;
}
export function Rating({ value }: { value:number }) { return <span className="rating"><Star size={14} fill="currentColor"/> {value}</span>; }
export function StatusBadge({ status }: { status:ProductStatus | 'INACTIVE' | 'OUT_OF_STOCK' }) { const labels = { PENDING:'Pending', APPROVED:'Approved', REJECTED:'Rejected', INACTIVE:'Inactive', OUT_OF_STOCK:'Out of Stock' }; return <span className={`status ${status.toLowerCase()}`}>{labels[status]}</span>; }
export function ProductCard({ product }: { product:Product }) {
  return <article className="product-card"><div className="product-image"><img src={product.image} alt={product.name}/><span className="sample-product-label">Sample</span><span className="distance"><MapPin size={13}/>{product.distance} km</span></div><div className="product-body"><div className="product-meta"><span>{product.category}</span><Rating value={product.rating}/></div><h3>{product.name}</h3><p className="seller-line">{product.seller} {product.verified&&<BadgeCheck size={15} aria-label="Sample verification"/>}</p><div className="price-row"><strong>₹{product.price.toLocaleString('en-IN')}</strong><Link className="text-link" to={`/buyer/products/${product.id}`}>View product →</Link></div></div></article>;
}
export function RadiusSelector({ value,onChange }: { value:number;onChange:(n:number)=>void }) { return <div className="radius-select" aria-label="Distance radius">{[1,2,3].map(n=><button type="button" className={value===n?'active':''} key={n} onClick={()=>onChange(n)}>{n} KM</button>)}</div>; }
export function RadiusVisual() { return <div className="radius-visual"><span className="ring ring-3"><b>3 KM</b></span><span className="ring ring-2"><b>2 KM</b></span><span className="ring ring-1"><b>1 KM</b></span><span className="maker-pin">🏺<small>Local maker</small></span><span className="buyer-dot one">●<small>0.8 km</small></span><span className="buyer-dot two">●<small>1.7 km</small></span><span className="buyer-dot three">●<small>2.7 km</small></span></div>; }
export function EmptyState({ title='Nothing nearby yet', description='Try widening your radius or clearing a filter.', action }: { title?:string;description?:string;action?:()=>void }) { return <div className="empty"><HelpCircle size={36}/><h3>{title}</h3><p>{description}</p>{action&&<button className="btn btn-outline" onClick={action}>Reset filters</button>}</div>; }
export function WhatsAppButton() { const url='https://wa.me/918080098882?text='+encodeURIComponent('Hi, I would like to know more about your local marketplace.'); return <div className="whatsapp"><span>Need help?<small>Chat with us on WhatsApp</small></span><a href={url} target="_blank" rel="noreferrer" aria-label="Chat with us on WhatsApp"><MessageCircle/></a></div>; }
export function DashboardShell({ role,children }: { role:'buyer'|'seller'|'admin';children:ReactNode }) {
  const auth = useAuth(); const navigate = useNavigate();
  const links = role==='buyer'?[['/buyer','Sample discovery'],['/buyer/cart','Sample cart'],['/buyer/profile','Profile'],['/buyer/addresses','Addresses'],['/buyer/orders','Orders']]:role==='seller'?[['/seller','Overview'],['/seller/profile','Shop profile'],['/seller/products/new','Add product'],['/seller/orders','Orders'],['/seller/addresses','Addresses']]:[['/admin','Moderation'],['/admin/addresses','Addresses']];
  return <div className={`dash-shell ${role}`}><aside><Logo light={role==='admin'}/><p className="eyebrow">{role} workspace</p><nav>{links.map(([href,label])=><NavLink key={href} end to={href}>{label}</NavLink>)}</nav><p className="session-identity">{auth.user?.name}</p><button className="btn btn-outline btn-sm logout-button" onClick={()=>{auth.logout();navigate(`/login/${role}`,{replace:true});}}>Log out</button><Link className="back-home" to="/">Back to marketplace</Link></aside><main>{children}</main></div>;
}
export function PageTop({ eyebrow,title,action }: { eyebrow:string;title:string;action?:ReactNode }) { return <div className="page-top"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div>{action}</div>; }
export function Metric({ label,value,note }: {label:string;value:string|number;note?:string}) { return <div className="metric"><span>{label}</span><strong>{value}</strong>{note&&<small>{note}</small>}</div>; }
export function CartIcon({ count }: { count:number }) { return <span className="cart-icon"><ShoppingBag/>{count>0&&<b>{count}</b>}</span>; }
