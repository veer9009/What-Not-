import { afterEach, expect, it, vi } from 'vitest';
import configuration from '../../vite.config.ts';
import manifest from '../../package.json';

afterEach(() => vi.unstubAllEnvs());

it('selects the reviewed TypeScript configuration despite legacy generated config files', () => {
  for (const command of [manifest.scripts.build, manifest.scripts.dev, manifest.scripts.test, manifest.scripts.preview]) {
    expect(command).toContain('--config vite.config.ts');
  }
});
function build() {
  if (typeof configuration !== 'function') throw new Error('Expected build configuration factory');
  return configuration({ command: 'build', mode: 'production' });
}

it('refuses a development NODE_ENV rather than emitting development API routing in a production artifact', () => {
  vi.stubEnv('NODE_ENV', 'development');
  vi.stubEnv('VITE_API_BASE_URL', '');
  expect(build).toThrow(/NODE_ENV/);
});

it('rejects a production build with an accidental development API override', () => {
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000/api/v1');
  expect(build).toThrow(/API configuration/);
});

it('accepts the default same-origin production build', () => {
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('VITE_API_BASE_URL', '');
  expect(build()).toBeTruthy();
});

it('refuses a development NODE_ENV supplied through Vite environment loading', () => {
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('VITE_USER_NODE_ENV', 'development');
  vi.stubEnv('VITE_API_BASE_URL', '');
  expect(build).toThrow(/NODE_ENV/);
});
