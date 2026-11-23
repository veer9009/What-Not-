import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach } from 'vitest';
import { createBroadcastChannelEnvironment } from './broadcastChannel';

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
