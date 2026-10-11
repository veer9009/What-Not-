import { describe, expect, it } from 'vitest';
import { demoReducer } from './demoReducer';
import { products } from '../data/mockData';
import { filterProducts } from '../utils/products';
import type { DemoState, Product } from '../types';

const product = { ...products[0], status: 'APPROVED', isActive: true, stock: 3 } as Product;
const initial = (p = product): DemoState => ({ products: [p], cart: [], orders: [] });

describe('marketplace approval and order rules', () => {
  it('forces a new seller product to pending, clearing any supplied approval/reason', () => {
    const next = demoReducer(initial(), { type: 'product/add', seller: product.seller, product: { ...product, id: 'new', rejectionReason: 'old' } });
    expect(next.products[1]).toMatchObject({ status: 'PENDING', isActive: true, rejectionReason: undefined });
  });
  it('cannot approve through a seller edit or edit another shop’s listing', () => {
    const state = initial({ ...product, status: 'REJECTED', rejectionReason: 'Photo unclear' });
    const edited = demoReducer(state, { type: 'product/update', seller: product.seller, product: { ...product, name: 'Updated' } });
    expect(edited.products[0]).toMatchObject({ status: 'REJECTED', rejectionReason: 'Photo unclear', name: 'Updated' });
    expect(demoReducer(state, { type: 'product/update', seller: 'Other shop', product })).toBe(state);
  });
  it('requires the admin role and a pending product for approval', () => {
    const state = initial({ ...product, status: 'PENDING' });
    expect(demoReducer(state, { type: 'product/status', role: 'seller', id: product.id, status: 'APPROVED' } as never)).toBe(state);
    expect(demoReducer(state, { type: 'product/status', role: 'admin', id: product.id, status: 'APPROVED' }).products[0].status).toBe('APPROVED');
    expect(demoReducer(initial(), { type: 'product/status', role: 'admin', id: product.id, status: 'REJECTED', rejectionReason: 'Bad photo' })).toEqual(initial());
  });
  it('requires a nonblank rejection reason and preserves the trimmed reason', () => {
    const state = initial({ ...product, status: 'PENDING' });
    expect(demoReducer(state, { type: 'product/status', role: 'admin', id: product.id, status: 'REJECTED', rejectionReason: '  ' })).toBe(state);
    const rejected = demoReducer(state, { type: 'product/status', role: 'admin', id: product.id, status: 'REJECTED', rejectionReason: '  Use a clear photo  ' });
    expect(rejected.products[0]).toMatchObject({ status: 'REJECTED', rejectionReason: 'Use a clear photo' });
    const resubmitted = demoReducer(rejected, { type: 'product/resubmit', seller: product.seller, id: product.id });
    expect(resubmitted.products[0]).toMatchObject({ status: 'PENDING', rejectionReason: undefined });
  });
  it('sends approved edits back to review and deactivation removes cart entries', () => {
    const state = { ...initial(), cart: [{ productId: product.id, quantity: 1 }] };
    expect(demoReducer(state, { type: 'product/update', seller: product.seller, product: { ...product, price: 999 } }).products[0].status).toBe('PENDING');
    const inactive = demoReducer(state, { type: 'product/active', seller: product.seller, id: product.id, isActive: false });
    expect(inactive.cart).toEqual([]);
    expect(inactive.products[0].isActive).toBe(false);
    expect(demoReducer(inactive, { type: 'product/active', seller: product.seller, id: product.id, isActive: true }).products[0].status).toBe('APPROVED');
  });
  it.each([
    { status: 'PENDING' }, { status: 'REJECTED' }, { isActive: false }, { stock: 0 }, { distance: 3.1 },
  ])('hides and prevents purchasing an ineligible product: %j', change => {
    const p = { ...product, radius: 3, ...change } as Product;
    expect(filterProducts([p], '', 'All', 3)).toEqual([]);
    expect(demoReducer(initial(p), { type: 'cart/add', id: p.id }).cart).toEqual([]);
    const stale = { ...initial(p), cart: [{ productId: p.id, quantity: 1 }] };
    expect(demoReducer(stale, { type: 'checkout', id: 'checkout' }).orders).toEqual([]);
  });
  it('shows an approved, active, stocked product on the radius boundary', () => {
    expect(filterProducts([{ ...product, distance: 3, radius: 3 }], '', 'All', 3)).toHaveLength(1);
  });
  it('creates one order per seller, snapshots items, reduces stock and clears cart', () => {
    const other = { ...product, id: 'other', seller: 'Other maker' };
    const state = { ...initial(), products: [product, other], cart: [{ productId: product.id, quantity: 2 }, { productId: other.id, quantity: 1 }] };
    const next = demoReducer(state, { type: 'checkout', id: 'checkout' });
    expect(next.orders).toHaveLength(2);
    expect(next.orders.map(order => order.seller)).toEqual([product.seller, other.seller]);
    next.orders.forEach(order => expect(order.items.every(item => item.product.seller === order.seller)).toBe(true));
    expect(next.orders[0].items[0].product.stock).toBe(3);
    expect(next.products.map(p => p.stock)).toEqual([1, 2]);
    expect(next.cart).toEqual([]);
    expect(demoReducer(next, { type: 'checkout', id: 'again' }).orders).toHaveLength(2);
  });
  it('blocks checkout if quantity exceeds stock or is not a positive integer', () => {
    for (const quantity of [4, 0, 1.5, NaN]) {
      const state = { ...initial(), cart: [{ productId: product.id, quantity }] };
      expect(demoReducer(state, { type: 'checkout', id: 'checkout' }).orders).toEqual([]);
    }
  });
});
