import { afterEach, expect, it, vi } from 'vitest';
import { paymentsApi } from './payments';
import { setAccessToken } from './client';
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it('preserves unsafe order IDs and sends only method, reference or reviewed status',async()=>{
  setAccessToken('test-token');const fetcher=vi.fn(async()=>new Response('{}',{status:200}));vi.stubGlobal('fetch',fetcher);
  const id='9007199254740993';
  await paymentsApi.method(id,'UPI');await paymentsApi.report(id,'REF-123');await paymentsApi.confirm(id,'BUYER_REPORTED');
  const calls=fetcher.mock.calls as unknown as [string,RequestInit][];
  expect(calls.map(([url])=>url)).toEqual([`/api/v1/payments/orders/${id}/method`,`/api/v1/payments/orders/${id}/report`,`/api/v1/payments/orders/${id}/confirm`]);
  expect(calls.map(([,options])=>JSON.parse(String(options.body)))).toEqual([{method:'UPI'},{reference:'REF-123'},{expected_status:'BUYER_REPORTED'}]);
});
