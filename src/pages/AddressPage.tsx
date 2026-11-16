import { CollectionNotice } from '../components/LegalNavigation';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { MapPin } from 'lucide-react';
import { DashboardShell, EmptyState, PageTop } from '../components/Shared';
import { ErrorNotice, Field, Loading } from '../components/ApiStates';
import { addressesApi } from '../api/addresses';
import { ApiError, errorMessage } from '../api/client';
import type { Address, AddressInput } from '../api/types';
import { useResource } from '../state/useResource';
import { useAuth } from '../state/AuthContext';
import { acquireLocation, coordinates, LocationError } from '../location/geolocation';
import '../styles/buyer-checkout.css';
const blank:AddressInput={label:'',address_line1:'',address_line2:null,city:'',state:'',pincode:'',latitude:'',longitude:'',is_default:false};
export function AddressPage(){
  const {user}=useAuth();const role=user!.role.toLowerCase() as 'buyer'|'seller'|'admin';const resource=useResource(addressesApi.list);const [editing,setEditing]=useState<Address|null|undefined>();const [error,setError]=useState('');const [notice,setNotice]=useState('');const [fields,setFields]=useState<Record<string,string>>({});const [busy,setBusy]=useState(false);
  async function save(body:AddressInput){if(busy)return;setBusy(true);setError('');setNotice('');setFields({});try{if(editing){const changed=Object.fromEntries(Object.entries(body).filter(([key,value])=>value!==editing[key as keyof AddressInput]));if(!Object.keys(changed).length){setNotice('No address changes to save.');return;}await addressesApi.update(editing.id,changed);}else await addressesApi.create(body);setEditing(undefined);const refreshed=await resource.reload();setNotice(refreshed?'Address saved.':'Address saved. Refresh to see the current address list.');}catch(reason){setError(errorMessage(reason));if(reason instanceof ApiError)setFields(reason.fields);}finally{setBusy(false);}}
  async function makeDefault(id:string){if(busy)return;setBusy(true);setError('');setNotice('');try{await addressesApi.default(id);const refreshed=await resource.reload();setNotice(refreshed?'Default address updated.':'Default saved. Refresh to see the current list.');}catch(reason){setError(errorMessage(reason));}finally{setBusy(false);}}
  return <DashboardShell role={role}><PageTop eyebrow="Your account" title="Your addresses" action={<button className="btn btn-primary" disabled={busy} onClick={()=>{setEditing(null);setError('');setFields({});}}>Add address</button>}/><p className="approval-help">Addresses referenced by historical orders keep their delivery fields. Create a replacement address if those fields must change. Labels and default selection can still be updated.</p>{error&&<ErrorNotice message={error}/>} {notice&&<p className="success-note" role="status">{notice}</p>}{editing!==undefined&&<AddressForm key={editing?.id??'new'} address={editing??undefined} busy={busy} fields={fields} save={save} cancel={()=>{setEditing(undefined);setError('');}}/>}{resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:resource.data?.length?<div className="resource-list">{resource.data.map(address=><article className="panel" key={address.id}><h2>{address.label}</h2><p>{address.address_line1}</p>{address.address_line2&&<p>{address.address_line2}</p>}<p>{address.city}, {address.state} {address.pincode}</p>{address.is_default&&<p className="status approved">Default address</p>}<div className="form-actions"><button className="btn btn-outline btn-sm" disabled={busy} onClick={()=>{setEditing(address);setError('');setFields({});}}>Edit address</button>{!address.is_default&&<button className="btn btn-primary btn-sm" disabled={busy} onClick={()=>void makeDefault(address.id)}>Make default</button>}</div></article>)}</div>:<EmptyState title="No addresses yet" description="Add your own address to your account."/>}</DashboardShell>;
}
function AddressForm({address,busy,fields,save,cancel}:{address?:Address;busy:boolean;fields:Record<string,string>;save:(body:AddressInput)=>Promise<void>;cancel:()=>void}){
  const [form,setForm]=useState<AddressInput>(address?Object.fromEntries(Object.keys(blank).map(key=>[key,address[key as keyof AddressInput]])) as unknown as AddressInput:{...blank});
  const [locating,setLocating]=useState(false),[advanced,setAdvanced]=useState(false);
  const [locationError,setLocationError]=useState(''),[locationStatus,setLocationStatus]=useState('');
  const acquisition=useRef<AbortController|null>(null);
  useEffect(()=>()=>{acquisition.current?.abort();acquisition.current=null;},[]);
  const inputs=[['label','Label',80],['address_line1','Address line 1',255],['address_line2','Address line 2',255],['city','City',120],['state','State',120],['pincode','PIN code',20]] as const;
  function editCoordinate(key:'latitude'|'longitude',value:string){
    acquisition.current?.abort();acquisition.current=null;setLocating(false);
    setLocationError('');setLocationStatus('');setForm(current=>({...current,[key]:value}));
  }
  async function locate(){
    if(busy||acquisition.current)return;
    const request=new AbortController();acquisition.current=request;
    setLocating(true);setLocationError('');setLocationStatus('Detecting your current location...');
    try{
      const point=await acquireLocation(undefined,request.signal);
      if(acquisition.current!==request)return;
      setForm(current=>({...current,latitude:String(point.latitude),longitude:String(point.longitude)}));
      setLocationStatus(`Location detected. Review your postal details, then save your address.${point.accuracyMeters===null?' Browser accuracy is unavailable.':` Browser-reported accuracy: about ${Math.ceil(point.accuracyMeters)} m.`}`);
    }catch(reason){
      if(acquisition.current!==request)return;
      setLocationStatus('');setAdvanced(true);
      setLocationError(reason instanceof LocationError?reason.message:'Location is unavailable. Enter coordinates in Advanced location details.');
    }finally{if(acquisition.current===request){acquisition.current=null;setLocating(false);}}
  }
  function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();if(busy||locating)return;
    try{
      if(!form.latitude.trim()||!form.longitude.trim())throw new LocationError('invalid');
      coordinates(Number(form.latitude),Number(form.longitude));
    }catch{setAdvanced(true);setLocationError('Enter a valid latitude (-90 to 90) and longitude (-180 to 180), or use current location.');return;}
    if(!event.currentTarget.reportValidity())return;
    setLocationError('');void save({...form,address_line2:form.address_line2?.trim()||null});
  }
  return <form className="product-form address-form" aria-label={address?'Edit saved address':'Create saved address'} onSubmit={submit} noValidate><section>
    <h2>{address?'Edit address':'Add address'}</h2>
    <CollectionNotice label="Address">Postal details and coordinates support discovery and checkout. The assigned seller can request your name, phone and postal address during eligible fulfilment/dispute states. Historical orders retain address details. Saving this address does not confirm sharing your precise delivery point with a seller; review and optionally confirm it in each order's details.</CollectionNotice>
    <div className="address-location"><h3>Delivery location</h3><p>Use GPS to fill your location. Enter your postal address below; GPS does not fill street details or your PIN code.</p>
      <button type="button" className="btn btn-outline" disabled={busy||locating} onClick={()=>void locate()}><MapPin size={18}/>{locating?'Detecting location...':'Use Current Location'}</button>
      {locationStatus&&<p role="status" className={locating?'approval-help':'success-note'}>{locationStatus}</p>}
      {locationError&&<ErrorNotice message={locationError}/>}
    </div>
    <div className="form-grid address-postal-fields">{inputs.map(([key,label,length])=><Field key={key} label={label} name={key} value={form[key]??''} onChange={value=>setForm(current=>({...current,[key]:value}))} maxLength={length} required={key!=='address_line2'} error={fields[key]}/>)}</div>
    <details className="address-advanced" open={advanced||Boolean(fields.latitude||fields.longitude)} onToggle={event=>setAdvanced(event.currentTarget.open)}>
      <summary>Advanced location details</summary><p>Optional manual entry if GPS is unavailable or needs correction. A valid location is required to save this address.</p>
      <div className="form-grid">{(['latitude','longitude'] as const).map(key=><Field key={key} label={key==='latitude'?'Latitude':'Longitude'} name={key} type="number" step="0.000001" min={key==='latitude'?-90:-180} max={key==='latitude'?90:180} value={form[key]} onChange={value=>editCoordinate(key,value)} error={fields[key]}/>)}</div>
    </details>
    <p className="approval-help">Select this saved address explicitly when discovering products or checking out. Your current device location may differ from the delivery address.</p>
    <label className="checkbox-field"><input type="checkbox" checked={form.is_default} onChange={event=>setForm(current=>({...current,is_default:event.target.checked}))}/>Default address</label>
    </section><div className="form-actions"><button className="btn btn-outline" type="button" disabled={busy} onClick={cancel}>Cancel</button><button className="btn btn-primary" disabled={busy||locating}>{busy?'Saving address...':'Save address'}</button></div></form>;
}
