import { render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from './AuthContext';
import { getAccessToken, setAccessToken } from '../api/client';
const buyer={id:1,name:'Buyer',email:'buyer@example.test',role:'BUYER'};
const seller={id:2,name:'Seller',email:'seller@example.test',role:'SELLER'};
const response=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
function Probe(){const auth=useAuth();return <><span>{auth.user?.name??'anonymous'}</span><span>{auth.error}</span><button onClick={()=>void auth.login('seller@example.test',crypto.randomUUID()).catch(()=>{})}>Login</button><button onClick={auth.logout}>Logout</button></>;}
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
describe('authentication lifecycle',()=>{
  it('restores exactly once through StrictMode effect cleanup',async()=>{
    let finish!:(value:Response)=>void;
    const fetcher=vi.fn(()=>new Promise<Response>(resolve=>{finish=resolve;}));vi.stubGlobal('fetch',fetcher);
    render(<StrictMode><AuthProvider><Probe/></AuthProvider></StrictMode>);
    await waitFor(()=>expect(fetcher).toHaveBeenCalledTimes(1));
    finish(response({access_token:'restored',token_type:'bearer',expires_in:900,user:buyer}));
    await screen.findByText('Buyer');expect(getAccessToken()).toBe('restored');expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('does not let old restoration invalidate a new login',async()=>{
    setAccessToken('old');let finish!: (response:Response)=>void;let meCount=0;
    vi.stubGlobal('fetch',vi.fn(async(url:string)=>url.endsWith('/auth/login')?response({access_token:'new',token_type:'bearer',expires_in:900,user:seller}):++meCount===1?new Promise<Response>(resolve=>{finish=resolve;}):response(seller)));
    render(<AuthProvider><Probe/></AuthProvider>);await userEvent.click(screen.getByRole('button',{name:'Login'}));await screen.findByText('Seller');finish(response(buyer));await waitFor(()=>expect(getAccessToken()).toBe('new'));await new Promise(resolve=>setTimeout(resolve,20));expect(screen.getByText('Seller')).toBeInTheDocument();
  });
  it('does not revive a session when login completes after logout',async()=>{
    let finish!: (response:Response)=>void;vi.stubGlobal('fetch',vi.fn((url:string)=>url.endsWith('/auth/login')?new Promise<Response>(resolve=>{finish=resolve;}):Promise.resolve(response({},url.endsWith('/auth/refresh')?401:200))));
    render(<AuthProvider><Probe/></AuthProvider>);await userEvent.click(screen.getByRole('button',{name:'Login'}));await userEvent.click(screen.getByRole('button',{name:'Logout'}));finish(response({access_token:'late',token_type:'bearer',expires_in:900,user:seller}));await new Promise(resolve=>setTimeout(resolve,20));expect(getAccessToken()).toBeNull();expect(screen.getByText('anonymous')).toBeInTheDocument();
  });
  it('clears token when identity loading fails after credential verification',async()=>{
    vi.stubGlobal('fetch',vi.fn(async(url:string)=>url.endsWith('/auth/login')?response({access_token:'new',token_type:'bearer',expires_in:900,user:seller}):response({},503)));
    render(<AuthProvider><Probe/></AuthProvider>);await userEvent.click(screen.getByRole('button',{name:'Login'}));await screen.findByText(/service is unavailable/i);expect(getAccessToken()).toBeNull();
  });
  it('invalidates a pending login when its provider unmounts',async()=>{
    let finish!: (response:Response)=>void;vi.stubGlobal('fetch',vi.fn((url:string)=>url.endsWith('/auth/login')?new Promise<Response>(resolve=>{finish=resolve;}):Promise.resolve(response({},url.endsWith('/auth/refresh')?401:200))));
    const view=render(<AuthProvider><Probe/></AuthProvider>);await userEvent.click(screen.getByRole('button',{name:'Login'}));view.unmount();render(<AuthProvider><Probe/></AuthProvider>);finish(response({access_token:'late',token_type:'bearer',expires_in:900,user:seller}));await new Promise(resolve=>setTimeout(resolve,20));expect(getAccessToken()).toBeNull();expect(screen.getByText('anonymous')).toBeInTheDocument();
  });
  it('expires a session without waiting for another HTTP request',async()=>{
    vi.stubGlobal('fetch',vi.fn(async(url:string)=>url.endsWith('/auth/login')?response({access_token:'short',token_type:'bearer',expires_in:0.2,user:seller}):url.endsWith('/auth/refresh')?response({},401):response(seller)));
    render(<AuthProvider><Probe/></AuthProvider>);await userEvent.click(screen.getByRole('button',{name:'Login'}));await screen.findByText('Seller');expect(sessionStorage.length).toBe(0);expect(localStorage.length).toBe(0);await screen.findByText(/session expired/i);expect(getAccessToken()).toBeNull();expect(screen.getByText('anonymous')).toBeInTheDocument();
  });
});
