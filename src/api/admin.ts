import { api, identifier } from './client';
import type { Id, Product } from './types';
export const adminApi = {
  pending: () => api<Product[]>('/admin/products/pending'),
  approve: (id: Id) => api<Product>(`/admin/products/${identifier(id)}/approve`, { method: 'POST' }),
  reject: (id: Id, rejection_reason: string) => api<Product>(`/admin/products/${identifier(id)}/reject`, { method: 'POST', body: { rejection_reason } }),
};
