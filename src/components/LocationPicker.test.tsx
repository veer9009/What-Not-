import { render, screen, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { LocationPicker } from './LocationPicker';

afterEach(()=>vi.unstubAllGlobals());
it('displays broad device accuracy without sending it as a coordinate or retaining it after manual edits',async()=>{
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(success:PositionCallback)=>success({coords:{latitude:19,longitude:72,accuracy:1800.25}} as GeolocationPosition)}});
  const save=vi.fn().mockResolvedValue(undefined);
  render(<LocationPicker onConfirm={save} confirmLabel="Use point"/>);
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  expect(screen.getByText(/browser-reported accuracy: about 1801 m/i)).toHaveTextContent(/at least 1 km/i);
  await userEvent.click(screen.getByRole('button',{name:'Use point'}));
  expect(save).toHaveBeenCalledWith({latitude:19,longitude:72});
  expect(screen.getByText(/browser-reported accuracy/i)).toBeInTheDocument();
  await userEvent.clear(screen.getByLabelText('Latitude'));
  expect(screen.queryByText(/browser-reported accuracy/i)).not.toBeInTheDocument();
});
it('labels missing accuracy honestly and clears it while requesting a new position',async()=>{
  let success!:PositionCallback;
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(callback:PositionCallback)=>{success=callback;}}});
  render(<LocationPicker onConfirm={async()=>{}} confirmLabel="Use point"/>);
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  await act(async()=>success({coords:{latitude:19,longitude:72}} as GeolocationPosition));
  expect(screen.getByText(/browser did not report usable accuracy/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  expect(screen.queryByText(/browser did not report usable accuracy/i)).not.toBeInTheDocument();
});
it('never requests on mount and confirms only the manually chosen point', async()=>{
  const getCurrentPosition=vi.fn();vi.stubGlobal('navigator',{geolocation:{getCurrentPosition}});
  const save=vi.fn().mockResolvedValue(undefined);
  render(<LocationPicker onConfirm={save} confirmLabel="Use for discovery"/>);
  expect(getCurrentPosition).not.toHaveBeenCalled();
  await userEvent.type(screen.getByLabelText('Latitude'),'19');
  await userEvent.type(screen.getByLabelText('Longitude'),'72');
  expect(save).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button',{name:'Use for discovery'}));
  expect(save).toHaveBeenCalledWith({latitude:19,longitude:72});
});
it('keeps acquired GPS as a draft until explicitly confirmed', async()=>{
  let success!:PositionCallback;
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(callback:PositionCallback)=>{success=callback;}}});
  const save=vi.fn().mockResolvedValue(undefined);
  render(<LocationPicker onConfirm={save} confirmLabel="Confirm dispatch location"/>);
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  expect(screen.getByRole('status')).toHaveTextContent(/requesting/i);
  await act(async()=>success({coords:{latitude:19,longitude:72}} as GeolocationPosition));
  expect(screen.getByLabelText('Latitude')).toHaveValue(19);
  expect(save).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button',{name:'Confirm dispatch location'}));
  expect(save).toHaveBeenCalledWith({latitude:19,longitude:72});
});
it('ignores late GPS after a newer manual draft', async()=>{
  let success!:PositionCallback;
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(callback:PositionCallback)=>{success=callback;}}});
  render(<LocationPicker onConfirm={async()=>{}} confirmLabel="Use point"/>);
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  await userEvent.type(screen.getByLabelText('Latitude'),'12');
  await act(async()=>success({coords:{latitude:19,longitude:72}} as GeolocationPosition));
  expect(screen.getByLabelText('Latitude')).toHaveValue(12);
});
it('reports unsupported geolocation and retains manual entry', async()=>{
  vi.stubGlobal('navigator',{geolocation:undefined});
  render(<LocationPicker onConfirm={async()=>{}} confirmLabel="Use point"/>);
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  expect(screen.getByRole('alert')).toHaveTextContent(/unavailable/i);
  expect(screen.getByLabelText('Latitude')).toBeEnabled();
});
it('rejects empty coordinates without treating them as zero', async()=>{
  const save=vi.fn();render(<LocationPicker onConfirm={save} confirmLabel="Use point"/>);
  await userEvent.click(screen.getByRole('button',{name:'Use point'}));
  expect(screen.getByRole('alert')).toHaveTextContent(/valid latitude/i);
  expect(save).not.toHaveBeenCalled();
});
it('prevents newer draft edits while confirmation is pending', async()=>{
  let finish!:()=>void;
  render(<LocationPicker initial={{latitude:19,longitude:72}} onConfirm={()=>new Promise(resolve=>{finish=resolve;})} confirmLabel="Confirm"/>);
  await userEvent.click(screen.getByRole('button',{name:'Confirm'}));
  expect(screen.getByLabelText('Latitude')).toBeDisabled();
  expect(screen.getByLabelText('Longitude')).toBeDisabled();
  await act(async()=>finish());
  expect(screen.getByLabelText('Latitude')).toBeEnabled();
});
it('blocks stale confirmation and repeated GPS requests while detecting',async()=>{
  const getCurrentPosition=vi.fn();vi.stubGlobal('navigator',{geolocation:{getCurrentPosition}});
  const save=vi.fn();
  render(<LocationPicker initial={{latitude:19,longitude:72}} onConfirm={save} confirmLabel="Use point"/>);
  fireEvent.click(screen.getByRole('button',{name:'Use current location'}));
  expect(screen.getByRole('button',{name:/locating/i})).toBeDisabled();
  expect(screen.getByRole('button',{name:'Use point'})).toBeDisabled();
  expect(screen.getByLabelText('Latitude')).toHaveValue(null);
  fireEvent.submit(screen.getByRole('button',{name:'Use point'}).closest('form')!);
  expect(save).not.toHaveBeenCalled();
  expect(getCurrentPosition).toHaveBeenCalledTimes(1);
});
it.each([[1,/permission was denied/i],[2,/position is unavailable/i],[3,/timed out/i]])('shows browser error %s and permits manual fallback',async(code,message)=>{
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(_success:PositionCallback,error:PositionErrorCallback)=>error({code,message:'private diagnostic'} as GeolocationPositionError)}});
  const save=vi.fn().mockResolvedValue(undefined);
  render(<LocationPicker onConfirm={save} confirmLabel="Use point"/>);
  await userEvent.click(screen.getByRole('button',{name:'Use current location'}));
  expect(screen.getByRole('alert')).toHaveTextContent(message);
  expect(screen.queryByText('private diagnostic')).not.toBeInTheDocument();
  await userEvent.type(screen.getByLabelText('Latitude'),'0');
  await userEvent.type(screen.getByLabelText('Longitude'),'0');
  await userEvent.click(screen.getByRole('button',{name:'Use point'}));
  expect(save).toHaveBeenCalledWith({latitude:0,longitude:0});
});
