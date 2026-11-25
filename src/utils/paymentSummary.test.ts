import { expect, it } from 'vitest';
import type { PaymentRecord } from '../api/payments';
import { paymentSummary } from './paymentSummary';
const row=(overrides:Partial<PaymentRecord>={}):PaymentRecord=>({order_id:'1',seller_id:'2',seller_name:'Shop',amount:'0.10',currency:'INR',order_status:'ACCEPTED',order_date:'2026-11-24T00:00:00Z',method:'UPI',status:'PENDING',reference:null,reported_at:null,confirmed_at:null,can_select_method:false,can_report:false,can_confirm:true,...overrides});
it('adds authoritative page values exactly without binary floating point',()=>{
  const result=paymentSummary([row(),row({amount:'0.20',method:'COD'})]);
  expect(result).toMatchObject({orderValue:'0.30',awaitingValue:'0.30',collectedValue:'0.00',codPending:1,upiPending:1,count:2});
});
it('separates unknown methods and cancelled values from awaiting collections',()=>{
  const result=paymentSummary([row({amount:'100.00',method:null,status:'NOT_RECORDED'}),row({amount:'20.00',order_status:'CANCELLED'}),row({amount:'30.00',order_status:'REJECTED'}),row({amount:'0.20',status:'BUYER_REPORTED'}),row({amount:'0.10',order_status:'CANCELLED',status:'SELLER_CONFIRMED'})]);
  expect(result).toMatchObject({orderValue:'150.30',awaitingValue:'0.20',collectedValue:'0.10',unrecordedValue:'100.00',codPending:0,upiPending:1});
});
it('withholds unsupported or malformed monetary data instead of inventing totals',()=>{
  expect(paymentSummary([row({amount:'not an amount'})])).toBeNull();
  expect(paymentSummary([row({amount:'1.234'})])).toBeNull();
  expect(paymentSummary([row({amount:'9007199254740993.99'}),row({amount:'0.01'})])?.orderValue).toBe('9007199254740994.00');
});
it('withholds totals when the runtime response contains an unsupported method',()=>{
  expect(paymentSummary([row({amount:'10.00',method:'CARD' as PaymentRecord['method']})])).toBeNull();
});
