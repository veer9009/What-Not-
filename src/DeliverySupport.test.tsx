import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { setAccessToken } from './api/client';

const order = { id: '9007199254740993', buyer_id: 1, seller_id: 2, status: 'DELIVERED', subtotal: '250.00', delivery_fee: '0.00', total: '250.00', items: [{ product_id: 3, seller_id: 2, name: 'Homemade lunch', quantity: 1, unit_price: '250.00' }] };
function setup({ role = 'BUYER', status = 'DELIVERED', path = `/${role.toLowerCase()}/orders/${order.id}`, failure = 0, pending = false, refreshFailure = false, keepStatus = false } = {}) {
  setAccessToken('private-token');
  let current = status;
  let submitted = false;
  let release: () => void = () => {};
  const wait = new Promise<void>(resolve => { release = resolve; });
  const writes: { path: string; method: string; body: unknown }[] = [];
  const fetcher = vi.fn(async (input: string, options: RequestInit) => {
    const route = new URL(input).pathname.replace('/api/v1', '');
    let data: unknown;
    let code = 200;
    if (route === '/auth/me') data = { id: 1, name: 'Buyer', email: 'private@example.test', role };
    else if (options.method === 'PATCH') {
      writes.push({ path: route, method: options.method, body: JSON.parse(String(options.body)) });
      if (pending) await wait;
      submitted = true;
      code = failure || 200;
      if (!failure && !keepStatus) current = JSON.parse(String(options.body)).status;
      data = failure ? { detail: 'SQL secret private-token 19.123456' } : { ...order, status: current };
    } else {
      code = submitted && refreshFailure ? 503 : 200;
      data = { ...order, status: current };
    }
    return new Response(JSON.stringify(data), { status: code, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
  return { writes, release, fetcher };
}
afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });

it.each([
  ['PLACED', 'Order placed'], ['ACCEPTED', 'Seller accepted'], ['PREPARING', 'Preparing'],
  ['OUT_FOR_DELIVERY', 'Out for delivery'], ['DELIVERED', 'Delivered'], ['COMPLETED', 'Completed'],
])('tracks %s with an accessible current step', async (status, label) => {
  setup({ status });
  const tracking = await screen.findByRole('region', { name: 'Order progress' });
  expect(within(tracking).getAllByText(label).some(element=>element.closest('li')?.getAttribute('aria-current')==='step')).toBe(true);
  expect(tracking.querySelectorAll('[aria-current="step"]')).toHaveLength(1);
});
it.each(['CANCELLED', 'REJECTED'])('does not show a delivery progression for %s', async status => {
  setup({ status }); await screen.findByText('Homemade lunch');
  expect(screen.queryByRole('region', { name: 'Order progress' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Yes, I received it' })).not.toBeInTheDocument();
});
it('confirms receipt through the real API and reloads backend truth', async () => {
  const { writes, fetcher } = setup();
  await userEvent.click(await screen.findByRole('button', { name: 'Yes, I received it' }));
  await screen.findByRole('status');
  expect(writes).toEqual([{ path: '/orders/9007199254740993/status', method: 'PATCH', body: { status: 'COMPLETED' } }]);
  expect(fetcher.mock.calls.filter(([url]) => String(url).endsWith(`/orders/${order.id}`))).toHaveLength(2);
  expect(screen.queryByRole('button', { name: 'Yes, I received it' })).not.toBeInTheDocument();
});
it.each(['PLACED', 'ACCEPTED', 'PREPARING', 'OUT_FOR_DELIVERY', 'COMPLETED', 'DELIVERY_DISPUTED'])('does not offer confirmation in %s', async status => {
  setup({ status }); await screen.findByText('Homemade lunch');
  expect(screen.queryByRole('button', { name: 'Yes, I received it' })).not.toBeInTheDocument();
});
it('offers seller handover without a final delivery action', async () => {
  const { writes } = setup({ role: 'SELLER', status: 'OUT_FOR_DELIVERY' });
  await userEvent.click(await screen.findByRole('button', { name: 'Mark delivered' }));
  await screen.findByRole('status');
  expect(writes[0].body).toEqual({ status: 'DELIVERED' });
  expect(screen.queryByRole('button', { name: /mark delivered|Yes, I received it/i })).not.toBeInTheDocument();
});
it('records a delivery dispute through the API and removes confirmation actions', async () => {
  const { writes } = setup();
  await userEvent.click(await screen.findByRole('button', { name: 'Report not received' }));
  await screen.findByRole('status');
  expect(writes[0].body).toEqual({ status: 'DELIVERY_DISPUTED' });
  expect(screen.getByText(/Automatic completion is paused/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Yes, I received it' })).not.toBeInTheDocument();
});
it('provides order support containing only the public order reference', async () => {
  setup();
  const link = await screen.findByRole('link', { name: 'Need help with this order?' });
  expect(link).toHaveAttribute('href', 'https://wa.me/918080098882?text=Hi%20What%20Not%20Support%2C%20I%20need%20help%20with%20Order%20%239007199254740993.');
  expect(link.getAttribute('href')).not.toMatch(/private|token|buyer_id|seller_id|latitude/i);
});
it('discovers dedicated support through buyer navigation with encoded general message', async () => {
  setup();
  await userEvent.click(await screen.findByRole('link', { name: 'Help & Support' }));
  await screen.findByRole('heading', { name: 'Help & Support' });
  expect(screen.getByText('+91 80800 98882')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Chat with What Not Support' })).toHaveAttribute('href', 'https://wa.me/918080098882?text=Hi%20What%20Not%20Support%2C%20I%20need%20help%20with%20my%20marketplace%20account%2Forder.');
});
it.each(['BUYER', 'SELLER'])('prevents duplicate pending transitions for %s', async role => {
  const { writes, release } = setup({ role, status: role === 'SELLER' ? 'OUT_FOR_DELIVERY' : 'DELIVERED', pending: true });
  const button = await screen.findByRole('button', { name: role === 'SELLER' ? 'Mark delivered' : 'Yes, I received it' });
  fireEvent.click(button); fireEvent.click(button);
  expect(button).toBeDisabled(); expect(writes).toHaveLength(1);
  release(); await screen.findByRole('status');
});
it('displays a safe error and preserves confirmation after rejection', async () => {
  setup({ failure: 409 });
  await userEvent.click(await screen.findByRole('button', { name: 'Yes, I received it' }));
  const alert = await screen.findByRole('alert');
  expect(alert.textContent).not.toMatch(/SQL|secret|private-token|19\.123456/);
  expect(alert.textContent).toMatch(/changed|refresh|conflict|cannot/i);
  expect(screen.getByRole('button', { name: 'Yes, I received it' })).toBeEnabled();
});
it('reports a saved confirmation separately from a failed refresh', async () => {
  setup({ refreshFailure: true });
  await userEvent.click(await screen.findByRole('button', { name: 'Yes, I received it' }));
  await screen.findByRole('alert');
  expect(screen.getByRole('status')).toHaveTextContent(/updated.*Refresh/i);
  expect(screen.queryByRole('button', { name: 'Yes, I received it' })).not.toBeInTheDocument();
});
it('uses the refreshed status rather than assuming the requested status', async () => {
  setup({ keepStatus: true });
  await userEvent.click(await screen.findByRole('button', { name: 'Yes, I received it' }));
  await screen.findByRole('status');
  expect(screen.getByRole('button', { name: 'Yes, I received it' })).toBeInTheDocument();
  const tracking = screen.getByRole('region', { name: 'Order progress' });
  expect(within(tracking).getByText('Delivered').closest('li')).toHaveAttribute('aria-current', 'step');
});
it('does not offer the seller a receipt confirmation while awaiting the buyer', async () => {
  setup({ role: 'SELLER' }); await screen.findByText('Homemade lunch');
  expect(screen.queryByRole('button', { name: /received|handed over|delivered/i })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'View delivery details' })).toBeInTheDocument();
});
it.each(['SELLER', 'ADMIN'])('protects buyer Help & Support from %s routes', async role => {
  setup({ role, path: '/buyer/help' });
  await screen.findByRole('heading', { name: 'This page is not available for your account.' });
  expect(screen.queryByRole('link', { name: 'Chat with What Not Support' })).not.toBeInTheDocument();
});
