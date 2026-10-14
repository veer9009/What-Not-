import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { authApi } from '../api/auth';
import { ApiError, errorMessage, getAccessToken, onUnauthorized, setAccessToken } from '../api/client';
import type { Role, User } from '../api/types';
let expiresAt: number | null = null;
export const roleHome = (role: Role) => `/${role.toLowerCase()}`;
interface AuthState { user: User | null; loading: boolean; error: string; sessionKey: number; login: (email: string,password: string) => Promise<User>; logout: () => void }
const Context = createContext<AuthState | null>(null);
function identity(user: User) { if (!user || !['BUYER','SELLER','ADMIN'].includes(user.role)) throw new ApiError(0,'The API returned an invalid account. Please sign in again.'); return user; }
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,setUser]=useState<User|null>(null);
  const [loading,setLoading]=useState(Boolean(getAccessToken()));
  const [error,setError]=useState('');
  const [sessionKey,setSessionKey]=useState(0);
  const [deadline,setDeadline]=useState<number|null>(expiresAt);
  const operation=useRef(0);
  function clear(message='') { operation.current++; setAccessToken(null); expiresAt=null; setDeadline(null); setUser(null); setLoading(false); setError(message); setSessionKey(k=>k+1); }
  useEffect(() => {
    let active=true; const ticket=operation.current;
    const stop=onUnauthorized(()=>clear('Your session expired or is invalid. Please sign in again.'));
    if (getAccessToken()) {
      authApi.me().then(result=>{if(active&&ticket===operation.current){setUser(identity(result));setLoading(false);}}).catch(reason=>{if(active&&ticket===operation.current)clear(errorMessage(reason));});
    }
    return ()=>{active=false;operation.current++;stop();};
  },[]);
  useEffect(()=>{
    if (!deadline) return;
    const timer=window.setTimeout(()=>clear('Your session expired. Please sign in again.'),Math.max(0,deadline-Date.now()));
    return ()=>window.clearTimeout(timer);
  },[deadline]);
  async function login(email:string,password:string) {
    clear(); const ticket=operation.current; setLoading(true);
    try {
      const result=await authApi.login(email,password);
      if(ticket!==operation.current)throw new ApiError(0,'Your session changed. Please try again.');
      if (!result.access_token || result.token_type!=='bearer' || !Number.isFinite(result.expires_in) || result.expires_in<=0) throw new ApiError(0,'The API returned an invalid sign-in response.');
      setAccessToken(result.access_token);
      expiresAt=Date.now()+result.expires_in*1000; setDeadline(expiresAt);
      const current=identity(await authApi.me());
      if(ticket!==operation.current)throw new ApiError(0,'Your session changed. Please try again.');
      setUser(current); setLoading(false); setSessionKey(k=>k+1); return current;
    } catch(reason) { if(ticket===operation.current)clear(errorMessage(reason)); throw reason; }
  }
  return <Context.Provider value={{user,loading,error,sessionKey,login,logout:()=>clear()}}>{children}</Context.Provider>;
}
export function useAuth() { const value=useContext(Context); if(!value)throw new Error('AuthProvider is required'); return value; }
