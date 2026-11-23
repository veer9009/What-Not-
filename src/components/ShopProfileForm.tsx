import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, errorMessage } from '../api/client';
import { sellersApi, setDispatchLocation, setPublicDiscovery } from '../api/sellers';
import type { Shop, ShopInput } from '../api/types';
import { acquireLocation, coordinates, LocationError } from '../location/geolocation';
import { useMounted } from '../state/useMounted';
import { CollectionNotice } from './LegalNavigation';
import { ErrorNotice, Field } from './ApiStates';
import { PageTop } from './Shared';

export function ShopProfileForm({shop,reload,saved,onPartialSave}:{shop:Shop|null;reload:()=>Promise<boolean>;saved:()=>void;onPartialSave:(shop:Shop)=>void}) {
  const [form,setForm]=useState<ShopInput>(shop?{shop_name:shop.shop_name,description:shop.description,phone:shop.phone,latitude:shop.latitude,longitude:shop.longitude}:{shop_name:'',description:null,phone:'',latitude:'',longitude:''});
  const [error,setError]=useState(''),[fields,setFields]=useState<Record<string,string>>({}),[busy,setBusy]=useState(false);
  const [locating,setLocating]=useState(false),[locationStatus,setLocationStatus]=useState(''),[locationError,setLocationError]=useState('');
  const [confirmed,setConfirmed]=useState(false),[sharePublic,setSharePublic]=useState(false);
  const savedShop=useRef(shop),saving=useRef(false),acquisition=useRef<AbortController|null>(null),mounted=useMounted();
  useEffect(()=>()=>{acquisition.current?.abort();acquisition.current=null;},[]);
  const samePoint=()=>Boolean(savedShop.current&&Number(form.latitude)===Number(savedShop.current.latitude)&&Number(form.longitude)===Number(savedShop.current.longitude));
  const needsConfirmation=!savedShop.current?.dispatch_location_confirmed_at||!samePoint();
  const needsPublicConsent=needsConfirmation||!savedShop.current?.public_discovery_confirmed_at||savedShop.current.public_discovery_consent_version!=='public-discovery-v1';
  function resetConsent(){setConfirmed(false);setSharePublic(false);}
  function set(key:keyof ShopInput,value:string){
    if(key==='latitude'||key==='longitude'){
      acquisition.current?.abort();acquisition.current=null;setLocating(false);setLocationStatus('');setLocationError('');resetConsent();
    }
    setForm(current=>({...current,[key]:value}));
  }
  async function locate(){
    if(saving.current||acquisition.current)return;
    const request=new AbortController();acquisition.current=request;setLocating(true);setLocationError('');resetConsent();
    setLocationStatus('Finding your current location...');
    try{
      const point=await acquireLocation(undefined,request.signal);
      if(!mounted.current||acquisition.current!==request)return;
      setForm(current=>({...current,latitude:String(point.latitude),longitude:String(point.longitude)}));
      setFields(current=>({...current,latitude:'',longitude:''}));
      setLocationStatus('Shop location selected. Confirm it below, then save. Nothing has been saved or publicly shared.');
    }catch(reason){if(mounted.current&&acquisition.current===request){setLocationStatus('');setLocationError(reason instanceof LocationError?reason.message:'Location is unavailable. Use the manual fallback.');}}
    finally{if(acquisition.current===request){acquisition.current=null;if(mounted.current)setLocating(false);}}
  }
  async function submit(event:FormEvent){
    event.preventDefault();if(saving.current||acquisition.current)return;setError('');setFields({});
    let persisted=false;
    try{
      if(!form.latitude.trim()||!form.longitude.trim())throw new LocationError('invalid');
      const point=coordinates(Number(form.latitude),Number(form.longitude));
      if(needsConfirmation&&!confirmed)throw new ApiError(422,'Please confirm this is where you send products from.');
      saving.current=true;setBusy(true);
      const body={...form,description:form.description?.trim()||null};
      savedShop.current=await (savedShop.current?sellersApi.update(body):sellersApi.create(body));
      persisted=true;
      if(!mounted.current)return;
      if(needsConfirmation){savedShop.current=await setDispatchLocation(point);if(!mounted.current)return;}
      // The saved private point becomes public only after this specific opt-in.
      if(sharePublic){savedShop.current=await setPublicDiscovery(point);if(!mounted.current)return;}
      setLocationStatus('');setLocationError('');setConfirmed(false);setSharePublic(false);saved();
      const refreshed=await reload();
      if(mounted.current&&!refreshed)setError('Your shop was saved. Refresh this page to see its current discovery status.');
    }catch(reason){
      if(mounted.current){
        if(persisted&&savedShop.current)onPartialSave(savedShop.current);
        setError((persisted?'Your profile was saved. Retry to finish shop location setup. ':'')+(reason instanceof LocationError?reason.message:errorMessage(reason)));
        if(reason instanceof ApiError)setFields(reason.fields);
      }
    }finally{saving.current=false;if(mounted.current)setBusy(false);}
  }
  return <>
    <PageTop eyebrow="Shop details" title={shop?'Seller profile':'Create seller profile'}/>
    <CollectionNotice label="Seller">Your dispatch location is private. Only a point you explicitly agree to share is used for public discovery.</CollectionNotice>
    <p>Set your shop location once. We reuse it for every product.</p>
    {shop&&<p>{shop.is_verified?'Verified seller profile':'Profile not yet verified'}</p>}
    <form className="product-form" onSubmit={submit}>
      <fieldset className="product-form" disabled={busy} style={{border:0,padding:0,margin:0,minWidth:0}}>
        <section><div className="form-grid">
          <Field label="Shop name" name="shop_name" value={form.shop_name} onChange={value=>set('shop_name',value)} required maxLength={120} error={fields.shop_name}/>
          <Field label="Phone" name="phone" value={form.phone} onChange={value=>set('phone',value)} required maxLength={32} error={fields.phone}/>
          <label className="full">Description<textarea maxLength={5000} value={form.description??''} onChange={event=>set('description',event.target.value)} aria-invalid={Boolean(fields.description)}/>{fields.description&&<small>{fields.description}</small>}</label>
        </div></section>
        <section aria-label="Shop location"><h2>Where do you send products from?</h2>
          <p id="profile-location-help">Choose your actual shop location. It may differ from your current device location.</p>
          <button type="button" className="btn btn-outline btn-sm" aria-describedby="profile-location-help" disabled={locating} onClick={()=>void locate()}>{locating?'Detecting location...':'Use Current Location'}</button>
          {locationStatus&&<p role="status">{locationStatus}</p>}{locationError&&<ErrorNotice message={locationError}/>}
          <details><summary>Enter coordinates manually</summary><p>Use this fallback if device location is unavailable. A PIN code alone cannot identify an exact location.</p><div className="form-grid">
            <Field label="Latitude" name="latitude" value={form.latitude} onChange={value=>set('latitude',value)} type="number" step="0.000001" min={-90} max={90} error={fields.latitude}/>
            <Field label="Longitude" name="longitude" value={form.longitude} onChange={value=>set('longitude',value)} type="number" step="0.000001" min={-180} max={180} error={fields.longitude}/>
          </div></details>
          {!needsConfirmation&&<p>Saved dispatch location confirmed. New products use it automatically.</p>}
          {needsConfirmation&&<label className="public-point-consent"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>I confirm this is where I send products from.</label>}
          {needsPublicConsent&&<><p>Nearby discovery needs a public shop point. If this is a private home, leave this unchecked and choose a different public point below after saving.</p><label className="public-point-consent"><input type="checkbox" checked={sharePublic} onChange={event=>setSharePublic(event.target.checked)}/>I agree to use this point for public discovery. Buyers may infer this location.</label></>}
          {shop&&!samePoint()&&<p>Changing this location pauses discovery until you give permission for a public point again.</p>}
        </section>
      </fieldset>
      {error&&<ErrorNotice message={error}/>}<div className="form-actions"><Link className="btn btn-outline" to="/seller" aria-disabled={busy} onClick={event=>{if(busy)event.preventDefault();}}>Back to dashboard</Link><button className="btn btn-primary" disabled={busy||locating}>Save profile</button></div>
    </form>
  </>;
}
