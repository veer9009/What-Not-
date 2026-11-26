import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { DispatchLocation } from './DispatchLocation';
const shop={id:'2',user_id:'1',shop_name:'Maker',phone:'100',description:null,latitude:'19',longitude:'72',is_verified:false,dispatch_location_confirmed_at:null};
afterEach(()=>vi.unstubAllGlobals());
it('retains the original dispatch point after a failed GPS replacement',async()=>{let reject=true;const bodies:unknown[]=[];vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(cb:PositionCallback)=>cb({coords:{latitude:20,longitude:73,accuracy:10}} as GeolocationPosition)}});vi.stubGlobal('fetch',async(_url:string,options:RequestInit)=>{bodies.push(JSON.parse(String(options.body)));return new Response(JSON.stringify(reject?{}:{...shop,dispatch_location_confirmed_at:'2026-11-25'}),{status:reject?503:200});});render(<DispatchLocation shop={{...shop,dispatch_location_confirmed_at:'2026-11-24'}} reload={async()=>true}/>);await userEvent.click(screen.getByRole('button',{name:'Update dispatch location'}));await userEvent.click(screen.getByRole('button',{name:'Use current location'}));await userEvent.click(screen.getByRole('button',{name:'Confirm dispatch location'}));await screen.findByRole('alert');await userEvent.click(screen.getByRole('button',{name:'Cancel'}));reject=false;await userEvent.click(screen.getByRole('button',{name:'Update dispatch location'}));await userEvent.click(screen.getByRole('button',{name:'Confirm dispatch location'}));await screen.findByText('Dispatch location saved.');expect(bodies).toEqual([{latitude:20,longitude:73},{latitude:19,longitude:72}]);});
it('requires explicit confirmation and hides the saved point',async()=>{
  const fetcher=vi.fn(async(_url:string,options:RequestInit)=>{expect(JSON.parse(String(options.body))).toEqual({latitude:19,longitude:72});return new Response(JSON.stringify({...shop,dispatch_location_confirmed_at:'2026-10-18'}));});
  vi.stubGlobal('fetch',fetcher);
  render(<DispatchLocation shop={shop} reload={async()=>true}/>);
  expect(screen.queryByText(/19, 72/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button',{name:'Set dispatch location'}));
  expect(fetcher).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button',{name:'Confirm dispatch location'}));
  await screen.findByText(/Dispatch location confirmed/);
});
