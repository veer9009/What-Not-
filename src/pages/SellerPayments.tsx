import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Banknote, CheckCircle, Clock, FileText, RefreshCw, Wallet } from 'lucide-react';
import { paymentsApi, type PaymentRecord, type PaymentMethod } from '../api/payments';
import { PaymentMethodLabel, paymentStatusLabels } from '../components/PaymentPresentation';
import { PageTop } from '../components/Shared';
import { CollectionNotice } from '../components/LegalNavigation';
import { useMobileNavigation } from '../components/MobileNavigation';
import { paymentSummary } from '../utils/paymentSummary';
import { useResource } from '../state/useResource';
import '../styles/seller-payments.css';

export type PaymentAction=(operation:()=>Promise<unknown>,orderId:string)=>Promise<boolean>;
const labels=paymentStatusLabels;
const money=(value:string)=>`INR ${value}`;
const date=(value:string|null)=>value?new Date(value).toLocaleString():'Not recorded';
type Props={rows:PaymentRecord[]|null;loading:boolean;loadError:string;actionError:string;notice:string;busy:boolean;offset:number;hasMore:boolean;refresh:()=>void;changePage:(offset:number)=>void;act:PaymentAction};
type StatusFilter='ALL'|'COD_PENDING'|'UPI_PENDING'|'CONFIRMED';
function matchesStatus(row:PaymentRecord,filter:StatusFilter){
  if(filter==='ALL')return true;
  if(filter==='CONFIRMED')return row.status==='SELLER_CONFIRMED';
  if(['CANCELLED','REJECTED'].includes(row.order_status))return false;
  if(filter==='COD_PENDING')return row.method==='COD'&&row.status==='PENDING';
  return row.method==='UPI'&&['PENDING','BUYER_REPORTED'].includes(row.status);
}

