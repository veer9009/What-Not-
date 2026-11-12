import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { setAccessToken } from './api/client';
import { Field } from './components/ApiStates';

afterEach(() => { cleanup(); setAccessToken(null); vi.unstubAllGlobals(); });
const routes = [
  ['/privacy', 'Privacy Policy'], ['/terms', 'Terms & Conditions'],
  ['/cookies', 'Cookie Policy'], ['/refunds', 'Refund / Cancellation Policy'],
  ['/contact', 'Contact & Grievance Support'], ['/support', 'Contact & Grievance Support'],
];
it.each(routes)('opens %s directly without authentication or protected API requests', (path, title) => {
  const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
  expect(screen.getByRole('heading', { level: 1, name: title })).toBeInTheDocument();
  expect(screen.getByText(/OWNER INPUT REQUIRED BEFORE PUBLIC LAUNCH/)).toBeInTheDocument();
  expect(fetcher).not.toHaveBeenCalled();
  expect(screen.getByRole('navigation', { name: 'Legal and support' })).toBeInTheDocument();
});
it('provides legal links and collection disclosure on registration without fake consent', async () => {
  render(<MemoryRouter initialEntries={['/register']}><App/></MemoryRouter>);
  const notice = screen.getByLabelText('Account privacy notice');
  expect(notice).toHaveTextContent(/name, email, phone/i);
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('link', { name: 'Privacy Policy' }));
  expect(screen.getByRole('heading', { level: 1, name: 'Privacy Policy' })).toBeInTheDocument();
});
it('keeps repeated form-field errors associated with the correct control', () => {
  render(<><Field label="First name" name="name" value="" onChange={()=>{}} error="First error"/>
    <Field label="Second name" name="name" value="" onChange={()=>{}} error="Second error"/></>);
  const first = screen.getByLabelText('First name'), second = screen.getByLabelText('Second name');
  expect(first).toHaveAccessibleDescription('First error');
  expect(second).toHaveAccessibleDescription('Second error');
  expect(first.getAttribute('aria-describedby')).not.toBe(second.getAttribute('aria-describedby'));
});
it('labels sample trust signals explicitly and suppresses outbound referrers on images', () => {
  render(<MemoryRouter><App/></MemoryRouter>);
  expect(screen.queryByLabelText('Sample verification')).not.toBeInTheDocument();
  expect(screen.getAllByText(/Sample rating:/).length).toBeGreaterThan(0);
  for (const img of document.querySelectorAll('img')) expect(img).toHaveAttribute('referrerpolicy', 'no-referrer');
});
it('keeps policy pages reachable with an authenticated account', async () => {
  setAccessToken('synthetic-test-token');
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({id: '1', name:'Buyer', email:'buyer@example.test', role:'BUYER'}))));
  render(<MemoryRouter initialEntries={['/privacy']}><App/></MemoryRouter>);
  // /auth/me replaces the identity-scoped provider tree; assert against the live node.
  await waitFor(()=>expect(screen.getByRole('heading', {level:1, name:'Privacy Policy'})).toBeInTheDocument());
  expect(screen.queryByRole('button', {name:'Sign in'})).not.toBeInTheDocument();
});
it('makes skip navigation the first keyboard stop', async () => {
  render(<MemoryRouter><App/></MemoryRouter>);
  await userEvent.tab();
  expect(screen.getByRole('link', {name:'Skip to main content'})).toHaveFocus();
  expect(document.getElementById('main-content')).toBeInTheDocument();
});
