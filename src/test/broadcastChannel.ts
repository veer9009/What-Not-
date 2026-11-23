/** In-memory transport: each factory is an independent browser/test-file context.
 * Delivery uses a microtask, so tests can await it without clocks or worker I/O.
 * This models the message/close API used by the app, not browser task scheduling.
 */
export function createBroadcastChannelEnvironment() {
  type Listener = { type: string; callback: EventListenerOrEventListenerObject; options?: boolean | AddEventListenerOptions };
  type Snapshot = { onmessage: MemoryBroadcastChannel['onmessage']; onmessageerror: MemoryBroadcastChannel['onmessageerror']; listeners: Listener[] };
  const connections = new Set<MemoryBroadcastChannel>();
  let baseline: Map<MemoryBroadcastChannel, Snapshot> | undefined;
  let epoch = 0;

  class MemoryBroadcastChannel extends EventTarget {
    readonly name: string;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onmessageerror: ((event: MessageEvent) => void) | null = null;
    private closed = false;
    private listeners: Listener[] = [];

    constructor(name: string) {
      super();
      this.name = String(name);
      connections.add(this);
    }

    override addEventListener(type: string, callback: EventListenerOrEventListenerObject | null, options?: boolean | AddEventListenerOptions) {
      super.addEventListener(type, callback, options);
      if (callback) this.listeners.push({ type, callback, options });
    }

    override removeEventListener(type: string, callback: EventListenerOrEventListenerObject | null, options?: boolean | EventListenerOptions) {
      super.removeEventListener(type, callback, options);
      const capture = typeof options === 'boolean' ? options : !!options?.capture;
      this.listeners = this.listeners.filter(item => item.type !== type || item.callback !== callback
        || (typeof item.options === 'boolean' ? item.options : !!item.options?.capture) !== capture);
    }

    postMessage(message: unknown) {
      if (this.closed) throw new DOMException('BroadcastChannel is closed', 'InvalidStateError');
      const data = structuredClone(message);
      const sentIn = epoch;
      for (const peer of connections) {
        if (peer === this || peer.closed || peer.name !== this.name) continue;
        void Promise.resolve().then(() => {
          if (epoch !== sentIn || peer.closed) return;
          const event = new MessageEvent('message', { data: structuredClone(data) });
          peer.onmessage?.call(peer, event);
          peer.dispatchEvent(event);
        });
      }
    }

    close() { this.closed = true; connections.delete(this); }

    snapshot(): Snapshot {
      return { onmessage: this.onmessage, onmessageerror: this.onmessageerror, listeners: [...this.listeners] };
    }

    restore(snapshot?: Snapshot) {
      for (const item of this.listeners) super.removeEventListener(item.type, item.callback, item.options);
      this.listeners = [];
      this.onmessage = snapshot?.onmessage ?? null;
      this.onmessageerror = snapshot?.onmessageerror ?? null;
      if (snapshot) {
        this.closed = false;
        connections.add(this);
        for (const item of snapshot.listeners) this.addEventListener(item.type, item.callback, item.options);
      } else this.close();
    }
  }

  return {
    BroadcastChannel: MemoryBroadcastChannel,
    // Capture channels created by static application imports. Those singleton
    // channels and their original listeners must remain usable in later cases.
    captureBaseline() {
      baseline ??= new Map([...connections].map(channel => [channel, channel.snapshot()]));
    },
    reset() {
      epoch++;
      for (const channel of [...connections]) channel.restore(baseline?.get(channel));
      for (const [channel, snapshot] of baseline ?? []) channel.restore(snapshot);
    },
  };
}
