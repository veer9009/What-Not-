import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api, setAccessToken, getAccessToken, onUnauthorized } from './client';

afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });
function response(body: string, status = 200) { return new Response(body, { status, headers: { 'Content-Type': 'application/json' } }); }
describe('HTTP client', () => {
  it('sends JSON and bearer credentials without actor IDs', async () => {
    setAccessToken('test-credential'); const fetcher = vi.fn().mockResolvedValue(response('{"id":1}')); vi.stubGlobal('fetch', fetcher);
    expect(await api('/products', { method: 'POST', body: { name: 'Candle' } })).toEqual({ id: '1' });
    const [url, options] = fetcher.mock.calls[0]; expect(url).toContain('/api/v1/products');
    expect(options.headers.get('Authorization')).toBe('Bearer test-credential'); expect(options.body).toBe('{"name":"Candle"}'); expect(options.cache).toBe('no-store');
  });
  it('preserves BIGINT identities including the maximum and ignores numeric text', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response('{"id":9223372036854775807,"seller_id":9007199254740993,"name":"id: 9223372036854775807","stock_quantity":2}')));
    expect(await api('/products')).toEqual({ id: '9223372036854775807', seller_id: '9007199254740993', name: 'id: 9223372036854775807', stock_quantity: 2 });
  });
  it.each([401,403,404,409,422,500,503])('maps %s without exposing server text', async status => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response('{"detail":"private SQL traceback"}',status)));
    const error = await api('/addresses').catch(e => e) as ApiError; expect(error).toBeInstanceOf(ApiError); expect(error.status).toBe(status); expect(error.message).not.toContain('private');
  });
  it('maps validation locations without echoing supplied secrets', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response('{"detail":[{"loc":["body","phone"],"type":"string_too_short","input":"secret","msg":"secret"}]}',422)));
    const error = await api('/auth/register',{auth:false}).catch(e => e) as ApiError; expect(error.fields.phone).toBeTruthy(); expect(JSON.stringify(error.fields)).not.toContain('secret');
  });
  it('clears a rejected protected token and notifies the auth provider', async () => {
    setAccessToken('expired'); const listener = vi.fn(); const stop = onUnauthorized(listener);
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response('{}',401))); await api('/auth/me').catch(() => {});
    expect(getAccessToken()).toBeNull(); expect(listener).toHaveBeenCalledOnce(); stop();
  });
  it('does not send an existing token or clear it for public login failure', async () => {
    setAccessToken('current'); const fetcher=vi.fn().mockResolvedValue(response('{}',401)); vi.stubGlobal('fetch',fetcher);
    await api('/auth/login',{auth:false}).catch(() => {}); expect(fetcher.mock.calls[0][1].headers.has('Authorization')).toBe(false); expect(getAccessToken()).toBe('current');
  });
  it('rejects late results after logout or a session switch', async () => {
    setAccessToken('old'); let finish!: (r: Response) => void; vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(r => { finish=r; })));
    const pending = api('/orders'); setAccessToken(null); finish(response('[]')); await expect(pending).rejects.toThrow(/session changed/i);
  });
  it('reports network failure safely', async () => { vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('private network detail'))); await expect(api('/orders')).rejects.toThrow(/Unable to reach/); });
  it('rejects malformed success JSON', async () => { vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response('<html>trace</html>'))); await expect(api('/orders')).rejects.toThrow(/invalid response/i); });
  it('accepts empty responses', async () => { vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(null,{status:204}))); expect(await api('/orders')).toBeUndefined(); });
});
