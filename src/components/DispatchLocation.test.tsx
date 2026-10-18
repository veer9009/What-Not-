import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { DispatchLocation } from './DispatchLocation';
const shop={id:'2',user_id:'1',shop_name:'Maker',phone:'100',description:null,latitude:'19',longitude:'72',is_verified:false,dispatch_location_confirmed_at:null};
afterEach(()=>vi.unstubAllGlobals());
it('requires explicit confirmation before persisting a dispatch draft',async()=>{
  const fetcher=vi.fn(async(_url:string,options:RequestInit)=>{
    expect(JSON.parse(String(options.body))).toEqual({latitude:19,longitude:72});
    return new Response(JSON.stringify({...shop,dispatch_location_confirmed_at:'2026-10-18T00:00:00Z'}));
  });vi.stubGlobal('fetch',fetcher);
  render(<DispatchLocation shop={shop} reload={async()=>true}/>);
  expect(screen.getByText(/Dispatch location not confirmed/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button',{name:'Set dispatch location'}));
  expect(fetcher).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button',{name:'Confirm dispatch location'}));
  await screen.findByText(/Dispatch location confirmed/);
});
it('keeps the previous saved point on failure and shows the error',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response('{}',{status:503})));
  render(<DispatchLocation shop={{...shop,dispatch_location_confirmed_at:'2026-10-18T00:00:00Z'}} reload={async()=>true}/>);
  await userEvent.click(screen.getByRole('button',{name:'Update dispatch location'}));
  await userEvent.clear(screen.getByLabelText('Latitude'));await userEvent.type(screen.getByLabelText('Latitude'),'20');
  await userEvent.click(screen.getByRole('button',{name:'Confirm dispatch location'}));
  await screen.findByRole('alert');
  expect(screen.getByText(/Saved dispatch point: 19, 72/)).toBeInTheDocument();
});
