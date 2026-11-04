import { Minus, Plus, Trash2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { DashboardShell, EmptyState, PageTop } from '../components/Shared';
import { DemoNotice, ErrorNotice, Loading } from '../components/ApiStates';
import { useDemo } from '../state/DemoContext';
import { useAuth } from '../state/AuthContext';
import { saveAttempt, forgetAttempt } from '../state/checkoutRecovery';
import { useResource } from '../state/useResource';
import { createSellerOrders } from '../utils/orders';
import { addressesApi } from '../api/addresses';
import { discoveryApi } from '../api/discovery';
import { ordersApi } from '../api/orders';
import { ApiError, getAccessToken } from '../api/client';
import type { Address, Order } from '../api/types';
import type { PlacementAttempt } from '../types';

function placementError(reason: unknown) {
  if (reason instanceof ApiError && reason.code === 'CHECKOUT_RECOVERY_UNAVAILABLE')
    return 'Your browser could not save this order’s recovery key. Enable session storage and try again. No order was sent.';
  if (reason instanceof ApiError && reason.code === 'IDEMPOTENCY_CONFLICT')
    return 'This checkout key belongs to a different order request. Check your order history before starting another order.';
  if (reason instanceof ApiError && reason.code === 'DELIVERY_INELIGIBLE')
    return 'This product is outside the selected delivery address. Choose another saved address or remove the product.';
  const status = reason instanceof ApiError ? reason.status : 0;
  if (status === 401) return 'Your session expired. Please sign in again.';
  if (status === 403) return 'The address or products are not permitted for this account. Check your saved address and basket.';
  if (status === 404) return 'A product or delivery address is unavailable, or the product cannot be delivered to this address. Review your basket and saved addresses.';
  if (status === 409) return 'Stock or product availability changed. Review quantities and refresh the product before trying again.';
  if (status === 422) return 'Check your selected address and product quantities before trying again.';
  return 'The service is unavailable. Please try again later.';
}

export function CartPage() {
  const { state, dispatch } = useDemo();
  const { user } = useAuth();
  const groups = createSellerOrders(state.products, state.cart, 'preview');
  const hasReal = groups.some(group => group.sellerId);
  const hasSamples = groups.some(group => !group.sellerId);
  const [busy, setBusy] = useState(false);
  const placing = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [addressId, setAddressId] = useState('');
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [results, setResults] = useState<{ seller: string; sellerId: string; order?: Order; error?: string }[]>([]);
  const attempts = state.placements ?? [];
  const uncertain = attempts.length > 0 || state.cart.some(item => item.placementUncertain);
  const pending = attempts.some(attempt => attempt.pending) || state.cart.some(item => item.placementPending);
  const canReconcile = attempts.length > 0 && !pending;
  const subtotal = groups.reduce((sum, group) => sum + group.subtotal, 0);
  const selected = addresses.some(address => address.id === addressId);

  async function placeOrders() {
    if (placing.current || pending || !user || (uncertain ? !canReconcile : !selected || !hasReal)) return;
    placing.current = true; setBusy(true);
    setResults(previous => previous.filter(result => result.order));
    const token = getAccessToken();
    const sameSession = () => token === getAccessToken();
    const active = () => mounted.current && sameSession();
    const tasks = uncertain ? attempts : groups.filter(group => group.sellerId).map(group => ({
      seller: group.seller, cartIds: group.items.map(({ product })=>product.id),
      request: { address_id: addressId, seller_id: group.sellerId!,
        items: group.items.map(({ product, quantity })=>({ product_id: product.backend!.productId, quantity,expected_unit_price:product.backend!.unitPrice??product.price.toFixed(2) })) },
      key: '', pending: false,
    }));
    try {
      for (const task of tasks) {
        if (!active()) break;
        let submitted = false;
        let attempt: PlacementAttempt | undefined;
        try {
          if (!task.key) {
            // Reconciliation goes straight to the server's idempotency lookup: the
            // original order may already have consumed the stock shown in discovery.
            for (const item of task.request.items) {
              const current = await discoveryApi.detail(item.product_id, { address_id: task.request.address_id });
              if (!active()) return;
              if (current.id !== item.product_id || current.seller_id !== task.request.seller_id)
                throw new ApiError(404, 'Product is unavailable');
              if (item.quantity > current.stock_quantity) throw new ApiError(409, 'Insufficient stock');
              if ('expected_unit_price' in item && current.price !== item.expected_unit_price)
                throw new ApiError(409,'Price changed; refresh the product and accept its current price');
            }
          }
          try {
            attempt = { ...task, key: task.key || crypto.randomUUID(), pending: true };
            saveAttempt(user.id, attempt);
          } catch { throw new ApiError(0, 'Recovery storage unavailable', {}, 'CHECKOUT_RECOVERY_UNAVAILABLE'); }
          dispatch({ type: 'cart/placement', ids: task.cartIds, uncertain: true, pending: true, attempt });
          submitted = true;
          const order = await ordersApi.create(attempt.request, attempt.key);
          if (!sameSession()) return;
          forgetAttempt(user.id, attempt.key);
          dispatch({ type: 'cart/ordered', ids: task.cartIds });
          if (!mounted.current) return;
          setResults(previous => [...previous, { seller: task.seller, sellerId: task.request.seller_id, order }]);
        } catch (reason) {
          if (!sameSession()) return;
          const status = reason instanceof ApiError ? reason.status : 0;
          const conflict = reason instanceof ApiError && reason.code === 'IDEMPOTENCY_CONFLICT';
          let unknown = submitted && (status === 0 || status >= 500 || conflict);
          let cleanupFailed = false;
          if (submitted) {
            if (!unknown && attempt) {
              cleanupFailed = !forgetAttempt(user.id, attempt.key);
              if (cleanupFailed) unknown = true;
            }
            dispatch({ type: 'cart/placement', ids: task.cartIds, uncertain: unknown });
          }
          if (!mounted.current) return;
          setResults(previous => [...previous, { seller: task.seller, sellerId: task.request.seller_id,
            error: cleanupFailed ? `${placementError(reason)} Recovery data could not be cleared; reconcile this request before starting another order.`
              : unknown && !conflict ? 'Order outcome could not be confirmed. Reconcile orders safely using the original request, or check your order history.' : placementError(reason) }]);
          if (status === 401 || unknown) break;
        }
      }
    } finally {
      placing.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  return <DashboardShell role="buyer">{hasSamples&&(hasReal?<p className="development-notice">Sample items are illustrative and cannot be ordered. Real discovered products can be ordered below.</p>:<DemoNotice/>)}<PageTop eyebrow="Your local basket" title="Shopping Cart" action={<Link className="text-link" to="/buyer">Continue shopping</Link>}/>
    {results.length > 0 && <section className="panel" aria-label="Order placement results">{results.map((result, index) => <div key={`${result.sellerId}-${index}`}>
      {result.order ? <p className="success-note" role="status">{result.seller} (seller #{result.sellerId}): Order placed, total ₹{result.order.total}. <Link to={`/buyer/orders/${result.order.id}`}>View order {result.order.id}</Link></p>
        : <p className="form-error" role="alert">{result.seller} (seller #{result.sellerId}): {result.error}</p>}
    </div>)}<Link className="text-link" to="/buyer/orders">View buyer orders</Link></section>}
    {uncertain && !results.some(result => result.error) && <p className="form-error" role="alert">An earlier order outcome is unconfirmed. Reconcile it using the original request or <Link to="/buyer/orders">check your order history</Link>.</p>}
    {canReconcile && !state.cart.length && <section className="panel"><button className="btn btn-primary" disabled={busy} onClick={()=>void placeOrders()}>{busy?'Placing orders…':'Reconcile orders'}</button></section>}
    {state.cart.length ? groups.length ? <div className="cart-layout"><div className="cart-list">
      <p className="approval-help">{groups.length} separate seller {groups.length === 1 ? 'order' : 'orders'}. Delivery is Free (₹0). {hasSamples&&'Sample items are illustrative and will not be ordered.'}</p>
      {groups.map(group => <section className="seller-order-group" key={group.sellerId ? `backend:${group.sellerId}` : `sample:${group.seller}`}><h2>{group.seller}{!group.sellerId&&' · Sample, not orderable'}</h2>{group.items.map(({ product, quantity }) => <article className="cart-item" key={product.id}>
        {product.image?<img src={product.image} alt={product.name}/>:<span aria-hidden="true"/>}<div><p className="eyebrow">{product.seller}</p><h3>{product.name}</h3><span>{product.backend?'Nearby locality':`${product.distance} km away`}</span></div>
        <div className="quantity"><button aria-label={`Decrease ${product.name} quantity`} disabled={busy || state.cart.some(item => item.productId === product.id && item.placementUncertain) || quantity <= 1} onClick={() => dispatch({ type: 'cart/quantity', id: product.id, quantity: quantity - 1 })}><Minus/></button><b>{quantity}</b><button aria-label={`Increase ${product.name} quantity`} disabled={busy || state.cart.some(item => item.productId === product.id && item.placementUncertain) || quantity >= product.stock} onClick={() => dispatch({ type: 'cart/quantity', id: product.id, quantity: quantity + 1 })}><Plus/></button></div>
        <strong>₹{(product.price * quantity).toLocaleString('en-IN')}</strong><button className="trash" aria-label={`Remove ${product.name}`} disabled={busy || state.cart.some(item => item.productId === product.id && item.placementUncertain)} onClick={() => dispatch({ type: 'cart/remove', id: product.id })}><Trash2/></button>
      </article>)}<p className="seller-order-total">Seller subtotal ₹{group.subtotal.toLocaleString('en-IN')} + delivery Free (₹0) = ₹{group.total.toLocaleString('en-IN')}</p></section>)}
    </div><aside className="order-card"><p className="eyebrow">Order summary</p><h2>Almost yours</h2><div><span>Subtotal</span><b>₹{subtotal.toLocaleString('en-IN')}</b></div><div><span>Local delivery ({groups.length} {groups.length === 1 ? 'seller' : 'sellers'})</span><b>Free (₹0)</b></div><div className="total"><span>Estimated total{hasSamples&&' (includes samples)'}</span><b>₹{subtotal.toLocaleString('en-IN')}</b></div>
      {hasReal && <SavedDeliveryAddress busy={busy} value={addressId} change={setAddressId} loaded={setAddresses}/>}
      <button className="btn btn-primary wide" disabled={busy || pending || (uncertain ? !canReconcile : !hasReal || !selected)} onClick={()=>void placeOrders()}>{busy ? 'Placing orders…' : canReconcile ? 'Reconcile orders' : hasReal ? 'Place orders' : 'Checkout unavailable'}</button>
      <small>{hasReal ? 'Only real products will be ordered. The server confirms prices, totals and stock. No payment is collected.' : 'Sample basket only. Add real nearby products from discovery to place orders.'}</small></aside></div>
      : <section className="panel"><p className="form-error" role="alert">Some cart items are no longer eligible or exceed current stock. Remove them or adjust quantities before checkout.</p>{state.cart.map(item => <div className="unavailable-cart-item" key={item.productId}><span>{state.products.find(product => product.id === item.productId)?.name ?? 'Unavailable product'}</span><button className="btn btn-outline btn-sm" disabled={busy} onClick={() => dispatch({ type: 'cart/remove', id: item.productId })}>Remove</button></div>)}</section>
      : <EmptyState title="Your local basket is empty" description="Discover nearby products and add your favourites to your basket."/>}
  </DashboardShell>;
}

function SavedDeliveryAddress({ busy, value, change, loaded }: { busy: boolean; value: string;
  change: (value: string) => void; loaded: (addresses: Address[]) => void }) {
  const resource = useResource(addressesApi.list);
  useEffect(() => { loaded(resource.data ?? []); }, [resource.data, loaded]);
  if (resource.loading) return <Loading/>;
  if (resource.error) return <ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>;
  return <><label className="field"><span>Delivery address</span><select aria-label="Delivery address" value={value} disabled={busy} onChange={event=>change(event.target.value)}>
    <option value="">Select a saved address</option>{resource.data?.map(address=><option key={address.id} value={address.id}>{address.label} — {address.address_line1}, {address.city}, {address.state} {address.pincode}</option>)}
  </select></label><Link className="text-link" to="/buyer/addresses">Manage saved addresses</Link></>;
}
