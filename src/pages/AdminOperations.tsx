import { useCallback, useRef, useState } from 'react';
import { api, errorMessage, identifier } from '../api/client';
import type { Fulfillment, Order } from '../api/types';
import type { CreativeListing } from '../api/creative';
import { PageTop, EmptyState } from '../components/Shared';
import { AdminReasonField, AdminWorkspace, useAdminConfirmation } from '../components/AdminWorkspace';
import { Loading, ErrorNotice } from '../components/ApiStates';
import { orderStatusLabels } from '../components/OrderTracking';
import { useResource } from '../state/useResource';
import { useSearchParams } from 'react-router-dom';

interface Account{id:string;name:string;email:string;phone:string;role:string;is_active:boolean;phone_verified_at?:string|null;email_verified_at?:string|null}
interface Audit{id:string;actor_id:string|null;action:string;entity_type:string;entity_id:string;reason:string|null;created_at:string}
interface Operations{email_provider_enabled:boolean;outbox_counts:Record<string,number>;oldest_pending_at:string|null}

export function AdminOperationsPage(){
  const [offset,setOffset]=useState(0);const [filter,setFilter]=useState('');const [reason,setReason]=useState('');
  const [error,setError]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);const pending=useRef(false);
  const [delivery,setDelivery]=useState<Fulfillment|null>(null);const [productId,setProductId]=useState('');
  const confirmation=useAdminConfirmation();const locked=busy||confirmation.pending;
  const load=useCallback(async()=>{const [users,orders,audit,operations]=await Promise.all([
    api<Account[]>(`/admin/users?offset=${offset}&limit=50`),
    api<Order[]>(`/admin/orders?offset=${offset}&limit=50${filter?`&status=${filter}`:''}`),
    api<Audit[]>(`/admin/audit?offset=${offset}&limit=50`),api<Operations>('/admin/operations')]);return{users,orders,audit,operations};},[offset,filter]);
  const resource=useResource(load);
  function validReason(){if(!reason.trim()){setError('Enter an investigation reason before taking action.');return false;}return true;}
  async function act(operation:()=>Promise<unknown>){
    if(pending.current||!validReason())return;
    pending.current=true;setBusy(true);setError('');setNotice('');setDelivery(null);
    try{await operation();const refreshed=await resource.reload();setNotice(refreshed?'Action recorded and audited.':'Action recorded. Refresh to see current data.');}
    catch(failure){setError(errorMessage(failure));}finally{pending.current=false;setBusy(false);}
  }
  function confirm(operation:()=>Promise<unknown>,title:string,label:string,description:string){
    if(locked||!validReason())return;
    setError('');confirmation.request({title,label,description,onConfirm:()=>void act(operation)});
  }
  const resolve=(id:string,action:string,label:string)=>confirm(
    ()=>api(`/admin/orders/${identifier(id)}/resolve`,{method:'POST',body:{action,reason:reason.trim()}}),
    `Confirm resolution for order #${id}`,label,
    `This records the selected resolution using your investigation reason. Prepared or dispatched goods are not automatically restocked by investigated cancellation.`);
  return <AdminWorkspace>
    <PageTop eyebrow="Controlled beta operations" title="Orders, disputes and accounts"/>
    <p>Actions require an investigation reason and create an audit record. Dispatched or prepared goods are never automatically restocked by investigated cancellation.</p>
    <AdminReasonField label="Investigation reason" helpId="investigation-reason-help" help="Required for account actions, order resolutions, product takedowns and private delivery investigations. Record the evidence for this action; avoid unnecessary personal details." value={reason} disabled={locked} onChange={setReason}/>
    {error&&<ErrorNotice message={error}/ >}{notice&&<p className="success-note" role="status">{notice}</p>}
    {confirmation.content}
    {delivery&&<section className="panel admin-private-details" aria-label="Investigated delivery details"><h2>Investigated delivery details</h2><address>{delivery.recipient_name}<br/>{delivery.phone}<br/>{delivery.address_line1}<br/>{delivery.address_line2}<br/>{delivery.city}, {delivery.state} {delivery.pincode}</address></section>}
    {resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:resource.data&&<>
      <section className="panel admin-email-status" aria-labelledby="email-processing-title">
        <h2 id="email-processing-title">Email processing</h2>
        <p>{resource.data.operations.email_provider_enabled?'Email provider configured':'Email delivery disabled; events remain in the outbox until configured.'}</p>
        {Object.keys(resource.data.operations.outbox_counts).length?<dl className="admin-outbox">{Object.entries(resource.data.operations.outbox_counts).map(([state,count])=><div key={state}><dt>{state}</dt><dd>{count}</dd></div>)}</dl>:<p>No email events in the outbox.</p>}
        {resource.data.operations.oldest_pending_at&&<p>Oldest pending event: {new Date(resource.data.operations.oldest_pending_at).toLocaleString()}</p>}
        <p className="admin-help">Workers require an operator or external scheduler. Check the beta runbook before enabling them.</p>
      </section>
      <section className="panel" aria-labelledby="accounts-title">
        <div className="admin-section-head"><h2 id="accounts-title">Accounts</h2><span className="admin-help">Up to 50 accounts per page</span></div>
        {resource.data.users.length?<div className="admin-record-grid">{resource.data.users.map(account=><article className="admin-record" aria-labelledby={`account-${account.id}`} key={account.id}>
          <header><h3 id={`account-${account.id}`}>{account.name}</h3><div className="admin-badges"><span className="admin-badge">{account.role}</span><span className={`admin-badge ${account.is_active?'positive':'caution'}`}>{account.is_active?'Active':'Suspended'}</span></div></header>
          <dl className="admin-facts">
            <div><dt>Account</dt><dd>#{account.id}</dd></div>
            <div><dt>Email</dt><dd>{account.email}</dd></div>
            <div><dt>Phone</dt><dd>{account.phone}</dd></div>
            <div><dt>Phone verification</dt><dd>{account.phone_verified_at?'Manual phone verification recorded':'Phone not verified'}</dd></div>
            <div><dt>Email verification</dt><dd>{account.email_verified_at?'Manual email verification recorded':'Email not verified'}</dd></div>
          </dl>
          {account.role!=='ADMIN'?<div className="admin-actions">
            <button className={`btn ${account.is_active?'btn-danger':'btn-outline'}`} disabled={locked} onClick={()=>{
              const operation=()=>api(`/admin/users/${identifier(account.id)}/active`,{method:'PATCH',body:{is_active:!account.is_active,reason:reason.trim()}});
              if(account.is_active)confirm(operation,`Suspend ${account.name}?`,'Confirm suspension','This suspends account access and records your investigation reason in the audit trail.');
              else void act(operation);
            }}>{account.is_active?'Suspend':'Reactivate'} {account.name}</button>
            {!account.phone_verified_at&&<button className="btn btn-outline" disabled={locked} onClick={()=>void act(()=>api(`/admin/users/${identifier(account.id)}/verify`,{method:'POST',body:{channel:'phone',reason:reason.trim()}}))}>Record checked phone for {account.name}</button>}
            {!account.email_verified_at&&<button className="btn btn-outline" disabled={locked} onClick={()=>void act(()=>api(`/admin/users/${identifier(account.id)}/verify`,{method:'POST',body:{channel:'email',reason:reason.trim()}}))}>Record checked email for {account.name}</button>}
          </div>:<p className="admin-help">Administrator accounts cannot be changed here.</p>}
        </article>)}</div>:<EmptyState title="No accounts on this page" description="No accounts were returned for this page."/>}
      </section>
      <section className="panel" aria-labelledby="operations-orders-title">
        <div className="admin-section-head"><h2 id="operations-orders-title">Orders and delivery disputes</h2><label className="admin-field">Status filter<select value={filter} disabled={locked} onChange={event=>{setFilter(event.target.value);setOffset(0);setDelivery(null);}}><option value="">All orders</option>{['DELIVERY_DISPUTED','PLACED','ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','COMPLETED','CANCELLED','REJECTED'].map(status=><option value={status} key={status}>{orderStatusLabels[status as Order['status']]}</option>)}</select></label></div>
        {resource.data.orders.length?<div className="admin-record-grid">{resource.data.orders.map(order=><article className="admin-record" key={order.id} aria-labelledby={`admin-order-${order.id}`}>
          <header><h3 id={`admin-order-${order.id}`}>Order #{order.id}</h3><div className="admin-badges"><span className="admin-badge">{orderStatusLabels[order.status]}</span></div></header>
          <p>₹{order.total} · buyer #{order.buyer_id} · seller #{order.seller_id}</p>
          <p>{order.items.map(item=>`${item.name} × ${item.quantity} (product #${item.product_id})`).join(', ')}</p>
          <div className="admin-actions">
            {order.status==='DELIVERY_DISPUTED'&&<><button className="btn btn-primary" disabled={locked} onClick={()=>resolve(order.id,'COMPLETE_DISPUTE','Confirm delivered resolution')}>Resolve delivered #{order.id}</button><button className="btn btn-danger" disabled={locked} onClick={()=>resolve(order.id,'CANCEL_DISPUTE','Confirm cancellation')}>Resolve cancelled #{order.id}</button></>}
            {['PLACED','ACCEPTED'].includes(order.status)&&<button className="btn btn-danger" disabled={locked} onClick={()=>resolve(order.id,'CANCEL_STRANDED','Confirm cancellation')}>Cancel stranded order #{order.id}</button>}
            {['PREPARING','OUT_FOR_DELIVERY','DELIVERED'].includes(order.status)&&<button className="btn btn-danger" disabled={locked} onClick={()=>resolve(order.id,'CANCEL_INVESTIGATED','Confirm cancellation')}>Investigated cancellation #{order.id}</button>}
            <button className="btn btn-outline" disabled={locked} onClick={()=>void act(async()=>{setDelivery(await api<Fulfillment>(`/admin/orders/${identifier(order.id)}/fulfillment`,{method:'POST',body:{reason:reason.trim()}}));})}>Investigate delivery #{order.id}</button>
          </div>
        </article>)}</div>:<EmptyState title="No orders on this page" description="Change the status filter or page to inspect other orders."/>}
      </section>
      <div className="admin-utility-grid">
        <section className="panel admin-takedown"><h2>Product takedown</h2><p className="admin-help">Use the product identifier from the investigated listing.</p><label className="admin-field">Product ID<input value={productId} disabled={locked} onChange={event=>setProductId(event.target.value)} inputMode="numeric"/></label><button className="btn btn-danger" disabled={locked||!productId} onClick={()=>confirm(()=>api(`/admin/products/${identifier(productId)}/takedown`,{method:'POST',body:{reason:reason.trim()}}),`Take down product #${productId}?`,'Confirm takedown','This removes the product from public availability and records your investigation reason.')}>Take down product</button></section>
        <section className="panel admin-audit"><h2>Recent audit events</h2>{resource.data.audit.length?resource.data.audit.map(event=><article key={event.id}><b>{event.action}</b><p>{event.entity_type} #{event.entity_id} · actor #{event.actor_id??'system'} · {new Date(event.created_at).toLocaleString()}</p>{event.reason&&<p>{event.reason}</p>}</article>):<p className="admin-help">No audit events on this page.</p>}</section>
      </div>
      <nav className="admin-toolbar" aria-label="Operations pagination"><button className="btn btn-outline" disabled={locked||offset===0} onClick={()=>{setOffset(Math.max(0,offset-50));setDelivery(null);}}>Previous records</button><button className="btn btn-outline" disabled={locked||Math.max(resource.data.users.length,resource.data.orders.length,resource.data.audit.length)<50} onClick={()=>{setOffset(offset+50);setDelivery(null);}}>More records</button></nav>
    </>}
    <div className="admin-toolbar"><button className="btn btn-outline" disabled={locked||resource.loading} onClick={()=>{setDelivery(null);void resource.reload();}}>Refresh operations</button></div>
  </AdminWorkspace>;
}

export function CreativeModerationPage(){
  const [offset,setOffset]=useState(0);const [reason,setReason]=useState('');const [busy,setBusy]=useState(false);const pending=useRef(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const [params]=useSearchParams();
  const [domain,setDomain]=useState<'CREATIVE'|'PROFESSIONAL'>(()=>params.get('domain')==='PROFESSIONAL'?'PROFESSIONAL':'CREATIVE');
  const confirmation=useAdminConfirmation();const locked=busy||confirmation.pending;
  const identity=`${domain}:${offset}`;
  const load=useCallback(async()=>({identity:`${domain}:${offset}`,rows:await api<CreativeListing[]>(`/creative/admin/listings?offset=${offset}&limit=50&domain=${domain}`)}),[offset,domain]);const resource=useResource(load);
  async function moderate(listing:CreativeListing,status:string){
    if(pending.current)return;
    if(status!=='APPROVED'&&!reason.trim()){setError('Enter a rejection or takedown reason.');return;}
    if(status==='APPROVED'&&!listing.updated_at){setError('Refresh this listing before approving its reviewed version.');return;}
    pending.current=true;setBusy(true);setError('');setNotice('');
    try{await api(`/creative/admin/listings/${identifier(listing.id)}/moderate`,{method:'POST',body:status==='APPROVED'?{status,expected_updated_at:listing.updated_at}:{status,reason:reason.trim()}});const refreshed=await resource.reload();setNotice(refreshed?'Service moderation recorded.':'Moderation recorded. Refresh to see current state.');}
    catch(failure){setError(errorMessage(failure));}finally{pending.current=false;setBusy(false);}
  }
  function confirmModeration(listing:CreativeListing,status:'REJECTED'|'TAKEN_DOWN'){
    if(locked)return;
    if(!reason.trim()){setError('Enter a rejection or takedown reason.');return;}
    setError('');
    confirmation.request({title:`${status==='REJECTED'?'Reject':'Take down'} ${listing.title}?`,
      label:status==='REJECTED'?'Confirm rejection':'Confirm takedown',
      description:'This changes the service moderation status using the reason you entered. Review the listing and investigation before confirming.',
      onConfirm:()=>void moderate(listing,status)});
  }
  return <AdminWorkspace>
    <PageTop eyebrow="Creative Services" title="Service moderation"/>
    <label>Service domain<select value={domain} disabled={locked} onChange={event=>{setDomain(event.target.value as 'CREATIVE'|'PROFESSIONAL');setOffset(0);setReason('');setNotice('');setError('');}}><option value="CREATIVE">Creative Services</option><option value="PROFESSIONAL">Professional Services</option></select></label>
    <p>Review service details and portfolio references before approving. Rejections and takedowns require a clear reason.</p>
    <AdminReasonField label="Rejection or takedown reason" helpId="service-reason-help" help="Required to reject or take down a service. Explain the issue so the provider understands the moderation decision." value={reason} disabled={locked} onChange={setReason}/>
    {error&&<ErrorNotice message={error}/ >}{notice&&<p className="success-note" role="status">{notice}</p>}
    {confirmation.content}
    {resource.loading||(resource.data!==null&&resource.data.identity!==identity)?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:resource.data?.rows.length?
      <div className="admin-record-grid">{resource.data.rows.map(listing=><article className="panel admin-record" key={listing.id} aria-labelledby={`service-${listing.id}`}>
        <header><h2 id={`service-${listing.id}`}>{listing.title}</h2><div className="admin-badges"><span className="admin-badge">{listing.status.replaceAll('_',' ')}</span><span className="admin-badge">{listing.category}</span></div></header>
        <p>{listing.description}</p>
        <dl className="admin-facts"><div><dt>Pricing</dt><dd>{listing.pricing.replaceAll('_',' ')} · {listing.amount??'Quotation'} INR</dd></div><div><dt>Location</dt><dd>{listing.remote?'Remote':listing.locality}</dd></div><div><dt>Provider</dt><dd>#{listing.provider_id}</dd></div></dl>
        {listing.rejection_reason&&<p><b>Moderation reason:</b> {listing.rejection_reason}</p>}
        {listing.portfolio.length>0&&<div className="admin-actions">{listing.portfolio.map((url,index)=><a className="text-link" href={url} key={url} target="_blank" rel="noopener noreferrer">Portfolio reference {index+1}</a>)}</div>}
        <div className="admin-actions">
          {listing.status==='PENDING'&&<><button className="btn btn-primary" disabled={locked} onClick={()=>void moderate(listing,'APPROVED')}>Approve {listing.title}</button><button className="btn btn-danger" disabled={locked} onClick={()=>confirmModeration(listing,'REJECTED')}>Reject {listing.title}</button></>}
          {listing.status==='APPROVED'&&<button className="btn btn-danger" disabled={locked} onClick={()=>confirmModeration(listing,'TAKEN_DOWN')}>Take down {listing.title}</button>}
        </div>
      </article>)}</div>:<EmptyState title="No services on this page" description="No service listings were returned. Refresh or check another page."/>}
    <nav className="admin-toolbar" aria-label="Service moderation pagination"><button className="btn btn-outline" disabled={locked||resource.loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous services</button><button className="btn btn-outline" disabled={locked||resource.loading||resource.data?.identity!==identity||(resource.data?.rows.length??0)<50} onClick={()=>setOffset(offset+50)}>More services</button><button className="btn btn-outline" disabled={locked||resource.loading} onClick={()=>void resource.reload()}>Refresh services</button></nav>
  </AdminWorkspace>;
}
