import type { OrderStatus } from '../api/types';

export const orderStatusLabels: Record<OrderStatus, string> = {
  PLACED: 'Order placed', ACCEPTED: 'Seller accepted', PREPARING: 'Preparing',
  OUT_FOR_DELIVERY: 'Out for delivery', AWAITING_BUYER_CONFIRMATION: 'Awaiting your confirmation',
  DELIVERED: 'Delivered', CANCELLED: 'Cancelled', REJECTED: 'Rejected by seller',
};

const stages: OrderStatus[] = ['PLACED', 'ACCEPTED', 'PREPARING', 'OUT_FOR_DELIVERY', 'AWAITING_BUYER_CONFIRMATION', 'DELIVERED'];

export function OrderTracking({ status }: { status: OrderStatus }) {
  if (status === 'CANCELLED' || status === 'REJECTED') {
    return <p className="order-ended">{status === 'CANCELLED' ? 'This order was cancelled.' : 'The seller could not accept this order.'} Delivery tracking has ended.</p>;
  }
  const current = stages.indexOf(status);
  return <section className="order-tracking" aria-label="Order progress">
    <h2>Order progress</h2>
    <ol>{stages.map((stage, index) => <li key={stage} className={index === current ? 'current' : index < current ? 'completed' : 'upcoming'} aria-current={index === current ? 'step' : undefined}>
      <span className="tracking-marker" aria-hidden="true">{index < current ? '✓' : index + 1}</span>
      <span>{orderStatusLabels[stage]}<small>{index === current ? 'Current stage' : index < current ? 'Completed' : 'Upcoming'}</small></span>
    </li>)}</ol>
  </section>;
}
