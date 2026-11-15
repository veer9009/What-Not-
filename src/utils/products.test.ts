import { describe, expect, it } from 'vitest';
import { products } from '../data/mockData';
import { filterProducts } from './products';

describe('filterProducts', () => {
  it.each([1,2,3])('keeps inclusive %s km sample filters separate from live discovery',radius=>{
    const listed=[1,2,3,3.001].map(distance=>({...products[0],id:String(distance),
      status:'APPROVED' as const,isActive:true,stock:1,radius:3 as const,distance}));
    expect(filterProducts(listed,'','All',radius).map(p=>p.distance)).toEqual([1,2,3].filter(d=>d<=radius));
  });
  it('matches product and seller text case-insensitively', () => {
    expect(filterProducts(products, 'NILA', 'All', 3).map(p => p.id)).toEqual(['clay-pot']);
  });
  it('applies category and inclusive radius boundaries', () => {
    expect(filterProducts(products, '', 'Fashion', 2.7).map(p => p.id)).toEqual(['woven-bag']);
  });
  it('returns no products when filters have no match', () => {
    expect(filterProducts(products, 'not here', 'All', 3)).toEqual([]);
  });
  it('honours each seller radius and sorts closest first', () => {
    const listed = [
      { ...products[0], id:'far', distance:1.4, radius:1 as const },
      { ...products[1], id:'near', distance:0.4, radius:3 as const }
    ];
    expect(filterProducts(listed, '', 'All', 3).map(p => p.id)).toEqual(['near']);
  });
});
