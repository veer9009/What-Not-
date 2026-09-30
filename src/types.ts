export type ProductStatus = 'approved' | 'pending' | 'rejected';
export type Category = 'Handmade' | 'Home Decor' | 'Gifts' | 'Fashion' | 'Jewellery' | 'Crafts';

export interface Product {
  id: string; name: string; seller: string; price: number; distance: number; radius: 1 | 2 | 3;
  rating: number; category: Category; stock: number; description: string; status: ProductStatus;
  image: string; verified: boolean;
}
export interface CartItem { productId: string; quantity: number }
export interface DemoState { products: Product[]; cart: CartItem[] }
export type DemoAction =
  | { type: 'cart/add'; id: string }
  | { type: 'cart/quantity'; id: string; quantity: number }
  | { type: 'cart/remove'; id: string }
  | { type: 'product/add'; product: Product }
  | { type: 'product/update'; product: Product }
  | { type: 'product/delete'; id: string }
  | { type: 'product/status'; id: string; status: ProductStatus };

