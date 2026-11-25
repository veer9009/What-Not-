import { CircleHelp, Smartphone, Truck } from 'lucide-react';
import type { PaymentMethod } from '../api/payments';

export const paymentStatusLabels={NOT_RECORDED:'Not recorded',PENDING:'Awaiting collection',BUYER_REPORTED:'Payment reported',SELLER_CONFIRMED:'Seller confirmed'};

export function PaymentMethodLabel({method}:{method:PaymentMethod|null}){
  const Icon=method==='COD'?Truck:method==='UPI'?Smartphone:CircleHelp;
  const label=method==='COD'?'Cash on delivery':method==='UPI'?'Direct UPI':method===null?'Not recorded':'Unavailable';
  return <span className="payment-method-label"><Icon size={18} aria-hidden="true"/>{label}</span>;
}
