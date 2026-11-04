import { useCallback, useRef, useState } from 'react';
import { api, errorMessage, identifier } from '../api/client';
import type { Fulfillment, Order } from '../api/types';
import type { CreativeListing } from '../api/creative';
import { DashboardShell, PageTop, EmptyState } from '../components/Shared';
import { Loading, ErrorNotice } from '../components/ApiStates';
import { orderStatusLabels } from '../components/OrderTracking';
import { useResource } from '../state/useResource';

interface Account{id:string;name:string;email:string;phone:string;role:string;is_active:boolean;phone_verified_at?:string|null;email_verified_at?:string|null}
interface Audit{id:string;actor_id:string|null;action:string;entity_type:string;entity_id:string;reason:string|null;created_at:string}
interface Operations{email_provider_enabled:boolean;outbox_counts:Record<string,number>;oldest_pending_at:string|null}

export function AdminOperationsPage(){
  const [offset,setOffset]=useState(0);const [filter,setFilter]=useState('');const [reason,setReason]=useState('');
  const [error,setError]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);const pending=useRef(false);
  const [delivery,setDelivery]=useState<Fulfillment|null>(null);const [productId,setProductId]=useState('');
  const load=useCallback(async()=>{const [users,orders,audit,operations]=await Promise.all([
    api<Account[]>(`/admin/users?offset=${offset}&limit=50`),
    api<Order[]>(`/admin/orders?offset=${offset}&limit=50${filter?`&status=${filter}`:''}`),
    api<Audit[]>(`/admin/audit?offset=${offset}&limit=50`),api<Operations>('/admin/operations')]);return{users,orders,audit,operations};},[offset,filter]);
  const resource=useResource(load);
  async function act(operation:()=>Promise<unknown>){
    if(pending.current)return;if(!reason.trim()){setError('Enter an investigation reason before taking action.');return;}
    pending.current=true;setBusy(true);setError('');setNotice('');setDelivery(null);
    try{await operation();const refreshed=await resource.reload();setNotice(refreshed?'Action recorded and audited.':'Action recorded. Refresh to see current data.');}
    catch(failure){setError(errorMessage(failure));}finally{pending.current=false;setBusy(false);}
  }
  const resolve=(id:string,action:string)=>act(()=>api(`/admin/orders/${identifier(id)}/resolve`,{method:'POST',body:{action,reason:reason.trim()}}));
  return <DashboardShell role="admin"><PageTop eyebrow="Controlled beta operations" title="Orders, disputes and accounts"/>
    <p>Actions require an investigation reason and create an audit record. Dispatched or prepared goods are never automatically restocked by investigated cancellation.</p>
    <label className="field">Investigation reason<textarea aria-label="Investigation reason" maxLength={1000} value={reason} disabled={busy} onChange={event=>setReason(event.target.value)}/></label>
    {error&&<ErrorNotice message={error}/ >}{notice&&<p role="status">{notice}</p>}
    {delivery&&<address>{delivery.recipient_name}<br/>{delivery.phone}<br/>{delivery.address_line1}<br/>{delivery.address_line2}<br/>{delivery.city}, {delivery.state} {delivery.pincode}</address>}
    {resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:resource.data&&<>
      <section className="panel"><h2>Email processing</h2><p>{resource.data.operations.email_provider_enabled?'Email provider configured':'Email delivery disabled; events remain in the outbox until configured.'}</p>
        {Object.entries(resource.data.operations.outbox_counts).map(([state,count])=><p key={state}>{state}: {count}</p>)}
        {resource.data.operations.oldest_pending_at&&<p>Oldest pending event: {new Date(resource.data.operations.oldest_pending_at).toLocaleString()}</p>}
        <p>Workers require an operator or external scheduler. Check the beta runbook before enabling them.</p></section>
      <section className="panel"><h2>Accounts</h2>{resource.data.users.map(account=><article key={account.id}><h3>{account.name}</h3><p>#{account.id} · {account.role} · {account.email} · {account.phone}</p>
        <p>{account.is_active?'Active':'Suspended'} · {account.phone_verified_at?'Manual phone verification recorded':'Phone not verified'} · {account.email_verified_at?'Manual email verification recorded':'Email not verified'}</p>
        {account.role!=='ADMIN'&&<div className="form-actions"><button disabled={busy} onClick={()=>void act(()=>api(`/admin/users/${identifier(account.id)}/active`,{method:'PATCH',body:{is_active:!account.is_active,reason:reason.trim()}}))}>{account.is_active?'Suspend':'Reactivate'} {account.name}</button>
          {!account.phone_verified_at&&<button disabled={busy} onClick={()=>void act(()=>api(`/admin/users/${identifier(account.id)}/verify`,{method:'POST',body:{channel:'phone',reason:reason.trim()}}))}>Record checked phone for {account.name}</button>}
          {!account.email_verified_at&&<button disabled={busy} onClick={()=>void act(()=>api(`/admin/users/${identifier(account.id)}/verify`,{method:'POST',body:{channel:'email',reason:reason.trim()}}))}>Record checked email for {account.name}</button>}</div>}</article>)}</section>
      <section className="panel"><h2>Orders and delivery disputes</h2><label>Status filter<select value={filter} disabled={busy} onChange={event=>{setFilter(event.target.value);setOffset(0);setDelivery(null);}}><option value="">All orders</option>{['DELIVERY_DISPUTED','PLACED','ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','COMPLETED','CANCELLED','REJECTED'].map(status=><option key={status}>{status}</option>)}</select></label>
        {resource.data.orders.length?resource.data.orders.map(order=><article key={order.id}><h3>Order #{order.id}</h3><p>{orderStatusLabels[order.status]} · ₹{order.total} · buyer #{order.buyer_id} · seller #{order.seller_id}</p>
          <p>{order.items.map(item=>`${item.name} × ${item.quantity} (product #${item.product_id})`).join(', ')}</p><div className="form-actions">
            {order.status==='DELIVERY_DISPUTED'&&<><button disabled={busy} onClick={()=>void resolve(order.id,'COMPLETE_DISPUTE')}>Resolve delivered #{order.id}</button><button disabled={busy} onClick={()=>void resolve(order.id,'CANCEL_DISPUTE')}>Resolve cancelled #{order.id}</button></>}
            {['PLACED','ACCEPTED'].includes(order.status)&&<button disabled={busy} onClick={()=>void resolve(order.id,'CANCEL_STRANDED')}>Cancel stranded order #{order.id}</button>}
            {['PREPARING','OUT_FOR_DELIVERY','DELIVERED'].includes(order.status)&&<button disabled={busy} onClick={()=>void resolve(order.id,'CANCEL_INVESTIGATED')}>Investigated cancellation #{order.id}</button>}
            <button disabled={busy} onClick={()=>void act(async()=>{setDelivery(await api<Fulfillment>(`/admin/orders/${identifier(order.id)}/fulfillment`,{method:'POST',body:{reason:reason.trim()}}));})}>Investigate delivery #{order.id}</button>
          </div></article>):<EmptyState title="No orders on this page" description="Change the status filter or page to inspect other orders."/>}</section>
      <section className="panel"><h2>Product takedown</h2><label>Product ID<input value={productId} onChange={event=>setProductId(event.target.value)} inputMode="numeric"/></label><button disabled={busy||!productId} onClick={()=>void act(()=>api(`/admin/products/${identifier(productId)}/takedown`,{method:'POST',body:{reason:reason.trim()}}))}>Take down product</button></section>
      <section className="panel"><h2>Recent audit events</h2>{resource.data.audit.map(event=><article key={event.id}><b>{event.action}</b><p>{event.entity_type} #{event.entity_id} · actor #{event.actor_id??'system'} · {new Date(event.created_at).toLocaleString()}</p>{event.reason&&<p>{event.reason}</p>}</article>)}</section>
      <div className="form-actions"><button disabled={busy||offset===0} onClick={()=>{setOffset(Math.max(0,offset-50));setDelivery(null);}}>Previous records</button><button disabled={busy||Math.max(resource.data.users.length,resource.data.orders.length,resource.data.audit.length)<50} onClick={()=>{setOffset(offset+50);setDelivery(null);}}>More records</button></div>
    </>}<button className="btn btn-outline" disabled={busy||resource.loading} onClick={()=>{setDelivery(null);void resource.reload();}}>Refresh operations</button></DashboardShell>;
}

export function CreativeModerationPage(){
  const [offset,setOffset]=useState(0);const [reason,setReason]=useState('');const [busy,setBusy]=useState(false);const pending=useRef(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const load=useCallback(()=>api<CreativeListing[]>(`/creative/admin/listings?offset=${offset}&limit=50`),[offset]);const resource=useResource(load);
  async function moderate(listing:CreativeListing,status:string){
    if(pending.current)return;
    if(status!=='APPROVED'&&!reason.trim()){setError('Enter a rejection or takedown reason.');return;}
    if(status==='APPROVED'&&!listing.updated_at){setError('Refresh this listing before approving its reviewed version.');return;}
    pending.current=true;setBusy(true);setError('');setNotice('');
    try{await api(`/creative/admin/listings/${identifier(listing.id)}/moderate`,{method:'POST',body:status==='APPROVED'?{status,expected_updated_at:listing.updated_at}:{status,reason:reason.trim()}});const refreshed=await resource.reload();setNotice(refreshed?'Service moderation recorded.':'Moderation recorded. Refresh to see current state.');}
    catch(failure){setError(errorMessage(failure));}finally{pending.current=false;setBusy(false);}
  }
  return <DashboardShell role="admin"><PageTop eyebrow="Creative Services" title="Service moderation"/>
    <label>Rejection or takedown reason<textarea value={reason} maxLength={1000} onChange={event=>setReason(event.target.value)}/></label>{error&&<ErrorNotice message={error}/ >}{notice&&<p role="status">{notice}</p>}
    {resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:resource.data?.map(listing=><article className="panel" key={listing.id}><h2>{listing.title}</h2><p>{listing.description}</p><p>{listing.category} · {listing.pricing} · {listing.amount??'Quotation'} INR · {listing.remote?'Remote':listing.locality}</p><p>{listing.status} · provider #{listing.provider_id}</p>{listing.rejection_reason&&<p>{listing.rejection_reason}</p>}
      {listing.portfolio.map(url=><p key={url}><a href={url} target="_blank" rel="noreferrer">Portfolio reference</a></p>)}
      {listing.status==='PENDING'&&<><button disabled={busy} onClick={()=>void moderate(listing,'APPROVED')}>Approve {listing.title}</button><button disabled={busy} onClick={()=>void moderate(listing,'REJECTED')}>Reject {listing.title}</button></>}
      {listing.status==='APPROVED'&&<button disabled={busy} onClick={()=>void moderate(listing,'TAKEN_DOWN')}>Take down {listing.title}</button>}</article>)}
    <div className="form-actions"><button disabled={busy||offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous services</button><button disabled={busy||(resource.data?.length??0)<50} onClick={()=>setOffset(offset+50)}>More services</button><button disabled={busy} onClick={()=>void resource.reload()}>Refresh services</button></div>
  </DashboardShell>;
}
