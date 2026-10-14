import { api, identifier } from './client';
import type { Id, Product, ProductInput } from './types';
export const productsApi = {
  own: () => api<Product[]>('/sellers/me/products'),
  create: (body: ProductInput) => api<Product>('/products', { method: 'POST', body }),
  update: (id: Id, body: Partial<ProductInput>) => api<Product>(`/products/${identifier(id)}`, { method: 'PATCH', body }),
  activate: (id: Id, is_active: boolean) => api<Product>(`/products/${identifier(id)}/activation`, { method: 'PATCH', body: { is_active } }),
  resubmit: (id: Id) => api<Product>(`/products/${identifier(id)}/resubmit`, { method: 'POST' }),
};
