import { describe, it, expect, vi, afterEach } from 'vitest';
import { creativeApi } from './creative';
afterEach(()=>vi.unstubAllGlobals());
describe('creative API',()=>{
  it('sends professional search filters to the server before pagination',async()=>{
    const fetcher=vi.fn().mockResolvedValue(new Response('[]',{status:200}));vi.stubGlobal('fetch',fetcher);
    await creativeApi.listings(50,'PROFESSIONAL',{q:'cloud work',category:'Cloud and DevOps',remote:true});
    const url=new URL(String(fetcher.mock.calls[0][0]),'http://localhost');
    expect(Object.fromEntries(url.searchParams)).toMatchObject({domain:'PROFESSIONAL',q:'cloud work',category:'Cloud and DevOps',remote:'true',offset:'50'});
  });
  it('keeps exact engagement identifiers in confirmation paths',async()=>{
    const fetcher=vi.fn().mockResolvedValue(new Response('{}',{status:200}));vi.stubGlobal('fetch',fetcher);
    await creativeApi.complete('9007199254740993');
    expect(fetcher.mock.calls[0][0]).toContain('/creative/engagements/9007199254740993/complete');
  });
  it('rejects invalid identifiers before sending',async()=>{
    const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);
    expect(()=>creativeApi.accept('1/../../admin')).toThrow();expect(fetcher).not.toHaveBeenCalled();
  });
});
