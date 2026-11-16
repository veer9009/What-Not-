// Real React markup and synthetic data only; used by the offline Chrome checker.
import { writeFileSync } from 'node:fs';
import { useEffect } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { AddressPage } from '../src/pages/AddressPage';
import { CartPage } from '../src/pages/CartPage';
import { DemoProvider, useDemo } from '../src/state/DemoContext';
import { addressesApi } from '../src/api/addresses';
import type { BuyerProduct } from '../src/api/discovery';

vi.mock('../src/state/AuthContext',()=>({useAuth:()=>({user:{id:'1',role:'BUYER',name:'Layout buyer'},logout:vi.fn()})}));
const product:BuyerProduct={id:'3',seller_id:'2',name:'A handmade neighbourhood vase with a deliberately long product name',shop_name:'Local maker with a long business name',description:'Synthetic layout data',price:'12500.00',stock_quantity:5,category:'Crafts',delivery_radius_km:3,image_url:null,is_verified:false};
function Seed(){const {dispatch}=useDemo();useEffect(()=>{dispatch({type:'cart/add-discovered',product});},[dispatch]);return <CartPage/>;}
afterEach(()=>vi.restoreAllMocks());
it('keeps checkout disabled until explicit address selection and exports address/cart layouts',async()=>{
  vi.spyOn(addressesApi,'list').mockResolvedValue([{id:'4',user_id:'1',label:'Home',address_line1:'A long postal address for checkout dropdown containment',address_line2:null,city:'Mumbai',state:'Maharashtra',pincode:'400001',latitude:'19',longitude:'72',is_default:true}]);
  render(<MemoryRouter><AddressPage/><DemoProvider ownerId="1"><Seed/></DemoProvider></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button',{name:'Edit address'}));
  expect(screen.getByText('Advanced location details').closest('details')).not.toHaveAttribute('open');
  fireEvent.click(screen.getByText('Advanced location details'));
  await screen.findByRole('combobox',{name:'Delivery address'});
  expect(screen.getByRole('button',{name:'Place orders'})).toBeDisabled();
  fireEvent.change(screen.getByRole('combobox',{name:'Delivery address'}),{target:{value:'4'}});
  expect(screen.getByRole('combobox',{name:'Delivery address'})).toHaveValue('4');
  expect(screen.getByRole('button',{name:'Place orders'})).toBeEnabled();
  expect(screen.getByRole('link',{name:'Manage saved addresses'})).toHaveAttribute('href','/buyer/addresses');
  // DOM serialization otherwise loses select.value and shows the placeholder.
  document.querySelectorAll('select option').forEach(option=>{
    if((option as HTMLOptionElement).selected)option.setAttribute('selected','');
    else option.removeAttribute('selected');
  });
  writeFileSync('docs/security/evidence/buyer-layout-fixture.html',document.body.innerHTML);
});
