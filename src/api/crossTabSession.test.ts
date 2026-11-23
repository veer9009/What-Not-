import { afterEach, expect, it, vi } from 'vitest';
import { createBroadcastChannelEnvironment } from '../test/broadcastChannel';

afterEach(() => { vi.unstubAllGlobals(); vi.resetModules(); });

it('logs out another independently loaded client through the shared session channel', async () => {
  vi.resetModules();
  const firstTab = await import('./client');
  vi.resetModules();
  const secondTab = await import('./client');
  const unauthorized = vi.fn();
  const stop = secondTab.onUnauthorized(unauthorized);
  firstTab.setAccessToken('first-tab');
  secondTab.setAccessToken('second-tab');
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
  try {
    await firstTab.logoutSession();
    expect(firstTab.getAccessToken()).toBeNull();
    expect(secondTab.getAccessToken()).toBeNull();
    expect(unauthorized).toHaveBeenCalledOnce();
  } finally { stop(); }
});

it('keeps a client in another browser context signed in when a local tab logs out', async () => {
  const firstContext = createBroadcastChannelEnvironment();
  const secondContext = createBroadcastChannelEnvironment();
  vi.resetModules();
  vi.stubGlobal('BroadcastChannel', firstContext.BroadcastChannel);
  const firstTab = await import('./client');
  vi.resetModules();
  vi.stubGlobal('BroadcastChannel', secondContext.BroadcastChannel);
  const secondTab = await import('./client');
  firstTab.setAccessToken('first-context');
  secondTab.setAccessToken('second-context');
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
  try {
    await firstTab.logoutSession();
    expect(firstTab.getAccessToken()).toBeNull();
    expect(secondTab.getAccessToken()).toBe('second-context');
  } finally { firstContext.reset(); secondContext.reset(); }
});
