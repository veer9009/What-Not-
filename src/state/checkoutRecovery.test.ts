import { afterEach, expect, it } from 'vitest';
import { forgetAttempt, loadAttempts, saveAttempt } from './checkoutRecovery';
import type { PlacementAttempt } from '../types';

const attempt: PlacementAttempt = { key: '43f7847e-b81c-471c-8938-14d74e363bf7', seller: 'Maker',
  request: { seller_id: '2', address_id: '4', items: [{ product_id: '9007199254740993', quantity: 2 }] },
  cartIds: ['backend:9007199254740993'], pending: true };
afterEach(()=>sessionStorage.clear());

it('keeps recovery requests scoped to the buyer and restores in-flight requests as uncertain', () => {
  saveAttempt('1', attempt);
  expect(loadAttempts('2')).toEqual([]);
  expect(loadAttempts('1')).toEqual([{ ...attempt, pending: false }]);
});

it('cleans up only the confirmed attempt', () => {
  const other = { ...attempt, key: '5c316001-2254-42bf-a77c-93779195b134' };
  saveAttempt('1', attempt);
  saveAttempt('1', other);
  forgetAttempt('1', attempt.key);
  expect(loadAttempts('1').map(item=>item.key)).toEqual([other.key]);
  forgetAttempt('1', other.key);
  expect(loadAttempts('1')).toEqual([]);
});

it('restores only public payload fields and preserves exact BIGINT IDs', () => {
  sessionStorage.setItem('whatnot:order-recovery:1', JSON.stringify([{ ...attempt,
    request: { ...attempt.request, buyer_id: '999', total: '0.00', distance: 0,
      items: [{ ...attempt.request.items[0], unit_price: '0.00' }] } }]));
  expect(loadAttempts('1')[0].request).toEqual(attempt.request);
});

it('ignores corrupted recovery data without creating a replacement request', () => {
  sessionStorage.setItem('whatnot:order-recovery:1', 'corrupted');
  expect(loadAttempts('1')).toEqual([]);
  expect(()=>saveAttempt('1', attempt)).toThrow();
  expect(forgetAttempt('1', attempt.key)).toBe(false);
  sessionStorage.setItem('whatnot:order-recovery:1', JSON.stringify([{ ...attempt, key: 'weak-key' }]));
  expect(loadAttempts('1')).toEqual([]);
});
