import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, beforeEach } from 'vitest';
import { createBroadcastChannelEnvironment } from './broadcastChannel';

// jsdom has no scrolling implementation. Navigation tests spy on this boundary;
// real scroll/focus behavior is checked separately in headless Chrome.
Object.defineProperty(window,'scrollTo',{configurable:true,writable:true,value:()=>{}});
// Role queries traverse the full sidebar in jsdom. Allow async rendering to finish
// on slower Windows hosts; assertions still fail if the expected UI never appears.
configure({asyncUtilTimeout:5000});

const channels = createBroadcastChannelEnvironment();
// Use a regular global definition: vi.unstubAllGlobals() in application tests
// must not restore Node's process-wide, cross-worker BroadcastChannel.
Object.defineProperty(globalThis, 'BroadcastChannel', { configurable: true, writable: true, value: channels.BroadcastChannel });

beforeEach(() => {
  channels.captureBaseline();
  channels.reset();
});
afterEach(() => {
  try { cleanup(); } finally { channels.reset(); }
});
