import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { getAccessToken, setAccessToken } from './api/client';

export const account = (role='BUYER') => ({ id: 1, name: 'Ravi', email: 'ravi@example.test', role });
export function mockApi(handler: (path: string, method: string, body: any) => [number, unknown]) {
  const fetcher=vi.fn(async (input: string, options: RequestInit) => {
    const path=new URL(input).pathname.replace('/api/v1','');
    const [status,body]=handler(path,options.method || 'GET',options.body ? JSON.parse(String(options.body)) : undefined);
    return new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
  }); vi.stubGlobal('fetch',fetcher); return fetcher;
}
export function open(path: string) { return render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>); }
afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });
describe('authenticated marketplace routes', () => {
  it('offers only Buyer and Seller on the public login selection', () => {
    open('/login');
    expect(screen.getByRole('heading', { name: 'Buyer' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Seller' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Continue as buyer/i })).toHaveAttribute('href', '/login/buyer');
    expect(screen.getByRole('link', { name: /Continue as seller/i })).toHaveAttribute('href', '/login/seller');
    expect(screen.queryByRole('heading', { name: 'Admin' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Create a buyer or seller account' })).toHaveAttribute('href', '/register');
  });
  it.each(['/admin/login', '/login/admin', '/admin', '/admin/addresses'])('renders separate admin sign-in at %s without fetching protected records', path => {
    const fetcher = mockApi(() => [500, {}]);
    open(path);
    expect(screen.getByRole('heading', { name: 'What Not? Administration' })).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toHaveAttribute('type', 'email');
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password');
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.getByText('Authorized administrators only')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /create.*account|register/i })).not.toBeInTheDocument();
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('does not promote admin sign-in on the public homepage', () => {
    open('/');
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument();
    expect(document.querySelector('a[href="/admin/login"]')).toBeNull();
  });
  it('authenticates an administrator through the existing backend identity flow and logs out to admin sign-in', async () => {
    const fetcher = mockApi(path => path === '/auth/login'
      ? [200, { access_token: 'test-token', expires_in: 900, token_type: 'bearer', user: account('BUYER') }]
      : path === '/auth/me' ? [200, account('ADMIN')] : [200, []]);
    open('/admin/login');
    await userEvent.type(screen.getByLabelText('Email'), 'ravi@example.test');
    await userEvent.type(screen.getByLabelText('Password'), crypto.randomUUID());
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await screen.findByText('admin workspace');
    expect(fetcher.mock.calls.map(([url]) => new URL(url).pathname)).toContain('/api/v1/auth/me');
    await userEvent.click(screen.getByRole('button', { name: /log out/i }));
    await screen.findByRole('heading', { name: 'What Not? Administration' });
    expect(getAccessToken()).toBeNull();
  });
  it.each(['BUYER', 'SELLER'])('does not grant ADMIN from the admin login route or login response: %s', async role => {
    const fetcher = mockApi(path => path === '/auth/login'
      ? [200, { access_token: 'test-token', expires_in: 900, token_type: 'bearer', user: account('ADMIN') }]
      : path === '/auth/me' ? [200, account(role)] : path === '/sellers/me' ? [404, {}] : [200, []]);
    open('/admin/login');
    await userEvent.type(screen.getByLabelText('Email'), 'ravi@example.test');
    await userEvent.type(screen.getByLabelText('Password'), crypto.randomUUID());
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await screen.findByText(`${role.toLowerCase()} workspace`);
    expect(screen.queryByText('admin workspace')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.some(([url]) => new URL(url).pathname.startsWith('/api/v1/admin'))).toBe(false);
  });
  it('validates blank admin login before sending credentials', async () => {
    const fetcher = mockApi(() => [500, {}]);
    open('/admin/login');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(screen.getByRole('alert')).toHaveTextContent(/email and password/i);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('reports admin authentication failure without retaining the password or token', async () => {
    mockApi(() => [401, {}]);
    open('/admin/login');
    await userEvent.type(screen.getByLabelText('Email'), 'ravi@example.test');
    await userEvent.type(screen.getByLabelText('Password'), crypto.randomUUID());
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await screen.findByRole('alert');
    expect(screen.getByLabelText('Password')).toHaveValue('');
    expect(getAccessToken()).toBeNull();
  });
  it('keeps the landing layout and labels sample geography', () => { open('/'); expect(screen.getByRole('heading',{name:/Local life.\s*More possibilities./i})).toBeInTheDocument(); expect(screen.getByText(/sample catalogue.*geography/i)).toBeInTheDocument(); });
  it('redirects protected pages to login without fetching sensitive records', () => { const fetcher=mockApi(() => [500,{}]); open('/seller'); expect(screen.getByRole('heading',{name:/welcome back/i})).toBeInTheDocument(); expect(fetcher).not.toHaveBeenCalled(); });
  it('validates blank login before sending credentials', async () => { const fetcher=mockApi(() => [500,{}]); open('/login/buyer'); await userEvent.click(screen.getByRole('button',{name:/sign in/i})); expect(screen.getByRole('alert')).toHaveTextContent(/email and password/i); expect(fetcher).not.toHaveBeenCalled(); });
  it.each(['BUYER','SELLER','ADMIN'])('routes by auth/me identity rather than chosen login role: %s', async role => {
    mockApi(path => path==='/auth/login' ? [200,{access_token:'test-token',expires_in:900,token_type:'bearer',user:account('BUYER')}] : path==='/auth/me' ? [200,account(role)] : path==='/sellers/me' ? [404,{}] : [200,[]]);
    open('/login/buyer'); await userEvent.type(screen.getByLabelText('Email address'),'ravi@example.test'); await userEvent.type(screen.getByLabelText('Password'),crypto.randomUUID()); await userEvent.click(screen.getByRole('button',{name:/sign in/i}));
    await screen.findByRole('button',{name:/log out/i}); expect(screen.getByText(`${role.toLowerCase()} workspace`)).toBeInTheDocument();
  });
  it.each([401,503])('reports login failure %s and clears the password', async status => { mockApi(() => [status,{detail:'private'}]); open('/login/buyer'); await userEvent.type(screen.getByLabelText('Email address'),'ravi@example.test'); await userEvent.type(screen.getByLabelText('Password'),crypto.randomUUID()); await userEvent.click(screen.getByRole('button',{name:/sign in/i})); await screen.findByRole('alert'); expect(screen.getByLabelText('Password')).toHaveValue(''); expect(getAccessToken()).toBeNull(); });
  it('highlights sanitized backend login validation errors',async()=>{
    mockApi(()=>[422,{detail:[{loc:['body','email'],type:'value_error',msg:'private input',input:'private input'}]}]);open('/login/buyer');await userEvent.type(screen.getByLabelText('Email address'),'invalid');await userEvent.type(screen.getByLabelText('Password'),crypto.randomUUID());await userEvent.click(screen.getByRole('button',{name:/sign in/i}));await screen.findByRole('alert');expect(screen.getByLabelText('Email address')).toHaveAttribute('aria-invalid','true');expect(screen.queryByText('private input')).not.toBeInTheDocument();
  });
  it('offers only public buyer/seller registration and explains profile setup', async () => {
    const fetcher=mockApi((path,method,body) => { expect(path).toBe('/auth/register'); expect(method).toBe('POST'); expect(body.role).toBe('SELLER'); expect(body.phone).toBe('1000000001'); return [201,account('SELLER')]; });
    open('/register'); expect(screen.queryByRole('option',{name:'Admin'})).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Name'),'Ravi'); await userEvent.type(screen.getByLabelText('Email address'),'ravi@example.test'); await userEvent.type(screen.getByLabelText('Phone'),'1000000001'); await userEvent.type(screen.getByLabelText('Password'),crypto.randomUUID()); await userEvent.selectOptions(screen.getByLabelText('Account type'),'SELLER'); await userEvent.click(screen.getByRole('button',{name:/create account/i})); await screen.findByText(/account created.*profile/i); expect(fetcher).toHaveBeenCalledOnce(); expect(screen.getByLabelText('Password')).toHaveValue('');
  });
  it.each([409,422])('reports registration rejection %s', async status => { mockApi(() => [status,{}]); open('/register'); await userEvent.type(screen.getByLabelText('Name'),'Ravi'); await userEvent.type(screen.getByLabelText('Email address'),'ravi@example.test'); await userEvent.type(screen.getByLabelText('Phone'),'1000000001'); await userEvent.type(screen.getByLabelText('Password'),crypto.randomUUID()); await userEvent.click(screen.getByRole('button',{name:/create account/i})); await screen.findByRole('alert'); expect(screen.getByLabelText('Password')).toHaveValue(''); });
  it('restores an existing in-memory credential using auth/me, then logout clears it', async () => { setAccessToken('restored'); mockApi(path => path==='/auth/me' ? [200,account()] : [200,[]]); open('/buyer/orders'); await screen.findByRole('heading',{name:'Your orders'}); await userEvent.click(screen.getByRole('button',{name:/log out/i})); await screen.findByRole('heading',{name:/welcome back/i}); expect(getAccessToken()).toBeNull(); });
  it('clears an invalid restored credential and shows a useful notice', async () => { setAccessToken('expired'); mockApi(() => [401,{}]); open('/buyer/orders'); await screen.findByRole('heading',{name:/welcome back/i}); expect(getAccessToken()).toBeNull(); expect(screen.getByRole('alert')).toHaveTextContent(/sign in/i); });
  it.each(['BUYER','SELLER'])('blocks a valid %s from the admin workspace', async role => { setAccessToken('test-token'); const fetcher=mockApi(() => [200,account(role)]); open('/admin'); await screen.findByText(/This page is not available for your account/i); expect(fetcher).toHaveBeenCalledOnce(); });
  it.each(['BUYER','SELLER'])('blocks a valid %s from admin address routes', async role => { setAccessToken('test-token'); const fetcher=mockApi(() => [200,account(role)]); open('/admin/addresses'); await screen.findByText(/This page is not available for your account/i); expect(fetcher).toHaveBeenCalledOnce(); });
});
