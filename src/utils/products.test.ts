import { describe, expect, it } from 'vitest';
import { products } from '../data/mockData';
import { filterProducts } from './products';

describe('filterProducts', () => {
  it('matches product and seller text case-insensitively', () => {
    expect(filterProducts(products, 'NILA', 'All', 3).map(p => p.id)).toEqual(['clay-pot']);
  });
  it('applies category and inclusive radius boundaries', () => {
    expect(filterProducts(products, '', 'Fashion', 2.7).map(p => p.id)).toEqual(['woven-bag']);
  });
  it('returns no products when filters have no match', () => {
    expect(filterProducts(products, 'not here', 'All', 3)).toEqual([]);
  });
});

