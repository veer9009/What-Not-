import { useEffect, useRef, useState } from 'react';
import '../styles/product-images.css';
import { productsApi } from '../api/products';
import type { Product, ProductImage } from '../api/types';

type DraftImage = { key: string; image?: ProductImage; file?: File; preview: string; legacy?: boolean; progress?: number };
export function useProductImages(product?: Product) {
  const [items, setItems] = useState<DraftImage[]>(() => product?.images?.length
    ? [...product.images].sort((a,b)=>a.sort_order-b.sort_order).map(image=>({key:image.id,image,preview:image.image_url}))
    : product?.image_url ? [{key:'legacy',preview:product.image_url,legacy:true}] : []);
  const [removed,setRemoved] = useState<string[]>([]);
  const [legacyRemoved,setLegacyRemoved] = useState(false);
  const [primary,setPrimary] = useState<string|undefined>(items.find(item=>item.image?.is_primary)?.key ?? items[0]?.key);
  const [error,setError] = useState('');
  const urls = useRef(new Set<string>());
  const serial = useRef(0);
  const request = useRef<AbortController|null>(null);
  useEffect(()=>{
    const controller=new AbortController();request.current=controller;
    return ()=>{controller.abort();urls.current.forEach(url=>URL.revokeObjectURL(url));urls.current.clear();};
  },[]);
  function release(preview:string) {
    if (urls.current.delete(preview)) URL.revokeObjectURL(preview);
  }
  function choose(files: File[], replaceKey?: string) {
    setError('');
    if (items.length + (replaceKey ? 0 : files.length) > 5) { setError('A product can have at most five images, including existing hosted images.'); return; }
    if (files.some(file=>!['image/jpeg','image/png','image/webp'].includes(file.type))) { setError('Choose JPG, PNG or WebP images.'); return; }
    if (files.some(file=>file.size>5*1024*1024)) { setError('Each image must be 5 MiB or smaller.'); return; }
    const drafts = files.map(file=>{const preview=URL.createObjectURL(file);urls.current.add(preview);return {key:`draft-${++serial.current}`,file,preview};});
    if (replaceKey && drafts[0]) {
      const original=items.find(item=>item.key===replaceKey);
      if (original?.legacy) setLegacyRemoved(true);
      if (original) release(original.preview);
      setItems(current=>current.map(item=>item.key===replaceKey?{...item,file:drafts[0].file,preview:drafts[0].preview,progress:undefined}:item));
    } else {
      setItems(current=>[...current,...drafts]);
      if (!primary && drafts[0]) setPrimary(drafts[0].key);
    }
  }
  function remove(key:string) {
    const item=items.find(image=>image.key===key);
    if (item) release(item.preview);
    if (item?.image) setRemoved(current=>[...current,item.image!.id]);
    if (item?.legacy) setLegacyRemoved(true);
    setItems(current=>current.filter(image=>image.key!==key));
    if (primary===key) setPrimary(items.find(image=>image.key!==key)?.key);
    setError('');
  }
  // Record each accepted operation immediately so an explicit retry skips completed work.
  async function save(id:string) {
    const signal=request.current?.signal;
    const active=()=>{if(!signal||signal.aborted)throw new DOMException('Image changes cancelled.','AbortError');};
    active();
    for (const imageId of removed) {
      active();
      await productsApi.removeImage(id,imageId,signal);
      active();
      setRemoved(current=>current.filter(value=>value!==imageId));
    }
    for (const item of items) {
      active();
      if (!item.file) continue;
      const progress=(percent:number)=>{if(!signal?.aborted)setItems(current=>current.map(image=>image.key===item.key?{...image,progress:percent}:image));};
      progress(0);
      const result=item.image
        ? await productsApi.replaceImage(id,item.image.id,item.file,progress,signal)
        : await productsApi.uploadImage(id,item.file,progress,signal);
      active();
      const known = new Set(items.flatMap(image=>image.image?[image.image.id]:[]));
      const legacyUrls = new Set(items.filter(image=>image.legacy).map(image=>image.preview));
      const isAdded = (image:ProductImage) => !known.has(image.id) && !legacyUrls.has(image.image_url);
      let image = item.image ? result.images?.find(image=>image.id===item.image!.id) : result.images?.find(isAdded);
      if (!image) {
        const refreshed = await productsApi.images(id,signal);
        active();
        image = item.image ? refreshed.find(image=>image.id===item.image!.id) : refreshed.find(isAdded);
      }
      if (!image) throw new Error('Image response is incomplete');
      // Update this local snapshot too: subsequent uploads must exclude this ID.
      release(item.preview);
      item.image=image;item.file=undefined;item.legacy=false;item.preview=image.image_url;
      setItems(current=>current.map(draft=>draft.key===item.key?{...item,progress:undefined}:draft));
    }
    const selected=items.find(item=>item.key===primary);
    active();
    if (selected?.image && !selected.image.is_primary) {
      await productsApi.primaryImage(id,selected.image.id,signal);
      active();
      selected.image={...selected.image,is_primary:true};
    }
  }
  return {items,primary,setPrimary,error,choose,remove,save,legacyRemoved,
    changed: removed.length>0 || legacyRemoved || items.some(item=>item.file) || Boolean(items.find(item=>item.key===primary)?.image && !items.find(item=>item.key===primary)?.image?.is_primary)};
}

export function ProductImages({draft,busy}:{draft:ReturnType<typeof useProductImages>;busy:boolean}) {
  return <section><h2>Product images</h2><p>Choose up to five JPG, PNG or WebP images, each 5 MiB or smaller. Image changes upload only when you submit or save this form. Existing hosted images count toward the limit.</p>
    <label>Product images<input type="file" accept="image/jpeg,image/png,image/webp" multiple disabled={busy} onChange={event=>{draft.choose(Array.from(event.target.files??[]));event.target.value='';}}/></label>
    {draft.error&&<p role="alert">{draft.error}</p>}
    <div className="product-image-previews">{draft.items.map((item,index)=><figure key={item.key}>
      <img src={item.preview} alt={item.file?.name??`Product image ${index+1}`} referrerPolicy="no-referrer"/>
      <figcaption>{item.file?.name??(item.legacy?'Existing hosted image':`Image ${index+1}`)} {draft.primary===item.key&&<span>Primary image</span>}</figcaption>
      {item.progress!==undefined&&<label>Uploading {item.file?.name}<progress value={item.progress} max={100}/>{item.progress}%{item.progress===100?' — processing image':''}</label>}
      <button type="button" className="btn btn-outline btn-sm" disabled={busy} onClick={()=>draft.remove(item.key)}>Remove image {index+1}</button>
      <button type="button" className="btn btn-outline btn-sm" disabled={busy||draft.primary===item.key} onClick={()=>draft.setPrimary(item.key)}>Make image {index+1} primary</button>
      <label>Replace image {index+1}<input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={event=>{draft.choose(Array.from(event.target.files??[]),item.key);event.target.value='';}}/></label>
    </figure>)}</div>
  </section>;
}
