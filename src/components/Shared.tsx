import { Bell, CalendarDays, ClipboardCheck, Code2, FileText, Heart, HelpCircle, House, HousePlus, Images, LayoutDashboard, LogOut, MapPin, Menu, MessageCircle, MessageSquare, Package, Palette, PlusCircle, ShoppingBasket, ShoppingBag, ShoppingCart, Star, Store, UserRound, type LucideIcon } from 'lucide-react';
import { useEffect, useRef, type ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../state/AuthContext';
import type { Product, ProductStatus } from '../types';
import { supportUrl } from '../utils/support';
import { ListingImage } from './ListingImage';
import { Wallet } from 'lucide-react';
import { NotificationBell } from './NotificationBell';
import { WishlistCount } from '../state/WishlistContext';
import { MobileNavigation, openMobileMenu, useMobileNavigation } from './MobileNavigation';

export function Logo({ light = false }: { light?: boolean }) {
  return <Link className={`logo ${light ? 'logo-light' : ''}`} to="/" aria-label="What Not? Home"><span className="logo-mark" aria-hidden="true">N</span><span>What Not?<small>discover local possibilities</small></span></Link>;
}
export interface NavigationItem {href:string;label:string;icon:LucideIcon;matchPrefix?:string;group?:string}
function useSectionTarget(content?:ReactNode){
  const {pathname,hash,key:locationKey}=useLocation();const handled=useRef('');
  useEffect(()=>{
    const key=locationKey+pathname+hash;if(handled.current===key)return;
    const initial=handled.current==='';
    if(!hash){
      handled.current=key;
      if(initial&&locationKey==='default')return;
      const main=document.getElementById('main-content');
      main?.focus({preventScroll:true});window.scrollTo({top:0,left:0,behavior:'instant'});
      return;
    }
    const target=document.getElementById(hash.slice(1));
    if(target){target.tabIndex=-1;target.focus({preventScroll:true});target.scrollIntoView?.({block:'start'});handled.current=key;}
  },[pathname,hash,locationKey,content]);
}
const publicLinks:NavigationItem[]=[
  {href:'/',label:'Home',icon:House},
  {href:'/#homemade',label:'Marketplace',icon:ShoppingBasket},
  {href:'/#real-estate',label:'Property',icon:HousePlus},
  {href:'/#creative-services',label:'Creative Services',icon:Palette,matchPrefix:'/creative-services'},
  {href:'/#professional-services',label:'Professional Services',icon:Code2,matchPrefix:'/professional-services'},
  {href:'/login/seller',label:'Become a Seller',icon:Store},
  {href:'/login',label:'Login',icon:UserRound},
];
function SidebarLinks({items,label}:{items:NavigationItem[];label:string}){
  const location=useLocation();
  const exact=items.find(item=>item.href===location.pathname+location.hash);
  const active=exact??items.filter(item=>item.matchPrefix?location.pathname.startsWith(item.matchPrefix):!item.href.includes('#')&&item.href!=='/'&&(location.pathname===item.href||location.pathname.startsWith(item.href+'/'))).sort((a,b)=>(b.matchPrefix??b.href).length-(a.matchPrefix??a.href).length)[0];
  const groups=[...new Set(items.map(item=>item.group??''))];
  return <nav aria-label={label}>{groups.map(group=><div className="sidebar-group" key={group}>{group&&<p className="nav-group-title">{group}</p>}{items.filter(item=>(item.group??'')===group).map(({href,label,icon:Icon})=>{const selected=active?.href===href&&active?.label===label;return <Link key={`${href}:${label}`} to={href} aria-label={label} title={label} aria-current={selected?(exact?.href===href&&href.includes('#')?'location':'page'):undefined} className={selected?'active':undefined}><Icon size={20} aria-hidden="true"/><span className="nav-label">{label}</span>{href==='/buyer/wishlist'&&<WishlistCount/>}</Link>;})}</div>)}</nav>;
}
export function PublicSidebar(){
  useSectionTarget();const mobile=useMobileNavigation(),auth=useAuth(),navigate=useNavigate();
  const role=auth.user?.role.toLowerCase() as 'buyer'|'seller'|'admin'|undefined;
  const items=role?[...workspaceLinks(role,false,true),...publicLinks.filter(item=>item.href==='/'||item.href.startsWith('/#'))]:publicLinks;
  return mobile?<MobileNavigation items={items} role={role} accountControls={auth.user?<><p>{auth.user.name}</p><button type="button" className="btn btn-outline" onClick={()=>{void auth.logout();navigate('/login');}}>Log out</button></>:undefined}/>:<aside className="app-sidebar public-sidebar" aria-label="Marketplace"><p className="eyebrow workspace-label">Explore</p><SidebarLinks items={publicLinks} label="Main navigation"/></aside>;
}
export function PublicHeader({compact=false}:{compact?:boolean}={}) {
  const {user}=useAuth();
  const locationLink=user?.role==='SELLER'?'/seller/profile':user?.role==='ADMIN'?'/admin/addresses':'/buyer';
  const profile=user?.role==='SELLER'?'/seller/profile':user?.role==='ADMIN'?'/admin/operations':user?'/buyer/profile':'/login';
  if(compact)return <><PublicSidebar/><header className="public-header"><button type="button" className="home-menu-button" aria-label="Open menu" onClick={openMobileMenu}><Menu size={26} aria-hidden="true"/></button><Logo/><div className="home-header-actions">{user?<NotificationBell/>:<Link className="home-notification-login" to="/login" aria-label="Sign in for notifications"><Bell size={24} aria-hidden="true"/></Link>}<Link className="home-profile-avatar" to={profile} aria-label={user?'Open profile':'Sign in'}>{user?.name?.trim().slice(0,1).toUpperCase()||<UserRound size={21} aria-hidden="true"/>}</Link></div></header></>;
  return <><PublicSidebar/><header className="public-header"><Logo/><Link className="marketplace-location-link" to={locationLink}><MapPin size={17} aria-hidden="true"/>{user?.role==='SELLER'?'Shop location':user?.role==='ADMIN'?'Saved addresses':'Choose your area'}</Link></header></>;
}
export function Rating({ value }: { value:number }) { return <span className="rating"><Star size={14} fill="currentColor" aria-hidden="true"/> Sample rating: {value}</span>; }
export function StatusBadge({ status }: { status:ProductStatus | 'INACTIVE' | 'OUT_OF_STOCK' }) { const labels = { PENDING:'Pending', APPROVED:'Approved', REJECTED:'Rejected', INACTIVE:'Inactive', OUT_OF_STOCK:'Out of Stock' }; return <span className={`status ${status.toLowerCase()}`}>{labels[status]}</span>; }
export function ProductCard({ product }: { product:Product }) {
  return <article className="product-card"><div className="product-image"><ListingImage src={product.image} alt={product.name}/><span className="sample-product-label">Sample</span><span className="distance"><MapPin size={13} aria-hidden="true"/>Sample {product.distance} km</span></div><div className="product-body"><div className="product-meta"><span>{product.category}</span><Rating value={product.rating}/></div><h3>{product.name}</h3><p className="seller-line">{product.seller}</p><div className="price-row"><strong>₹{product.price.toLocaleString('en-IN')}</strong><Link className="text-link" to={`/buyer/samples/products/${product.id}`}>View product →</Link></div></div></article>;
}
export function RadiusSelector({ value,onChange,label='Distance radius' }: { value:number;onChange:(n:1|2|3)=>void;label?:string }) { return <div className="radius-select" role="group" aria-label={label}>{([1,2,3] as const).map(n=><button type="button" className={value===n?'active':''} aria-pressed={value===n} key={n} onClick={()=>onChange(n)}>{n} KM</button>)}</div>; }
export function RadiusVisual() { return <div className="radius-visual"><span className="ring ring-3"><b>3 KM</b></span><span className="ring ring-2"><b>2 KM</b></span><span className="ring ring-1"><b>1 KM</b></span><span className="maker-pin">🏺<small>Local maker</small></span><span className="buyer-dot one">●<small>0.8 km</small></span><span className="buyer-dot two">●<small>1.7 km</small></span><span className="buyer-dot three">●<small>2.7 km</small></span></div>; }
export function EmptyState({ title='Nothing nearby yet', description='Try widening your radius or clearing a filter.', action }: { title?:string;description?:string;action?:()=>void }) { return <div className="empty"><HelpCircle size={36}/><h3>{title}</h3><p>{description}</p>{action&&<button className="btn btn-outline" onClick={action}>Reset filters</button>}</div>; }
export function WhatsAppButton() { return <div className="whatsapp"><span>Need help?<small>Chat with us on WhatsApp</small></span><a href={supportUrl()} target="_blank" rel="noreferrer" aria-label="Chat with us on WhatsApp"><MessageCircle/></a></div>; }
function workspaceLinks(role:'buyer'|'seller'|'admin',creative:boolean,sectionsReady:boolean,professional=false){
  const entry=(href:string,label:string,icon:LucideIcon):NavigationItem=>({href,label,icon});
  const studio=professional?'/seller/professional':'/seller/creative';
  const links=role==='buyer'?[
    entry('/buyer','Homemade Products',ShoppingBasket),entry('/buyer/cart','Cart',ShoppingCart),entry('/buyer/properties','Real Estate',HousePlus),entry('/buyer/properties/saved','Saved properties',Heart),entry('/buyer/properties/requests','Enquiries & visits',CalendarDays),entry('/buyer/creative','Creative Services',Palette),entry('/buyer/notifications','Notifications',Bell),entry('/buyer/profile','Profile',UserRound),entry('/buyer/addresses','Addresses',MapPin),entry('/buyer/orders','Orders',ShoppingBag),entry('/buyer/help','Help & Support',HelpCircle),
  ]:role==='seller'?creative||professional?[
    entry(studio,'Overview',LayoutDashboard),...(sectionsReady?[entry(studio+'#provider','Provider Profile',UserRound),entry(studio+'#services','Services',professional?Code2:Palette),entry(studio+'#portfolio','Portfolio',Images),entry(studio+'#enquiries','Enquiries',MessageSquare),entry(studio+'#quotations','Quotations',FileText),entry(studio+'#projects','Projects',ClipboardCheck),entry(studio+'#reviews','Customer Reviews',Star)]:[]),entry('/seller','Seller Studio',Store),entry(professional?'/seller/creative':'/seller/professional',professional?'Creative Studio':'Professional Dashboard',professional?Palette:Code2),entry('/seller/properties','Real Estate',HousePlus),entry('/seller/notifications','Notifications',Bell),entry('/seller/addresses','Addresses',MapPin),
  ]:[
    entry('/seller','Overview',LayoutDashboard),entry('/seller/profile','Shop Profile',Store),...(sectionsReady?[{...entry('/seller#products','Products',Package),matchPrefix:'/seller/products/'}]:[]),entry('/seller/products/new','Add product',PlusCircle),entry('/seller/orders','Orders',ShoppingBag),entry('/seller/creative','Creative Studio',Palette),entry('/seller/properties','Manage properties',HousePlus),entry('/seller/properties/requests','Enquiries & visits',CalendarDays),entry('/seller/notifications','Notifications',Bell),entry('/seller/addresses','Addresses',MapPin),
  ]:[entry('/admin','Product moderation',ClipboardCheck),entry('/admin/properties','Property reports',HousePlus),entry('/admin/creative','Service moderation',Palette),entry('/admin/operations','Orders & accounts',ShoppingBag),entry('/admin/notifications','Notifications',Bell),entry('/admin/addresses','Addresses',MapPin)];
  if(role==='buyer')links.push(entry('/buyer/wishlist','Wishlist',Heart));
  if(role==='seller')links.push(entry('/seller/payment-settings','Payment settings',Wallet));
  if(role==='admin')links.push(entry('/admin/payment-settings','Payment destination reviews',Wallet));
  links.push(entry(`/${role}/payments`,role==='admin'?'Payments & Transactions':'Payments',Wallet));
  if(role==='buyer')links.splice(6,0,entry('/buyer/professional','Professional Services',Code2));
  if(role==='seller'&&!creative&&!professional)links.splice(6,0,entry('/seller/professional','Professional Dashboard',Code2));
  return links.map(item=>({...item,group:
    /\/(notifications|addresses|profile|help)$/.test(item.href)?'Account':
    creative||professional?(item.href.startsWith(studio)?professional?'Professional Dashboard':'Creative Studio':'Workspaces'):
    role==='seller'?(item.href.includes('/properties')||item.href==='/seller/creative'||item.href==='/seller/professional'?'Workspaces':'Manage shop'):
    role==='buyer'?(item.href.includes('/properties')||item.href==='/buyer/creative'||item.href==='/buyer/professional'?'Explore':'Shopping'):
    item.href==='/admin/operations'||item.href==='/admin/payments'?'Management':'Moderation'}));
}
export function DashboardShell({ role,children,sectionsReady=true }: { role:'buyer'|'seller'|'admin';children:ReactNode;sectionsReady?:boolean }) {
  const auth=useAuth(),navigate=useNavigate(),location=useLocation(),mobile=useMobileNavigation();
  const creative=role==='seller'&&location.pathname==='/seller/creative';
  const professional=role==='seller'&&location.pathname==='/seller/professional';
  const workspaceLabel=professional?'Professional Dashboard':creative?'Creative Studio':role==='seller'?'Seller Studio':`${role} workspace`;
  const links=workspaceLinks(role,creative,sectionsReady,professional);
  const logout=<button className="btn btn-outline btn-sm logout-button" aria-label="Log out" title="Log out" onClick={()=>{auth.logout();navigate(role==='admin'?'/admin/login':`/login/${role}`,{replace:true});}}><LogOut size={20} aria-hidden="true"/><span className="nav-label">Log out</span></button>;
  // Resolve anchors after asynchronous sections load, without stealing form focus on later renders.
  useSectionTarget(children);
  return <div className={`dash-shell ${role}${creative?' creative-studio':''}`}>
    {mobile?<><header className="workspace-mobile-header"><Logo/><span className="workspace-context">{workspaceLabel}</span><NotificationBell/></header><MobileNavigation items={links} role={role} creative={creative} professional={professional} accountControls={<><p className="session-identity">{auth.user?.name}</p>{logout}</>}/></>:<aside className="app-sidebar"><Logo light={role==='admin'}/><p className="eyebrow workspace-label">{workspaceLabel}</p><SidebarLinks items={links} label="Workspace navigation"/><NotificationBell/><p className="session-identity">{auth.user?.name}</p>{logout}<Link className="back-home" to="/" aria-label="Back to marketplace" title="Back to marketplace"><House size={20} aria-hidden="true"/><span className="nav-label">Back to marketplace</span></Link></aside>}
    <main id="main-content" tabIndex={-1}>{children}</main></div>;
}
export function PageTop({ eyebrow,title,action }: { eyebrow:string;title:string;action?:ReactNode }) { return <div className="page-top"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div>{action}</div>; }
export function Metric({ label,value,note }: {label:string;value:string|number;note?:string}) { return <div className="metric"><span>{label}</span><strong>{value}</strong>{note&&<small>{note}</small>}</div>; }
export function CartIcon({ count }: { count:number }) { return <span className="cart-icon"><ShoppingBag/>{count>0&&<b>{count}</b>}</span>; }
