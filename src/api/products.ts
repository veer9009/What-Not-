import { api, identifier, uploadBinary } from './client';
import type { Id, Product, ProductInput, ProductImage } from './types';
export const productsApi = {
  images: (id: Id, signal?: AbortSignal) => api<ProductImage[]>(`/products/${identifier(id)}/images`, { signal }),
  uploadImage: (id: Id, file: File, progress?: (percent: number) => void, signal?: AbortSignal) => uploadBinary<Product>(`/products/${identifier(id)}/images`, file, progress, signal),
  replaceImage: (id: Id, imageId: Id, file: File, progress?: (percent: number) => void, signal?: AbortSignal) => uploadBinary<Product>(`/products/${identifier(id)}/images/${identifier(imageId)}/replace`, file, progress, signal),
  removeImage: (id: Id, imageId: Id, signal?: AbortSignal) => api<Product>(`/products/${identifier(id)}/images/${identifier(imageId)}/remove`, { method: 'POST', body: {}, signal }),
  primaryImage: (id: Id, imageId: Id, signal?: AbortSignal) => api<Product>(`/products/${identifier(id)}/images/${identifier(imageId)}/primary`, { method: 'POST', body: {}, signal }),
  own: () => api<Product[]>('/sellers/me/products'),
  create: (body: ProductInput) => api<Product>('/products', { method: 'POST', body }),
  update: (id: Id, body: Partial<ProductInput>) => api<Product>(`/products/${identifier(id)}`, { method: 'PATCH', body }),
  activate: (id: Id, is_active: boolean) => api<Product>(`/products/${identifier(id)}/activation`, { method: 'PATCH', body: { is_active } }),
  resubmit: (id: Id) => api<Product>(`/products/${identifier(id)}/resubmit`, { method: 'POST' }),
};
