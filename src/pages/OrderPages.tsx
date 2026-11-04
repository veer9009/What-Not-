import { useCallback, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { DashboardShell, EmptyState, PageTop } from '../components/Shared';
import { ErrorNotice, Loading } from '../components/ApiStates';
import { OrderTracking, orderStatusLabels } from '../components/OrderTracking';
import { ordersApi } from '../api/orders';
import { errorMessage } from '../api/client';
import type { Fulfillment, OrderStatus } from '../api/types';
import { useResource } from '../state/useResource';
import { useAuth } from '../state/AuthContext';
import { supportUrl } from '../utils/support';

// Suggestions for UX only. Every attempted transition is authorized by the service.
const sellerActions: Partial<Record<OrderStatus, [OrderStatus, string][]>> = {
  PLACED: [['ACCEPTED', 'Accept order'], ['CANCELLED', 'Cancel order'], ['REJECTED', 'Reject order']],
  ACCEPTED: [['PREPARING', 'Start preparing'], ['CANCELLED', 'Cancel order']],
  PREPARING: [['OUT_FOR_DELIVERY', 'Out for delivery']],
  OUT_FOR_DELIVERY: [['DELIVERED', 'Mark delivered']],
};
function statusLabel(status: OrderStatus, _role: 'buyer' | 'seller') {
  return orderStatusLabels[status];
}

export function OrderHistoryPage() {
  const { user } = useAuth();
  const role = user!.role.toLowerCase() as 'buyer' | 'seller';
  const [offset,setOffset]=useState(0);
  const load=useCallback(()=>ordersApi.list(offset),[offset]);
  const resource = useResource(load);
  return <DashboardShell role={role}>
    <PageTop eyebrow="Order history" title={role === 'buyer' ? 'Your orders' : 'Incoming orders'}/>
    <p className="approval-help">Newest orders first, 50 per page. No payment is collected.</p>
    {resource.loading ? <Loading/> : resource.error ? <ErrorNotice message={resource.error} retry={() => void resource.reload()}/> : resource.data?.length ?
      <div className="resource-list">{resource.data.map(order => <article className="panel" key={order.id}>
        <h2>Order #{order.id}</h2><p>{statusLabel(order.status, role)}</p><p>₹{order.total}</p>
        <Link className="text-link" to={`/${role}/orders/${order.id}`}>View order {order.id}</Link>
      </article>)}</div> : <EmptyState title="No orders yet" description="There are no orders on this page. Add nearby products to your cart to place an order."/>}
    <div className="form-actions"><button className="btn btn-outline" disabled={offset===0||resource.loading} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous orders</button><button className="btn btn-outline" disabled={resource.loading||(resource.data?.length??0)<50} onClick={()=>setOffset(offset+50)}>More orders</button></div>
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
  const [fulfillment,setFulfillment]=useState<Fulfillment|null>(null);

  async function loadFulfillment(){
    if(pending.current||!id)return;
    pending.current=true;setBusy(true);setError('');
    try{setFulfillment(await ordersApi.fulfillment(id));}catch(reason){setError(errorMessage(reason));}
    finally{pending.current=false;setBusy(false);}
  }

  async function transition(status: OrderStatus) {
    if (pending.current || !id) return;
    pending.current = true;
    setBusy(true); setError(''); setNotice('');
    try {
      await ordersApi.transition(id, status);
      setFulfillment(null);
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
        {role === 'buyer' && order.status === 'DELIVERED' && <section className="delivery-confirmation" aria-label="Confirm receipt">
          <h2>Have you received your order?</h2>
          <p>Seller has marked this order delivered. Confirm receipt or record a delivery problem.</p>
          <div className="delivery-actions">
            <button className="btn btn-primary" disabled={busy} onClick={() => void transition('COMPLETED')}>Yes, I received it</button>
            <button className="btn btn-outline" disabled={busy} onClick={() => void transition('DELIVERY_DISPUTED')}>Report not received</button>
          </div>
          <p className="approval-help">Reporting a problem pauses automatic completion and records a dispute for investigation.</p>
        </section>}
        {order.status==='DELIVERED'&&order.confirmation_deadline&&<p>Confirmation deadline: {new Date(order.confirmation_deadline).toLocaleString()}. Without a dispute, this order is eligible for automatic completion after that time.</p>}
        {role==='seller'&&['ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','DELIVERY_DISPUTED'].includes(order.status)&&<section aria-label="Delivery details"><button className="btn btn-outline" disabled={busy} onClick={()=>void loadFulfillment()}>View delivery details</button>{fulfillment&&<address>{fulfillment.recipient_name}<br/>{fulfillment.phone}<br/>{fulfillment.address_line1}{fulfillment.address_line2&&<><br/>{fulfillment.address_line2}</>}<br/>{fulfillment.city}, {fulfillment.state} {fulfillment.pincode}</address>}</section>}
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
