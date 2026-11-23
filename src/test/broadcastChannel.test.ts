import { expect, it, vi } from 'vitest';
import { createBroadcastChannelEnvironment } from './broadcastChannel';

it('delivers named peer messages asynchronously without a native worker transport', async () => {
  const sender = new BroadcastChannel('test-session');
  const receiver = new BroadcastChannel('test-session');
  const receive = vi.fn();
  receiver.onmessage = receive;
  try {
    sender.postMessage('logout');
    expect(receive).not.toHaveBeenCalled();
    await Promise.resolve();
    expect(receive).toHaveBeenCalledOnce();
    expect(receive.mock.calls[0][0].data).toBe('logout');
  } finally {
    sender.close();
    receiver.close();
  }
});

it('keeps identical names isolated between transport contexts', async () => {
  const first = createBroadcastChannelEnvironment();
  const second = createBroadcastChannelEnvironment();
  const sender = new first.BroadcastChannel('session');
  const receiver = new second.BroadcastChannel('session');
  const receive = vi.fn();
  receiver.onmessage = receive;
  sender.postMessage('logout');
  await Promise.resolve();
  expect(receive).not.toHaveBeenCalled();
  first.reset(); second.reset();
});

it('excludes the sender, other names, closed peers and peers opened after sending', async () => {
  const context = createBroadcastChannelEnvironment();
  const sender = new context.BroadcastChannel('session');
  const other = new context.BroadcastChannel('other');
  const closed = new context.BroadcastChannel('session');
  const receive = vi.fn();
  sender.onmessage = other.onmessage = closed.onmessage = receive;
  sender.postMessage('logout');
  closed.close();
  const late = new context.BroadcastChannel('session');
  late.onmessage = receive;
  await Promise.resolve();
  expect(receive).not.toHaveBeenCalled();
  expect(() => closed.postMessage('logout')).toThrow(/closed/);
  context.reset();
});

it('clones messages at send time for onmessage and event listeners', async () => {
  const context = createBroadcastChannelEnvironment();
  const sender = new context.BroadcastChannel('session');
  const receiver = new context.BroadcastChannel('session');
  const receive = vi.fn(); const listen = vi.fn();
  receiver.onmessage = receive;
  receiver.addEventListener('message', listen);
  const payload = { action: 'logout' };
  sender.postMessage(payload);
  payload.action = 'login';
  await Promise.resolve();
  expect(receive.mock.calls[0][0].data).toEqual({ action: 'logout' });
  expect(listen.mock.calls[0][0].data).toEqual({ action: 'logout' });
  context.reset();
});

it('cancels queued messages and removes test peers and handlers on reset', async () => {
  const context = createBroadcastChannelEnvironment();
  const singleton = new context.BroadcastChannel('session');
  const initial = vi.fn(); const leaked = vi.fn();
  singleton.onmessage = initial;
  context.captureBaseline();
  const peer = new context.BroadcastChannel('session');
  singleton.onmessage = leaked;
  singleton.addEventListener('message', leaked);
  peer.onmessage = leaked;
  peer.postMessage('queued-before-reset');
  context.reset();
  await Promise.resolve();
  expect(initial).not.toHaveBeenCalled();
  expect(leaked).not.toHaveBeenCalled();
  expect(() => peer.postMessage('stale')).toThrow(/closed/);
  const nextPeer = new context.BroadcastChannel('session');
  nextPeer.postMessage('next-case');
  await Promise.resolve();
  expect(initial).toHaveBeenCalledOnce();
  expect(initial.mock.calls[0][0].data).toBe('next-case');
  expect(leaked).not.toHaveBeenCalled();
  context.reset();
});

// Constructed during module collection, like src/api/client.ts's singleton.
const moduleChannel = new BroadcastChannel('module-singleton');
const moduleMessages: string[] = [];
moduleChannel.onmessage = event => moduleMessages.push(event.data);

it('uses a module-level connection in the first case', async () => {
  const peer = new BroadcastChannel('module-singleton');
  peer.postMessage('first');
  await Promise.resolve();
  expect(moduleMessages).toContain('first');
  moduleChannel.onmessage = () => { throw new Error('handler leaked from previous case'); };
});

it('restores the module-level connection and handler for a later case', async () => {
  const peer = new BroadcastChannel('module-singleton');
  peer.postMessage('second');
  await Promise.resolve();
  expect(moduleMessages).toContain('second');
});
