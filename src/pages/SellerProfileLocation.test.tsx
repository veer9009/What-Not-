import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../App';
import { setAccessToken } from '../api/client';

const shop = { id: 2, user_id: 1, shop_name: 'Maker', phone: '100', description: null,
  latitude: '19', longitude: '72', is_verified: false, dispatch_location_confirmed_at: null };
function device() {
  let success!: PositionCallback;
  let failure!: PositionErrorCallback;
  const getCurrentPosition = vi.fn((ok: PositionCallback, fail: PositionErrorCallback) => { success = ok; failure = fail; });
  vi.stubGlobal('navigator', { geolocation: { getCurrentPosition } });
  return { getCurrentPosition, locate: async (latitude = 12.12345678, longitude = -45.12345678) => {
    await act(async () => success({ coords: { latitude, longitude, accuracy: 10 } } as GeolocationPosition));
  }, fail: async (code: number) => { await act(async () => failure({ code } as GeolocationPositionError)); } };
}
async function open(existing = true) {
  setAccessToken('test-only');
  const writes = vi.fn();
  const fetcher = vi.fn(async (url: string, options: RequestInit) => {
    const path = new URL(url, location.origin).pathname;
    if (options.method !== 'GET') writes(path, options.method, JSON.parse(String(options.body)));
    const data = path.endsWith('/auth/me') ? { id: 1, name: 'Maker', email: 'maker@example.test', role: 'SELLER' } : shop;
    return new Response(JSON.stringify(data), { status: !existing && path.endsWith('/sellers/me') && options.method === 'GET' ? 404 : 200 });
  });
  vi.stubGlobal('fetch', fetcher);
  const view = render(<MemoryRouter initialEntries={['/seller/profile']}><App /></MemoryRouter>);
  await screen.findByRole('button', { name: 'Save profile' }, { timeout: 5000 });
  return { ...view, writes, fetcher };
}
afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });

it.each([true, false])('acquires only on click and fills an unsaved draft (existing profile: %s)', async existing => {
  const gps = device(); const { writes } = await open(existing);
  expect(gps.getCurrentPosition).not.toHaveBeenCalled();
  const button = screen.getByRole('button', { name: 'Use Current Location' });
  expect(button.compareDocumentPosition(screen.getByLabelText('Latitude')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  fireEvent.click(button);
  expect(gps.getCurrentPosition).toHaveBeenCalledOnce();
  expect(screen.getByRole('button', { name: /detecting location/i })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Save profile' })).toBeDisabled();
  await gps.locate();
  expect(screen.getByLabelText('Latitude')).toHaveValue(12.123457);
  expect(screen.getByLabelText('Longitude')).toHaveValue(-45.123457);
  expect(screen.getByText(/may differ from your current device location/i)).toBeInTheDocument();
  expect(writes).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: 'Save profile' })).toBeEnabled();
  if (existing) {
    fireEvent.click(screen.getByRole('checkbox', { name: /I confirm this is where I send products from/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }));
    await waitFor(() => expect(writes).toHaveBeenCalledWith('/api/v1/sellers/me', 'PATCH', {
      shop_name: 'Maker', phone: '100', description: null, latitude: '12.123457', longitude: '-45.123457',
    }));
    await waitFor(() => expect(writes).toHaveBeenCalledWith('/api/v1/sellers/me/dispatch-location', 'PATCH', { latitude: 12.123457, longitude: -45.123457 }));
    expect(writes).toHaveBeenCalledTimes(2);
    expect(writes.mock.calls.some(([path]) => path.endsWith('/public-discovery-location'))).toBe(false);
    await screen.findByText(/Shop location saved/i);
    expect(screen.queryByText(/nothing has been saved/i)).not.toBeInTheDocument();
  }
});

it.each([[1, /permission was denied/i], [2, /position is unavailable/i], [3, /timed out/i]] as const)(
  'reports browser error %s and preserves manual coordinates', async (code, message) => {
    const gps = device(); const { writes } = await open();
    fireEvent.click(screen.getByRole('button', { name: 'Use Current Location' })); await gps.fail(code);
    expect(screen.getByRole('alert')).toHaveTextContent(message);
    expect(screen.getByLabelText('Latitude')).toHaveValue(19);
    fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: '20' } });
    fireEvent.click(screen.getByRole('checkbox', { name: /I confirm this is where I send products from/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }));
    await waitFor(() => expect(writes).toHaveBeenCalledWith('/api/v1/sellers/me', 'PATCH', expect.objectContaining({ latitude: '20', longitude: '72' })));
  });

it('reports unsupported browsers and leaves manual entry available', async () => {
  vi.stubGlobal('navigator', { geolocation: undefined }); await open();
  fireEvent.click(screen.getByRole('button', { name: 'Use Current Location' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/geolocation is unavailable/i);
  expect(screen.getByLabelText('Latitude')).toBeEnabled();
});

it.each([[91, 0], [0, -181], [NaN, 0]])('rejects invalid device point %s, %s', async (lat, lon) => {
  const gps = device(); const { writes } = await open();
  fireEvent.click(screen.getByRole('button', { name: 'Use Current Location' })); await gps.locate(lat, lon);
  expect(screen.getByRole('alert')).toHaveTextContent(/valid latitude/i);
  expect(screen.getByLabelText('Latitude')).toHaveValue(19);
  expect(writes).not.toHaveBeenCalled();
});

it('ignores a late location after manual edits and after unmount', async () => {
  const gps = device(); const { unmount, writes } = await open();
  fireEvent.click(screen.getByRole('button', { name: 'Use Current Location' }));
  fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: '21' } });
  await gps.locate(); expect(screen.getByLabelText('Latitude')).toHaveValue(21);
  fireEvent.click(screen.getByRole('button', { name: 'Use Current Location' }));
  unmount(); await gps.locate(); expect(writes).not.toHaveBeenCalled();
});

it.each([['91', '72'], ['19', '181'], ['', '72']])('validates manual coordinates before sending %s, %s', async (lat, lon) => {
  const { writes } = await open();
  fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: lat } });
  fireEvent.change(screen.getByLabelText('Longitude'), { target: { value: lon } });
  fireEvent.submit(screen.getByRole('button', { name: 'Save profile' }).closest('form')!);
  expect(await screen.findByRole('alert')).toHaveTextContent(/valid latitude/i);
  expect(writes).not.toHaveBeenCalled();
});
