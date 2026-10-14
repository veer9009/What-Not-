import { api, identifier } from './client';
import type { Address, AddressInput, Id } from './types';
export const addressesApi = {
  list: () => api<Address[]>('/addresses'),
  create: (body: AddressInput) => api<Address>('/addresses', { method: 'POST', body }),
  update: (id: Id, body: Partial<AddressInput>) => api<Address>(`/addresses/${identifier(id)}`, { method: 'PATCH', body }),
  default: (id: Id) => api<Address>(`/addresses/${identifier(id)}/default`, { method: 'POST' }),
};
