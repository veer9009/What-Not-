import { afterEach, expect, it, vi } from 'vitest';
import { ordersApi } from './orders';
import { setAccessToken } from './client';
const key = '43f7847e-b81c-471c-8938-14d74e363bf7';

afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });

it('creates an authenticated order with exact BIGINT IDs and only public input fields', async () => {
  setAccessToken('buyer-token');
  vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
    expect(url).toMatch(/\/orders$/);
    expect(options.method).toBe('POST');
    expect(new Headers(options.headers).get('Authorization')).toBe('Bearer buyer-token');
    expect(new Headers(options.headers).get('Idempotency-Key')).toBe(key);
    expect(options.body).toBe('{"seller_id":9223372036854775807,"address_id":9007199254740993,"items":[{"product_id":9007199254740995,"quantity":2}]}');
    return new Response('{"id":9223372036854775807,"buyer_id":1,"seller_id":9223372036854775807,"status":"PLACED","subtotal":"500.00","delivery_fee":"0.00","total":"500.00","items":[]}', { status: 201 });
  });
  const input = { seller_id: '9223372036854775807', address_id: '9007199254740993',
    items: [{ product_id: '9007199254740995', quantity: 2, unit_price: '0.00' }], buyer_id: '999', total: '0.00' };
  const result = await ordersApi.create(input, key);
  expect(result.id).toBe('9223372036854775807');
  expect(result.buyer_id).toBe('1');
  expect(result.total).toBe('500.00');
});

it('preserves stock conflict errors from order creation', async () => {
  vi.stubGlobal('fetch', async () => new Response('{"detail":"Requested quantity exceeds available stock"}', { status: 409 }));
  await expect(ordersApi.create({ seller_id: '1', address_id: '2', items: [{ product_id: '3', quantity: 6 }] }, key))
    .rejects.toMatchObject({ status: 409 });
});
