import { useEffect, useRef, useState, type FormEvent } from 'react';
import { acquireLocation, coordinates, LocationError, type Coordinates } from '../location/geolocation';
import { errorMessage } from '../api/client';
import { ErrorNotice, Field } from './ApiStates';

export function LocationPicker({initial,onConfirm,confirmLabel,onDraftChange}:{initial?:Coordinates;onConfirm:(point:Coordinates)=>Promise<void>;confirmLabel:string;onDraftChange?:()=>void}){
  const [latitude,setLatitude]=useState(initial?String(initial.latitude):'');
  const [longitude,setLongitude]=useState(initial?String(initial.longitude):'');
  const [status,setStatus]=useState('');const [error,setError]=useState('');const [saving,setSaving]=useState(false);
  const version=useRef(0);const mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;version.current++;};},[]);
  function edit(set:(value:string)=>void,value:string){version.current++;set(value);setStatus('');setError('');onDraftChange?.();}
  async function locate(){
    const ticket=++version.current;onDraftChange?.();setStatus('Requesting location permission...');setError('');
    try{const point=await acquireLocation();if(!mounted.current||ticket!==version.current)return;setLatitude(String(point.latitude));setLongitude(String(point.longitude));setStatus('Location acquired. Confirm this draft to use it.');}
    catch(reason){if(mounted.current&&ticket===version.current){setStatus('');setError(reason instanceof LocationError?reason.message:'Location is unavailable. Enter coordinates manually.');}}
  }
  async function submit(event:FormEvent){
    event.preventDefault();if(saving)return;version.current++;setError('');setStatus('');
    try{
      if(!latitude.trim()||!longitude.trim())throw new LocationError('invalid');
      const point=coordinates(Number(latitude),Number(longitude));setSaving(true);setStatus('Updating location...');
      await onConfirm(point);if(mounted.current)setStatus('Location available.');
    }catch(reason){if(mounted.current){setStatus('');setError(reason instanceof LocationError?reason.message:errorMessage(reason));}}
    finally{if(mounted.current)setSaving(false);}
  }
  return <form className="product-form location-picker" onSubmit={submit} noValidate><p>Use your current location, or enter coordinates manually as a technical fallback. Location and distances are approximate.</p><button type="button" className="btn btn-outline btn-sm" disabled={saving} onClick={()=>void locate()}>Use current location</button><fieldset disabled={saving} style={{border:0,padding:0,margin:0,minWidth:0}}><div className="form-grid"><Field label="Latitude" name="latitude" type="number" min={-90} max={90} step="0.000001" value={latitude} onChange={value=>edit(setLatitude,value)}/><Field label="Longitude" name="longitude" type="number" min={-180} max={180} step="0.000001" value={longitude} onChange={value=>edit(setLongitude,value)}/></div></fieldset>{status&&<p role="status">{status}</p>}{error&&<ErrorNotice message={error}/>}<button className="btn btn-primary" disabled={saving}>{confirmLabel}</button></form>;
}
