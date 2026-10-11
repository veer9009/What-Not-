import { describe, expect, it } from 'vitest';
import { validateProduct } from './validation';

describe('validateProduct', () => {
  it('requires a supported category and delivery radius', () => {
    const input = { name:'Doll', description:'Handmade doll', category:'Handmade' as const, price:200, stock:3, seller:'Maker', radius:2 as const };
    expect(validateProduct({ ...input, category: 'Invalid' as never, radius: 4 as never })).toMatchObject({ category: 'Choose a valid category', radius: 'Choose a 1, 2 or 3 km delivery radius' });
  });
  it('rejects blank required fields and non-positive numbers', () => {
    const errors = validateProduct({ name:'', description:'', category:'Handmade', price:0, stock:-1, seller:'', radius:1 });
    expect(errors).toMatchObject({ name:'Required', description:'Required', price:'Enter a positive price', stock:'Enter a valid quantity', seller:'Required' });
  });
  it('accepts a complete valid product', () => {
    expect(validateProduct({ name:'Doll', description:'Handmade doll', category:'Handmade', price:200, stock:3, seller:'Maker', radius:2 })).toEqual({});
  });
  it('rejects blank and nonfinite numeric input', () => {
    expect(validateProduct({ name:'Doll', description:'Handmade', category:'Handmade', price:Number.NaN, stock:'' as unknown as number, seller:'Maker', radius:1 })).toMatchObject({ price:'Enter a positive price', stock:'Enter a valid quantity' });
  });
});
