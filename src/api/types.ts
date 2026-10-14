export type Id = string;
export type Role = 'BUYER' | 'SELLER' | 'ADMIN';
export interface User { id: Id; name: string; email: string; role: Role }
export interface TokenResponse { access_token: string; token_type: 'bearer'; expires_in: number; user: User }
export interface Registration { name: string; email: string; phone: string; password: string; role: 'BUYER' | 'SELLER' }
export interface ShopInput { shop_name: string; description: string | null; phone: string; latitude: string; longitude: string }
export interface Shop extends ShopInput { id: Id; user_id: Id; is_verified: boolean }
export type Category = 'Handmade' | 'Home Decor' | 'Gifts' | 'Fashion' | 'Jewellery' | 'Crafts';
export interface ProductInput { name: string; description: string; price: string; stock_quantity: number; category: Category; delivery_radius_km: 1 | 2 | 3; image_url: string | null }
export interface Product extends ProductInput { id: Id; seller_id: Id; status: 'PENDING' | 'APPROVED' | 'REJECTED'; rejection_reason: string | null; is_active: boolean }
export interface AddressInput { label: string; address_line1: string; address_line2: string | null; city: string; state: string; pincode: string; latitude: string; longitude: string; is_default: boolean }
export interface Address extends AddressInput { id: Id; user_id: Id }
export type OrderStatus = 'PLACED' | 'ACCEPTED' | 'PREPARING' | 'OUT_FOR_DELIVERY' | 'DELIVERED' | 'CANCELLED' | 'REJECTED';
export interface Order { id: Id; buyer_id: Id; seller_id: Id; status: OrderStatus; subtotal: string; delivery_fee: string; total: string; items: { product_id: Id; seller_id: Id; name: string; quantity: number; unit_price: string }[] }
