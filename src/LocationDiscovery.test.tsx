import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { setAccessToken } from './api/client';

const product={id:3,seller_id:2,name:'Nearby vase',description:'A handmade vase',price:'250.00',stock_quantity:5,category:'Crafts',delivery_radius_km:2,image_url:null,shop_name:'Local maker',is_verified:false,delivery_eligibility: 'CONFIRMED_AT_CHECKOUT'};
const address={id:4,user_id:1,label:'Home',address_line1:'Maker Lane',city:'Mumbai',state:'Maharashtra',pincode:'400001',latitude:'19',longitude:'72',is_default:true};
type Reply = [number, unknown];
function setup(handler:(path:string,body:any)=>Reply|Promise<Reply>,path='/buyer'){
  setAccessToken('location-test');
  const fetcher=vi.fn(async(input:string,options:RequestInit)=>{
    const path=new URL(input, location.origin).pathname.replace('/api/v1','');
    const [status,body]=path==='/auth/me'?[200,{id:1,name:'Ravi',email:'ravi@example.com',role:'BUYER'}]:path==='/wishlist'?[200,{items:[],count:0}]:path==='/notifications/unread-count'?[200,{count:0}]:await handler(path,options.body?JSON.parse(String(options.body)):undefined);
    return new Response(JSON.stringify(body),{status});
  });vi.stubGlobal('fetch',fetcher);
  render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
  return fetcher;
}
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it('refreshes supported, unsupported and supported GPS points without retaining stale cards',async()=>{let complete!:PositionCallback;const points:any[]=[];vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(cb:PositionCallback)=>{complete=cb;}}});setup((path,body)=>{if(path==='/addresses')return [200,[]];points.push(body);return [200,body.location.latitude===0?[product]:[]];});for(const latitude of [0,1,0]){await userEvent.click(await screen.findByRole('button',{name:'Use current location'}));expect(screen.queryByText('Nearby vase')).not.toBeInTheDocument();await act(async()=>complete({coords:{latitude,longitude:0,accuracy:10}} as GeolocationPosition));await userEvent.click(screen.getByRole('button',{name:'Use for discovery'}));await screen.findByText(latitude===0?'Nearby vase':'No products nearby');}expect(points.map(point=>point.location.latitude)).toEqual([0,1,0]);expect(points.every(point=>point.radius_km===3&&point.location.longitude===0)).toBe(true);});
it('changes live backend radius without reacquiring location and ignores stale responses',async()=>{
  let finish!:(value:Reply)=>void;
  const bodies:any[]=[];
  setup((path,body)=>{
    if(path==='/addresses')return [200,[]];
    bodies.push(body);
    if(body.radius_km===2)return new Promise(resolve=>{finish=resolve;});
    return [200,body.radius_km===1?[]:[product]];
  });
  await manual();await screen.findByText('Nearby vase');
  const radius=screen.getByRole('group',{name:'Discovery radius'});
  await userEvent.click(within(radius).getByRole('button',{name:'2 KM'}));
  expect(screen.queryByText('Nearby vase')).not.toBeInTheDocument();
  await userEvent.click(within(radius).getByRole('button',{name:'1 KM'}));
  await screen.findByText('No products nearby');
  await act(async()=>finish([200,[product]]));
  expect(screen.queryByText('Nearby vase')).not.toBeInTheDocument();
  await userEvent.click(within(radius).getByRole('button',{name:'3 KM'}));
  await screen.findByText('Nearby vase');
  expect(bodies.map(body=>body.radius_km)).toEqual([3,2,1,3]);
  expect(bodies.every(body=>body.location.latitude===19&&body.location.longitude===72)).toBe(true);
});
it('associates PIN guidance and styles the clear action as a secondary button',async()=>{
  setup(path=>path==='/addresses'?[200,[]]:[200,[]]);
  await screen.findByLabelText('PIN code');
  expect(screen.getByLabelText('PIN code')).toHaveAccessibleDescription(/A PIN code alone does not identify an exact location/);
  await manual();
  expect(screen.getByRole('button',{name:'Clear discovery location'})).toHaveClass('btn','btn-outline');
});
async function manual(){
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(success:PositionCallback)=>success({coords:{latitude:19,longitude:72,accuracy:20}} as GeolocationPosition)}});
  await screen.findByRole('button',{name:'Use current location'});
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  await userEvent.click(screen.getByRole('button',{name:'Use for discovery'}));
}
it('requires an explicit source, uses backend list/detail and adds real products to the cart',async()=>{
  const fetcher=setup((path,body)=>{
    if(path==='/addresses')return [200,[]];
    expect(body).toEqual({location:{latitude:19,longitude:72},radius_km:3});
    return [200,path.endsWith('/3')?product:[product]];
  });
  await screen.findByText('Location not set');
  expect(fetcher.mock.calls.some(([url])=>url.includes('/discovery/'))).toBe(false);
  await manual();
  await screen.findByText('Nearby vase');
  expect(screen.getByText(/Crafts · Nearby locality/)).toBeInTheDocument();
  expect(screen.queryByText(/0.14 km/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/sample distance/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('link',{name:'View Nearby vase'}));
  await screen.findByRole('heading',{name:'Nearby vase'});
  await userEvent.click(screen.getByRole('button',{name:/add to cart/i}));
  expect(screen.getByRole('link',{name:'View cart'})).toHaveAttribute('href','/buyer/cart');
  await userEvent.click(screen.getByRole('link',{name:'Back to discovery'}));
  await screen.findByRole('link',{name:'View Nearby vase'});
});
it('does not silently select a default address',async()=>{
  const fetcher=setup((path,body)=>path==='/addresses'?[200,[address]]:(expect(body).toEqual({address_id:4,radius_km:3}),[200,[]]));
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
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
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
it('uses confirmed device coordinates in a POST body without exposing them in URLs or storage',async()=>{
  const point={latitude:19.123457,longitude:72.123457};
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(success:PositionCallback)=>success({coords:{latitude:19.12345678,longitude:72.12345678}} as GeolocationPosition)}});
  const fetcher=setup((path,body)=>path==='/addresses'?[200,[]]:(expect(body).toEqual({location:point,radius_km:3}),[200,[product]]));
  await screen.findByText('Location not set');
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  expect(fetcher.mock.calls.some(([url])=>url.includes('/discovery/'))).toBe(false);
  await userEvent.click(screen.getByRole('button',{name:'Use for discovery'}));
  await screen.findByText('Nearby vase');
  const request=fetcher.mock.calls.find(([url])=>url.includes('/discovery/'))!;
  expect(request[0]).not.toContain(String(point.latitude));
  expect(request[0]).not.toContain(String(point.longitude));
  expect(request[1].method).toBe('POST');
  expect(JSON.stringify(localStorage)).not.toContain(String(point.latitude));
  expect(JSON.stringify(sessionStorage)).not.toContain(String(point.longitude));
});
it('offers manual PIN lookup of saved addresses after permission denial, without inventing coordinates',async()=>{
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(_success:PositionCallback,error:PositionErrorCallback)=>error({code:1} as GeolocationPositionError)}});
  const fetcher=setup((path,body)=>path==='/addresses'?[200,[address,{...address,id:5,label:'Work',pincode:'411001'}]]:(expect(body).toEqual({address_id:4,radius_km:3}),[200,[product]]));
  await screen.findByRole('button',{name:'Use Home for discovery'});
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  expect(screen.getByRole('alert')).toHaveTextContent(/permission was denied/i);
  await userEvent.type(screen.getByLabelText('PIN code'),'400001');
  expect(screen.queryByRole('button',{name:'Use Work for discovery'})).not.toBeInTheDocument();
  expect(fetcher.mock.calls.some(([url])=>url.includes('/discovery/'))).toBe(false);
  await userEvent.click(screen.getByRole('button',{name:'Use Home for discovery'}));
  await screen.findByText('Nearby vase');
});
it('does not request discovery for an unknown manually entered PIN',async()=>{
  const fetcher=setup(path=>path==='/addresses'?[200,[address]]:[200,[]]);
  await screen.findByRole('button',{name:'Use Home for discovery'});
  await userEvent.type(screen.getByLabelText('PIN code'),'999999');
  expect(screen.getByText(/no saved address matches/i)).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Use Home for discovery'})).not.toBeInTheDocument();
  expect(fetcher.mock.calls.some(([url])=>url.includes('/discovery/'))).toBe(false);
});
it('re-detects into a fresh draft, clears old results and sends only the newly confirmed point',async()=>{
  let success!:PositionCallback;
  const getCurrentPosition=vi.fn((callback:PositionCallback)=>{success=callback;});
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition}});
  const points:any[]=[];
  setup((path,body)=>{
    if(path==='/addresses')return [200,[]];
    points.push(body);
    return [200,points.length===1?[product]:[]];
  });
  await screen.findByText('Location not set');
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  await act(async()=>success({coords:{latitude:19,longitude:72,accuracy:25}} as GeolocationPosition));
  await userEvent.click(screen.getByRole('button',{name:'Use for discovery'}));
  await screen.findByText('Nearby vase');
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  expect(screen.queryByText('Nearby vase')).not.toBeInTheDocument();
  expect(points).toHaveLength(1);
  await act(async()=>success({coords:{latitude:-20,longitude:73,accuracy:210}} as GeolocationPosition));
  expect(screen.getByText(/browser-reported accuracy: about 210 m/i)).toBeInTheDocument();
  expect(points).toHaveLength(1);
  await userEvent.click(screen.getByRole('button',{name:'Use for discovery'}));
  await screen.findByText('No products nearby');
  expect(getCurrentPosition).toHaveBeenCalledTimes(2);
  expect(points).toEqual([{location:{latitude:19,longitude:72},radius_km:3},{location:{latitude:-20,longitude:73},radius_km:3}]);
});
