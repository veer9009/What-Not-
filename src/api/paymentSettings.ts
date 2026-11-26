import { api, identifier } from './client';
export interface SellerPaymentSettings {
  seller_id:string;upi_id:string|null;account_holder_name:string|null;accept_cod:boolean;accept_upi:boolean;
  verification_status:string;updated_at:string;revision:number;review_reason:string|null;
  upi_enabled:boolean;upi_unavailable_reason:string|null;
}
export type PaymentSettingsInput=Pick<SellerPaymentSettings,'upi_id'|'account_holder_name'|'accept_cod'|'accept_upi'>;
export const paymentSettingsApi={
  get:()=>api<SellerPaymentSettings>('/payments/settings'),
  save:(input:PaymentSettingsInput)=>api<SellerPaymentSettings>('/payments/settings',{method:'PUT',body:input}),
  admin:()=>api<{items:SellerPaymentSettings[]}>('/payments/admin/settings'),
  review:(sellerId:string,input:{status:'APPROVED'|'REJECTED';expected_updated_at:string;reason:string})=>api<SellerPaymentSettings>(`/payments/admin/settings/${identifier(sellerId)}/review`,{method:'POST',body:input}),
};
