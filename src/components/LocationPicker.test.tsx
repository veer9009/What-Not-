import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { LocationPicker } from './LocationPicker';

afterEach(()=>vi.unstubAllGlobals());
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
