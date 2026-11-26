import { api, identifier } from './client';
import type { Order } from './types';
export type CheckoutMethod = 'COD' | 'UPI';
export interface CheckoutRequest { address_id:string; sellers:{seller_id:string;items:{product_id:string;quantity:number;expected_unit_price:string}[];payment_method?:CheckoutMethod}[] }
export interface CheckoutPreview { groups:{seller_id:string;seller_name:string;items:{product_id:string;name:string;quantity:number;unit_price:string;image_url?:string|null}[];subtotal:string;delivery_fee:string;total:string;available_payment_methods:CheckoutMethod[];upi_unavailable_reason:string|null}[]; total:string;currency:'INR' }
export function checkoutBody(input:CheckoutRequest) {
 return `{"address_id":${identifier(input.address_id)},"sellers":[${input.sellers.map(seller=>`{"seller_id":${identifier(seller.seller_id)},"items":[${seller.items.map(item=>`{"product_id":${identifier(item.product_id)},"quantity":${JSON.stringify(item.quantity)},"expected_unit_price":${JSON.stringify(item.expected_unit_price)}}`).join(',')}]${seller.payment_method?`,"payment_method":${JSON.stringify(seller.payment_method)}`:''}}`).join(',')}]}`;
}
export const checkoutApi={
 preview:(input:CheckoutRequest)=>api<CheckoutPreview>('/checkout/preview',{method:'POST',bodyText:checkoutBody(input)}),
 place:(input:CheckoutRequest,key:string)=>api<{orders:Order[]}>('/checkout',{method:'POST',bodyText:checkoutBody(input),idempotencyKey:key}),
};
