// Real React markup and synthetic data only; used by the offline Chrome checker.
import { writeFileSync } from 'node:fs';
import { useEffect } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { AddressPage } from '../src/pages/AddressPage';
import { CartPage } from '../src/pages/CartPage';
import { CheckoutPage } from '../src/pages/CheckoutPage';
import { checkoutApi } from '../src/api/checkout';
import { DemoProvider, useDemo } from '../src/state/DemoContext';
import { addressesApi } from '../src/api/addresses';
import type { BuyerProduct } from '../src/api/discovery';

vi.mock('../src/state/AuthContext',()=>({useAuth:()=>({user:{id:'1',role:'BUYER',name:'Layout buyer'},logout:vi.fn()})}));
const product:BuyerProduct={id:'3',seller_id:'2',name:'A handmade neighbourhood vase with a deliberately long product name',shop_name:'Local maker with a long business name',description:'Synthetic layout data',price:'12500.00',stock_quantity:5,category:'Crafts',delivery_radius_km:3,image_url:null,is_verified:false};
function Seed(){const {dispatch}=useDemo();useEffect(()=>{dispatch({type:'cart/add-discovered',product});},[dispatch]);return <><CartPage/><CheckoutPage/></>;}
afterEach(()=>vi.restoreAllMocks());
it('opens checkout from cart and requires explicit address and payment before confirmation',async()=>{
  vi.spyOn(checkoutApi,'preview').mockResolvedValue({groups:[{seller_id:'2',seller_name:product.shop_name,items:[{product_id:'3',name:product.name,quantity:1,unit_price:'12500.00'}],subtotal:'12500.00',delivery_fee:'0.00',total:'12500.00',available_payment_methods:['COD'],upi_unavailable_reason:'UPI disabled pending approval.'}],total:'12500.00',currency:'INR'});
  vi.spyOn(addressesApi,'list').mockResolvedValue([{id:'4',user_id:'1',label:'Home',address_line1:'A long postal address for checkout dropdown containment',address_line2:null,city:'Mumbai',state:'Maharashtra',pincode:'400001',latitude:'19',longitude:'72',is_default:true}]);
  render(<MemoryRouter><AddressPage/><DemoProvider ownerId="1"><Seed/></DemoProvider></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button',{name:'Edit address'}));
  expect(screen.queryByLabelText('Latitude')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Longitude')).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Use Current Location'})).toBeEnabled();
  await screen.findByRole('combobox',{name:'Delivery address'});
  expect(screen.getByRole('link',{name:'Checkout'})).toHaveAttribute('href','/buyer/checkout');
  expect(screen.getByRole('button',{name:'Review final order'})).toBeDisabled();
  fireEvent.change(screen.getByRole('combobox',{name:'Delivery address'}),{target:{value:'4'}});
  expect(screen.getByRole('combobox',{name:'Delivery address'})).toHaveValue('4');
  await screen.findByLabelText(`Cash on delivery — ${product.shop_name}`);
  expect(screen.getByRole('button',{name:'Review final order'})).toBeDisabled();
  fireEvent.click(screen.getByLabelText(`Cash on delivery — ${product.shop_name}`));
  expect(screen.getByRole('button',{name:'Review final order'})).toBeEnabled();
  expect(screen.getByRole('link',{name:'Manage saved addresses'})).toHaveAttribute('href','/buyer/addresses');
  // DOM serialization otherwise loses select.value and shows the placeholder.
  document.querySelectorAll('select option').forEach(option=>{
    if((option as HTMLOptionElement).selected)option.setAttribute('selected','');
    else option.removeAttribute('selected');
  });
  writeFileSync('docs/security/evidence/buyer-layout-fixture.html',document.body.innerHTML);
});
