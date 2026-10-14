import { api, identifier } from './client';
import type { Id, Order, OrderStatus } from './types';
export const ordersApi = { list: () => api<Order[]>('/orders'), get: (id: Id) => api<Order>(`/orders/${identifier(id)}`), transition: (id: Id, status: OrderStatus) => api<Order>(`/orders/${identifier(id)}/status`, { method: 'PATCH', body: { status } }) };
