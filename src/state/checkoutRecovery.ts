import { identifier } from '../api/client';
import type { PlacementAttempt } from '../types';

const storageKey = (buyerId: string) => `whatnot:order-recovery:${identifier(buyerId)}`;
const uuid4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function readAttempts(buyerId: string | undefined, strict: boolean): PlacementAttempt[] {
  if (!buyerId) return [];
  try {
    const entries: unknown = JSON.parse(sessionStorage.getItem(storageKey(buyerId)) ?? '[]');
    if (!Array.isArray(entries)) throw new Error();
    const keys = new Set<string>();
    return entries.map(entry => {
      if (!entry || typeof entry.key !== 'string' || !uuid4.test(entry.key) || keys.has(entry.key)) throw new Error();
      keys.add(entry.key);
      const request = entry.request;
      const seller_id = identifier(request.seller_id), address_id = identifier(request.address_id);
      if (!Array.isArray(request.items) || !request.items.length) throw new Error();
      const seen = new Set<string>();
      const items = request.items.map((item: { product_id: string; quantity: number }) => {
        const product_id = identifier(item.product_id);
        if (seen.has(product_id) || !Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > 2147483647) throw new Error();
        seen.add(product_id);
        return { product_id, quantity: item.quantity };
      });
      // Restore only public request fields. No token, address coordinates, or prices are stored.
      return { key: entry.key, request: { seller_id, address_id, items },
        seller: typeof entry.seller === 'string' ? entry.seller : `Seller #${seller_id}`,
        cartIds: items.map((item: { product_id: string })=>`backend:${item.product_id}`), pending: false };
    });
  } catch (error) { if (strict) throw error; return []; }
}

export function loadAttempts(buyerId?: string) { return readAttempts(buyerId, false); }

export function saveAttempt(buyerId: string, attempt: PlacementAttempt) {
  const entries = readAttempts(buyerId, true).filter(item=>item.key !== attempt.key);
  // Must succeed synchronously before submitting; failure means no order request is sent.
  sessionStorage.setItem(storageKey(buyerId), JSON.stringify([...entries, attempt]));
}

export function forgetAttempt(buyerId: string, key: string) {
  try {
    const entries = readAttempts(buyerId, true).filter(item=>item.key !== key);
    if (entries.length) sessionStorage.setItem(storageKey(buyerId), JSON.stringify(entries));
    else sessionStorage.removeItem(storageKey(buyerId));
    return true;
  } catch { return false; }
}
