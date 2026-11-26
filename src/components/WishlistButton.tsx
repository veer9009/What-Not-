import { useState } from 'react';
import { Heart } from 'lucide-react';
import { useWishlist } from '../state/WishlistContext';
import { errorMessage } from '../api/client';
export function WishlistButton({id,name}:{id:string;name:string}){
  const {data,loading,busy,setSaved}=useWishlist();const [error,setError]=useState('');
  const saved=!!data?.items.some(item=>item.product_id===id);
  return <><button type="button" className="btn btn-outline btn-sm" aria-pressed={saved} aria-label={`${saved?'Remove':'Save'} ${name} ${saved?'from':'to'} Wishlist`} disabled={loading||busy.has(id)||!data} onClick={()=>{setError('');void setSaved(id,!saved).catch(reason=>setError(errorMessage(reason)));}}><Heart size={18} aria-hidden="true" fill={saved?'currentColor':'none'}/>{saved?'Saved':'Save'}</button>{error&&<p role="alert">{error}</p>}</>;
}
