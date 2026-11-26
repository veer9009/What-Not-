import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { House, Plus, Package, Palette, Search, ShoppingBag, UserRound, Code2, HousePlus, X } from 'lucide-react';
import type { NavigationItem } from './Shared';
import '../styles/mobile-navigation-polish.css';

const MENU_EVENT='whatnot:open-mobile-menu';
export function openMobileMenu(){window.dispatchEvent(new Event(MENU_EVENT));}

export function useMobileNavigation(){
  const [mobile,setMobile]=useState(()=>typeof matchMedia==='function'&&matchMedia('(max-width: 760px)').matches);
  useEffect(()=>{
    if(typeof matchMedia!=='function')return;
    const media=matchMedia('(max-width: 760px)'),update=()=>setMobile(media.matches);
    update();media.addEventListener?.('change',update);
    return()=>media.removeEventListener?.('change',update);
  },[]);
  return mobile;
}

type Role='buyer'|'seller'|'admin';
type Panel='more'|'create'|null;
export function MobileNavigation({items,role,creative=false,professional=false,accountControls}:{items:NavigationItem[];role?:Role;creative?:boolean;professional?:boolean;accountControls?:ReactNode}){
  const location=useLocation(),[panel,setPanel]=useState<Panel>(null);
  const dialog=useRef<HTMLDialogElement>(null),returnFocus=useRef<HTMLElement|null>(null),restore=useRef(false);
  const exploreHref=role==='buyer'?'/buyer':'/#explore';
  const ordersHref=role==='admin'?'/admin/operations':role?`/${role}/orders`:'/login/buyer';
  const all=[...items,{href:'/',label:'Home',icon:House}];
  const exact=all.find(item=>item.href===location.pathname+location.hash);
  const active=exact??all.filter(item=>item.matchPrefix?location.pathname.startsWith(item.matchPrefix):!item.href.includes('#')&&item.href!=='/'&&(location.pathname===item.href||location.pathname.startsWith(item.href+'/'))).sort((a,b)=>(b.matchPrefix??b.href).length-(a.matchPrefix??a.href).length)[0];
  const homeActive=location.pathname==='/'&&!location.hash;
  const exploreActive=location.pathname+location.hash===exploreHref||location.pathname==='/creative-services'||location.pathname==='/professional-services';
  const ordersActive=Boolean(role&&(location.pathname===ordersHref||location.pathname.startsWith(ordersHref+'/')));
  const createActive=role==='seller'&&location.pathname==='/seller/products/new';
  const profileActive=Boolean(active&&!homeActive&&!exploreActive&&!ordersActive&&!createActive);
  const destinations=items.filter((item,index)=>items.findIndex(other=>other.href===item.href&&other.label===item.label)===index);
  if(!destinations.some(item=>item.href==='/'))destinations.push({href:'/',label:'Marketplace home',icon:House});
  const show=(next:Exclude<Panel,null>,source?:HTMLElement)=>{
    returnFocus.current=source??(document.activeElement instanceof HTMLElement?document.activeElement:null);
    restore.current=true;setPanel(next);
  };
  const close=()=>setPanel(null);
  const navigate=()=>{restore.current=false;setPanel(null);};
  useEffect(()=>{
    const open=()=>show('more');window.addEventListener(MENU_EVENT,open);
    return()=>window.removeEventListener(MENU_EVENT,open);
  },[]);
  useEffect(()=>{
    if(!panel)return;
    const element=dialog.current!;
    const previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';
    if(typeof element.showModal==='function')element.showModal();else element.setAttribute('open','');
    element.querySelector<HTMLButtonElement>('button')?.focus();
    return()=>{if(typeof element.close==='function')element.close();document.body.style.overflow=previousOverflow;if(restore.current&&returnFocus.current?.isConnected)returnFocus.current.focus();restore.current=false;};
  },[panel]);
  useEffect(()=>{restore.current=false;setPanel(null);},[location.key,role]);
  const current=(selected:boolean)=>selected?(location.hash?'location' as const:'page' as const):undefined;
  return <>
    <nav className="mobile-bottom-nav polished-mobile-navigation" aria-label="Primary navigation" data-items="5">
      <Link to="/" aria-current={current(homeActive)}><House size={21} aria-hidden="true"/><span>Home</span></Link>
      <Link to={exploreHref} aria-current={current(exploreActive)}><Search size={21} aria-hidden="true"/><span>Explore</span></Link>
      <button className="mobile-create-action" type="button" aria-label="Create" aria-expanded={panel==='create'} aria-controls="mobile-create-dialog" aria-haspopup="dialog" aria-current={current(createActive)} onClick={event=>show('create',event.currentTarget)}><span className="mobile-create-icon"><Plus size={25} aria-hidden="true"/></span><span>Create</span></button>
      <Link to={ordersHref} aria-current={current(ordersActive)}><ShoppingBag size={21} aria-hidden="true"/><span>Orders</span></Link>
      <button type="button" aria-label="Profile" aria-expanded={panel==='more'} aria-controls="mobile-more-dialog" aria-haspopup="dialog" aria-current={current(profileActive)} onClick={event=>show('more',event.currentTarget)}><UserRound size={21} aria-hidden="true"/><span>Profile</span></button>
    </nav>
    {panel&&<dialog ref={dialog} id={panel==='more'?'mobile-more-dialog':'mobile-create-dialog'} className="mobile-more-dialog polished-mobile-dialog" aria-modal="true" aria-labelledby="mobile-panel-title" onCancel={event=>{event.preventDefault();close();}} onKeyDown={event=>{
      if(event.key==='Escape'){event.preventDefault();close();return;}
      if(event.key!=='Tab')return;
      const controls=[...event.currentTarget.querySelectorAll<HTMLElement>('a[href],button:not([disabled])')];
      const first=controls[0],last=controls.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    }}>
      <div className="more-heading"><div><p className="eyebrow">{professional?'Professional Dashboard':creative?'Creative Studio':role?`${role} workspace`:'Marketplace'}</p><h2 id="mobile-panel-title">{panel==='more'?'More destinations':'Create something local'}</h2></div><button type="button" className="icon-button" aria-label={panel==='more'?'Close navigation':'Close create'} onClick={close}><X size={22} aria-hidden="true"/></button></div>
      {panel==='more'?<><nav aria-label="More destinations">{destinations.map(({href,label,icon:Icon})=><Link key={`${href}:${label}`} to={href} aria-current={active?.href===href?(href.includes('#')?'location':'page'):undefined} onClick={navigate}><Icon size={20} aria-hidden="true"/><span>{label}</span></Link>)}</nav>{accountControls&&<div className="more-account">{accountControls}</div>}</>:role==='seller'?<><p className="mobile-create-guidance">Choose what you want to offer. Your existing profile and approval requirements still apply.</p><nav aria-label="Creation workflows">{[
        {href:'/seller/products/new',label:'Add product',icon:Package},
        {href:'/seller/creative#services',label:'Creative service',icon:Palette},
        {href:'/seller/professional#services',label:'Professional service',icon:Code2},
        {href:'/seller/properties',label:'Property listing',icon:HousePlus},
      ].map(({href,label,icon:Icon})=><Link key={href} to={href} onClick={navigate}><Icon size={20} aria-hidden="true"/><span>{label}</span></Link>)}</nav></>:role==='admin'?<><p className="mobile-create-guidance">Review listings and manage marketplace operations in your administrator workspace.</p><nav aria-label="Administrator workspace"><Link to="/admin" onClick={navigate}>Open moderation workspace</Link></nav></>:<><p className="mobile-create-guidance">Listings are created through a seller account. Register as a seller or sign in with your seller account to get started.</p><nav aria-label="Seller account options"><Link to="/register?role=seller" onClick={navigate}>Register as a seller</Link><Link to="/login/seller" onClick={navigate}>Sign in as a seller</Link></nav></>}
    </dialog>}
  </>;
}
