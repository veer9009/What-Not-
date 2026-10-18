import { api } from './client';
import type { Shop, ShopInput } from './types';
import type { Coordinates } from '../location/geolocation';
export const sellersApi = { me: () => api<Shop>('/sellers/me'), create: (body: ShopInput) => api<Shop>('/sellers/me', { method: 'POST', body }), update: (body: Partial<ShopInput>) => api<Shop>('/sellers/me', { method: 'PATCH', body }) };
export const setDispatchLocation = (body:Coordinates) => api<Shop>('/sellers/me/dispatch-location',{method:'PATCH',body});
