import type { CartItem, Product, SellerOrder } from '../types';
import { isBuyerEligible } from './products';

export const DELIVERY_FEE = 49;

// Validate the entire basket again at checkout; never silently order a partial basket.
export function createSellerOrders(products: Product[], cart: CartItem[], id: string): SellerOrder[] {
  const groups = new Map<string, SellerOrder>();
  const seen = new Set<string>();
  for (const item of cart) {
    const product = products.find(p => p.id === item.productId);
    if (!product || !isBuyerEligible(product) || !Number.isInteger(item.quantity) ||
      item.quantity < 1 || item.quantity > product.stock || seen.has(item.productId)) return [];
    seen.add(item.productId);
    let order = groups.get(product.seller);
    if (!order) {
      order = { id: `${id}-${groups.size + 1}`, seller: product.seller, items: [], subtotal: 0, delivery: DELIVERY_FEE, total: 0 };
      groups.set(product.seller, order);
    }
    order.items.push({ product: { ...product }, quantity: item.quantity });
    order.subtotal += product.price * item.quantity;
    order.total = order.subtotal + order.delivery;
  }
  return [...groups.values()];
}
