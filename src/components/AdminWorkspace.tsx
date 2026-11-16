import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { DashboardShell } from './Shared';
import '../styles/admin-workspace.css';

export function AdminWorkspace({children}:{children:ReactNode}) {
  return <DashboardShell role="admin"><div className="admin-workspace">{children}</div></DashboardShell>;
}

export function AdminReasonField({label,helpId,help,value,disabled,onChange}:{label:string;helpId:string;help:string;value:string;disabled:boolean;onChange:(value:string)=>void}) {
  return <section className="panel admin-reason-panel">
    <label className="admin-field">{label}<textarea aria-describedby={helpId} maxLength={1000} rows={4} value={value} disabled={disabled} onChange={event=>onChange(event.target.value)}/></label>
    <p className="admin-help" id={helpId}>{help}</p>
  </section>;
}

interface Confirmation {title:string;description:string;label:string;onConfirm:()=>void}
export function useAdminConfirmation() {
  const [confirmation,setConfirmation]=useState<Confirmation|null>(null);
  const origin=useRef<HTMLElement|null>(null);
  const id=useId();
  useEffect(()=>{if(!confirmation&&origin.current){origin.current.focus();origin.current=null;}},[confirmation]);
  function request(action:Confirmation) {
    origin.current=document.activeElement instanceof HTMLElement?document.activeElement:null;
    setConfirmation(action);
  }
  const content=confirmation&&<section className="panel admin-confirmation" role="alertdialog" aria-modal="false" aria-labelledby={`${id}-title`} aria-describedby={`${id}-detail`}>
    <h2 id={`${id}-title`}>{confirmation.title}</h2>
    <p id={`${id}-detail`}>{confirmation.description}</p>
    <div className="admin-actions">
      <button type="button" className="btn btn-outline" autoFocus onClick={()=>setConfirmation(null)}>Cancel confirmation</button>
      <button type="button" className="btn btn-primary" onClick={()=>{const action=confirmation;setConfirmation(null);action.onConfirm();}}>{confirmation.label}</button>
    </div>
  </section>;
  return {pending:confirmation!==null,request,content};
}
