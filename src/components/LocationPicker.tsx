import { useEffect, useRef, useState, type FormEvent } from 'react';
import { acquireLocation, LocationError, type Coordinates } from '../location/geolocation';
import { errorMessage } from '../api/client';
import { ErrorNotice } from './ApiStates';

export function LocationPicker({initial,onConfirm,confirmLabel,onDraftChange}:{initial?:Coordinates;onConfirm:(point:Coordinates)=>Promise<void>;confirmLabel:string;onDraftChange?:()=>void}){
  const [point,setPoint]=useState<Coordinates|undefined>(initial);
  const [accuracy,setAccuracy]=useState<number|null|undefined>();
  const [status,setStatus]=useState(''),[error,setError]=useState(''),[saving,setSaving]=useState(false),[locating,setLocating]=useState(false);
  const [area,setArea]=useState(''),[areaMessage,setAreaMessage]=useState('');
  const acquisition=useRef<AbortController|null>(null),version=useRef(0),mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;version.current++;acquisition.current?.abort();};},[]);
  function cancel(){version.current++;acquisition.current?.abort();acquisition.current=null;setLocating(false);setStatus('Location request cancelled.');}
  async function locate(){
    if(saving||acquisition.current)return;
    const request=new AbortController();acquisition.current=request;setLocating(true);
    const ticket=++version.current;onDraftChange?.();setPoint(undefined);setAccuracy(undefined);setStatus('Requesting location permission and detecting your position...');setError('');
    try{const result=await acquireLocation(undefined,request.signal);if(!mounted.current||ticket!==version.current)return;setPoint({latitude:result.latitude,longitude:result.longitude});setAccuracy(result.accuracyMeters);setStatus('Location acquired. Confirm this draft to use it.');}
    catch(reason){if(mounted.current&&ticket===version.current){setStatus('');setError(reason instanceof LocationError?reason.message:'Location is unavailable. Try again or select a saved address.');}}
    finally{if(acquisition.current===request){acquisition.current=null;if(mounted.current)setLocating(false);}}
  }
  async function submit(event:FormEvent){event.preventDefault();if(saving||acquisition.current)return;setError('');setStatus('');if(!point){setError('Use current location before confirming.');return;}try{setSaving(true);setStatus('Updating location...');await onConfirm(point);if(mounted.current)setStatus('Location available.');}catch(reason){if(mounted.current){setStatus('');setError(errorMessage(reason));}}finally{if(mounted.current)setSaving(false);}}
  function lookup(){const value=area.trim();if(!value||(/^[0-9]+$/.test(value)?!/^\d{6}$/.test(value):(value.match(/[a-z]/gi)?.length??0)<2)){setAreaMessage('Enter an area name of at least two letters or a valid 6-digit PIN.');return;}setAreaMessage('Area and PIN lookup is not available yet. Use current location or select a saved address where available.');}
  return <form className="product-form location-picker" onSubmit={submit} noValidate><p>Use your current location. Location and distances are approximate; detect again after moving.</p><button type="button" className="btn btn-outline btn-sm" disabled={saving||locating} onClick={()=>void locate()}>{locating?'Locating...':'Use current location'}</button>{locating&&<button type="button" className="btn btn-outline btn-sm" onClick={cancel}>Cancel location request</button>}<label>Enter area or PIN<input value={area} disabled={saving} onChange={event=>{version.current++;acquisition.current?.abort();acquisition.current=null;setLocating(false);setPoint(undefined);setAccuracy(undefined);setStatus('');setError('');onDraftChange?.();setArea(event.target.value);setAreaMessage('');}} maxLength={120}/></label><button type="button" className="btn btn-outline btn-sm" disabled={saving} onClick={lookup}>Find area or PIN</button>{areaMessage&&<p role="status">{areaMessage}</p>}{accuracy!==undefined&&<p>{accuracy===null?'The browser did not report usable accuracy. Verify this location before confirming.':`Browser-reported accuracy: about ${Math.ceil(accuracy)} m. This is an estimate, not a delivery guarantee.${accuracy>=1000?' This estimate spans at least 1 km; retry or choose a known saved address before confirming.':''}`}</p>}{status&&<p role="status">{status}</p>}{error&&<ErrorNotice message={error}/>}<button className="btn btn-primary" disabled={saving||locating}>{confirmLabel}</button></form>;
}
