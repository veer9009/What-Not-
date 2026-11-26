import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import qrcode from 'qrcode-generator';
import { Copy, Printer, Smartphone, Wallet } from 'lucide-react';
import { paymentsApi, type PaymentInstructions, type PaymentRecord } from '../api/payments';
import type { Order } from '../api/types';
import { errorMessage } from '../api/client';
import { Loading, ErrorNotice } from './ApiStates';
import { paymentStatusLabels } from './PaymentPresentation';
import { useResource } from '../state/useResource';
import { refreshNotificationCount } from '../state/notificationEvents';
import '../styles/shopping-completion.css';

function approvedUri(data:PaymentInstructions,amount:string){
  if(!data.available||!data.upi_uri||!data.upi_id||!data.account_holder_name||data.amount!==amount||data.currency!=='INR')return null;
  try{const uri=new URL(data.upi_uri),keys=[...uri.searchParams.keys()];if(uri.protocol!=='upi:'||uri.hostname!=='pay'||uri.username||uri.password||uri.hash||new Set(keys).size!==keys.length||keys.some(k=>!['pa','pn','am','cu','tn','tr'].includes(k))||uri.searchParams.get('pa')!==data.upi_id||uri.searchParams.get('pn')!==data.account_holder_name||uri.searchParams.get('am')!==amount||uri.searchParams.get('cu')!=='INR')return null;return data.upi_uri;}catch{return null;}
}
function LocalPaymentQR({uri}:{uri:string}){
  const matrix=useMemo(()=>{const code=qrcode(0,'M');code.addData(uri);code.make();const size=code.getModuleCount();let path='';for(let y=0;y<size;y++)for(let x=0;x<size;x++)if(code.isDark(y,x))path+=`M${x+4} ${y+4}h1v1h-1z`;return {size:size+8,path};},[uri]);
  return <div className="payment-qr"><svg role="img" aria-label="Seller payment QR code" viewBox={`0 0 ${matrix.size} ${matrix.size}`} shapeRendering="crispEdges"><rect width="100%" height="100%" fill="#fff"/><path d={matrix.path} fill="#000"/></svg></div>;
}
export function ApprovedUPIInstructions({orderId,amount}:{orderId:string;amount:string}){
  const load=useCallback(()=>paymentsApi.instructions(orderId),[orderId]),resource=useResource(load);const [copyMessage,setCopyMessage]=useState('');
  useEffect(()=>{const refresh=()=>{void resource.reload();};const visible=()=>{if(document.visibilityState==='visible')refresh();};window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',visible);const timer=window.setInterval(refresh,30000);return()=>{window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',visible);window.clearInterval(timer);};},[resource.reload]);
  if(resource.loading)return <Loading/>;if(resource.error)return <ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>;if(!resource.data)return null;
  const data=resource.data,uri=approvedUri(data,amount);
  if(!uri)return <p role="status">{data.reason??'Approved payment instructions are unavailable. Do not transfer money; contact the seller or support.'}</p>;
  async function copy(){try{const current=await paymentsApi.instructions(orderId);if(approvedUri(current,amount)!==uri){setCopyMessage('Payment instructions changed. Review the current instructions before continuing.');await resource.reload();return;}await navigator.clipboard.writeText(current.upi_id!);setCopyMessage('UPI ID copied.');}catch{setCopyMessage('Payment instructions could not be revalidated or copied. Refresh before paying.');await resource.reload();}}
  async function openApp(){try{const current=await paymentsApi.instructions(orderId);const fresh=approvedUri(current,amount);if(fresh&&fresh===uri)window.location.assign(fresh);else{setCopyMessage('Payment instructions changed. Review the current instructions before continuing.');await resource.reload();}}catch{setCopyMessage('Payment instructions could not be revalidated. Do not transfer money until refreshed.');await resource.reload();}}
  return <section aria-label="Direct UPI instructions"><h3>Pay the seller directly</h3><p><strong>INR {amount}</strong> to {data.account_holder_name}</p><p>{data.verification_label??'Admin reviewed; not bank verified'}</p><p className="payment-destination">{data.upi_id}</p><LocalPaymentQR uri={uri}/><div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>void copy()}><Copy size={18} aria-hidden="true"/>Copy UPI ID</button><button type="button" className="btn btn-primary" onClick={()=>void openApp()}><Smartphone size={18} aria-hidden="true"/>Open UPI app</button></div>{copyMessage&&<p role="status">{copyMessage}</p>}<p className="approval-help">Use a compatible UPI app. Confirm the recipient and amount in that app. Never enter a UPI PIN, bank password or banking OTP here.</p></section>;
}
export function OrderPaymentPanel({orderId,role,onLoaded}:{orderId:string;role:'buyer'|'seller';onLoaded?:(payment:PaymentRecord)=>void}){
  const load=useCallback(()=>paymentsApi.get(orderId),[orderId]),resource=useResource(load);const [busy,setBusy]=useState(false),[error,setError]=useState(''),[reference,setReference]=useState(''),[attested,setAttested]=useState(false),[notice,setNotice]=useState('');const pending=useRef(false);
  useEffect(()=>{if(resource.data)onLoaded?.(resource.data);},[resource.data,onLoaded]);
  async function act(operation:()=>Promise<unknown>){if(pending.current)return;pending.current=true;setBusy(true);setError('');try{await operation();setAttested(false);await resource.reload();refreshNotificationCount();setNotice('Payment record updated.');}catch(reason){setError(errorMessage(reason));}finally{pending.current=false;setBusy(false);}}
  if(resource.loading)return <Loading/>;if(resource.error)return <ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>;const p=resource.data;if(!p)return null;
  const validReference=!reference.trim()||/^[A-Za-z0-9][A-Za-z0-9 _./-]{0,99}$/.test(reference.trim());
  return <section className="order-payment-panel" aria-label="Order payment"><h2><Wallet size={20} aria-hidden="true"/>Payment</h2><p>{p.method??'Method not recorded'} · {paymentStatusLabels[p.status]}</p>{p.method==='COD'&&p.status!=='SELLER_CONFIRMED'&&<p><strong>INR {p.amount} payable on delivery</strong></p>}
    {p.status!=='SELLER_CONFIRMED'?<p>Payment remains pending until the seller confirms actual receipt. Delivery status does not confirm payment.</p>:<p>Seller confirmed receipt of INR {p.amount}. This is not bank verification.</p>}
    {p.status==='BUYER_REPORTED'&&<p role="status">Awaiting seller verification. The buyer report and reference are not proof of payment.</p>}
    {['CANCELLED','REJECTED'].includes(p.order_status)&&<p>Cancellation does not confirm a refund. Any earlier collection remains recorded; arrange an external refund with the seller.</p>}
    {role==='buyer'&&p.method==='UPI'&&p.status==='PENDING'&&!['CANCELLED','REJECTED'].includes(p.order_status)&&<ApprovedUPIInstructions orderId={orderId} amount={p.amount}/>}
    {error&&<ErrorNotice message={error}/>} {notice&&<p role="status">{notice}</p>}
    {role==='buyer'&&p.can_report&&<form className="product-form" onSubmit={event=>{event.preventDefault();if(attested&&validReference)void act(()=>paymentsApi.report(orderId,reference.trim()||null));}}><label>Payment reference (optional)<input value={reference} maxLength={100} disabled={busy} aria-invalid={!validReference} onChange={e=>setReference(e.target.value)}/></label>{!validReference&&<p role="alert">Use up to 100 letters, digits, spaces or - _ . /.</p>}<label className="checkbox-field"><input type="checkbox" checked={attested} disabled={busy} onChange={e=>setAttested(e.target.checked)}/>I sent this payment directly to the seller</label><button className="btn btn-primary" disabled={busy||!attested||!validReference}>I Have Paid</button></form>}
    {role==='seller'&&p.can_confirm&&<div className="product-form"><label className="checkbox-field"><input type="checkbox" checked={attested} disabled={busy} onChange={e=>setAttested(e.target.checked)}/>I confirm I actually received INR {p.amount}</label><button className="btn btn-primary" disabled={busy||!attested} onClick={()=>void act(()=>paymentsApi.confirm(orderId,p.status as 'PENDING'|'BUYER_REPORTED'))}>Confirm Payment Received</button><p className="approval-help">Check actual cash or your own UPI account before confirming.</p></div>}
    <Link className="text-link" to={`/${role}/payments`}>View payment history</Link></section>;
}
function lineTotal(price:string,quantity:number){const [whole,fraction='00']=price.split('.');const cents=(BigInt(whole)*100n+BigInt(fraction.padEnd(2,'0')))*BigInt(quantity);return `${cents/100n}.${String(cents%100n).padStart(2,'0')}`;}
export function OrderReceipt({order,payment}:{order:Order;payment:PaymentRecord}){
  return <section className="panel order-receipt" aria-label="Order receipt"><h2>Order receipt</h2><p>Not proof of payment. This is not a tax invoice.</p><dl><dt>Order ID</dt><dd>#{order.id}</dd><dt>Order date</dt><dd>{new Date(payment.order_date).toLocaleString()}</dd><dt>Seller</dt><dd>{payment.seller_name}</dd><dt>Payment method</dt><dd>{payment.method??'Not recorded'}</dd><dt>Payment status</dt><dd>{paymentStatusLabels[payment.status]}</dd></dl><table><thead><tr><th>Product</th><th>Qty</th><th>Price</th><th>Amount</th></tr></thead><tbody>{order.items.map(item=><tr key={item.product_id}><td>{item.name}</td><td>{item.quantity}</td><td>INR {item.unit_price}</td><td>INR {lineTotal(item.unit_price,item.quantity)}</td></tr>)}</tbody></table><dl><dt>Subtotal</dt><dd>INR {order.subtotal}</dd><dt>Delivery</dt><dd>INR {order.delivery_fee}</dd><dt>Total</dt><dd>INR {order.total}</dd></dl>{['CANCELLED','REJECTED'].includes(order.status)&&<p>Cancellation does not confirm a refund. Contact the seller about any external collection.</p>}<button type="button" className="btn btn-outline" onClick={()=>window.print()}><Printer size={18} aria-hidden="true"/>Print order receipt</button></section>;
}
