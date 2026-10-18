import { afterEach, expect, it, vi } from 'vitest';
import { discoveryApi } from './discovery';
import { setAccessToken } from './client';
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it('sends an exact BIGINT address ID in a JSON body, never the URL',async()=>{
  vi.stubGlobal('fetch',async(url:string,options:RequestInit)=>{
    expect(url).not.toContain('9223372036854775807');
    expect(options.method).toBe('POST');
    expect(options.body).toBe('{"address_id":9223372036854775807}');
    return new Response('[]');
  });
  expect(await discoveryApi.list({address_id:'9223372036854775807'})).toEqual([]);
});
