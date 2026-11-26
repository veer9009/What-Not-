import { identifier } from '../api/client';
import { checkoutBody, type CheckoutRequest } from '../api/checkout';
export interface CheckoutBatch {key:string;request:CheckoutRequest}
const storageKey=(buyer:string)=>`whatnot:checkout-batch:${identifier(buyer)}`;
function validate(value:unknown):CheckoutBatch {
 const entry=value as CheckoutBatch;
 if(!entry||!/^([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/i.test(entry.key)||!entry.request)throw new Error('Invalid checkout recovery');
 identifier(entry.request.address_id);const sellers=new Set<string>();const products=new Set<string>();
 if(!Array.isArray(entry.request.sellers)||!entry.request.sellers.length)throw new Error('Invalid sellers');
 for(const seller of entry.request.sellers){identifier(seller.seller_id);if(sellers.has(seller.seller_id)||!['COD','UPI'].includes(seller.payment_method??'')||!Array.isArray(seller.items)||!seller.items.length)throw new Error('Invalid seller');sellers.add(seller.seller_id);
 for(const item of seller.items){identifier(item.product_id);if(products.has(item.product_id)||!Number.isInteger(item.quantity)||item.quantity<1||item.quantity>2147483647||!/^\d{1,10}\.\d{2}$/.test(item.expected_unit_price)||Number(item.expected_unit_price)<=0)throw new Error('Invalid item');products.add(item.product_id);}}
 // Strip unexpected fields and retain every original seller, quantity, price and method.
 return {key:entry.key,request:JSON.parse(checkoutBody(entry.request).replace(/"(address_id|seller_id|product_id)":(\d+)/g,'"$1":"$2"')) as CheckoutRequest};
}
export function loadBatch(buyer:string):CheckoutBatch|null {const raw=sessionStorage.getItem(storageKey(buyer));return raw===null?null:validate(JSON.parse(raw));}
export function saveBatch(buyer:string,attempt:CheckoutBatch){const next=validate(attempt);const current=loadBatch(buyer);if(current&&(current.key!==next.key||checkoutBody(current.request)!==checkoutBody(next.request)))throw new Error('Unresolved checkout already exists');sessionStorage.setItem(storageKey(buyer),JSON.stringify(next));if(JSON.stringify(loadBatch(buyer))!==JSON.stringify(next))throw new Error('Checkout recovery was not saved');}
export function forgetBatch(buyer:string,key:string){try{if(loadBatch(buyer)?.key!==key)return false;sessionStorage.removeItem(storageKey(buyer));return loadBatch(buyer)===null;}catch{return false;}}