export function SellerPayments({rows,loading,loadError,actionError,notice,busy,offset,hasMore,refresh,changePage,act}:Props){
  const mobile=useMobileNavigation();
  const [filter,setFilter]=useState<PaymentMethod|'ALL'>('ALL');
  const [statusFilter,setStatusFilter]=useState<StatusFilter>('ALL');
  const loadAccount=useCallback(async()=>paymentsApi.summary(),[rows]);
  const account=useResource(loadAccount);
  const filtered=rows?.filter(row=>(filter==='ALL'||row.method===filter)&&matchesStatus(row,statusFilter))??[];
  const summary=rows?paymentSummary(rows):null;
  const cards=[
    {label:'Displayed Orders Value',value:summary?.orderValue,icon:Wallet,accent:'orders'},
    {label:'Confirmed Received',value:summary?.collectedValue,icon:CheckCircle,accent:'confirmed'},
    {label:'Awaiting Collection',value:summary?.awaitingValue,icon:Clock,accent:'awaiting'},
  ];
  return <div className="seller-payments">
    <PageTop eyebrow="Seller Studio" title="Payments" action={<button className="btn btn-outline" aria-label="Refresh payments" disabled={busy||loading} onClick={refresh}><RefreshCw size={18} aria-hidden="true"/>Refresh</button>}/>
    <p className="seller-payments-subtitle">Track this page's orders and recorded collections.</p>
    <section className="seller-payment-summary" aria-label="All owned orders payment summary" aria-busy={account.loading}>
      <h2>All your orders</h2><p>Account totals from all your orders, across every page. Recorded collections are not bank verification; external refunds are not deducted.</p>
      {account.error?<><p role="alert">Account totals unavailable: {account.error}</p><button className="btn btn-outline" onClick={()=>void account.reload()}>Retry account totals</button></>:<dl className="seller-payment-metrics">{[
        ['Order value',account.data?.order_value],['Confirmed collections',account.data?.confirmed_collections],['Pending COD collections',account.data?.pending_cod_collections],['UPI awaiting verification',account.data?.upi_awaiting_verification],['Platform revenue',account.data?.platform_revenue],
      ].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{account.loading||!value?'Unavailable':money(value)}</dd></div>)}</dl>}
    </section>
    <section className="seller-payment-summary" aria-label="Payment summary on this page">
      <div className="seller-payments-section-heading"><h2>On this page</h2>{rows&&<span>{rows.length} {rows.length===1?'order':'orders'} shown</span>}</div>
      <p className="seller-payment-scope">Loaded page, up to 50 records; not your full account or all seller orders.</p>
      <dl className="seller-payment-metrics">{cards.map(({label,value,icon:Icon,accent})=><div key={label} data-accent={accent}><dt><Icon size={18} aria-hidden="true"/>{label}</dt><dd>{value===undefined?'Unavailable':money(value)}</dd></div>)}</dl>
      <p className="seller-payment-scope">Gross records, not bank-verified. External refunds are not deducted.</p>
    </section>
    <section className="seller-payment-records" aria-label="Payment-related orders" aria-busy={loading}>
      <h2>Payment records</h2>
      <div className="payment-method-filters" role="group" aria-label="Filter payment methods">{([{value:'ALL',label:'All Payments'},{value:'COD',label:'COD'},{value:'UPI',label:'UPI'}] as const).map(item=><button key={item.value} type="button" aria-pressed={filter===item.value} disabled={loading||!rows} onClick={()=>setFilter(item.value)}>{item.label}</button>)}</div>
      <div className="payment-method-filters" role="group" aria-label="Filter payment statuses">{([{value:'ALL',label:'All statuses'},{value:'COD_PENDING',label:'Pending collection'},{value:'UPI_PENDING',label:'Awaiting verification'},{value:'CONFIRMED',label:'Confirmed received'}] as const).map(item=><button key={item.value} type="button" aria-pressed={statusFilter===item.value} disabled={loading||!rows} onClick={()=>setStatusFilter(item.value)}>{item.label}</button>)}</div>
      {rows&&<p className="seller-payment-filter-scope" aria-live="polite">{filtered.length} of {rows.length} loaded records shown. Filters apply to this page; summary cards include all loaded records.</p>}
      {actionError&&<p className="seller-payment-error" role="alert">{actionError}</p>}
      {notice&&<p className="success-note" role="status">{notice}</p>}
      {loading?<p className="seller-payment-state" role="status">Loading payment records…</p>:loadError?<div className="seller-payment-state seller-payment-error" role="alert"><p>{loadError}</p><button className="btn btn-outline" onClick={refresh}>Retry</button></div>:filtered.length?mobile?<div className="seller-payment-card-list">{filtered.map(row=><SellerRecord key={row.order_id} row={row} mobile busy={busy} act={act}/>)}</div>:<table className="seller-payment-table" aria-label="Payment records"><thead><tr>{['Order','Amount','Method','Recorded status','Order date','Actions'].map(label=><th key={label} scope="col">{label}</th>)}</tr></thead><tbody>{filtered.map(row=><SellerRecord key={row.order_id} row={row} mobile={false} busy={busy} act={act}/>)}</tbody></table>:rows?.length&&statusFilter!=='ALL'?<div className="seller-payment-state"><h3>No matching payment records on this page</h3><p>Choose another status or reset the filters to see all loaded records.</p><button className="btn btn-outline" onClick={()=>{setFilter('ALL');setStatusFilter('ALL');}}>Show all payments</button></div>:rows?.length&&filter!=='ALL'?<div className="seller-payment-state"><h3>No {filter} records on this page</h3><p>Other methods may be present in the loaded records.</p><button className="btn btn-outline" onClick={()=>setFilter('ALL')}>Show all payments</button></div>:<div className="seller-payment-state"><h3>No payment records on this page</h3><p>Review your orders for incoming Homemade orders and their payment details.</p><Link className="btn btn-outline" to="/seller/orders">View orders</Link></div>}
      {rows&&<nav className="workspace-pagination" aria-label="Payments pages"><button className="btn btn-outline" disabled={busy||loading||offset===0} onClick={()=>changePage(Math.max(0,offset-50))}>Previous page</button><span aria-live="polite">Page {offset/50+1}</span><button className="btn btn-outline" disabled={busy||loading||!hasMore} onClick={()=>changePage(offset+50)}>Next page</button></nav>}
    </section>
    <details className="seller-payment-guidance"><summary>Payment guidance and limitations</summary>
      <p>What Not? does not collect funds or charge commission. Delivery is seller-managed. Buyers pay by COD or direct UPI to you. COD is due at delivery; order delivery never confirms receipt.</p>
      <p>A buyer report is a claim, not verified payment. Confirm collection only after checking your cash or UPI account. Your confirmation records receipt; it is not bank verification.</p>
      <CollectionNotice label="Payments">Payment references are visible to the order's buyer, seller and authorised administrators. Never enter UPI PINs, bank passwords or other payment credentials.</CollectionNotice>
      <p>Buyers explicitly choose a payment method for each seller during checkout, then review and confirm the order. Prepaid UPI is disabled by default; enabling it requires an approved refund policy and manually reviewed seller payment details. References are optional and do not prove receipt.</p>
      <p>Order value includes cancelled/rejected orders. Awaiting collection excludes cancelled/rejected orders and unrecorded methods. Confirmed Received is gross seller-recorded collection, including cancelled orders; external refunds are not tracked or deducted. These are page totals, not earnings or platform revenue.</p>
      {summary&&<p>{summary.codPending} COD orders awaiting collection · {summary.upiPending} UPI orders awaiting confirmation. Method not recorded: {money(summary.unrecordedValue)}.</p>}
      <p>There is no gateway, wallet, escrow, automatic refund or bank verification. Arrange any refund directly with the buyer; a cancelled order does not erase a recorded collection. Delivery disputes and payment records are separate.</p>
      <p>A confirmation date is when you recorded collection, not a bank transaction date. Historical orders remain unrecorded until a method is explicitly selected.</p>
    </details>
  </div>;
}

