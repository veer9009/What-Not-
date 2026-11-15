import { useEffect, useRef, useState, type FormEvent } from 'react';
import { acquireLocation, coordinates, LocationError, type Coordinates } from '../location/geolocation';
import { errorMessage } from '../api/client';
import { ErrorNotice, Field } from './ApiStates';

export function LocationPicker({initial,onConfirm,confirmLabel,onDraftChange}:{initial?:Coordinates;onConfirm:(point:Coordinates)=>Promise<void>;confirmLabel:string;onDraftChange?:()=>void}){
  const [latitude,setLatitude]=useState(initial?String(initial.latitude):'');
  const [longitude,setLongitude]=useState(initial?String(initial.longitude):'');
  const [accuracy,setAccuracy]=useState<number|null|undefined>(undefined);
  const [status,setStatus]=useState('');const [error,setError]=useState('');const [saving,setSaving]=useState(false);
  const [locating,setLocating]=useState(false);const acquisition=useRef<AbortController|null>(null);
  const version=useRef(0);const mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;version.current++;acquisition.current?.abort();};},[]);
  function edit(set:(value:string)=>void,value:string){version.current++;acquisition.current?.abort();acquisition.current=null;setLocating(false);setAccuracy(undefined);set(value);setStatus('');setError('');onDraftChange?.();}
  async function locate(){
    if(saving||acquisition.current)return;
    const request=new AbortController();acquisition.current=request;setLocating(true);
    const ticket=++version.current;onDraftChange?.();setAccuracy(undefined);setLatitude('');setLongitude('');setStatus('Requesting location permission and detecting your position...');setError('');
    try{const point=await acquireLocation(undefined,request.signal);if(!mounted.current||ticket!==version.current)return;setLatitude(String(point.latitude));setLongitude(String(point.longitude));setAccuracy(point.accuracyMeters);setStatus('Location acquired. Confirm this draft to use it.');}
    catch(reason){if(mounted.current&&ticket===version.current){setStatus('');setError(reason instanceof LocationError?reason.message:'Location is unavailable. Enter coordinates manually.');}}
    finally{if(acquisition.current===request){acquisition.current=null;if(mounted.current)setLocating(false);}}
  }
  async function submit(event:FormEvent){
    event.preventDefault();if(saving||acquisition.current)return;version.current++;setError('');setStatus('');
    try{
      if(!latitude.trim()||!longitude.trim())throw new LocationError('invalid');
      const point=coordinates(Number(latitude),Number(longitude));setSaving(true);setStatus('Updating location...');
      await onConfirm(point);if(mounted.current)setStatus('Location available.');
    }catch(reason){if(mounted.current){setStatus('');setError(reason instanceof LocationError?reason.message:errorMessage(reason));}}
    finally{if(mounted.current)setSaving(false);}
  }
  return <form className="product-form location-picker" onSubmit={submit} noValidate><p>Use your current location, or enter coordinates manually as a technical fallback. Location and distances are approximate. This is a one-time location; detect again after moving.</p><button type="button" className="btn btn-outline btn-sm" disabled={saving||locating} onClick={()=>void locate()}>{locating?'Locating...':'Use current location'}</button><fieldset disabled={saving} style={{border:0,padding:0,margin:0,minWidth:0}}><div className="form-grid"><Field label="Latitude" name="latitude" type="number" min={-90} max={90} step="0.000001" value={latitude} onChange={value=>edit(setLatitude,value)}/><Field label="Longitude" name="longitude" type="number" min={-180} max={180} step="0.000001" value={longitude} onChange={value=>edit(setLongitude,value)}/></div></fieldset>{accuracy!==undefined&&<p>{accuracy===null?'The browser did not report usable accuracy. Verify this point before confirming.':`Browser-reported accuracy: about ${Math.ceil(accuracy)} m. This is an estimate, not a delivery guarantee.${accuracy>=1000?' This estimate spans at least 1 km; retry or choose a known saved address before confirming.':''}`}</p>}{status&&<p role="status">{status}</p>}{error&&<ErrorNotice message={error}/>}<button className="btn btn-primary" disabled={saving||locating}>{confirmLabel}</button></form>;
}
