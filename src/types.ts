export type ProductStatus = 'APPROVED' | 'PENDING' | 'REJECTED';
export type Category = 'Handmade' | 'Home Decor' | 'Gifts' | 'Fashion' | 'Jewellery' | 'Crafts';

export interface Product {
  id: string; name: string; seller: string; price: number; distance: number; radius: 1 | 2 | 3;
  rating: number; category: Category; stock: number; description: string; status: ProductStatus;
  image: string; verified: boolean; isActive: boolean; rejectionReason?: string;
}
export interface CartItem { productId: string; quantity: number }
export interface SellerOrder { id: string; seller: string; items: { product: Product; quantity: number }[]; subtotal: number; delivery: number; total: number }
export interface DemoState { products: Product[]; cart: CartItem[]; orders: SellerOrder[] }
export type DemoAction =
  | { type: 'cart/add'; id: string }
  | { type: 'cart/quantity'; id: string; quantity: number }
  | { type: 'cart/remove'; id: string }
  | { type: 'product/add'; seller: string; product: Product }
  | { type: 'product/update'; seller: string; product: Product }
  | { type: 'product/delete'; seller: string; id: string }
  | { type: 'product/active'; seller: string; id: string; isActive: boolean }
  | { type: 'product/resubmit'; seller: string; id: string }
  | { type: 'product/status'; role: 'admin'; id: string; status: 'APPROVED' | 'REJECTED'; rejectionReason?: string }
  | { type: 'checkout'; id: string };

