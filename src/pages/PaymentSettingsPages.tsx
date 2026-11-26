import { useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, Wallet } from 'lucide-react';
import { DashboardShell, PageTop, EmptyState } from '../components/Shared';
import { Loading, ErrorNotice } from '../components/ApiStates';
import { paymentSettingsApi, type SellerPaymentSettings, type PaymentSettingsInput } from '../api/paymentSettings';
import { errorMessage } from '../api/client';
import { useResource } from '../state/useResource';
import '../styles/shopping-completion.css';

const reviewLabels:Record<string,string>={NOT_CONFIGURED:'Not configured',PENDING:'Pending admin review',APPROVED:'Admin reviewed',REJECTED:'Review rejected'};
export function SellerPaymentSettingsPage(){
  const resource=useResource(paymentSettingsApi.get);
  return <DashboardShell role="seller"><PageTop eyebrow="Shop settings" title="Payment settings" action={<Link className="text-link" to="/seller/payments">View payments</Link>}/><p>Choose accepted methods and submit your UPI destination for review. Admin review is not bank verification.</p>
    {resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:resource.data&&<SettingsForm key={resource.data.updated_at} settings={resource.data} reload={resource.reload}/>}</DashboardShell>;
}
function SettingsForm({settings,reload}:{settings:SellerPaymentSettings;reload:()=>Promise<unknown>}){
  const [form,setForm]=useState<PaymentSettingsInput>({upi_id:settings.upi_id,account_holder_name:settings.account_holder_name,accept_cod:settings.accept_cod,accept_upi:settings.accept_upi});
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');const pending=useRef(false);
  async function save(event:FormEvent){event.preventDefault();if(pending.current)return;pending.current=true;setBusy(true);setError('');setNotice('');try{await paymentSettingsApi.save({...form,upi_id:form.upi_id?.trim()||null,account_holder_name:form.account_holder_name?.trim()||null});setNotice('Payment settings saved. Changed destinations require a new review.');await reload();}catch(reason){setError(errorMessage(reason));}finally{pending.current=false;setBusy(false);}}
  return <section className="panel shopping-payment-settings"><p className="payment-review-state"><ShieldCheck size={20} aria-hidden="true"/>{reviewLabels[settings.verification_status]??settings.verification_status}</p>{settings.review_reason&&<p>Review note: {settings.review_reason}</p>}
    {!settings.upi_enabled&&<p role="status" className="payment-feature-notice">{settings.upi_unavailable_reason??'Prepaid UPI is disabled pending policy and destination approval.'}</p>}
    {error&&<ErrorNotice message={error}/>} {notice&&<p role="status">{notice}</p>}
    <form className="product-form" onSubmit={event=>void save(event)}><label>Seller UPI ID<input value={form.upi_id??''} disabled={busy} maxLength={255} autoComplete="off" onChange={e=>setForm({...form,upi_id:e.target.value})}/></label><label>Account holder name<input value={form.account_holder_name??''} disabled={busy} maxLength={120} onChange={e=>setForm({...form,account_holder_name:e.target.value})}/></label>
      <label className="checkbox-field"><input type="checkbox" checked={form.accept_cod} disabled={busy} onChange={e=>setForm({...form,accept_cod:e.target.checked})}/>Accept Cash on Delivery</label>
      <label className="checkbox-field"><input type="checkbox" checked={form.accept_upi} disabled={busy} onChange={e=>setForm({...form,accept_upi:e.target.checked})}/>Request direct UPI when approved</label><p className="approval-help">Saving details does not activate UPI. Changed payment details revoke the previous approval. Never enter a UPI PIN, bank password or OTP.</p><button className="btn btn-primary" disabled={busy}><Wallet size={18} aria-hidden="true"/>{busy?'Saving...':'Save payment settings'}</button></form></section>;
}
export function AdminPaymentSettingsPage(){
  const resource=useResource(paymentSettingsApi.admin);
  return <DashboardShell role="admin"><PageTop eyebrow="Payment safety" title="Seller payment destination reviews"/><p>Review submitted seller ownership evidence before approval. This is admin review, not bank verification. Approval alone does not activate prepaid UPI.</p>
    {resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:resource.data?.items.length?<div className="resource-list">{resource.data.items.map(settings=><DestinationReview key={`${settings.seller_id}:${settings.updated_at}`} settings={settings} reload={resource.reload}/>)}</div>:<EmptyState title="No payment destinations to review" description="Seller submissions will appear here."/>}</DashboardShell>;
}
function DestinationReview({settings,reload}:{settings:SellerPaymentSettings;reload:()=>Promise<unknown>}){
  const [reason,setReason]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');const pending=useRef(false);
  async function review(status:'APPROVED'|'REJECTED'){if(pending.current||!reason.trim())return;pending.current=true;setBusy(true);setError('');try{await paymentSettingsApi.review(settings.seller_id,{status,expected_updated_at:settings.updated_at,reason:reason.trim()});await reload();}catch(e){setError(errorMessage(e));}finally{pending.current=false;setBusy(false);}}
  return <section className="panel shopping-payment-settings"><h2>Seller #{settings.seller_id}</h2><dl><dt>UPI ID</dt><dd>{settings.upi_id??'Not submitted'}</dd><dt>Account holder</dt><dd>{settings.account_holder_name??'Not submitted'}</dd><dt>Review state</dt><dd>{reviewLabels[settings.verification_status]??settings.verification_status}</dd><dt>Revision</dt><dd>{settings.revision}</dd></dl>{settings.review_reason&&<p>Previous review: {settings.review_reason}</p>}{error&&<ErrorNotice message={error}/>}
    <label>Review reason<textarea value={reason} maxLength={1000} disabled={busy} onChange={e=>setReason(e.target.value)}/></label><div className="form-actions"><button className="btn btn-primary" disabled={busy||!reason.trim()||!settings.upi_id||!settings.account_holder_name} onClick={()=>void review('APPROVED')}>Approve destination</button><button className="btn btn-outline" disabled={busy||!reason.trim()} onClick={()=>void review('REJECTED')}>Reject destination</button></div></section>;
}
