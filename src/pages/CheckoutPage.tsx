import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { DashboardShell, PageTop } from '../components/Shared';
import { ListingImage } from '../components/ListingImage';
import { useDemo } from '../state/DemoContext';
import { useAuth } from '../state/AuthContext';
import { addressesApi } from '../api/addresses';
import { checkoutApi, type CheckoutMethod, type CheckoutPreview, type CheckoutRequest } from '../api/checkout';
import { ApiError, errorMessage } from '../api/client';
import type { Address, Order } from '../api/types';
import { createSellerOrders } from '../utils/orders';
import { forgetBatch, loadBatch, saveBatch, type CheckoutBatch } from '../state/checkoutBatchRecovery';
import './CheckoutPage.css';

export function CheckoutPage(){
 const {state,dispatch}=useDemo();const {user,sessionKey}=useAuth();
 const [addresses,setAddresses]=useState<Address[]>([]),[address,setAddress]=useState(''),[methods,setMethods]=useState<Record<string,CheckoutMethod>>({});
 const [preview,setPreview]=useState<CheckoutPreview|null>(null),[review,setReview]=useState<CheckoutRequest|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[orders,setOrders]=useState<Order[]>([]);
 const [recovery,setRecovery]=useState<CheckoutBatch|null>(null),[blocked,setBlocked]=useState(false);
 const inFlight=useRef(false),scope=useRef(''),mounted=useRef(true);scope.current=`${user?.id}:${sessionKey}`;
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
 const groups=createSellerOrders(state.products,state.cart,'checkout').filter(group=>group.sellerId);
 const base:CheckoutRequest={address_id:address,sellers:groups.map(group=>({seller_id:group.sellerId!,items:group.items.map(({product,quantity})=>({product_id:product.backend!.productId,quantity,expected_unit_price:product.backend!.unitPrice??product.price.toFixed(2)}))}))};
 const signature=JSON.stringify(base);
 const historical=!!state.placements?.length||state.cart.some(item=>item.placementUncertain);
 useEffect(()=>{setRecovery(null);setBlocked(false);setAddress('');setMethods({});setOrders([]);setReview(null);setPreview(null);setError('');if(!user)return;
  try{setRecovery(loadBatch(user.id));}catch{setBlocked(true);setError('Checkout recovery could not be read. Check your order history before starting another order.');}
  let active=true;addressesApi.list().then(value=>{if(active)setAddresses(value);}).catch(reason=>{if(active)setError(errorMessage(reason));});return()=>{active=false;};
 },[user?.id,sessionKey]);
 useEffect(()=>{setReview(null);setPreview(null);if(!address||!base.sellers.length||recovery||blocked||historical){if(!inFlight.current)setBusy(false);return;}let active=true;setBusy(true);setError('');
  checkoutApi.preview(base).then(value=>{if(active)setPreview(value);}).catch(reason=>{if(active)setError(checkoutError(reason));}).finally(()=>{if(active)setBusy(false);});return()=>{active=false;};
 // The serialized request changes for any address, seller, quantity, removal or price change.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[signature,recovery,blocked,historical]);
 const chosen=!!preview&&preview.groups.length===groups.length&&preview.groups.every(group=>methods[group.seller_id]&&group.available_payment_methods.includes(methods[group.seller_id]));
 const locked=busy||!!recovery||blocked||historical;
 async function finalReview(){if(!chosen||locked||inFlight.current)return;const origin=scope.current;const request={...base,sellers:base.sellers.map(seller=>({...seller,payment_method:methods[seller.seller_id]}))};setBusy(true);inFlight.current=true;setError('');try{const result=await checkoutApi.preview(request);if(mounted.current&&scope.current===origin){setPreview(result);if(result.groups.every(group=>group.available_payment_methods.includes(methods[group.seller_id])))setReview(request);else setError('Payment availability changed. Choose an available method again.');}}catch(reason){if(scope.current===origin)setError(checkoutError(reason));}finally{inFlight.current=false;if(mounted.current&&scope.current===origin)setBusy(false);}}
 async function confirm(){if(inFlight.current||!user||blocked||historical||(!recovery&&!review))return;if(!recovery&&review&&JSON.stringify({...review,sellers:review.sellers.map(({payment_method: _method,...seller})=>seller)})!==signature){setReview(null);return;}const buyer=user.id,origin=scope.current;inFlight.current=true;setBusy(true);setError('');let attempt:CheckoutBatch|undefined;let submitted=false;
  try{attempt=recovery??{key:crypto.randomUUID(),request:review!};saveBatch(buyer,attempt);setRecovery(attempt);
   submitted=true;const result=await checkoutApi.place(attempt.request,attempt.key);if(!mounted.current||scope.current!==origin)return;
   if(!forgetBatch(buyer,attempt.key)){setOrders(result.orders);setError('Orders are confirmed, but recovery storage could not be cleared. Retry the original checkout safely before starting another.');return;}
   setRecovery(null);setReview(null);setOrders(result.orders);dispatch({type:'cart/ordered',ids:attempt.request.sellers.flatMap(seller=>seller.items.map(item=>`backend:${item.product_id}`))});
  }catch(reason){if(!mounted.current||scope.current!==origin)return;
   // Timeouts, rate limits and intermediary responses do not prove that the
   // atomic transaction did not commit. Only explicit business rejections allow
   // a fresh checkout key; otherwise replay this original batch.
   const definitive=reason instanceof ApiError&&[400,401,403,404,409,422].includes(reason.status)&&reason.code!=='IDEMPOTENCY_CONFLICT'&&!(recovery&&[401,403,404].includes(reason.status));
   if(attempt&&submitted&&definitive&&forgetBatch(buyer,attempt.key)){setRecovery(null);setReview(null);setPreview(null);setAddress('');setMethods({});}setError(submitted?`${checkoutError(reason)} ${definitive?'Review the basket and address again.':'The outcome is unconfirmed. Retry the original checkout or check your orders. Do not start another checkout.'}`:'Recovery could not be saved. No checkout was sent. Enable session storage and try again.');
  }finally{inFlight.current=false;if(mounted.current&&scope.current===origin)setBusy(false);}
 }
 return <DashboardShell role="buyer"><PageTop eyebrow="Complete your purchase" title="Checkout" action={<Link to="/buyer/cart">Back to cart</Link>}/><div className="final-checkout">
 <ol className="checkout-progress" aria-label="Checkout steps"><li>Delivery address</li><li>Payment per seller</li><li>Final review</li><li>Instructions and tracking</li></ol>
 {error&&<p role="alert" className="form-error">{error}</p>}
 {historical&&<p role="alert">An earlier order outcome is unconfirmed. <Link to="/buyer/cart">Reconcile the original order in your cart</Link> before a new checkout.</p>}
 {orders.length>0&&<section className="panel" role="status"><h2>Orders placed</h2><p>Each seller has a separate order. Payment has not been collected here.</p>{orders.map(order=><p key={order.id}><Link to={`/buyer/orders/${order.id}`}>Track order #{order.id}</Link> · ₹{order.total}</p>)}<Link to="/buyer/payments">Payment instructions and status</Link> · <Link to="/buyer/orders">All orders</Link></section>}
 {recovery&&<section className="panel"><h2>Unconfirmed checkout</h2><p>The complete original request is saved. Retry it safely with the same checkout key, even if your current basket has changed.</p><button className="btn btn-primary" disabled={busy||blocked||historical} onClick={()=>void confirm()}>{busy?'Checking checkout…':'Retry original checkout'}</button><p><Link to="/buyer/orders">Check order history</Link></p></section>}
 {!recovery&&!orders.length&&<><section className="panel"><h2>1. Delivery address</h2><label className="field"><span>Delivery address</span><select aria-label="Delivery address" value={address} disabled={locked} onChange={event=>{setAddress(event.target.value);setMethods({});}}><option value="">Select a saved address</option>{addresses.map(item=><option key={item.id} value={item.id}>{item.label} — {item.address_line1}, {item.city}, {item.state} {item.pincode}</option>)}</select></label><Link to="/buyer/addresses">Manage saved addresses</Link></section>
 <section className="panel"><h2>2. Products and payment</h2><p>Choose a payment method for every seller. No payment method is selected automatically.</p>{!groups.length&&<p>Add available real products to your cart to continue.</p>}{groups.map(group=><section className="checkout-seller" key={group.sellerId}><h3>{group.seller}</h3>{group.items.map(({product,quantity})=><div className="checkout-item" key={product.id}><div className="checkout-product"><ListingImage src={product.image} alt={product.name}/><span>{product.name}<small>₹{product.backend?.unitPrice??product.price.toFixed(2)} each</small></span></div><label>Quantity<input aria-label={`${product.name} quantity`} type="number" min="1" max={product.stock} value={quantity} disabled={locked} onChange={event=>dispatch({type:'cart/quantity',id:product.id,quantity:Number(event.target.value)})}/></label><button className="btn btn-outline btn-sm" disabled={locked} onClick={()=>dispatch({type:'cart/remove',id:product.id})}>Remove {product.name}</button></div>)}{preview?.groups.filter(item=>item.seller_id===group.sellerId).map(item=><fieldset key={item.seller_id} disabled={locked}><legend>Payment for {item.seller_name}</legend><label><input type="radio" name={`payment-${item.seller_id}`} aria-label={`Cash on delivery — ${item.seller_name}`} checked={methods[item.seller_id]==='COD'} disabled={!item.available_payment_methods.includes('COD')} onChange={()=>{setMethods(old=>({...old,[item.seller_id]:'COD'}));setReview(null);}}/> Cash on delivery</label><label><input type="radio" name={`payment-${item.seller_id}`} aria-label={`UPI — ${item.seller_name}`} checked={methods[item.seller_id]==='UPI'} disabled={!item.available_payment_methods.includes('UPI')} onChange={()=>{setMethods(old=>({...old,[item.seller_id]:'UPI'}));setReview(null);}}/> Direct UPI</label>{!item.available_payment_methods.includes('UPI')&&<p className="approval-help">{item.upi_unavailable_reason||'UPI is unavailable while payment and refund policy approval is pending.'}</p>}<p>Subtotal ₹{item.subtotal} + delivery ₹{item.delivery_fee} = ₹{item.total}</p></fieldset>)}</section>)}</section>
 <section className="panel"><h2>3. Final review</h2>{preview&&<><p>Server confirmed total: <strong>₹{preview.total} {preview.currency}</strong></p><p>Platform commission: ₹0. Stock is checked again when you confirm.</p></>}<button className="btn btn-primary" disabled={!chosen||locked} onClick={()=>void finalReview()}>Review final order</button>{review&&<div className="checkout-confirm"><h3>Confirm your purchase</h3>{addresses.filter(item=>item.id===review.address_id).map(item=><p key={item.id}>{item.label}: {item.address_line1}{item.address_line2&&`, ${item.address_line2}`}, {item.city}, {item.state} {item.pincode}</p>)}{preview?.groups.map(group=><div key={group.seller_id}><p>{group.seller_name}: {methods[group.seller_id]==='COD'?'Cash on delivery':'Direct UPI'} · ₹{group.total}</p>{group.items.map(item=><p key={item.product_id}>{item.name} × {item.quantity} · ₹{item.unit_price} each</p>)}</div>)}<p>Confirming creates all seller orders together. Follow payment instructions after placement. What Not? does not collect funds.</p><button className="btn btn-primary" disabled={locked} onClick={()=>void confirm()}>Confirm and place orders</button></div>}</section></>}
 </div></DashboardShell>;
}
function checkoutError(reason:unknown){if(reason instanceof ApiError){if(reason.code==='IDEMPOTENCY_CONFLICT')return 'This checkout key belongs to a different request. Check order history; the saved original request is retained.';if(reason.status===409)return 'Prices, stock, payment availability or delivery eligibility changed. Refresh products and review your address.';}return errorMessage(reason);}
