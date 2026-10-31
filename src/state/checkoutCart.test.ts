import { expect, it } from 'vitest';
import { demoReducer } from './demoReducer';
import { products } from '../data/mockData';
import { createSellerOrders } from '../utils/orders';
import type { BuyerProduct } from '../api/discovery';
import type { DemoState } from '../types';

const product: BuyerProduct = { id: '9223372036854775807', seller_id: '9007199254740993', name: 'Real vase',
  description: 'Real', price: '250.00', stock_quantity: 5, category: 'Crafts', delivery_radius_km: 2,
  image_url: null, shop_name: 'Maker', is_verified: false, distance_km: 0.14 };
const empty: DemoState = { products: [], cart: [], orders: [] };

it('preserves exact backend identifiers separately from the cart display key', () => {
  const state = demoReducer(empty, { type: 'cart/add-discovered', product });
  expect(state.cart).toEqual([{ productId: 'backend:9223372036854775807', quantity: 1 }]);
  expect(state.products[0].backend).toEqual({ productId: '9223372036854775807', sellerId: '9007199254740993' });
  expect(createSellerOrders(state.products, state.cart, 'preview')[0].sellerId).toBe('9007199254740993');
});

it.each([{ id: 'sample' }, { seller_id: 'sample' }, { id: '9223372036854775808' }, { seller_id: '' }])(
  'rejects invalid discovered identifiers: %j', change => {
    expect(demoReducer(empty, { type: 'cart/add-discovered', product: { ...product, ...change } }).cart).toEqual([]);
  });

it('never infers backend provenance from numeric sample IDs', () => {
  const sample = { ...products[0], id: '3' };
  const state = demoReducer({ ...empty, products: [sample] }, { type: 'cart/add', id: '3' });
  expect(createSellerOrders(state.products, state.cart, 'preview')[0].sellerId).toBeUndefined();
});

it('does not use the legacy sample checkout action to order backend products', () => {
  const state = demoReducer(empty, { type: 'cart/add-discovered', product });
  const next = demoReducer(state, { type: 'checkout', id: 'fake-order' });
  expect(next.cart).toEqual(state.cart);
  expect(next.products[0].stock).toBe(5);
  expect(next.orders).toEqual([]);
});

it('keeps pending items locked against removal and readdition across navigation', () => {
  const added = demoReducer(empty, { type: 'cart/add-discovered', product });
  const pending = demoReducer(added, { type: 'cart/placement', ids: ['backend:9223372036854775807'], uncertain: true, pending: true });
  const removed = demoReducer(pending, { type: 'cart/remove', id: 'backend:9223372036854775807' });
  const readded = demoReducer(removed, { type: 'cart/add-discovered', product });
  expect(readded.cart).toHaveLength(1);
  expect(readded.cart[0]).toMatchObject({ quantity: 1, placementUncertain: true, placementPending: true });
});
