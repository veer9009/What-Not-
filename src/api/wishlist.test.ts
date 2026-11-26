import { afterEach, expect, it, vi } from 'vitest';
import { wishlistApi } from './wishlist';
import { setAccessToken } from './client';
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it('uses owned persistence endpoints with exact BIGINT product IDs and explicit saved state',async()=>{
 const fetch=vi.fn(async()=>new Response('{"saved":true}',{headers:{'content-type':'application/json'}}));vi.stubGlobal('fetch',fetch);
 await wishlistApi.set('9223372036854775807',true);
 expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/wishlist/9223372036854775807'),expect.objectContaining({method:'PUT',body:'{"saved":true}'}));
});
it('rejects malformed saved product identifiers before sending a request',async()=>{
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);expect(()=>wishlistApi.set('../orders',true)).toThrow();expect(fetch).not.toHaveBeenCalled();
});
