import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { wishlistApi } from '../api/wishlist';
import { useAuth } from './AuthContext';
import { useResource } from './useResource';
import type { Wishlist } from '../api/wishlist';
interface WishlistState { data:Wishlist|null; loading:boolean; error:string; busy:ReadonlySet<string>; reload:()=>Promise<boolean>; setSaved:(id:string,saved:boolean)=>Promise<void> }
const fallback:WishlistState={data:null,loading:false,error:'',busy:new Set(),reload:async()=>false,setSaved:async()=>{throw Error('Sign in to save products.');}};
const Context=createContext<WishlistState>(fallback);
export function WishlistProvider({children}:{children:ReactNode}){
  const {user,sessionKey}=useAuth();
  return <WishlistSession key={user?`${user.id}:${sessionKey}`:'anonymous'} enabled={user?.role==='BUYER'}>{children}</WishlistSession>;
}
function WishlistSession({children,enabled}:{children:ReactNode;enabled:boolean}){
  const load=useCallback(()=>enabled?wishlistApi.list():Promise.resolve({items:[],count:0}),[enabled]);
  const resource=useResource(load);const pending=useRef(new Set<string>());const [busy,setBusy]=useState<ReadonlySet<string>>(new Set());
  async function setSaved(id:string,saved:boolean){
    if(!enabled)throw Error('Sign in as a buyer to save products.');
    if(pending.current.has(id))return;
    pending.current.add(id);setBusy(new Set(pending.current));
    try{await wishlistApi.set(id,saved);await resource.reload();}
    finally{pending.current.delete(id);setBusy(new Set(pending.current));}
  }
  return <Context.Provider value={{...resource,busy,setSaved}}>{children}</Context.Provider>;
}
export function useWishlist(){return useContext(Context);}
export function WishlistCount(){const {data}=useWishlist();return data?<span aria-label={`${data.count} saved products`}>{data.count}</span>:null;}
