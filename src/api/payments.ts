import { api, identifier } from './client';
export type PaymentMethod='COD'|'UPI';
export type PaymentStatus='NOT_RECORDED'|'PENDING'|'BUYER_REPORTED'|'SELLER_CONFIRMED';
export interface PaymentRecord {
  order_id:string;seller_id:string;seller_name:string;amount:string;currency:'INR';order_status:string;order_date:string;
  method:PaymentMethod|null;status:PaymentStatus;reference:string|null;reported_at:string|null;confirmed_at:string|null;
  can_select_method:boolean;can_report:boolean;can_confirm:boolean;
}
export interface PaymentMetrics {
  currency:'INR';order_count:number;order_value:string;cod_order_value:string;upi_order_value:string;unrecorded_order_value:string;
  buyer_reported_count:number;buyer_reported_value:string;seller_confirmed_count:number;seller_confirmed_value:string;
  pending_confirmation_count:number;cancelled_order_value:string;cancelled_confirmed_value:string;platform_revenue:string;
}
export const paymentsApi={
  list:(offset=0)=>api<{items:PaymentRecord[];has_more:boolean}>(`/payments?offset=${offset}&limit=50`),
  metrics:()=>api<PaymentMetrics>('/payments/metrics'),
  method:(id:string,method:PaymentMethod)=>api<PaymentRecord>(`/payments/orders/${identifier(id)}/method`,{method:'POST',body:{method}}),
  report:(id:string,reference:string|null)=>api<PaymentRecord>(`/payments/orders/${identifier(id)}/report`,{method:'POST',body:{reference}}),
  confirm:(id:string,expected_status:'PENDING'|'BUYER_REPORTED')=>api<PaymentRecord>(`/payments/orders/${identifier(id)}/confirm`,{method:'POST',body:{expected_status}}),
};
