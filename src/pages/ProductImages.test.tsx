import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ProductForm } from './SellerPages';
import { productsApi } from '../api/products';
import type { Product } from '../api/types';
const product: Product = {id:'3',seller_id:'2',name:'Candle',description:'Handmade',price:'250',stock_quantity:2,category:'Crafts',delivery_radius_km:2,image_url:null,status:'REJECTED',rejection_reason:null,is_active:true};
function open(existing?:Product){return render(<MemoryRouter><ProductForm product={existing}/></MemoryRouter>);}
function choose(files:File[]){fireEvent.change(screen.getByLabelText('Product images'),{target:{files}});}
const photo=(name='candle.png')=>new File(['image'],name,{type:'image/png'});
beforeEach(()=>{let serial=0;Object.defineProperty(URL,'createObjectURL',{configurable:true,writable:true,value:vi.fn(()=>++serial===1?'blob:preview':`blob:preview-${serial}`)});Object.defineProperty(URL,'revokeObjectURL',{configurable:true,writable:true,value:vi.fn()});});
afterEach(()=>vi.restoreAllMocks());
it('queues previews without saving and validates type, size and total count',()=>{
  const create=vi.spyOn(productsApi,'create');open(product);choose([photo()]);expect(screen.getByAltText('candle.png')).toHaveAttribute('src','blob:preview');expect(create).not.toHaveBeenCalled();
  choose([new File(['x'],'bad.gif',{type:'image/gif'})]);expect(screen.getByRole('alert')).toHaveTextContent(/JPG, PNG or WebP/);
  const big=photo('big.png');Object.defineProperty(big,'size',{value:5*1024*1024+1});choose([big]);expect(screen.getByRole('alert')).toHaveTextContent(/5 MiB/);
  choose(Array.from({length:5},(_,i)=>photo(`${i}.png`)));expect(screen.getByRole('alert')).toHaveTextContent(/five/);
  fireEvent.click(screen.getByRole('button',{name:'Remove image 1'}));expect(screen.queryByAltText('candle.png')).not.toBeInTheDocument();
});
it('retains the created product on partial upload failure and retries only remaining files',async()=>{
  const create=vi.spyOn(productsApi,'create').mockResolvedValue(product);const update=vi.spyOn(productsApi,'update').mockResolvedValue(product);
  const upload=vi.spyOn(productsApi,'uploadImage').mockResolvedValueOnce({...product,images:[{id:'10',image_url:'https://example.test/one.png',is_primary:true,sort_order:0}]}).mockRejectedValueOnce(new Error('network')).mockResolvedValue({...product,images:[{id:'10',image_url:'https://example.test/one.png',is_primary:true,sort_order:0},{id:'11',image_url:'https://example.test/two.png',is_primary:false,sort_order:1}]});
  open();for(const [label,value] of [['Product Name','Candle'],['Description','Handmade'],['Price (₹)','250'],['Available Quantity','2'],['Category','Crafts']])fireEvent.change(screen.getByLabelText(label),{target:{value}});
  choose([photo('one.png'),photo('two.png')]);expect(create).not.toHaveBeenCalled();fireEvent.submit(screen.getByRole('button',{name:'Submit for Admin Approval'}).closest('form')!);
  await screen.findByRole('alert');expect(create).toHaveBeenCalledTimes(1);expect(screen.getByText(/product was saved/i)).toBeInTheDocument();
  fireEvent.submit(screen.getByRole('button',{name:'Submit for Admin Approval'}).closest('form')!);await waitFor(()=>expect(upload).toHaveBeenCalledTimes(3));expect(create).toHaveBeenCalledTimes(1);expect(update).not.toHaveBeenCalled();expect(upload.mock.calls[2][1].name).toBe('two.png');
});
it('counts hosted images and stages removal and primary selection until Save',async()=>{
  const remove=vi.spyOn(productsApi,'removeImage').mockResolvedValue(product);const primary=vi.spyOn(productsApi,'primaryImage').mockResolvedValue(product);
  open({...product,images:Array.from({length:5},(_,i)=>({id:String(i+10),image_url:`https://example.test/${i}.png`,is_primary:i===0,sort_order:i}))});choose([photo()]);expect(screen.getByRole('alert')).toHaveTextContent(/five/);
  fireEvent.click(screen.getByRole('button',{name:'Remove image 1'}));fireEvent.click(screen.getByRole('button',{name:'Make image 2 primary'}));expect(remove).not.toHaveBeenCalled();expect(primary).not.toHaveBeenCalled();fireEvent.submit(screen.getByRole('button',{name:'Save Changes'}).closest('form')!);await waitFor(()=>expect(primary).toHaveBeenCalledWith('3','12',expect.any(AbortSignal)));expect(remove).toHaveBeenCalledWith('3','10',expect.any(AbortSignal));
});
it('replaces an existing hosted image at the five-image limit and shows upload progress',async()=>{
  let finish!: (product:Product)=>void;
  const replace=vi.spyOn(productsApi,'replaceImage').mockImplementation((_id,_imageId,_file,progress)=>{progress?.(50);return new Promise(resolve=>{finish=resolve;});});
  const images=Array.from({length:5},(_,i)=>({id:String(i+10),image_url:`https://example.test/${i}.png`,is_primary:i===0,sort_order:i}));
  open({...product,images});fireEvent.change(screen.getByLabelText('Replace image 1'),{target:{files:[photo('new.png')]}});
  expect(screen.getByAltText('new.png')).toHaveAttribute('src','blob:preview');expect(replace).not.toHaveBeenCalled();
  fireEvent.submit(screen.getByRole('button',{name:'Save Changes'}).closest('form')!);
  await waitFor(()=>expect(screen.getByRole('progressbar')).toHaveAttribute('value','50'));
  expect(screen.getByRole('link',{name:'Cancel'})).toHaveAttribute('aria-disabled','true');
  expect(fireEvent.click(screen.getByRole('link',{name:'Cancel'}))).toBe(false);
  expect(replace).toHaveBeenCalledWith('3','10',expect.any(File),expect.any(Function),expect.any(AbortSignal));
  finish({...product,images});await waitFor(()=>expect(screen.queryByRole('progressbar')).not.toBeInTheDocument());
});
it('does not create a second product when submit events overlap',async()=>{
  let finish!: (value:Product)=>void;
  const create=vi.spyOn(productsApi,'create').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  open();const form=screen.getByRole('button',{name:'Submit for Admin Approval'}).closest('form')!;
  fireEvent.submit(form);fireEvent.submit(form);expect(create).toHaveBeenCalledTimes(1);finish(product);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Submit for Admin Approval'})).toBeEnabled());
});
it('stops image mutations when unmounted during the first upload',async()=>{
  let finish!: (value:Product)=>void;let signal:AbortSignal|undefined;
  const upload=vi.spyOn(productsApi,'uploadImage').mockImplementation((_id,_file,_progress,requestSignal)=>{signal=requestSignal;return new Promise(resolve=>{finish=resolve;});});
  const primary=vi.spyOn(productsApi,'primaryImage');const {unmount}=open(product);choose([photo('one.png'),photo('two.png')]);
  fireEvent.click(screen.getByRole('button',{name:'Make image 2 primary'}));fireEvent.submit(screen.getByRole('button',{name:'Save Changes'}).closest('form')!);
  await waitFor(()=>expect(upload).toHaveBeenCalledTimes(1));unmount();expect(signal?.aborted).toBe(true);
  finish({...product,images:[{id:'10',image_url:'https://example.test/one.png',is_primary:true,sort_order:0}]});
  await new Promise(resolve=>setTimeout(resolve,0));expect(upload).toHaveBeenCalledTimes(1);expect(primary).not.toHaveBeenCalled();
});
it('revokes removed and replaced preview URLs immediately',()=>{
  open(product);choose([photo()]);fireEvent.change(screen.getByLabelText('Replace image 1'),{target:{files:[photo('new.png')]}});
  expect(URL.revokeObjectURL).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'Remove image 1'}));expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2);
});
it('does not start later removals after unmount',async()=>{
  let finish!: (value:Product)=>void;
  const remove=vi.spyOn(productsApi,'removeImage').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const {unmount}=open({...product,images:[{id:'10',image_url:'https://example.test/a.png',is_primary:true,sort_order:0},{id:'11',image_url:'https://example.test/b.png',is_primary:false,sort_order:1}]});
  fireEvent.click(screen.getByRole('button',{name:'Remove image 1'}));fireEvent.click(screen.getByRole('button',{name:'Remove image 1'}));fireEvent.submit(screen.getByRole('button',{name:'Save Changes'}).closest('form')!);
  await waitFor(()=>expect(remove).toHaveBeenCalledTimes(1));unmount();finish(product);await new Promise(resolve=>setTimeout(resolve,0));expect(remove).toHaveBeenCalledTimes(1);
});
it('does not upload queued images after unmount while product creation was pending',async()=>{
  let finish!: (value:Product)=>void;
  const create=vi.spyOn(productsApi,'create').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));const upload=vi.spyOn(productsApi,'uploadImage');
  const {unmount}=open();choose([photo()]);fireEvent.submit(screen.getByRole('button',{name:'Submit for Admin Approval'}).closest('form')!);
  expect(create).toHaveBeenCalledOnce();unmount();finish(product);await new Promise(resolve=>setTimeout(resolve,0));expect(upload).not.toHaveBeenCalled();
});
it.each([false,true])('preserves an unindexed hosted image and selects the newly uploaded row as primary (fallback lookup: %s)',async fallback=>{
  const legacy='https://example.test/legacy.png';
  const images=[{id:'10',image_url:legacy,is_primary:true,sort_order:0},{id:'11',image_url:'https://example.test/new.png',is_primary:false,sort_order:1}];
  vi.spyOn(productsApi,'uploadImage').mockResolvedValue({...product,image_url:legacy,...(fallback?{}:{images})});
  vi.spyOn(productsApi,'images').mockResolvedValue(images);
  const update=vi.spyOn(productsApi,'update');const remove=vi.spyOn(productsApi,'removeImage');const primary=vi.spyOn(productsApi,'primaryImage').mockResolvedValue({...product,images});
  open({...product,image_url:legacy});choose([photo('new.png')]);fireEvent.click(screen.getByRole('button',{name:'Make image 2 primary'}));
  fireEvent.submit(screen.getByRole('button',{name:'Save Changes'}).closest('form')!);
  await waitFor(()=>expect(primary).toHaveBeenCalledWith('3','11',expect.any(AbortSignal)));
  expect(update).not.toHaveBeenCalled();expect(remove).not.toHaveBeenCalled();
});
