import { useRef, useState } from 'react';

// Private pending drafts stay in the current tab, scoped to account and entity.
// Persist before transmission; storage failures must never trigger a fresh write.
export function useCreativeRecovery<T extends {key:string}>(scope:string,fields:string[]){
  const storageKey=`whatnot:creative-recovery:${scope}`;
  const [initial]=useState(()=>{
    try{
      const raw=sessionStorage.getItem(storageKey);
      if(!raw)return {value:null as T|null,error:''};
      const value=JSON.parse(raw);
      if(!value||typeof value.key!=='string'||!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(value.key)
          ||fields.some(field=>typeof value[field]!=='string'||!value[field].length||value[field].length>5000))throw new Error();
      return {value:Object.fromEntries(['key',...fields].map(field=>[field,value[field]])) as T,error:''};
    }catch{return {value:null as T|null,error:'Pending request recovery is unavailable. Restore this tab’s storage before submitting.'};}
  });
  const pending=useRef<T|null>(initial.value);
  const [error,setError]=useState(initial.error);
  function save(value:T){
    if(error)return false;
    try{sessionStorage.setItem(storageKey,JSON.stringify(value));pending.current=value;return true;}
    catch{setError('Could not save the recovery key. No new request was sent.');return false;}
  }
  function clear(){
    try{sessionStorage.removeItem(storageKey);pending.current=null;return true;}
    catch{setError('Could not clear the recovery key. Retry the original request after restoring tab storage.');return false;}
  }
  return {pending,error,save,clear};
}
