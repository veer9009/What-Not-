import { useCallback, useLayoutEffect, useId, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { FileText, RefreshCw, Wallet } from 'lucide-react';
import { paymentsApi, type PaymentMethod, type PaymentRecord, type PaymentMetrics } from '../api/payments';
import { ApiError, errorMessage } from '../api/client';
import { DashboardShell, PageTop } from '../components/Shared';
import { CollectionNotice } from '../components/LegalNavigation';
import { ErrorNotice, Loading } from '../components/ApiStates';
import { useAuth } from '../state/AuthContext';
import { useMounted } from '../state/useMounted';
import { useResource } from '../state/useResource';
import { SellerPayments } from './SellerPayments';
import { PaymentMethodLabel, paymentStatusLabels } from '../components/PaymentPresentation';
import { Smartphone, Truck } from 'lucide-react';
import '../styles/payments.css';

const labels=paymentStatusLabels;
const money=(value:string)=>`INR ${value}`; // Preserve exact decimal strings, including aggregate values.
function date(value:string|null){return value?new Date(value).toLocaleString():'Not recorded';}
type Act=(operation:()=>Promise<unknown>,orderId:string)=>Promise<boolean>;

export function PaymentsPage(){
  const {user}=useAuth();const role=user!.role.toLowerCase() as 'buyer'|'seller'|'admin';
  const admin=role==='admin';const [offset,setOffset]=useState(0);
  const load=useCallback(async()=>({offset,page:await paymentsApi.list(offset),metrics:admin?await paymentsApi.metrics():null}),[offset,admin]);
  const resource=useResource(load),mounted=useMounted();const saving=useRef(false);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const focusOrder=useRef<string|null>(null),focusPage=useRef(false);
  useLayoutEffect(()=>{if(!resource.loading&&resource.data?.offset===offset&&(focusOrder.current||focusPage.current)){const orderId=focusOrder.current??resource.data.page.items[0]?.order_id;const target=document.getElementById(`payment-order-${orderId}`)??document.getElementById('main-content');target?.focus();focusOrder.current=null;focusPage.current=false;}},[resource.loading,resource.data,offset]);
  function changePage(next:number){focusPage.current=true;setOffset(next);}
  async function act(operation:()=>Promise<unknown>,orderId:string){
    if(saving.current)return false;saving.current=true;setBusy(true);setError('');setNotice('');
    try{await operation();if(!mounted.current)return true;focusOrder.current=orderId;const refreshed=await resource.reload();if(mounted.current)setNotice(refreshed?'Payment record saved.':'Saved. Refresh to see the current payment record.');return true;}
    catch(reason){if(mounted.current)setError(reason instanceof ApiError&&reason.status===409?'The payment record changed or this action is no longer allowed. Refresh and review before retrying.':reason instanceof ApiError&&reason.status===422?'Check the payment method and reference. Use up to 100 letters, digits, spaces or - _ . / in a reference.':errorMessage(reason));return false;}
    finally{saving.current=false;if(mounted.current)setBusy(false);}
  }
  const sellerLoading=resource.loading||Boolean(resource.data&&resource.data.offset!==offset);
  if(role==='seller')return <DashboardShell role="seller"><SellerPayments rows={!sellerLoading&&!resource.error?resource.data?.page.items??null:null} loading={sellerLoading} loadError={resource.error} actionError={error} notice={notice} busy={busy} offset={offset} hasMore={resource.data?.offset===offset&&resource.data.page.has_more} refresh={()=>void resource.reload()} changePage={changePage} act={act}/></DashboardShell>;
  return <DashboardShell role={role}><div className="payments-workspace"><PageTop eyebrow={admin?'Administration':'Direct payments'} title={admin?'Payments & Transactions':'Payments'} action={<button className="btn btn-outline" disabled={busy||resource.loading} onClick={()=>void resource.reload()}><RefreshCw size={18} aria-hidden="true"/>Refresh payments</button>}/>
    <p>{role==='buyer'?'Pay your seller by COD or direct UPI. COD is due at delivery; placing an order never confirms payment.':'Review order values and seller-recorded collections. Buyer reports remain unverified claims.'} Delivery is seller-managed. What Not? does not collect funds or charge commission.</p>
    <p className="payment-disclosure">A buyer report is a claim. Seller confirmation is not bank verification. Order delivery never confirms payment. This app does not issue refunds; arrange any external refund with the seller.</p>
    <CollectionNotice label="Payments">Payment references are visible to the order's buyer, seller and authorised administrators. Never enter UPI PINs, bank passwords or other payment credentials.</CollectionNotice>
    <details className="panel payment-help"><summary>Payment records and limitations</summary><p>Select the method in Payments after placing your order. For UPI, use payment details shared directly by the seller; this app provides no verified UPI directory. References are optional and do not prove receipt.</p><p>Order value is not seller collections or platform revenue. There is no gateway, wallet, escrow, automatic refund or bank verification. Arrange any refund directly with the seller; a cancelled order does not erase a recorded collection. Delivery disputes and payment records are separate.</p><p>A displayed confirmation date is when the seller recorded collection, not a bank transaction date. Historical orders remain unrecorded until a method is explicitly selected.</p></details>
    {error&&<ErrorNotice message={error}/ >}{notice&&<p role="status" className="success-note">{notice}</p>}
    {resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:resource.data&&<>
      {resource.data.metrics&&<Metrics data={resource.data.metrics}/>}
      <section className="payment-records" aria-label="Payment-related orders">{resource.data.page.items.length?resource.data.page.items.map(row=><PaymentCard key={row.order_id} row={row} role={role} busy={busy} act={act}/>):<div className="panel"><h2>No payment-related orders</h2><p>Your recorded orders will appear here. No payment details have been inferred.</p></div>}</section>
      <nav className="workspace-pagination" aria-label="Payments pages"><button className="btn btn-outline" disabled={busy||offset===0} onClick={()=>changePage(Math.max(0,offset-50))}>Previous page</button><span aria-live="polite">Page {offset/50+1}</span><button className="btn btn-outline" disabled={busy||!resource.data.page.has_more} onClick={()=>changePage(offset+50)}>Next page</button></nav>
    </>}</div></DashboardShell>;
}

function Metrics({data}:{data:PaymentMetrics}){
  const values=[['Gross order value',money(data.order_value)],['COD order value',money(data.cod_order_value)],['Direct-UPI order value',money(data.upi_order_value)],['Method not recorded',money(data.unrecorded_order_value)],['Buyer-reported value',money(data.buyer_reported_value)],['Seller-confirmed collections',money(data.seller_confirmed_value)],['Cancelled/rejected order value',money(data.cancelled_order_value)],['Collections on cancelled/rejected orders',money(data.cancelled_confirmed_value)],['Platform revenue',money(data.platform_revenue)]];
  return <section className="panel" aria-label="Payment metrics"><h2>Order value and collections</h2><p>Order value is not seller collections or platform revenue. Gross values include cancelled/rejected orders; confirmed collections are gross and do not subtract untracked external refunds.</p><dl className="payment-metrics">{values.map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><p>{data.order_count} orders · {data.buyer_reported_count} buyer reports · {data.seller_confirmed_count} seller confirmations · {data.pending_confirmation_count} pending confirmations</p></section>;
}

function PaymentCard({row,role,busy,act}:{row:PaymentRecord;role:'buyer'|'admin';busy:boolean;act:Act}){
  const save=(operation:()=>Promise<unknown>)=>act(operation,row.order_id);
  return <article className="panel payment-record"><div className="panel-head"><h2 id={`payment-order-${row.order_id}`} tabIndex={-1}><Wallet size={20} aria-hidden="true"/>Order #{row.order_id}</h2><span className="payment-status" data-status={row.status}>{labels[row.status]}</span></div>
    <h3>{row.seller_name}</h3><strong className="payment-amount">{money(row.amount)}</strong><dl className="payment-facts payment-primary-facts">
      <div><dt>Method</dt><dd><PaymentMethodLabel method={row.method}/></dd></div>
      <div><dt>Order status</dt><dd>{row.order_status.replaceAll('_',' ')}</dd></div></dl>
    {row.status==='BUYER_REPORTED'&&<p className="payment-unverified">Buyer report · unverified</p>}
    <details className="payment-details"><summary>Dates and payment reference</summary><dl className="payment-facts"><div><dt>Order date</dt><dd>{date(row.order_date)}</dd></div>
      <div><dt>Payment reference</dt><dd>{row.reference??'Not recorded'}</dd></div><div><dt>Buyer reported at</dt><dd>{date(row.reported_at)}</dd></div><div><dt>Seller confirmed at</dt><dd>{date(row.confirmed_at)}</dd></div>
    </dl></details><Link className="text-link" to={role==='admin'?'/admin/operations':`/${role}/orders/${row.order_id}`}><FileText size={18} aria-hidden="true"/>{role==='admin'?'Order operations':'Order details'}</Link>
    {['CANCELLED','REJECTED'].includes(row.order_status)&&<p>Order cancelled or rejected. Any collection remains recorded; external refunds are not tracked here.</p>}
    {role==='buyer'&&row.method==='UPI'&&row.status==='PENDING'&&!row.can_report&&row.order_status==='PLACED'&&<p>Report UPI payment after the seller accepts the order.</p>}
    {role==='buyer'&&row.can_select_method&&<MethodForm busy={busy} save={method=>save(()=>paymentsApi.method(row.order_id,method))}/>}
    {role==='buyer'&&row.can_report&&<ReportForm busy={busy} save={reference=>save(()=>paymentsApi.report(row.order_id,reference))}/>}
  </article>;
}

function MethodForm({busy,save}:{busy:boolean;save:(method:PaymentMethod)=>Promise<boolean>}){
  const [method,setMethod]=useState('');const id=useId();
  return <form className="product-form" onSubmit={event=>{event.preventDefault();if(method==='COD'||method==='UPI')void save(method);}}><fieldset className="payment-method-options" disabled={busy}><legend>Payment method</legend>{([{value:'COD',title:'Cash on delivery (COD)',description:'Pay cash to your seller at delivery.',icon:Truck},{value:'UPI',title:'Direct UPI',description:'Pay your seller directly; report payment after acceptance.',icon:Smartphone}] as const).map(({value,title,description,icon:Icon})=><label className="payment-method-choice" key={value}><input type="radio" name={`payment-method-${id}`} value={value} required checked={method===value} onChange={()=>setMethod(value)}/><Icon size={23} aria-hidden="true"/><span><strong>{title}</strong><small>{description}</small></span></label>)}</fieldset><p>The recorded method cannot be changed here. Recording a method does not confirm collection.</p><button className="btn btn-outline" disabled={busy}>Record method</button></form>;
}

function ReportForm({busy,save}:{busy:boolean;save:(reference:string|null)=>Promise<boolean>}){
  const [reference,setReference]=useState(''),[consent,setConsent]=useState(false),[error,setError]=useState('');const id=useId();
  function submit(event:FormEvent){event.preventDefault();if(busy||!consent)return;const value=reference.trim();if(value&&!/^[A-Za-z0-9][A-Za-z0-9 _./-]{0,99}$/.test(value)){setError('Use up to 100 letters, digits, spaces or - _ . / in a reference.');return;}setError('');void save(value||null);}
  return <form className="product-form" onSubmit={submit}><label>Payment reference (optional)<input value={reference} maxLength={100} disabled={busy} onChange={event=>{setReference(event.target.value);setError('');}} aria-invalid={Boolean(error)} aria-describedby={error?id:undefined}/></label>{error&&<p id={id} role="alert">{error}</p>}<label className="checkbox-field"><input type="checkbox" required checked={consent} disabled={busy} onChange={event=>setConsent(event.target.checked)}/>I sent this payment directly to the seller</label><p>This is a buyer report; the seller must independently confirm receipt.</p><button className="btn btn-outline" disabled={busy}>Report payment</button></form>;
}
