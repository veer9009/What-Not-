import { useCallback, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { DashboardShell, EmptyState, PageTop } from '../components/Shared';
import { ErrorNotice, Loading } from '../components/ApiStates';
import { OrderTracking, orderStatusLabels } from '../components/OrderTracking';
import { ordersApi } from '../api/orders';
import { errorMessage } from '../api/client';
import type { OrderStatus } from '../api/types';
import { useResource } from '../state/useResource';
import { useAuth } from '../state/AuthContext';
import { supportUrl } from '../utils/support';

// Suggestions for UX only. Every attempted transition is authorized by the service.
const sellerActions: Partial<Record<OrderStatus, [OrderStatus, string][]>> = {
  PLACED: [['ACCEPTED', 'Accept order'], ['CANCELLED', 'Cancel order'], ['REJECTED', 'Reject order']],
  ACCEPTED: [['PREPARING', 'Start preparing'], ['CANCELLED', 'Cancel order']],
  PREPARING: [['OUT_FOR_DELIVERY', 'Out for delivery']],
  OUT_FOR_DELIVERY: [['AWAITING_BUYER_CONFIRMATION', 'Mark as handed over']],
};
function statusLabel(status: OrderStatus, role: 'buyer' | 'seller') {
  return status === 'AWAITING_BUYER_CONFIRMATION' && role === 'seller' ? 'Awaiting buyer confirmation' : orderStatusLabels[status];
}

export function OrderHistoryPage() {
  const { user } = useAuth();
  const role = user!.role.toLowerCase() as 'buyer' | 'seller';
  const resource = useResource(ordersApi.list);
  return <DashboardShell role={role}>
    <PageTop eyebrow="Order history" title={role === 'buyer' ? 'Your orders' : 'Incoming orders'}/>
    <p className="approval-help">Up to 100 orders. Orders placed from your cart appear here. No payment is collected.</p>
    {resource.loading ? <Loading/> : resource.error ? <ErrorNotice message={resource.error} retry={() => void resource.reload()}/> : resource.data?.length ?
      <div className="resource-list">{resource.data.map(order => <article className="panel" key={order.id}>
        <h2>Order #{order.id}</h2><p>{statusLabel(order.status, role)}</p><p>₹{order.total}</p>
        <Link className="text-link" to={`/${role}/orders/${order.id}`}>View order {order.id}</Link>
      </article>)}</div> : <EmptyState title="No orders yet" description="There are no orders to show. Add nearby products to your cart to place an order."/>}
  </DashboardShell>;
}

export function OrderDetailsPage() {
  const { id } = useParams();
  return <OrderDetails key={id} id={id}/>;
}
function OrderDetails({ id }: { id: string | undefined }) {
  const { user } = useAuth();
  const role = user!.role.toLowerCase() as 'buyer' | 'seller';
  const loader = useCallback(() => ordersApi.get(id ?? ''), [id]);
  const resource = useResource(loader);
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function transition(status: OrderStatus) {
    if (pending.current || !id) return;
    pending.current = true;
    setBusy(true); setError(''); setNotice('');
    try {
      await ordersApi.transition(id, status);
      const refreshed = await resource.reload();
      setNotice(refreshed ? 'Order updated.' : 'Order updated. Refresh to see its current status.');
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      pending.current = false; setBusy(false);
    }
  }

  const order = resource.data;
  const actions: [OrderStatus, string][] = order ? role === 'seller' ? sellerActions[order.status] ?? [] :
    ['PLACED', 'ACCEPTED'].includes(order.status) ? [['CANCELLED', 'Cancel order']] : [] : [];
  return <DashboardShell role={role}>
    <PageTop eyebrow="Order details" title={`Order #${id}`}/>
    <Link className="text-link" to={`/${role}/orders`}>Back to orders</Link>
    {error && <ErrorNotice message={error}/>}
    {notice && <p className="success-note" role="status">{notice}</p>}
    {resource.loading ? <Loading/> : resource.error ? <ErrorNotice message={resource.error} retry={() => void resource.reload()}/> : order &&
      <section className="panel order-details">
        <p className="order-status">{statusLabel(order.status, role)}</p>
        {role === 'buyer' && <OrderTracking status={order.status}/>}
        {role === 'buyer' && order.status === 'AWAITING_BUYER_CONFIRMATION' && <section className="delivery-confirmation" aria-label="Confirm receipt">
          <h2>Have you received your order?</h2>
          <p>Seller has marked this order as handed over. Have you received your order?</p>
          <div className="delivery-actions">
            <button className="btn btn-primary" disabled={busy} onClick={() => void transition('DELIVERED')}>Yes, I received it</button>
            <a className="btn btn-outline" href={supportUrl(order.id)} target="_blank" rel="noreferrer">I haven't received it / Delivery problem</a>
          </div>
          <p className="approval-help">If there is a delivery problem, contact support. Your order will stay awaiting confirmation.</p>
        </section>}
        {role === 'seller' && order.status === 'AWAITING_BUYER_CONFIRMATION' && <p>The buyer needs to confirm receipt to complete this order.</p>}
        {order.items.map(item => <article key={item.product_id}><h3>{item.name}</h3><p>{item.quantity} × ₹{item.unit_price}</p></article>)}
        <p>Subtotal: ₹{order.subtotal}</p><p>Delivery fee: ₹{order.delivery_fee}</p><p><b>Total: ₹{order.total}</b></p>
        <div className="form-actions">{actions.map(([status, label]) => <button className="btn btn-primary" disabled={busy} key={status} onClick={() => void transition(status)}>{label}</button>)}</div>
        {role === 'buyer' && <div className="order-support"><a className="text-link" href={supportUrl(order.id)} target="_blank" rel="noreferrer">Need help with this order?</a><p>Chat with What Not Support on WhatsApp.</p></div>}
      </section>}
  </DashboardShell>;
}
export function BuyerProfilePage() {
  const { user } = useAuth();
  return <DashboardShell role="buyer"><PageTop eyebrow="Authenticated identity" title="Your profile"/><section className="panel"><h2>{user!.name}</h2><p>{user!.email}</p><p>Role: {user!.role}</p><p>Profile editing is not supported by the current API.</p><Link className="text-link" to="/buyer/addresses">Manage addresses</Link></section></DashboardShell>;
}
