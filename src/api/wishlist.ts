import { api, identifier } from './client';
import type { BuyerProduct } from './discovery';
export interface WishlistItem { product_id:string; available:boolean; product:BuyerProduct|null }
export interface Wishlist { items:WishlistItem[]; count:number }
export const wishlistApi={
  list:()=>api<Wishlist>('/wishlist'),
  set:(id:string,saved:boolean)=>api<{saved:boolean}>(`/wishlist/${identifier(id)}`,{method:'PUT',body:{saved}}),
};