function SellerRecord({row,mobile,busy,act}:{row:PaymentRecord;mobile:boolean;busy:boolean;act:PaymentAction}){
  const [reviewing,setReviewing]=useState(false),titleId=useId();
  const origin=useRef<HTMLButtonElement|null>(null),restoreFocus=useRef(false);
  useEffect(()=>{if(!reviewing&&restoreFocus.current){origin.current?.focus();restoreFocus.current=false;}},[reviewing]);
  const title=`payment-order-${row.order_id}`;
  const heading=<h3 id={title} tabIndex={-1}>Order #{row.order_id}</h3>;
  const status=<div className="seller-record-status"><span className="payment-status" data-status={row.status}>{labels[row.status]??'Unavailable'}</span>{row.status==='BUYER_REPORTED'&&<small className="payment-unverified">Buyer report · unverified</small>}{row.reference&&<p className="seller-record-reference">Reference: {row.reference}</p>}</div>;
  const method=<PaymentMethodLabel method={row.method}/>;
  const orderDate=<time dateTime={row.order_date}>{date(row.order_date)}</time>;
  const details=<details className="seller-record-details"><summary>Reference and dates</summary><dl><div><dt>Payment reference</dt><dd>{row.reference??'Not recorded'}</dd></div><div><dt>Buyer reported at</dt><dd>{date(row.reported_at)}</dd></div><div><dt>Seller confirmed at</dt><dd>{date(row.confirmed_at)}</dd></div><div><dt>Order status</dt><dd>{row.order_status.replaceAll('_',' ')}</dd></div></dl></details>;
  const actions=<div className="seller-payment-actions"><Link className="text-link" to={`/seller/orders/${row.order_id}`}><FileText size={16} aria-hidden="true"/>View details</Link>
    {['CANCELLED','REJECTED'].includes(row.order_status)&&<p>Order cancelled or rejected. Any collection remains recorded; external refunds are not tracked here.</p>}
    {row.method==='COD'&&row.status==='PENDING'&&!row.can_confirm&&!['CANCELLED','REJECTED'].includes(row.order_status)&&<p>Confirm COD only after delivery or completion is recorded, and after checking actual cash collection.</p>}
    {row.can_confirm&&!reviewing&&<button ref={origin} className="btn btn-primary" disabled={busy} onClick={()=>setReviewing(true)}><Banknote size={18} aria-hidden="true"/>Review collection</button>}</div>;
  // Existing receipt eligibility/payload; the desktop panel spans the full record width.
  const review=row.can_confirm&&reviewing?<section className="payment-confirmation" role="alertdialog" aria-modal="false" aria-labelledby={titleId}><h3 id={titleId}>Confirm collection for order #{row.order_id}</h3><p>{money(row.amount)} · {row.method} · Reference: {row.reference??'Not recorded'}</p><p>Check your cash or UPI account before confirming the full amount. This records your confirmation, not bank verification.</p><div className="form-actions"><button className="btn btn-outline" autoFocus disabled={busy} onClick={()=>{restoreFocus.current=true;setReviewing(false);}}>Cancel</button><button className="btn btn-primary" disabled={busy} onClick={()=>void act(()=>paymentsApi.confirm(row.order_id,row.status as 'PENDING'|'BUYER_REPORTED'),row.order_id)}><CheckCircle size={18} aria-hidden="true"/>Confirm collected</button></div></section>:null;
  return mobile?<article className="seller-payment-card" aria-labelledby={title}><header>{heading}{status}</header><dl className="seller-payment-facts"><div><dt>Amount</dt><dd className="seller-record-amount">{money(row.amount)}</dd></div><div><dt>Method</dt><dd>{method}</dd></div><div><dt>Order date</dt><dd>{orderDate}</dd></div></dl>{details}{actions}{review}</article>:<><tr><th scope="row">{heading}</th><td className="seller-record-amount">{money(row.amount)}</td><td>{method}</td><td>{status}</td><td>{orderDate}{details}</td><td>{actions}</td></tr>{review&&<tr className="seller-payment-review-row"><td colSpan={6}>{review}</td></tr>}</>;
}
