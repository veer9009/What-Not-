export type Id = string;
export type Role = 'BUYER' | 'SELLER' | 'ADMIN';
export interface User { id: Id; name: string; email: string; role: Role }
export interface TokenResponse { access_token: string; token_type: 'bearer'; expires_in: number; user: User }
export interface Registration { name: string; email: string; phone: string; password: string; role: 'BUYER' | 'SELLER' }
export interface ShopInput { shop_name: string; description: string | null; phone: string; latitude: string; longitude: string }
export interface Shop extends ShopInput { id: Id; user_id: Id; is_verified: boolean; dispatch_location_confirmed_at: string | null }
export type Category = 'Handmade' | 'Home Decor' | 'Gifts' | 'Fashion' | 'Jewellery' | 'Crafts';
export interface ProductInput { name: string; description: string; price: string; stock_quantity: number; category: Category; delivery_radius_km: 1 | 2 | 3; image_url: string | null }
export interface Product extends ProductInput { id: Id; seller_id: Id; status: 'PENDING' | 'APPROVED' | 'REJECTED'; rejection_reason: string | null; is_active: boolean;updated_at?:string|null }
export interface AddressInput { label: string; address_line1: string; address_line2: string | null; city: string; state: string; pincode: string; latitude: string; longitude: string; is_default: boolean }
export interface Address extends AddressInput { id: Id; user_id: Id }
export type OrderStatus = 'PLACED' | 'ACCEPTED' | 'PREPARING' | 'OUT_FOR_DELIVERY' | 'DELIVERED' | 'COMPLETED' | 'DELIVERY_DISPUTED' | 'CANCELLED' | 'REJECTED';
export interface OrderCreate { seller_id: Id; address_id: Id; items: { product_id: Id; quantity: number; expected_unit_price?: string }[] }
export interface Order { id: Id; buyer_id: Id; seller_id: Id; status: OrderStatus; subtotal: string; delivery_fee: string; total: string; delivered_at?:string|null; confirmation_deadline?:string|null; completed_at?:string|null; completion_source?:string|null; items: { product_id: Id; seller_id: Id; name: string; quantity: number; unit_price: string }[] }
export interface Fulfillment {recipient_name:string;phone:string;address_line1:string;address_line2?:string|null;city:string;state:string;pincode:string}
