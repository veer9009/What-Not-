import { PlusCircle, Store, ShoppingBag, Wallet } from 'lucide-react';
import { ListingImage } from '../components/ListingImage';
import { ProductImages, useProductImages } from '../components/ProductImages';
import { CollectionNotice } from '../components/LegalNavigation';
import { PublicDiscoveryLocation } from '../components/PublicDiscoveryLocation';
import { useCallback, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { DashboardShell, EmptyState, Metric, PageTop, RadiusSelector, StatusBadge } from '../components/Shared';
import { ErrorNotice, Field, Loading } from '../components/ApiStates';
import { ApiError, errorMessage } from '../api/client';
import { productsApi } from '../api/products';
import { sellersApi } from '../api/sellers';
import type { Category, Product, ProductInput, Shop } from '../api/types';
import { useResource } from '../state/useResource';
import { useMounted } from '../state/useMounted';
import { ShopProfileForm } from '../components/ShopProfileForm';
import { shopDiscoveryIssues } from '../location/shopReadiness';
async function ownShop() { try{return await sellersApi.me();}catch(error){if(error instanceof ApiError&&error.status===404)return null;throw error;} }
async function storefront(){const shop=await ownShop();return {shop,products:shop?await productsApi.own():[]};}
function SetupNotice(){return <section className="panel"><h2>Set up your seller profile</h2><p>Complete your shop profile to add products.</p><Link className="btn btn-primary" to="/seller/profile"><Store size={18} aria-hidden="true"/>Create seller profile</Link></section>;}
export function SellerDashboard(){
  const resource=useResource(storefront);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
  async function mutate(action:()=>Promise<Product>){if(busy)return;setBusy(true);setError('');setNotice('');try{await action();const refreshed=await resource.reload();setNotice(refreshed?'Listing updated.':'Change saved. Refresh the listing to see the current state.');}catch(reason){setError(errorMessage(reason));}finally{setBusy(false);}}
  const own=resource.data?.products??[];
  const locationIssues=resource.data?.shop?shopDiscoveryIssues(resource.data.shop):[];
  const ready=locationIssues.length===0?own.filter(p=>p.status==='APPROVED'&&p.is_active&&p.stock_quantity>0).length:0;
  return <DashboardShell role="seller" sectionsReady={!resource.loading&&!resource.error}><PageTop eyebrow={resource.data?.shop?.shop_name??'Seller account'} title="Your local storefront" action={resource.data?.shop&&<Link className="btn btn-primary" to="/seller/products/new"><PlusCircle size={18} aria-hidden="true"/>Add New Product</Link>}/>{notice&&<p className="success-note" role="status">{notice}</p>}{error&&<ErrorNotice message={error}/>} {resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:!resource.data?.shop?<div id="products"><SetupNotice/></div>:<><div className="metrics-grid"><Metric label="Products shown" value={own.length}/><Metric label="Discovery ready" value={ready}/><Metric label="Pending review" value={own.filter(p=>p.status==='PENDING').length}/></div><section className="panel" aria-label="Nearby discovery readiness"><h2>Nearby discovery</h2>{locationIssues.length?<><p>Finish your shop location before products can appear nearby.</p><ul>{locationIssues.map(issue=><li key={issue}>{issue}</li>)}</ul><Link className="btn btn-outline" to="/seller/profile">Complete shop location</Link></>:<p>Your shop location is saved and reused for every product.</p>}<p>Products also need approval, available stock and active status. Buyers must be within range. Delivery is confirmed at checkout.</p></section><nav className="seller-quick-actions" aria-label="Seller quick actions"><Link className="btn btn-outline" to="/seller/orders"><ShoppingBag size={18} aria-hidden="true"/>Manage orders</Link><Link className="btn btn-outline" to="/seller/payments"><Wallet size={18} aria-hidden="true"/>Review collections</Link><Link className="btn btn-outline" to="/seller/profile"><Store size={18} aria-hidden="true"/>Shop &amp; delivery</Link></nav><p className="approval-help">Listings show up to 100 products. Adding a product never changes your saved shop location.</p><section id="products" className="panel"><h2>Your products</h2>{own.length?<div className="seller-products">{own.map(product=><article key={product.id}><ListingImage src={product.image_url} alt={product.name}/><div className="listing-main"><div className="listing-badges"><StatusBadge status={product.status}/>{!product.is_active&&<StatusBadge status="INACTIVE"/>}{product.stock_quantity===0&&<StatusBadge status="OUT_OF_STOCK"/>}</div><h3>{product.name}</h3><p>₹{product.price} · {product.delivery_radius_km} KM configured radius · {product.stock_quantity} in stock · {product.category}</p><p>{product.description}</p>{product.status==='REJECTED'&&<div className="rejection-note"><b>Changes requested</b><p>{product.rejection_reason}</p><button className="btn btn-outline btn-sm" disabled={busy} onClick={()=>void mutate(()=>productsApi.resubmit(product.id))}>Resubmit for Review</button></div>}</div><div className="row-actions"><Link className="text-link" to={`/seller/products/${product.id}/edit`}>Edit product</Link><button className="listing-toggle" disabled={busy} onClick={()=>void mutate(()=>productsApi.activate(product.id,!product.is_active))}>{product.is_active?'Deactivate':'Reactivate'}</button></div></article>)}</div>:<EmptyState title="Your shop has no products yet" description="Add a product to submit it for review."/>}</section></>}</DashboardShell>;
}
export function SellerProfilePage(){
  const resource=useResource(ownShop);const [notice,setNotice]=useState('');const [partialShop,setPartialShop]=useState<Shop|null>(null);
  const reload=useCallback(async()=>{const refreshed=await resource.reload();if(refreshed)setPartialShop(null);return refreshed;},[resource.reload]);
  const publicShop=partialShop??resource.data;
  return <DashboardShell role="seller">
    {notice&&<p className="success-note" role="status">{notice}</p>}
    {resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void reload()}/>:<ShopProfileForm key={resource.data?.id??'new'} shop={resource.data} reload={reload} onPartialSave={setPartialShop} saved={()=>setNotice('Shop location saved. It is reused for every product. Public discovery still needs your permission and eligible products.')}/>}
    {!resource.loading&&publicShop&&<PublicDiscoveryLocation key={[publicShop.id,publicShop.public_discovery_confirmed_at].join(':')} shop={publicShop} reload={reload}/>}
  </DashboardShell>;
}
const categories:Category[]=['Handmade','Home Decor','Gifts','Fashion','Jewellery','Crafts'];
export function ProductFormPage(){
  const {id}=useParams();
  const loader=useCallback(async()=>{const shop=await ownShop();return {shop,products:shop&&id?await productsApi.own():[]};},[id]);const resource=useResource(loader);
  const product=resource.data?.products.find(item=>item.id===id);
  return <DashboardShell role="seller">{resource.loading?<Loading/>:resource.error?<ErrorNotice message={resource.error} retry={()=>void resource.reload()}/>:!resource.data?.shop?<SetupNotice/>:id&&!product?<><EmptyState title="That listing was not found" description="This listing is absent from your owned products (up to 100)."/><Link className="btn btn-primary" to="/seller">Return to seller dashboard</Link></>:<ProductForm key={id??'new'} product={product}/>}</DashboardShell>;
}
export function ProductForm({product}:{product?:Product}){
  const nav=useNavigate();const mounted=useMounted();const [notice,setNotice]=useState('');const [form,setForm]=useState({name:product?.name??'',description:product?.description??'',price:product?.price??'',stock_quantity:String(product?.stock_quantity??''),category:product?.category??'Handmade' as Category,delivery_radius_km:product?.delivery_radius_km??2,image_url:product?.image_url??''});const [error,setError]=useState('');const [fields,setFields]=useState<Record<string,string>>({});const [busy,setBusy]=useState(false);
  const images=useProductImages(product);const savedProduct=useRef<Product|undefined>(product);
  const set=(key:keyof typeof form,value:string|number)=>setForm(current=>({...current,[key]:value}));
  async function submit(event:FormEvent){
    event.preventDefault();if(busy)return;setBusy(true);setError('');setFields({});
    try{
      const previous=savedProduct.current;
      const body:ProductInput={...form,stock_quantity:Number(form.stock_quantity),image_url:images.legacyRemoved?null:form.image_url.trim()||null};
      if(previous){
        const changed=Object.fromEntries(Object.entries(body).filter(([key,value])=>value!==previous[key as keyof ProductInput]));
        if(!Object.keys(changed).length&&!images.changed){setNotice('No product changes to save.');return;}
        if(Object.keys(changed).length){const result=await productsApi.update(previous.id,changed);savedProduct.current={...previous,...result,...body};}
      }else savedProduct.current=await productsApi.create(body);
      if(!mounted.current)return;
      await images.save(savedProduct.current!.id);
      if(mounted.current)nav('/seller');
    }catch(reason){if(mounted.current){setError((savedProduct.current&&!product?'Your product was saved. Retry this form to upload the remaining images without creating another product. ':'')+errorMessage(reason));if(reason instanceof ApiError)setFields(reason.fields);}}
    finally{if(mounted.current)setBusy(false);}
  }
  return <><PageTop eyebrow={product?'Update listing':'Create a listing'} title={product?'Edit Product':'Add New Product'}/><p className="approval-help">This form supports handmade product listings with the existing categories. Food-specific listing and compliance tools are not available. Use the property and Creative Services workspaces for those listings.</p><p className="approval-help">Approved edits return to PENDING. Rejected edits keep the reason until explicit resubmission.</p>{product?.status==='REJECTED'&&<div className="rejection-note"><b>Changes requested</b><p>{product.rejection_reason}</p></div>}<form className="product-form" onSubmit={submit}><section><h2>Product details</h2><CollectionNotice label="Product">Approved product text and images are shown to buyers. Submit only material you have rights to use. Hosted image URLs load from external servers; keep personal details out of public text.</CollectionNotice><div className="form-grid"><Field label="Product Name" name="name" value={form.name} onChange={value=>set('name',value)} required maxLength={120} error={fields.name}/><label>Category<select value={form.category} onChange={event=>set('category',event.target.value)}>{categories.map(category=><option key={category}>{category}</option>)}</select></label><label className="full">Description<textarea required maxLength={5000} value={form.description} onChange={event=>set('description',event.target.value)} aria-invalid={Boolean(fields.description)}/>{fields.description&&<small>{fields.description}</small>}</label><Field label="Price (₹)" name="price" type="number" step="0.01" min={0.01} max={9999999999.99} value={form.price} onChange={value=>set('price',value)} required error={fields.price}/><Field label="Available Quantity" name="stock_quantity" type="number" step="1" min={0} max={2147483647} value={form.stock_quantity} onChange={value=>set('stock_quantity',value)} required error={fields.stock_quantity}/></div></section><ProductImages draft={images} busy={busy}/><section><h2>Selling radius</h2><RadiusSelector value={form.delivery_radius_km} onChange={value=>set('delivery_radius_km',value)}/><div className="radius-note">The backend enforces this radius for nearby discovery after dispatch confirmation.</div></section>{error&&<ErrorNotice message={error}/>} {notice&&<p className="success-note" role="status">{notice}</p>}<div className="form-actions"><Link className="btn btn-outline" to="/seller" aria-disabled={busy} tabIndex={busy?-1:undefined} onClick={event=>{if(busy)event.preventDefault();}}>Cancel</Link><button className="btn btn-primary" disabled={busy}>{product?.status==='REJECTED'?'Save Changes':'Submit for Admin Approval'}</button></div></form></>;
}
