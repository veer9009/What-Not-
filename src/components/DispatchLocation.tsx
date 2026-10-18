import { useState } from 'react';
import type { Shop } from '../api/types';
import { setDispatchLocation } from '../api/sellers';
import { LocationPicker } from './LocationPicker';

export function DispatchLocation({shop,reload}:{shop:Shop;reload:()=>Promise<boolean>}){
  const [saved,setSaved]=useState(shop);const [editing,setEditing]=useState(false);const [notice,setNotice]=useState('');
  return <section className="panel" aria-label="Business dispatch location"><h2>Business / dispatch location</h2><p>{saved.dispatch_location_confirmed_at?'Dispatch location confirmed.':'Dispatch location not confirmed. Your products will not appear in nearby discovery until you confirm.'}</p><p>Use the actual place where products are prepared and dispatched. Logging in elsewhere never changes this point. Saving a new point changes marketplace availability.</p><p>Saved dispatch point: {saved.latitude}, {saved.longitude}</p>{notice&&<p role="status">{notice}</p>}{editing?<LocationPicker initial={{latitude:Number(saved.latitude),longitude:Number(saved.longitude)}} confirmLabel="Confirm dispatch location" onConfirm={async point=>{const updated=await setDispatchLocation(point);setSaved(updated);setEditing(false);setNotice('Dispatch location saved.');await reload();}}/>:<button className="btn btn-primary" onClick={()=>setEditing(true)}>{saved.dispatch_location_confirmed_at?'Update dispatch location':'Set dispatch location'}</button>}</section>;
}
