import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { AddressPage } from './AddressPage';
import { addressesApi } from '../api/addresses';
import type { Address } from '../api/types';

vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{id:'1',role:'BUYER',name:'Buyer'},logout:vi.fn()})}));
const address:Address={id:'4',user_id:'1',label:'Home',address_line1:'Maker Lane',address_line2:null,city:'Mumbai',state:'Maharashtra',pincode:'400001',latitude:'19',longitude:'72',is_default:false};
function device(){
  let success!:PositionCallback, failure!:PositionErrorCallback;
  const request=vi.fn((ok:PositionCallback,fail:PositionErrorCallback)=>{success=ok;failure=fail;});
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:request}});
  return {request,locate:async(latitude=12.12345678,longitude=-45.12345678)=>act(async()=>success({coords:{latitude,longitude,accuracy:25}} as GeolocationPosition)),fail:async(code:number)=>act(async()=>failure({code} as GeolocationPositionError))};
}
async function open(edit=false){
  vi.spyOn(addressesApi,'list').mockResolvedValue(edit?[address]:[]);
  const create=vi.spyOn(addressesApi,'create').mockResolvedValue(address);
  const update=vi.spyOn(addressesApi,'update').mockResolvedValue(address);
  const view=render(<MemoryRouter><AddressPage/></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button',{name:edit?'Edit address':'Add address'}));
  return {...view,create,update};
}
function postal(){for(const [label,value] of [['Label','Home'],['Address line 1','Maker Lane'],['City','Mumbai'],['State','Maharashtra'],['PIN code','400001']])fireEvent.change(screen.getByLabelText(label),{target:{value}});}
function manual(latitude='19',longitude='72'){
  const disclosure=screen.getByText('Advanced location details');
  if(!disclosure.closest('details')!.open)fireEvent.click(disclosure);
  expect(screen.getByLabelText('Latitude')).toBeVisible();
  fireEvent.change(screen.getByLabelText('Latitude'),{target:{value:latitude}});
  fireEvent.change(screen.getByLabelText('Longitude'),{target:{value:longitude}});
}
function save(){fireEvent.submit(screen.getByRole('button',{name:'Save address'}).closest('form')!);}
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});

it('detects only on click, keeps postal fields editable and saves GPS only after explicit save',async()=>{
  const gps=device();const {create}=await open();
  expect(gps.request).not.toHaveBeenCalled();
  expect(screen.getByText('Advanced location details').closest('details')).not.toHaveAttribute('open');
  fireEvent.click(screen.getByRole('button',{name:'Use Current Location'}));
  expect(screen.getByRole('button',{name:/detecting location/i})).toBeDisabled();
  expect(screen.getByRole('button',{name:'Save address'})).toBeDisabled();
  expect(screen.getByLabelText('Address line 1')).toBeEnabled();
  await gps.locate();
  expect(screen.getByLabelText('Latitude')).toHaveValue(12.123457);
  expect(screen.getByLabelText('Longitude')).toHaveValue(-45.123457);
  expect(screen.getByLabelText('PIN code')).toHaveValue('');
  expect(screen.getByLabelText('Address line 1')).toHaveValue('');
  expect(screen.getByText(/location detected/i)).toBeInTheDocument();
  expect(create).not.toHaveBeenCalled();postal();save();
  await waitFor(()=>expect(create).toHaveBeenCalledWith({label:'Home',address_line1:'Maker Lane',address_line2:null,city:'Mumbai',state:'Maharashtra',pincode:'400001',latitude:'12.123457',longitude:'-45.123457',is_default:false}));
});
it.each([[1,/permission was denied/i],[2,/position is unavailable/i],[3,/timed out/i]] as const)('GPS failure %s preserves a manual fallback',async(code,message)=>{
  const gps=device();const {update}=await open(true);
  fireEvent.click(screen.getByRole('button',{name:'Use Current Location'}));await gps.fail(code);
  expect(screen.getByRole('alert')).toHaveTextContent(message);
  expect(screen.getByText('Advanced location details').closest('details')).toHaveAttribute('open');
  expect(screen.getByLabelText('Latitude')).toHaveValue(19);
  fireEvent.change(screen.getByLabelText('Latitude'),{target:{value:'20'}});save();
  await waitFor(()=>expect(update).toHaveBeenCalledWith('4',{latitude:'20'}));
});
it('offers manual fallback when geolocation is unsupported',async()=>{
  vi.stubGlobal('navigator',{geolocation:undefined});const {create}=await open();
  fireEvent.click(screen.getByRole('button',{name:'Use Current Location'}));
  expect(await screen.findByRole('alert')).toHaveTextContent(/geolocation is unavailable/i);
  expect(screen.getByLabelText('Latitude')).toBeEnabled();postal();manual('0','0');save();
  await waitFor(()=>expect(create).toHaveBeenCalledWith(expect.objectContaining({latitude:'0',longitude:'0'})));
});
it.each([['91','72'],['19','181'],['','72']])('rejects invalid manual coordinates %s %s without an API write',async(lat,lon)=>{
  const {create}=await open();postal();manual(lat,lon);save();
  expect(await screen.findByRole('alert')).toHaveTextContent(/valid latitude/i);
  expect(create).not.toHaveBeenCalled();
});
it('requires postal fields even after GPS succeeds',async()=>{
  const gps=device();const {create}=await open();
  fireEvent.click(screen.getByRole('button',{name:'Use Current Location'}));await gps.locate();save();
  expect(create).not.toHaveBeenCalled();expect(screen.getByLabelText('City')).toBeInvalid();
});
it('ignores GPS after manual edits or form cancellation',async()=>{
  const gps=device();const {create}=await open();
  fireEvent.click(screen.getByRole('button',{name:'Use Current Location'}));manual('21','73');await gps.locate();
  expect(screen.getByLabelText('Latitude')).toHaveValue(21);
  fireEvent.click(screen.getByRole('button',{name:'Use Current Location'}));
  fireEvent.click(screen.getByRole('button',{name:'Cancel'}));await gps.locate();
  expect(screen.queryByRole('button',{name:'Save address'})).not.toBeInTheDocument();expect(create).not.toHaveBeenCalled();
});
it('preserves coordinates on postal edits and sends only changed fields',async()=>{
  const gps=device();const {update}=await open(true);
  fireEvent.change(screen.getByLabelText('Label'),{target:{value:'New label'}});save();
  await waitFor(()=>expect(update).toHaveBeenCalledWith('4',{label:'New label'}));
  expect(gps.request).not.toHaveBeenCalled();
});
