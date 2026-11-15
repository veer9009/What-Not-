import { afterEach, expect, it, vi } from 'vitest';
import { api, setAccessToken } from './client';

afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

function configured(production: boolean, base = '') {
  vi.stubEnv('PROD', production);
  vi.stubEnv('VITE_API_BASE_URL', base);
  const fetcher = vi.fn().mockResolvedValue(new Response('[]', { status: 200 }));
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}

it.each(['/auth/register', '/auth/login', '/auth/me', '/orders', '/discovery/products'])(
  'uses same-origin production API for %s without duplicating the prefix', async path => {
    const fetcher = configured(true);
    await api(path);
    expect(fetcher.mock.calls[0][0]).toBe(`/api/v1${path}`);
  });

it('preserves the Windows loopback development default', async () => {
  const fetcher = configured(false);
  await api('/auth/login', { auth: false });
  expect(fetcher.mock.calls[0][0]).toBe('http://127.0.0.1:8000/api/v1/auth/login');
});

it.each(['/api/v1', '/api/v1/'])('accepts the exact same-origin prefix %s', async base => {
  const fetcher = configured(true, base);
  await api('/orders');
  expect(fetcher.mock.calls[0][0]).toBe('/api/v1/orders');
});

it('permits an explicit HTTPS API deployment with the existing version prefix', async () => {
  const fetcher = configured(true, 'https://api.example.test/api/v1/');
  await api('/orders');
  expect(fetcher.mock.calls[0][0]).toBe('https://api.example.test/api/v1/orders');
});

it.each([
  'http://api.example.test/api/v1', 'https://localhost/api/v1',
  'https://127.0.0.2/api/v1', 'https://[::1]/api/v1', 'https://0.0.0.0/api/v1',
  'https://localhost./api/v1', 'https://api.localhost/api/v1',
  '//api.example.test/api/v1', 'https://api.example.test/api/api/v1',
  'https://api.example.test/api', 'https://api.example.test',
  'https://user:private@api.example.test/api/v1',
  'https://api.example.test/api/v1?private=value', 'https://api.example.test/api/v1#fragment',
])('rejects an unsafe or wrong-prefix production API override without making a request: %s', async base => {
  const fetcher = configured(true, base);
  await expect(api('/orders')).rejects.toThrow(/API configuration/);
  expect(fetcher).not.toHaveBeenCalled();
});

it('rejects a caller that repeats the API prefix', async () => {
  const fetcher = configured(true);
  await expect(api('/api/v1/orders')).rejects.toThrow(/API path/);
  expect(fetcher).not.toHaveBeenCalled();
});
