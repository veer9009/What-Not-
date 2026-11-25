import type { PaymentRecord } from '../api/payments';

/** Exact totals for the supplied page only. Never implies an account-wide aggregate. */
export function paymentSummary(records:PaymentRecord[]){
  let order=0n,awaiting=0n,collected=0n,unrecorded=0n,codPending=0,upiPending=0;
  for(const row of records){
    const value=/^(\d+)(?:\.(\d{1,2}))?$/.exec(row.amount);
    if(!value||row.currency!=='INR'||(row.method!==null&&row.method!=='COD'&&row.method!=='UPI'))return null;
    const amount=BigInt(value[1])*100n+BigInt((value[2]??'').padEnd(2,'0'));
    order+=amount;
    if(row.status==='SELLER_CONFIRMED')collected+=amount;
    else if(row.method===null||row.status==='NOT_RECORDED')unrecorded+=amount;
    else if(!['CANCELLED','REJECTED'].includes(row.order_status)&&['PENDING','BUYER_REPORTED'].includes(row.status)){
      awaiting+=amount;
      if(row.method==='COD')codPending++;else if(row.method==='UPI')upiPending++;
    }
  }
  const exact=(value:bigint)=>`${value/100n}.${String(value%100n).padStart(2,'0')}`;
  return {count:records.length,orderValue:exact(order),awaitingValue:exact(awaiting),collectedValue:exact(collected),unrecordedValue:exact(unrecorded),codPending,upiPending};
}
