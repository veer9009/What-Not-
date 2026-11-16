import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { OrderDetailsPage } from './OrderPages';
import { ordersApi } from '../api/orders';
import type { Fulfillment, Order } from '../api/types';

const auth = vi.hoisted(()=>({role:'SELLER'}));
vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{name:'Test',role:auth.role}})}));
const order:Order={id:'9',buyer_id:'1',seller_id:'2',status:'ACCEPTED',subtotal:'10',delivery_fee:'0',total:'10',items:[]};
const delivery:Fulfillment={recipient_name:'Buyer',phone:'100',address_line1:'Private Lane',city:'City',state:'State',pincode:'400001'};
afterEach(()=>{vi.restoreAllMocks();auth.role='SELLER';});
function open(data:Fulfillment,status:Order['status']='ACCEPTED'){
  vi.spyOn(ordersApi,'get').mockResolvedValue({...order,status});
  vi.spyOn(ordersApi,'fulfillment').mockResolvedValue(data);
  render(<MemoryRouter initialEntries={['/orders/9']}><Routes><Route path="/orders/:id" element={<OrderDetailsPage/>}/></Routes></MemoryRouter>);
}
it('opens validated confirmed coordinates securely only after authorized delivery details load',async()=>{
  open({...delivery,delivery_location:{latitude:'19.07',longitude:'-72.87'},delivery_location_confirmed:true});
  expect(screen.queryByRole('link',{name:'Navigate to Buyer'})).not.toBeInTheDocument();
  fireEvent.click(await screen.findByRole('button',{name:'View delivery details'}));
  const link=await screen.findByRole('link',{name:'Navigate to Buyer'});
  expect(link).toHaveAttribute('href','https://www.google.com/maps/dir/?api=1&destination=19.07%2C-72.87');
  expect(link).toHaveAttribute('target','_blank');
  expect(link).toHaveAttribute('rel','noopener noreferrer');
});
it.each([null,{latitude:'',longitude:'0'},{latitude:'NaN',longitude:'2'},{latitude:'91',longitude:'0'},
  {latitude:'0',longitude:'181'},{latitude:'1&evil=x',longitude:'2'}])('offers a fallback for unusable coordinates %s',async point=>{
  open({...delivery,delivery_location:point,delivery_location_confirmed:true});
  fireEvent.click(await screen.findByRole('button',{name:'View delivery details'}));
  expect(await screen.findByText(/Buyer-confirmed delivery coordinates are unavailable/)).toBeInTheDocument();
  expect(screen.queryByRole('link',{name:'Navigate to Buyer'})).not.toBeInTheDocument();
});
it('never navigates an unconfirmed point',async()=>{
  open({...delivery,delivery_location:{latitude:'0',longitude:'0'},delivery_location_confirmed:false});
  fireEvent.click(await screen.findByRole('button',{name:'View delivery details'}));
  await screen.findByText(/Buyer-confirmed delivery coordinates are unavailable/);
  expect(screen.queryByRole('link',{name:'Navigate to Buyer'})).not.toBeInTheDocument();
});
it('accepts a confirmed zero coordinate without treating it as missing',async()=>{
  open({...delivery,delivery_location:{latitude:'0.000000',longitude:'0.000000'},delivery_location_confirmed:true});
  fireEvent.click(await screen.findByRole('button',{name:'View delivery details'}));
  expect(await screen.findByRole('link',{name:'Navigate to Buyer'})).toHaveAttribute('href','https://www.google.com/maps/dir/?api=1&destination=0%2C0');
});
it('shows no navigation when the backend denies fulfillment',async()=>{
  open(delivery);
  vi.mocked(ordersApi.fulfillment).mockRejectedValue(new Error('Forbidden'));
  fireEvent.click(await screen.findByRole('button',{name:'View delivery details'}));
  await screen.findByRole('alert');
  expect(screen.queryByRole('link',{name:'Navigate to Buyer'})).not.toBeInTheDocument();
});
it('clears the destination after an order status transition',async()=>{
  open({...delivery,delivery_location:{latitude:'19',longitude:'72'},delivery_location_confirmed:true});
  vi.spyOn(ordersApi,'transition').mockResolvedValue({...order,status:'CANCELLED'});
  fireEvent.click(await screen.findByRole('button',{name:'View delivery details'}));
  await screen.findByRole('link',{name:'Navigate to Buyer'});
  vi.mocked(ordersApi.get).mockResolvedValue({...order,status:'CANCELLED'});
  fireEvent.click(screen.getByRole('button',{name:'Cancel order'}));
  await screen.findByText('Order updated.');
  expect(screen.queryByRole('link',{name:'Navigate to Buyer'})).not.toBeInTheDocument();
});
it.each(['PLACED','COMPLETED','CANCELLED','REJECTED'] as const)('hides delivery navigation in %s',async status=>{
  const load=vi.spyOn(ordersApi,'fulfillment');
  open(delivery,status);
  await screen.findByText(/Subtotal:/);
  expect(screen.queryByRole('button',{name:'View delivery details'})).not.toBeInTheDocument();
  expect(load).not.toHaveBeenCalled();
});
it('requires buyer review and explicit confirmation of the order delivery point',async()=>{
  auth.role='BUYER';
  const confirm=vi.spyOn(ordersApi,'confirmDeliveryLocation').mockResolvedValue({...delivery,delivery_location:{latitude:'0',longitude:'0'},delivery_location_confirmed:true});
  open({...delivery,delivery_location:{latitude:'0',longitude:'0'},delivery_location_confirmed:false});
  expect(confirm).not.toHaveBeenCalled();
  fireEvent.click(await screen.findByRole('button',{name:'Review delivery location'}));
  await screen.findByText(/Latitude: 0, longitude: 0/);
  fireEvent.click(screen.getByRole('button',{name:'Confirm delivery location for seller navigation'}));
  await waitFor(()=>expect(confirm).toHaveBeenCalledWith('9',{latitude:'0',longitude:'0'}));
  expect(await screen.findByText(/Delivery location confirmed for this order/)).toBeInTheDocument();
  expect(screen.queryByRole('link',{name:'Navigate to Buyer'})).not.toBeInTheDocument();
});
