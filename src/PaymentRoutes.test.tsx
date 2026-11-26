import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { setAccessToken } from './api/client';
vi.mock('./pages/PaymentsPage',()=>({PaymentsPage:()=><main><h1>Owned payments</h1></main>}));
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it.each(['BUYER','SELLER','ADMIN'])('allows the existing %s role into its Payments route',async role=>{
  setAccessToken('synthetic-route-token');
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>new Response(JSON.stringify(input.endsWith('/wishlist')?{items:[],count:0}:input.endsWith('/notifications/unread-count')?{count:0}:{id:'1',name:'Test',email:'test@example.test',role}))));
  render(<MemoryRouter initialEntries={[`/${role.toLowerCase()}/payments`]}><App/></MemoryRouter>);
  expect(await screen.findByRole('heading',{name:'Owned payments'})).toBeInTheDocument();
});
it.each([['BUYER','seller'],['BUYER','admin'],['SELLER','buyer'],['SELLER','admin'],['ADMIN','buyer'],['ADMIN','seller']])('blocks %s from the %s Payments route',async(role,path)=>{
  setAccessToken('synthetic-route-token');const fetcher=vi.fn(async(input:string)=>new Response(JSON.stringify(input.endsWith('/wishlist')?{items:[],count:0}:input.endsWith('/notifications/unread-count')?{count:0}:{id:'1',name:'Test',email:'test@example.test',role})));
  vi.stubGlobal('fetch',fetcher);
  render(<MemoryRouter initialEntries={[`/${path}/payments`]}><App/></MemoryRouter>);
  expect(await screen.findByText('This page is not available for your account.')).toBeInTheDocument();
  expect(screen.queryByRole('heading',{name:'Owned payments'})).not.toBeInTheDocument();
  expect(fetcher.mock.calls.filter(([url])=>String(url).endsWith('/auth/me'))).toHaveLength(1);
  expect(fetcher.mock.calls.every(([url])=>/\/(auth\/me|notifications\/unread-count|wishlist)$/.test(String(url)))).toBe(true);
});
