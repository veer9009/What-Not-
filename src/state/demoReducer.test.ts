import { describe, expect, it } from 'vitest';
import { demoReducer } from './demoReducer';
import type { DemoState, Product } from '../types';

const product: Product = { id: 'p1', name: 'Candle', seller: 'Maker', price: 350, distance: 0.8, radius: 2, rating: 4.8, category: 'Gifts', stock: 4, description: 'Hand-poured', status: 'pending', image: 'candle.jpg', verified: true };
const state: DemoState = { products: [product], cart: [] };

describe('demoReducer', () => {
  it('adds products to cart and never lowers quantity below one', () => {
    const added = demoReducer(state, { type: 'cart/add', id: 'p1' });
    const lowered = demoReducer(added, { type: 'cart/quantity', id: 'p1', quantity: 0 });
    expect(lowered.cart).toEqual([{ productId: 'p1', quantity: 1 }]);
  });

  it('adds and moderates a seller listing', () => {
    const added = demoReducer(state, { type: 'product/add', product: { ...product, id: 'p2' } });
    const approved = demoReducer(added, { type: 'product/status', id: 'p2', status: 'approved' });
    expect(approved.products.find(item => item.id === 'p2')?.status).toBe('approved');
  });

  it('edits and deletes a listing', () => {
    const edited = demoReducer(state, { type: 'product/update', product: { ...product, name: 'New Candle' } });
    expect(edited.products[0].name).toBe('New Candle');
    expect(demoReducer(edited, { type: 'product/delete', id: 'p1' }).products).toHaveLength(0);
  });
});

