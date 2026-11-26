import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../state/AuthContext';
import { notificationChanged } from '../state/notificationEvents';
export function NotificationBell(){
  const {user,sessionKey}=useAuth();
  return user?<AccountBell key={`${user.id}:${sessionKey}`} role={user.role.toLowerCase()}/>:null;
}
function AccountBell({role}:{role:string}){
  const [count,setCount]=useState<number|null>(null);
  useEffect(()=>{
    let active=true;let version=0;
    const refresh=()=>{const ticket=++version;void api<{count:number}>('/notifications/unread-count').then(value=>{if(active&&ticket===version)setCount(value.count);}).catch(()=>{if(active&&ticket===version)setCount(null);});};
    refresh();window.addEventListener(notificationChanged,refresh);window.addEventListener('focus',refresh);
    const timer=window.setInterval(refresh,60000);
    return()=>{active=false;version++;window.clearInterval(timer);window.removeEventListener(notificationChanged,refresh);window.removeEventListener('focus',refresh);};
  },[]);
  return <Link className="btn btn-outline notification-bell" to={`/${role}/notifications`} aria-label={count===null?'Notifications':`Notifications, ${count} unread`}><Bell size={20} aria-hidden="true"/><span>Notifications</span>{count!==null&&<span aria-hidden="true">{count>99?'99+':count}</span>}</Link>;
}
