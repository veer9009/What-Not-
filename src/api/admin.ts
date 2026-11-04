import { api, identifier } from './client';
import type { Id, Product } from './types';
export const adminApi = {
  pending: (offset=0) => api<Product[]>(`/admin/products/pending?offset=${offset}&limit=50`),
  approve: (id: Id,expected_updated_at?:string|null) => api<Product>(`/admin/products/${identifier(id)}/approve`, { method: 'POST',body:{expected_updated_at} }),
  reject: (id: Id, rejection_reason: string) => api<Product>(`/admin/products/${identifier(id)}/reject`, { method: 'POST', body: { rejection_reason } }),
};
