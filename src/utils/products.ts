import type { Product } from '../types';

export function filterProducts(products: Product[], query: string, category: string, radius: number) {
  const term = query.trim().toLowerCase();
  return products.filter(product =>
    product.status === 'approved' &&
    product.distance <= radius &&
    (category === 'All' || product.category === category) &&
    (!term || `${product.name} ${product.seller}`.toLowerCase().includes(term))
  );
}

