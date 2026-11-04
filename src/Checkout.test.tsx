import { useEffect, useState } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from './state/AuthContext';
import { DemoProvider, useDemo } from './state/DemoContext';
import { CartPage } from './pages/BuyerPages';
import { setAccessToken } from './api/client';
import type { BuyerProduct } from './api/discovery';

const first: BuyerProduct = { id: '3', seller_id: '2', name: 'Real vase', shop_name: 'Local maker',
  description: 'A handmade vase', price: '250.00', stock_quantity: 5, category: 'Crafts',
  delivery_radius_km: 2, image_url: null, is_verified: false, delivery_eligibility: 'CONFIRMED_AT_CHECKOUT' };
const second: BuyerProduct = { ...first, id: '6', seller_id: '7', name: 'Real candle' };
const address = { id: 4, user_id: 1, label: 'Home', address_line1: 'Maker Lane', city: 'Mumbai',
  state: 'Maharashtra', pincode: '400001', latitude: '19', longitude: '72', is_default: true };
type Reply = [number, unknown];
type Call = { path: string; body: any; key: string | null };

function Seed({ products, sample }: { products: BuyerProduct[]; sample: boolean }) {
  const { dispatch } = useDemo();
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    products.forEach(product => dispatch({ type: 'cart/add-discovered', product }));
    if (sample) dispatch({ type: 'cart/add', id: 'candles' });
  }, [dispatch, products, sample]);
  return <><button onClick={()=>setVisible(value=>!value)}>{visible?'Leave cart':'Return to cart'}</button>{visible&&<CartPage/>}</>;
}
function Ready(props: { products: BuyerProduct[]; sample: boolean }) {
  const auth = useAuth();
  return auth.user ? <DemoProvider ownerId={auth.user.id}><Seed {...props}/></DemoProvider> : auth.error ? <p role="alert">{auth.error}</p> : null;
}
function setup(products = [first], handler?: (call: Call) => Reply | Promise<Reply>, sample = false, savedAddresses: unknown[] = [address]) {
  setAccessToken('checkout-test');
  const calls: Call[] = [];
  vi.stubGlobal('fetch', async (input: string, options: RequestInit) => {
    const path = new URL(input).pathname.replace('/api/v1', '');
    const body = options.body ? JSON.parse(String(options.body)) : undefined;
    const key = new Headers(options.headers).get('Idempotency-Key');
    calls.push({ path, body, key });
    let reply: Reply;
    if (path === '/auth/me') reply = [200, { id: 1, name: 'Buyer', email: 'buyer@example.test', role: 'BUYER' }];
    else if (path === '/addresses') reply = [200, savedAddresses];
    else if (path.startsWith('/discovery/')) {
      expect(body).toEqual({ address_id: 4 });
      reply = handler ? await handler({ path, body, key }) : [200, products.find(p => path.endsWith('/' + p.id))];
    } else reply = handler ? await handler({ path, body, key }) : [201, { id: 10, total: '250.00' }];
    return new Response(JSON.stringify(reply[1]), { status: reply[0] });
  });
  render(<MemoryRouter><AuthProvider><Ready products={products} sample={sample}/></AuthProvider></MemoryRouter>);
  return calls;
}
const orderCalls = (calls: Call[]) => calls.filter(c => c.path === '/orders');
async function selectAddress() {
  await screen.findByRole('combobox', { name: 'Delivery address' }, { timeout: 5000 });
  fireEvent.change(screen.getByRole('combobox', { name: 'Delivery address' }), { target: { value: '4' } });
}
afterEach(() => { setAccessToken(null); sessionStorage.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it('requires explicit saved address selection even when default and displays free delivery', async () => {
  const calls = setup();
  await screen.findByRole('combobox', { name: 'Delivery address' }, { timeout: 5000 });
  expect(screen.getByRole('combobox', { name: 'Delivery address' })).toHaveValue('');
  expect(screen.getByRole('button', { name: 'Place orders' })).toBeDisabled();
  expect(screen.getAllByText(/Free/).length).toBeGreaterThan(0);
  expect(screen.queryByText(/49/)).not.toBeInTheDocument();
  expect(orderCalls(calls)).toHaveLength(0);
});

it('creates one order per seller with only public fields, quantities and the selected address', async () => {
  const calls = setup([first, { ...first, id: '8', name: 'Real bowl' }]);
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Increase Real vase quantity' }));
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('link', { name: 'View order 10' });
  expect(orderCalls(calls).map(c => c.body)).toEqual([{ seller_id: 2, address_id: 4,
    items: [{ product_id: 3, quantity: 2, expected_unit_price: '250.00' }, { product_id: 8, quantity: 1, expected_unit_price: '250.00' }] }]);
  expect(screen.queryByRole('button', { name: 'Remove Real vase' })).not.toBeInTheDocument();
  expect(screen.getByText('Your local basket is empty')).toBeInTheDocument();
});

it('separates sellers with the same display name and preserves failed items on partial failure', async () => {
  let fail = true;
  const calls = setup([first, second], ({ path, body }) => {
    if (path.startsWith('/discovery/')) return [200, path.endsWith('/3') ? first : second];
    return body.seller_id === 2 ? [201, { id: 10, total: '250.00' }]
      : fail ? [409, { detail: 'private SQL stock failure' }] : [201, { id: 11, total: '250.00' }];
  });
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('link', { name: 'View order 10' });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Place orders' })).toBeEnabled());
  expect(orderCalls(calls).map(c => c.body)).toEqual([
    { seller_id: 2, address_id: 4, items: [{ product_id: 3, quantity: 1, expected_unit_price: '250.00' }] },
    { seller_id: 7, address_id: 4, items: [{ product_id: 6, quantity: 1, expected_unit_price: '250.00' }] },
  ]);
  expect(screen.queryByRole('button', { name: 'Remove Real vase' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Remove Real candle' })).toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent(/stock|availability/i);
  expect(screen.queryByText(/private SQL/)).not.toBeInTheDocument();
  fail = false;
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('link', { name: 'View order 11' });
  expect(orderCalls(calls).filter(c => c.body.seller_id === 2)).toHaveLength(1);
  expect(screen.getByRole('link', { name: 'View order 10' })).toBeInTheDocument();
});

it('prevents double submissions and cart editing until placement finishes', async () => {
  let finish!: (reply: Reply) => void;
  const calls = setup([first], ({ path }) => path.startsWith('/discovery/') ? [200, first]
    : new Promise(resolve => { finish = resolve; }));
  await selectAddress();
  const button = screen.getByRole('button', { name: 'Place orders' });
  fireEvent.click(button); fireEvent.click(button);
  await waitFor(() => expect(orderCalls(calls)).toHaveLength(1));
  expect(screen.getByRole('button', { name: /Placing orders/ })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Remove Real vase' })).toBeDisabled();
  await act(async () => finish([201, { id: 10, total: '250.00' }]));
  await screen.findByRole('link', { name: 'View order 10' });
  expect(orderCalls(calls)).toHaveLength(1);
});

it('keeps sample products non-orderable alongside real products', async () => {
  const calls = setup([first], undefined, true);
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('link', { name: 'View order 10' });
  expect(screen.getByRole('button', { name: 'Remove Handmade Candle Set' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Checkout unavailable' })).toBeDisabled();
  expect(orderCalls(calls)[0].body.items).toEqual([{ product_id: 3, quantity: 1, expected_unit_price: '250.00' }]);
});

it.each([[403, /address|permission/i], [404, /unavailable|address/i], [409, /stock|availability/i],
  [422, /address|quantit/i], [503, /confirm|history|unavailable/i]])('sanitizes placement error %s and preserves items', async (status, message) => {
  setup([first], ({ path }) => path.startsWith('/discovery/') ? [200, first] : [status as number, { detail: 'password-secret SQL' }]);
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(message as RegExp);
  expect(screen.getByRole('button', { name: 'Remove Real vase' })).toBeInTheDocument();
  expect(screen.queryByText(/password-secret/)).not.toBeInTheDocument();
});

it('does not place an order if discovery rejects the selected delivery address location', async () => {
  const calls = setup([first], () => [404, { detail: 'not eligible' }]);
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('alert');
  expect(orderCalls(calls)).toHaveLength(0);
});

it('translates authoritative geographic rejection after successful discovery without exposing raw details', async () => {
  setup([first], ({ path }) => path.startsWith('/discovery/') ? [200, first]
    : [409, { code: 'DELIVERY_INELIGIBLE', detail: 'private server coordinates' }]);
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/outside the selected delivery address/i);
  expect(screen.queryByText(/private server coordinates/)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Remove Real vase' })).toBeInTheDocument();
});

it('retains the key across navigation and reconciles a lost placement response without repeating discovery', async () => {
  let orderCount = 0;
  const calls = setup([first], ({ path }) => {
    if (path.startsWith('/discovery/')) return [200, first];
    if (++orderCount === 1) throw new Error('connection lost');
    return [201, { id: 10, total: '250.00' }];
  });
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/confirm|history/i);
  expect(screen.getByRole('button', { name: 'Reconcile orders' })).toBeEnabled();
  expect(screen.getByRole('link', { name: 'View buyer orders' })).toHaveAttribute('href', '/buyer/orders');
  expect(orderCalls(calls)).toHaveLength(1);
  fireEvent.click(screen.getByRole('button', { name: 'Leave cart' }));
  fireEvent.click(screen.getByRole('button', { name: 'Return to cart' }));
  await selectAddress();
  expect(screen.getByRole('button', { name: 'Reconcile orders' })).toBeEnabled();
  expect(screen.getByRole('alert')).toHaveTextContent(/unconfirmed/i);
  fireEvent.click(screen.getByRole('button', { name: 'Reconcile orders' }));
  await screen.findByRole('link', { name: 'View order 10' });
  expect(orderCalls(calls)).toHaveLength(2);
  expect(orderCalls(calls)[0].key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  expect(orderCalls(calls)[1]).toEqual(orderCalls(calls)[0]);
  expect(calls.filter(call=>call.path.startsWith('/discovery/'))).toHaveLength(1);
});

it('restores an uncertain request after page reload and reuses its original key and payload', async () => {
  const calls = setup([first], ({ path }) => {
    if (path.startsWith('/discovery/')) return [200, first];
    throw new Error('lost response');
  });
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('button', { name: 'Reconcile orders' });
  const original = orderCalls(calls)[0];
  cleanup();
  const recoveryCalls = setup([], ({ path }) => {
    expect(path).toBe('/orders');
    return [201, { id: 10, total: '250.00' }];
  });
  fireEvent.click(await screen.findByRole('button', { name: 'Reconcile orders' }));
  await screen.findByRole('link', { name: 'View order 10' });
  expect(orderCalls(recoveryCalls)).toEqual([original]);
});

it('uses a fresh key for an explicit new attempt after a definite business failure', async () => {
  let attempt = 0;
  const calls = setup([first], ({ path }) => path.startsWith('/discovery/') ? [200, first]
    : ++attempt === 1 ? [409, {}] : [201, { id: 10, total: '250.00' }]);
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('alert');
  expect(orderCalls(calls)).toHaveLength(1);
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('link', { name: 'View order 10' });
  expect(orderCalls(calls)[1].key).not.toBe(orderCalls(calls)[0].key);
});

it('saves the key and original public payload before sending the order request', async () => {
  setup([first], ({ path, body, key }) => {
    if (path.startsWith('/discovery/')) return [200, first];
    const saved = JSON.parse(sessionStorage.getItem('whatnot:order-recovery:1')!);
    expect(saved[0].key).toBe(key);
    expect(saved[0].request).toEqual({ seller_id: String(body.seller_id), address_id: String(body.address_id),
      items: [{ product_id: '3', quantity: 1, expected_unit_price: '250.00' }] });
    return [201, { id: 10, total: '250.00' }];
  });
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('link', { name: 'View order 10' });
  expect(sessionStorage.getItem('whatnot:order-recovery:1')).toBeNull();
});

it('does not submit if a recovery key cannot be durably saved', async () => {
  const calls = setup();
  await selectAddress();
  vi.spyOn(Storage.prototype, 'setItem').mockImplementationOnce(()=>{throw new DOMException('full', 'QuotaExceededError');});
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/could not save.*recovery key/i);
  expect(orderCalls(calls)).toHaveLength(0);
});

it('keeps fresh checkout blocked if rejected-attempt cleanup fails, preventing a stale-key duplicate after reload', async () => {
  let attempt = 0;
  const calls = setup([first], ({ path }) => path.startsWith('/discovery/') ? [200, first]
    : ++attempt === 1 ? [409, {}] : [201, { id: 10, total: '250.00' }]);
  await selectAddress();
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementationOnce(()=>{throw new DOMException('blocked', 'SecurityError');});
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('alert');
  expect(screen.queryByRole('button', { name: 'Place orders' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Reconcile orders' }));
  await screen.findByRole('link', { name: 'View order 10' });
  expect(orderCalls(calls)[1].key).toBe(orderCalls(calls)[0].key);
  cleanup();
  setup([]);
  await screen.findByText('Your local basket is empty');
  expect(screen.queryByRole('button', { name: 'Reconcile orders' })).not.toBeInTheDocument();
});

it('creates separate confirmed orders for multiple sellers', async () => {
  const calls = setup([first, second], ({ path, body }) => path.startsWith('/discovery/')
    ? [200, path.endsWith('/3') ? first : second]
    : [201, { id: body.seller_id === 2 ? 10 : 11, total: '250.00' }]);
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await screen.findByRole('link', { name: 'View order 11' });
  expect(screen.getByRole('link', { name: 'View order 10' })).toBeInTheDocument();
  expect(orderCalls(calls)).toHaveLength(2);
  expect(new Set(orderCalls(calls).map(call=>call.key)).size).toBe(2);
  expect(screen.getByText('Your local basket is empty')).toBeInTheDocument();
});

it('prevents resubmission after navigating away during placement and removes a late confirmed order', async () => {
  let finish!: (reply: Reply) => void;
  const calls = setup([first], ({ path }) => path.startsWith('/discovery/') ? [200, first]
    : new Promise(resolve => { finish = resolve; }));
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await waitFor(() => expect(orderCalls(calls)).toHaveLength(1));
  fireEvent.click(screen.getByRole('button', { name: 'Leave cart' }));
  fireEvent.click(screen.getByRole('button', { name: 'Return to cart' }));
  await selectAddress();
  expect(screen.getByRole('button', { name: 'Place orders' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Remove Real vase' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Remove Real vase' }));
  expect(screen.getByRole('button', { name: 'Remove Real vase' })).toBeInTheDocument();
  await act(async () => finish([201, { id: 10, total: '250.00' }]));
  await screen.findByText('Your local basket is empty');
  expect(orderCalls(calls)).toHaveLength(1);
});

it('handles an expired checkout session through the existing authentication state', async () => {
  setup([first], ({ path }) => path.startsWith('/discovery/') ? [200, first] : [401, { detail: 'private' }]);
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/session.*sign in/i);
  expect(screen.queryByText('private')).not.toBeInTheDocument();
});

it('offers the existing address manager when the buyer has no saved addresses', async () => {
  const calls = setup([first], undefined, false, []);
  await screen.findByRole('combobox', { name: 'Delivery address' }, { timeout: 5000 });
  expect(screen.getByRole('button', { name: 'Place orders' })).toBeDisabled();
  expect(screen.getByRole('link', { name: 'Manage saved addresses' })).toHaveAttribute('href', '/buyer/addresses');
  expect(orderCalls(calls)).toHaveLength(0);
});

it('rejects stale seller mappings and stock before submitting an order', async () => {
  const calls = setup([first, second], ({ path }) => [200, path.endsWith('/3')
    ? { ...first, seller_id: '99' } : { ...second, stock_quantity: 0 }]);
  await selectAddress();
  fireEvent.click(screen.getByRole('button', { name: 'Place orders' }));
  await waitFor(() => expect(screen.getAllByRole('alert')).toHaveLength(2));
  expect(orderCalls(calls)).toHaveLength(0);
  expect(screen.getByRole('button', { name: 'Remove Real vase' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Remove Real candle' })).toBeInTheDocument();
});
