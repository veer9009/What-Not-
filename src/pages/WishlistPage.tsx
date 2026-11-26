import { useState } from 'react';
import { DashboardShell, PageTop, EmptyState } from '../components/Shared';
import { Loading, ErrorNotice } from '../components/ApiStates';
import { ListingImage } from '../components/ListingImage';
import { useWishlist } from '../state/WishlistContext';
import { useDemo } from '../state/DemoContext';
import { errorMessage, identifier } from '../api/client';
export function WishlistPage(){
  const wishlist=useWishlist();const {state,dispatch}=useDemo();const [error,setError]=useState('');const [added,setAdded]=useState('');
  function remove(id:string){setError('');void wishlist.setSaved(id,false).catch(reason=>setError(errorMessage(reason)));}
  return <DashboardShell role="buyer"><PageTop eyebrow="Saved products" title="Wishlist"/><p>Saved products stay with your account across devices. Saving does not reserve stock. Saved properties remain in their own section.</p>{error&&<ErrorNotice message={error}/>}{added&&<p role="status">{added} added to your cart.</p>}{wishlist.loading?<Loading/>:wishlist.error?<ErrorNotice message={wishlist.error} retry={()=>void wishlist.reload()}/>:<><p>{wishlist.data?.count??0} saved products</p>{wishlist.data?.items.length?<div className="product-grid buyer-grid">{wishlist.data.items.map(item=>{
    const p=item.available?item.product:null;let valid=true;try{identifier(item.product_id);if(p)identifier(p.seller_id);}catch{valid=false;}
    const cart=state.cart.find(entry=>entry.productId===`backend:${item.product_id}`);const recovering=state.placements?.some(attempt=>attempt.cartIds.includes(`backend:${item.product_id}`));
    return <article className="product-card" key={item.product_id}>{p?<><div className="product-image"><ListingImage src={p.image_url} alt={p.name}/></div><div className="product-body"><h2>{p.name}</h2><p>{p.shop_name}{p.is_verified?' · Verified seller':''}</p><strong>₹{p.price}</strong><p>{p.stock_quantity>0?`${p.stock_quantity} in stock`:'Out of stock'}</p><div className="form-actions"><button className="btn btn-primary" disabled={!valid||recovering||cart?.placementUncertain||(cart?.quantity??0)>=p.stock_quantity} aria-label={`Add ${p.name} to cart`} onClick={()=>{dispatch({type:'cart/add-discovered',product:p});setAdded(p.name);}}>Add to Cart</button><button className="btn btn-outline" disabled={wishlist.busy.has(item.product_id)} aria-label={`Remove ${p.name} from Wishlist`} onClick={()=>remove(item.product_id)}>Remove</button></div></div></>:<div className="product-body"><h2>Product unavailable</h2><p>This saved product is no longer available to view.</p><button className="btn btn-outline" disabled={wishlist.busy.has(item.product_id)} aria-label="Remove unavailable product from Wishlist" onClick={()=>remove(item.product_id)}>Remove</button></div>}</article>;
  })}</div>:<EmptyState title="Your Wishlist is empty" description="Use the heart on a product to save it for later."/>}</>}<button className="btn btn-outline" disabled={wishlist.loading} onClick={()=>void wishlist.reload()}>Refresh Wishlist</button></DashboardShell>;
}
