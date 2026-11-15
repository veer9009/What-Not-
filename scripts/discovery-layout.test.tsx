// Node-only test tooling outside the browser TypeScript project; no real API/DB.
import { writeFileSync } from 'node:fs';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, it, vi } from 'vitest';
import App from '../src/App';
import { setAccessToken } from '../src/api/client';

afterEach(()=>{cleanup();setAccessToken(null);vi.unstubAllGlobals();});
it('exports actual rendered discovery markup with synthetic fixtures for offline geometry checks',async()=>{
  setAccessToken('synthetic-layout-only');
  const product={id:3,seller_id:2,name:'QA Nearby Vase',description:'Synthetic fixture',price:'250.00',stock_quantity:5,category:'Crafts',delivery_radius_km:2,image_url:null,shop_name:'Chrome QA Maker',is_verified:false,delivery_eligibility:'CONFIRMED_AT_CHECKOUT'};
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const path=new URL(input).pathname.replace('/api/v1','');
    const body=path==='/auth/me'?{id:1,name:'QA Buyer',email:'chrome-buyer@example.com',role:'BUYER'}:
      path==='/addresses'?[{id:4,user_id:1,label:'QA Home',address_line1:'Synthetic fixture',city:'QA',state:'QA',pincode:'999999',latitude:'0',longitude:'0',is_default:true}]:
      path==='/discovery/products'?[product,{...product,id:5,name:'QA Nearby Basket',price:'125.50'}]:[];
    return new Response(JSON.stringify(body),{status:200});
  }));
  render(<MemoryRouter initialEntries={['/buyer']}><App/></MemoryRouter>);
  await screen.findByLabelText('Latitude');
  await userEvent.type(screen.getByLabelText('Latitude'),'0');
  await userEvent.type(screen.getByLabelText('Longitude'),'0');
  await userEvent.click(screen.getByRole('button',{name:'Use for discovery'}));
  await screen.findByText('QA Nearby Vase');
  await screen.findByRole('button',{name:'Use QA Home for discovery'});
  writeFileSync('docs/security/evidence/discovery-layout-fixture.html',document.body.innerHTML);
},20000);
