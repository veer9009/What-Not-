import { useCallback, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage, identifier } from '../api/client';
import { DashboardShell, PageTop, EmptyState } from '../components/Shared';
import { ErrorNotice, Loading } from '../components/ApiStates';
import { useAuth } from '../state/AuthContext';
import { useResource } from '../state/useResource';

interface Notice{id:string;kind:string;entity_type:string;entity_id:string;title:string;body:string;created_at:string;read_at:string|null}
export function NotificationsPage(){
  const {user}=useAuth();const role=user!.role.toLowerCase() as 'buyer'|'seller'|'admin';
  const [offset,setOffset]=useState(0);const [busy,setBusy]=useState(false);const pending=useRef(false);const [error,setError]=useState('');
  const load=useCallback(async()=>{const [items,count]=await Promise.all([
    api<Notice[]>(`/notifications?offset=${offset}&limit=50`),api<{count:number}>('/notifications/unread-count')]);return{items,count:count.count};},[offset]);
  const resource=useResource(load);
  async function read(id?:string){if(pending.current)return;pending.current=true;setBusy(true);setError('');
    try{await api(id?`/notifications/${identifier(id)}/read`:'/notifications/read-all',{method:'PATCH'});await resource.reload();}
    catch(reason){setError(errorMessage(reason));}finally{pending.current=false;setBusy(false);}}
  function destination(item:Notice){
    if(role==='admin')return '/admin/operations';
    if(item.entity_type==='order')return `/${role}/orders/${identifier(item.entity_id)}`;
    if(item.entity_type.startsWith('creative'))return `/${role}/creative`;
    return `/${role}/properties/requests`;
  }
  return <DashboardShell role={role}><PageTop eyebrow="Your updates" title="Notifications"/>{error&&<ErrorNotice message={error}/>}
    {resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:resource.data&&<>
      <p>{resource.data.count} unread</p><button className="btn btn-outline" disabled={busy||resource.data.count===0} onClick={()=>void read()}>Mark all as read</button>
      {resource.data.items.length?resource.data.items.map(item=><article className="panel" key={item.id}><h2>{item.title}</h2><p>{item.body}</p><p>{new Date(item.created_at).toLocaleString()}</p><div className="form-actions"><Link className="text-link" to={destination(item)}>View update</Link>{!item.read_at&&<button className="btn btn-outline" disabled={busy} onClick={()=>void read(item.id)}>Mark as read</button>}</div></article>):<EmptyState title="No notifications on this page" description="Order and marketplace updates will appear here."/>}
      <div className="form-actions"><button disabled={offset===0||busy} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous updates</button><button disabled={busy||resource.data.items.length<50} onClick={()=>setOffset(offset+50)}>More updates</button></div>
    </>}<button className="btn btn-outline" disabled={busy||resource.loading} onClick={()=>void resource.reload()}>Refresh notifications</button></DashboardShell>;
}
