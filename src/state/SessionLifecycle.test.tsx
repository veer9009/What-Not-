import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from './AuthContext';
import { getAccessToken, setAccessToken } from '../api/client';
import { ordersApi } from '../api/orders';
import { authApi } from '../api/auth';
import type { Role } from '../api/types';

function Probe(){
  const auth=useAuth();
  return <><span>{auth.user?.role??'anonymous'}</span><span>{auth.error}</span>
    <button onClick={()=>void auth.login('test@example.test','synthetic-test-password')}>Login</button>
    <button onClick={auth.logout}>Logout</button>
    <button onClick={()=>void (auth.user?.role==='ADMIN'?authApi.me():ordersApi.list())}>Read workspace</button></>;
}
function setup(role:Role, renew=false){
  vi.useFakeTimers();
  const requests:{path:string;authorization:string|null}[]=[];
  vi.stubGlobal('fetch',vi.fn(async(url:string,options:RequestInit)=>{
    const path=new URL(url, location.origin).pathname;
    requests.push({path,authorization:new Headers(options.headers).get('Authorization')});
    const user={id:1,name:'Synthetic user',email:'test@example.test',role};
    if(path.endsWith('/auth/refresh'))return getAccessToken()&&renew
      ? new Response(JSON.stringify({access_token:'renewed-test-token',token_type:'bearer',expires_in:900,user}),{status:200})
      : new Response('{}',{status:401});
    const data=path.endsWith('/auth/login')?{access_token:'valid-test-token',token_type:'bearer',expires_in:900,user}:
      path.endsWith('/auth/me')?user:[];
    return new Response(JSON.stringify(data),{status:200});
  }));
  render(<AuthProvider><Probe/></AuthProvider>);
  return requests;
}
afterEach(()=>{setAccessToken(null);vi.useRealTimers();vi.restoreAllMocks();vi.unstubAllGlobals();});

it('renews before expiry and keeps the same workspace across multiple access-token lifetimes',async()=>{
  const requests=setup('BUYER',true);
  await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Login'})));
  const initial=requests.filter(request=>request.path.endsWith('/auth/refresh')).length;
  await act(async()=>{await vi.advanceTimersByTimeAsync(870001);});
  expect(getAccessToken()).toBe('renewed-test-token');expect(screen.getByText('BUYER')).toBeInTheDocument();
  await act(async()=>{await vi.advanceTimersByTimeAsync(870001);});
  expect(requests.filter(request=>request.path.endsWith('/auth/refresh'))).toHaveLength(initial+2);
  expect(screen.getByText('BUYER')).toBeInTheDocument();
  expect(sessionStorage.length).toBe(0);expect(localStorage.length).toBe(0);
});

it.each(['SELLER','BUYER','ADMIN'] as const)('keeps a valid %s session through tab events and three minutes of inactivity',async role=>{
  const requests=setup(role);
  await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Login'})));
  expect(screen.getByText(role)).toBeInTheDocument();
  const visibility=vi.spyOn(document,'visibilityState','get');
  await act(async()=>{
    visibility.mockReturnValue('hidden');document.dispatchEvent(new Event('visibilitychange'));
    window.dispatchEvent(new Event('blur'));vi.advanceTimersByTime(180000);
    visibility.mockReturnValue('visible');document.dispatchEvent(new Event('visibilitychange'));
    window.dispatchEvent(new Event('focus'));
  });
  expect(getAccessToken()).toBe('valid-test-token');
  expect(screen.getByText(role)).toBeInTheDocument();
  await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Read workspace'})));
  expect(requests.at(-1)).toEqual({path:role==='ADMIN'?'/api/v1/auth/me':'/api/v1/orders',
    authorization:'Bearer valid-test-token'});
  expect(requests.filter(request=>request.path.endsWith('/auth/login'))).toHaveLength(1);
  expect(localStorage.getItem('access_token')).toBeNull();
  expect(sessionStorage.getItem('access_token')).toBeNull();
});

it('expires a session when renewal is rejected',async()=>{
  const requests=setup('SELLER');
  await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Login'})));
  await act(async()=>vi.advanceTimersByTime(900001));
  expect(screen.getByText('anonymous')).toBeInTheDocument();
  expect(screen.getByText(/session expired/i)).toBeInTheDocument();
  expect(getAccessToken()).toBeNull();
  expect(requests.some(request=>request.path.includes('refresh'))).toBe(true);
});

it('logout clears the current browser session and pending expiry cannot restore it',async()=>{
  setup('SELLER');
  await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Login'})));
  await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Logout'})));
  await act(async()=>vi.advanceTimersByTime(900001));
  expect(getAccessToken()).toBeNull();
  expect(screen.getByText('anonymous')).toBeInTheDocument();
});
