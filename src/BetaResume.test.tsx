import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { setAccessToken } from './api/client';

afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it('submits the exact product revision reviewed by the administrator',async()=>{
  setAccessToken('test');const writes:unknown[]=[];
  const updated_at='2026-11-03T12:00:00.123456Z';
  vi.stubGlobal('fetch',async(input:string,options:RequestInit)=>{
    const path=new URL(input).pathname;
    if(options.method==='POST')writes.push(JSON.parse(String(options.body)));
    const data=path.endsWith('/auth/me')?{id:1,name:'Admin',role:'ADMIN',email:'admin@example.test'}:
      options.method==='POST'?{}:[{id:3,seller_id:2,name:'Reviewed vase',description:'Clay',price:'10.00',stock_quantity:1,category:'Crafts',delivery_radius_km:1,status:'PENDING',is_active:true,updated_at}];
    return new Response(JSON.stringify(data),{status:200});
  });
  render(<MemoryRouter initialEntries={['/admin']}><App/></MemoryRouter>);
  await userEvent.click(await screen.findByRole('button',{name:'Approve'}));
  await waitFor(()=>expect(writes).toEqual([{expected_updated_at:updated_at}]));
});

it('public copy advertises sale-only beta workflows without claiming legal proof verification',()=>{
  render(<MemoryRouter><App/></MemoryRouter>);
  expect(screen.queryByText(/rent or sale/i)).not.toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Explore sale properties'})).toHaveAttribute('href','/buyer/properties');
  expect(screen.getByRole('link',{name:'Explore Creative Services'})).toHaveAttribute('href','/buyer/creative');
  expect(screen.queryByText(/Checkout is unavailable/i)).not.toBeInTheDocument();
});
