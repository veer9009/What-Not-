import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { House, LayoutDashboard, MoreHorizontal, Package, Palette, Images, MessageSquare, Search, ShoppingCart, ShoppingBag, Wallet, X } from 'lucide-react';
import type { NavigationItem } from './Shared';

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
function primaryItems(role:Role|undefined,creative:boolean):NavigationItem[]{
  if(role==='buyer')return [
    {href:'/',label:'Home',icon:House},{href:'/buyer',label:'Explore',icon:Search},
    {href:'/buyer/cart',label:'Cart',icon:ShoppingCart},{href:'/buyer/orders',label:'Orders',icon:ShoppingBag},
  ];
  if(role==='seller'&&creative)return [
    {href:'/seller/creative',label:'Overview',icon:LayoutDashboard},
    {href:'/seller/creative#services',label:'Services',icon:Palette},
    {href:'/seller/creative#enquiries',label:'Enquiries',icon:MessageSquare},
    {href:'/seller/creative#portfolio',label:'Portfolio',icon:Images},
  ];
  if(role==='seller')return [
    {href:'/seller',label:'Overview',icon:LayoutDashboard},{href:'/seller#products',label:'Products',icon:Package,matchPrefix:'/seller/products/'},
    {href:'/seller/orders',label:'Orders',icon:ShoppingBag},{href:'/seller/payments',label:'Payments',icon:Wallet},
  ];
  if(role==='admin')return [
    {href:'/admin',label:'Review',icon:LayoutDashboard},{href:'/admin/operations',label:'Operations',icon:ShoppingBag},
    {href:'/admin/payments',label:'Payments',icon:Wallet},
  ];
  return [{href:'/',label:'Home',icon:House},{href:'/#explore',label:'Explore',icon:Search}];
}

export function MobileNavigation({items,role,creative=false,accountControls}:{items:NavigationItem[];role?:Role;creative?:boolean;accountControls?:ReactNode}){
  const location=useLocation(),[open,setOpen]=useState(false);
  const trigger=useRef<HTMLButtonElement>(null),dialog=useRef<HTMLDialogElement>(null),restore=useRef(false);
  const primary=primaryItems(role,creative).filter(item=>!creative||items.some(existing=>existing.href===item.href));
  const all=[...items,...primary];
  const exact=all.find(item=>item.href===location.pathname+location.hash);
  const active=exact??all.filter(item=>item.matchPrefix?location.pathname.startsWith(item.matchPrefix):!item.href.includes('#')&&item.href!=='/'&&(location.pathname===item.href||location.pathname.startsWith(item.href+'/'))).sort((a,b)=>(b.matchPrefix??b.href).length-(a.matchPrefix??a.href).length)[0];
  const secondary=items.filter(item=>!primary.some(first=>first.href===item.href));
  if(role&&!all.some(item=>item.href==='/'))secondary.push({href:'/',label:'Marketplace home',icon:House});
  const primaryActive=primary.find(item=>item.href===active?.href)??primary.find(item=>item.matchPrefix&&location.pathname.startsWith(item.matchPrefix));
  const secondaryActive=Boolean(active&&!primaryActive);
  const close=()=>{restore.current=true;setOpen(false);};
  useEffect(()=>{
    if(!open)return;
    const element=dialog.current!;
    const previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';
    if(typeof element.showModal==='function')element.showModal();else element.setAttribute('open','');
    element.querySelector<HTMLButtonElement>('button')?.focus();
    return()=>{if(typeof element.close==='function')element.close();document.body.style.overflow=previousOverflow;if(restore.current)trigger.current?.focus();restore.current=false;};
  },[open]);
  useEffect(()=>{setOpen(false);},[location.key]);
  return <>
    <nav className="mobile-bottom-nav" aria-label="Primary navigation" data-items={primary.length+1}>
      {primary.map(({href,label,icon:Icon})=><Link key={href} to={href} aria-current={primaryActive?.href===href?(location.hash&&href===location.pathname+location.hash?'location':'page'):undefined}><Icon size={21} aria-hidden="true"/><span>{label}</span></Link>)}
      <button ref={trigger} type="button" aria-label={role==='buyer'?'Account and more navigation':'More navigation'} aria-expanded={open} aria-controls="mobile-more-dialog" aria-haspopup="dialog" aria-current={secondaryActive?(location.hash?'location':'page'):undefined} onClick={()=>setOpen(true)}><MoreHorizontal size={21} aria-hidden="true"/><span>{role==='buyer'?'Account':'More'}</span></button>
    </nav>
    {open&&<dialog ref={dialog} id="mobile-more-dialog" className="mobile-more-dialog" aria-modal="true" aria-labelledby="mobile-more-title" onCancel={event=>{event.preventDefault();close();}} onKeyDown={event=>{
      if(event.key==='Escape'){event.preventDefault();close();return;}
      if(event.key!=='Tab')return;
      const controls=[...event.currentTarget.querySelectorAll<HTMLElement>('a[href],button:not([disabled])')];
      const first=controls[0],last=controls.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    }}>
      <div className="more-heading"><div><p className="eyebrow">{creative?'Creative Studio':role?`${role} workspace`:'Marketplace'}</p><h2 id="mobile-more-title">More destinations</h2></div><button type="button" className="icon-button" aria-label="Close navigation" onClick={close}><X size={22} aria-hidden="true"/></button></div>
      <nav aria-label="More destinations">{secondary.map(({href,label,icon:Icon})=><Link key={`${href}:${label}`} to={href} aria-current={active?.href===href?(href.includes('#')?'location':'page'):undefined} onClick={()=>{restore.current=false;setOpen(false);}}><Icon size={20} aria-hidden="true"/><span>{label}</span></Link>)}</nav>
      {accountControls&&<div className="more-account">{accountControls}</div>}
    </dialog>}
  </>;
}
