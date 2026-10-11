import type { Product } from '../types';

export function isBuyerEligible(product: Product) {
  return product.status === 'APPROVED' && product.isActive === true && product.stock > 0 &&
    product.distance >= 0 && product.distance <= product.radius;
}

export function filterProducts(products: Product[], query: string, category: string, radius: number) {
  const term = query.trim().toLowerCase();
  return products.filter(product =>
    isBuyerEligible(product) &&
    product.distance <= radius &&
    product.distance <= product.radius &&
    product.stock > 0 &&
    (category === 'All' || product.category === category) &&
    (!term || `${product.name} ${product.seller}`.toLowerCase().includes(term))
  ).sort((a,b) => a.distance - b.distance);
}
