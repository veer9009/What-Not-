import { api } from './client';
import type { Shop, ShopInput } from './types';
export const sellersApi = { me: () => api<Shop>('/sellers/me'), create: (body: ShopInput) => api<Shop>('/sellers/me', { method: 'POST', body }), update: (body: Partial<ShopInput>) => api<Shop>('/sellers/me', { method: 'PATCH', body }) };
