import { useState } from 'react';
import type { Shop } from '../api/types';
import { ApiError, errorMessage } from '../api/client';
import { setPublicDiscovery, revokePublicDiscovery } from '../api/sellers';
import { LocationPicker } from './LocationPicker';
import { ErrorNotice } from './ApiStates';

export function PublicDiscoveryLocation({shop,reload}:{shop:Shop;reload:()=>Promise<boolean>}){
  const [editing,setEditing]=useState(false),[consent,setConsent]=useState(false),[busy,setBusy]=useState(false);
  const [notice,setNotice]=useState(''),[error,setError]=useState('');
  return <section className="panel" aria-label="Public discovery location"><h2>Public discovery point</h2>
    <p>{shop.public_discovery_confirmed_at?'Public discovery point confirmed.':'No public discovery point confirmed. Products are excluded from live radius discovery until confirmation.'}</p>
    <p>Choose a business point you agree can be inferred by buyers from discovery results. This is separate from private dispatch. Do not choose a private home unless you intend that location to be discoverable. Delivery is still checked against your private dispatch point at checkout.</p>
    {notice&&<p role="status" className="success-note">{notice}</p>}{error&&<ErrorNotice message={error}/>}
    {editing?<><label className="public-point-consent"><input type="checkbox" checked={consent} onChange={event=>setConsent(event.target.checked)}/>I agree that this selected business point can be inferred publicly through discovery results.</label><LocationPicker confirmLabel="Confirm public discovery point" onDraftChange={()=>setConsent(false)} onConfirm={async point=>{
      if(!consent)throw new ApiError(422,'Confirm public-location consent after selecting your point.');
      await setPublicDiscovery(point);setEditing(false);setConsent(false);setNotice('Public discovery point confirmed.');await reload();
    }}/><button type="button" className="btn btn-outline" onClick={()=>{setEditing(false);setConsent(false);}}>Cancel</button></>:<button className="btn btn-primary" disabled={busy} onClick={()=>{setEditing(true);setConsent(false);setNotice('');setError('');}}>Set or change public discovery point</button>}
    {shop.public_discovery_confirmed_at&&!editing&&<button className="btn btn-outline" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{await revokePublicDiscovery();setNotice('Public discovery consent revoked.');await reload();}catch(reason){setError(errorMessage(reason));}finally{setBusy(false);}}}>Revoke public discovery consent</button>}
  </section>;
}
