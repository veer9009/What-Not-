import { api, identifier } from './client';
import type { Fulfillment, Id, Order, OrderCreate, OrderStatus } from './types';

export const ordersApi = {
  list: (offset=0) => api<Order[]>(`/orders?offset=${offset}&limit=50`),
  fulfillment: (id: Id) => api<Fulfillment>(`/orders/${identifier(id)}/fulfillment`),
  get: (id: Id) => api<Order>(`/orders/${identifier(id)}`),
  create: (input: OrderCreate, idempotencyKey: string) => {
    // Emit validated IDs as exact JSON integers, preserving PostgreSQL BIGINT precision.
    const items = input.items.map(item => `{"product_id":${identifier(item.product_id)},"quantity":${JSON.stringify(item.quantity)}${item.expected_unit_price === undefined ? '' : `,"expected_unit_price":${JSON.stringify(item.expected_unit_price)}`}}`);
    const bodyText = `{"seller_id":${identifier(input.seller_id)},"address_id":${identifier(input.address_id)},"items":[${items.join(',')}]}`;
    return api<Order>('/orders', { method: 'POST', bodyText, idempotencyKey });
  },
  transition: (id: Id, status: OrderStatus) => api<Order>(`/orders/${identifier(id)}/status`, { method: 'PATCH', body: { status } }),
};
