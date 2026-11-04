import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { setAccessToken } from './api/client';

afterEach(() => {setAccessToken(null);vi.unstubAllGlobals();});

function orderSetup(role='BUYER', status='DELIVERED') {
  let state=status;
  const writes: unknown[]=[];
  setAccessToken('beta-test');
  vi.stubGlobal('fetch', vi.fn(async(input:string, options:RequestInit)=>{
    const path=new URL(input).pathname.replace('/api/v1','');
    let data:unknown;
    if(path==='/auth/me')data={id:1,name:'Tester',email:'tester@example.com',role};
    else if(path.endsWith('/fulfillment'))data={recipient_name:'Buyer',phone:'9000000000',address_line1:'Private delivery lane',city:'City',state:'State',pincode:'400001'};
    else {
      if(options.method==='PATCH'){const body=JSON.parse(String(options.body));writes.push(body);state=body.status;}
      data={id:9,buyer_id:1,seller_id:2,status:state,subtotal:'100.00',delivery_fee:'0.00',total:'100.00',
        confirmation_deadline:'2026-11-04T12:00:00Z',items:[{product_id:3,seller_id:2,name:'Clay vase',quantity:1,unit_price:'100.00'}]};
    }
    return new Response(JSON.stringify(data),{status:200});
  }));
  render(<MemoryRouter initialEntries={[`/${role.toLowerCase()}/orders/9`]}><App/></MemoryRouter>);
  return writes;
}

it('records a delivery dispute through the backend rather than just opening support',async()=>{
  const writes=orderSetup();
  await screen.findByText('Clay vase',{}, {timeout:5000});
  await userEvent.click(await screen.findByRole('button',{name:/report not received/i}));
  await screen.findByText('Delivery disputed');
  expect(writes).toEqual([{status:'DELIVERY_DISPUTED'}]);
  expect(screen.queryByRole('button',{name:'Yes, I received it'})).not.toBeInTheDocument();
});

it('buyer receipt confirmation completes the seller-delivered order',async()=>{
  const writes=orderSetup();
  await userEvent.click(await screen.findByRole('button',{name:'Yes, I received it'}));
  await screen.findByRole('status');
  expect(writes).toEqual([{status:'COMPLETED'}]);
});

it('seller can retrieve only the active order fulfillment view',async()=>{
  orderSetup('SELLER','ACCEPTED');
  await userEvent.click(await screen.findByRole('button',{name:'View delivery details'}));
  expect(await screen.findByText(/Private delivery lane/)).toBeInTheDocument();
});

it('discovery explains checkout eligibility without showing private point distance',async()=>{
  setAccessToken('beta-test');
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const path=new URL(input).pathname;
    const data=path.endsWith('/auth/me')?{id:1,name:'Buyer',email:'buyer@example.com',role:'BUYER'}:
      path.endsWith('/addresses')?[]:[{id:3,seller_id:2,name:'Nearby vase',description:'Clay',price:'10.00',stock_quantity:1,
        category:'Crafts',delivery_radius_km:1,image_url:null,shop_name:'Maker',is_verified:false,delivery_eligibility:'CONFIRMED_AT_CHECKOUT'}];
    return new Response(JSON.stringify(data),{status:200});
  }));
  render(<MemoryRouter initialEntries={['/buyer']}><App/></MemoryRouter>);
  await screen.findByLabelText('Latitude');
  await userEvent.type(screen.getByLabelText('Latitude'),'19');
  await userEvent.type(screen.getByLabelText('Longitude'),'72');
  await userEvent.click(screen.getByRole('button',{name:'Use for discovery'}));
  expect(await screen.findByText('Nearby vase')).toBeInTheDocument();
  expect(screen.getAllByText(/delivery.*confirm.*checkout/i).length).toBeGreaterThan(0);
  expect(screen.queryByText(/km away/i)).not.toBeInTheDocument();
});

it('seller reads persisted notifications and clears the unread count through the API',async()=>{
  setAccessToken('beta-test');let read=false;
  const writes:string[]=[];
  vi.stubGlobal('fetch',vi.fn(async(input:string,options:RequestInit)=>{
    const path=new URL(input).pathname.replace('/api/v1','');
    if(options.method==='PATCH'){read=true;writes.push(path);}
    const data=path==='/auth/me'?{id:1,name:'Maker',email:'maker@example.com',role:'SELLER'}:
      path.endsWith('/unread-count')?{count:read?0:1}:
      [{id:7,kind:'NEW_ORDER',entity_type:'order',entity_id:9,title:'New order received',body:'Order #9, Amount: ₹100.00',created_at:'2026-11-03T12:00:00Z',read_at:read?'2026-11-03T12:01:00Z':null}];
    return new Response(JSON.stringify(data),{status:200});
  }));
  render(<MemoryRouter initialEntries={['/seller/notifications']}><App/></MemoryRouter>);
  await userEvent.click(await screen.findByRole('button',{name:'Mark as read'}));
  expect(await screen.findByText('0 unread')).toBeInTheDocument();
  expect(writes).toEqual(['/notifications/7/read']);
  expect(screen.getByRole('link',{name:'View update'})).toHaveAttribute('href','/seller/orders/9');
});
