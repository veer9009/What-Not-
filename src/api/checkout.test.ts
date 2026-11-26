import { afterEach, expect, it, vi } from 'vitest';
import { checkoutApi } from './checkout';
afterEach(()=>vi.unstubAllGlobals());
it('submits one atomic batch with exact BIGINT IDs and the original key', async()=>{
 const fetcher=vi.fn().mockResolvedValue(new Response('{"orders":[]}',{status:200}));vi.stubGlobal('fetch',fetcher);
 await checkoutApi.place({address_id:'9007199254740993',sellers:[{seller_id:'2',payment_method:'COD',items:[{product_id:'3',quantity:2,expected_unit_price:'1.20'}]}]},'batch-key');
 expect(fetcher.mock.calls[0][0]).toMatch(/\/checkout$/); const options=fetcher.mock.calls[0][1];
 expect(options.body).toContain('"address_id":9007199254740993');expect(options.headers.get('Idempotency-Key')).toBe('batch-key');expect(options.body).toContain('"payment_method":"COD"');
});
