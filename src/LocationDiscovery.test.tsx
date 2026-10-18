import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { setAccessToken } from './api/client';

const product={id:3,name:'Nearby vase',description:'A handmade vase',price:'250.00',stock_quantity:5,category:'Crafts',delivery_radius_km:2,image_url:null,shop_name:'Local maker',is_verified:false,distance_km:0.14};
const address={id:4,user_id:1,label:'Home',address_line1:'Maker Lane',city:'Mumbai',state:'Maharashtra',pincode:'400001',latitude:'19',longitude:'72',is_default:true};
type Reply = [number, unknown];
function setup(handler:(path:string,body:any)=>Reply|Promise<Reply>,path='/buyer'){
  setAccessToken('location-test');
  const fetcher=vi.fn(async(input:string,options:RequestInit)=>{
    const path=new URL(input).pathname.replace('/api/v1','');
    const [status,body]=path==='/auth/me'?[200,{id:1,name:'Ravi',email:'ravi@example.com',role:'BUYER'}]:await handler(path,options.body?JSON.parse(String(options.body)):undefined);
    return new Response(JSON.stringify(body),{status});
  });vi.stubGlobal('fetch',fetcher);
  render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
  return fetcher;
}
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
async function manual(){
  await screen.findByLabelText('Latitude');
  await userEvent.type(screen.getByLabelText('Latitude'),'19');
  await userEvent.type(screen.getByLabelText('Longitude'),'72');
  await userEvent.click(screen.getByRole('button',{name:'Use for discovery'}));
}
it('requires an explicit source, uses backend list/detail and keeps checkout disabled',async()=>{
  const fetcher=setup((path,body)=>{
    if(path==='/addresses')return [200,[]];
    expect(body).toEqual({location:{latitude:19,longitude:72}});
    return [200,path.endsWith('/3')?product:[product]];
  });
  await screen.findByText('Location not set');
  expect(fetcher.mock.calls.some(([url])=>url.includes('/discovery/'))).toBe(false);
  await manual();
  await screen.findByText('Nearby vase');
  expect(screen.getByText(/0.14 km/i)).toBeInTheDocument();
  expect(screen.queryByText(/sample distance/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('link',{name:'View Nearby vase'}));
  await screen.findByRole('heading',{name:'Nearby vase'});
  expect(screen.getByRole('button',{name:'Checkout unavailable'})).toBeDisabled();
  expect(screen.queryByRole('button',{name:/add to cart/i})).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('link',{name:'Back to discovery'}));
  await screen.findByRole('link',{name:'View Nearby vase'});
});
it('does not silently select a default address',async()=>{
  const fetcher=setup((path,body)=>path==='/addresses'?[200,[address]]:(expect(body).toEqual({address_id:4}),[200,[]]));
  await screen.findByRole('button',{name:'Use Home for discovery'});
  expect(fetcher.mock.calls.some(([url])=>url.includes('/discovery/'))).toBe(false);
  await userEvent.click(screen.getByRole('button',{name:'Use Home for discovery'}));
  await screen.findByText('No products nearby');
});
it('shows loading then sanitized discovery error',async()=>{
  let finish!:(value:Reply)=>void;
  setup(path=>path==='/addresses'?[200,[]]:new Promise(resolve=>{finish=resolve;}));
  await manual();
  expect(screen.getAllByRole('status').some(el=>/loading marketplace/i.test(el.textContent??''))).toBe(true);
  await act(async()=>finish([503,{detail:'sensitive coordinates'}]));
  expect(await screen.findByRole('alert')).toHaveTextContent(/unavailable/i);
  expect(screen.queryByText('sensitive coordinates')).not.toBeInTheDocument();
});
it('hides old results on draft edits and ignores their late response',async()=>{
  let finish!:(value:Reply)=>void;
  setup(path=>path==='/addresses'?[200,[]]:new Promise(resolve=>{finish=resolve;}));
  await manual();
  await userEvent.clear(screen.getByLabelText('Latitude'));
  await act(async()=>finish([200,[product]]));
  expect(screen.queryByText('Nearby vase')).not.toBeInTheDocument();
  expect(screen.getByText('Location not set')).toBeInTheDocument();
});
it('clears discovery data on logout',async()=>{
  setup(path=>path==='/addresses'?[200,[]]:[200,[product]]);
  await manual();await screen.findByText('Nearby vase');
  await userEvent.click(screen.getByRole('button',{name:'Log out'}));
  await screen.findByRole('heading',{name:/welcome back/i});
  expect(screen.queryByText('Nearby vase')).not.toBeInTheDocument();
});
