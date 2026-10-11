import { Edit3, Eye, PackagePlus, Plus, Trash2, Upload } from 'lucide-react';
import { ChangeEvent, FormEvent, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { DashboardShell, EmptyState, Metric, PageTop, RadiusSelector, StatusBadge } from '../components/Shared';
import { useDemo } from '../state/DemoContext';
import type { Category, Product } from '../types';
import { validateProduct } from '../utils/validation';
import { isBuyerEligible } from '../utils/products';
import { products as initialProducts } from '../data/mockData';

export function SellerDashboard() {
  const { state, dispatch, seller, setSeller } = useDemo();
  const location = useLocation();
  const [notice, setNotice] = useState<string>(location.state?.notice ?? '');
  const own = state.products.filter(p => p.seller === seller);
  const shops = [...new Set(['Mitti & Thread Studio', ...initialProducts.map(p => p.seller), ...state.products.map(p => p.seller), seller])];
  return <DashboardShell role="seller">
    <PageTop eyebrow={seller} title="Your local storefront" action={<Link className="btn btn-primary" to="/seller/products/new"><Plus/> Add New Product</Link>}/>
    <label className="shop-selector">Demo shop<select value={seller} onChange={e => { setSeller(e.target.value); setNotice(''); }}>{shops.map(shop => <option key={shop}>{shop}</option>)}</select></label>
    {notice && <p className="success-note" role="status">{notice}</p>}
    <div className="metrics-grid"><Metric label="Total Products" value={own.length}/><Metric label="Active Listings" value={own.filter(isBuyerEligible).length} note="Live nearby"/><Metric label="Pending Approval" value={own.filter(p => p.status === 'PENDING').length}/><Metric label="Orders" value={state.orders.filter(o => o.seller === seller).length} note="Demo orders"/><Metric label="Earnings" value="₹18.4k" note="Demo placeholder"/></div>
    <section className="panel"><div className="panel-head"><div><p className="eyebrow">Inventory</p><h2>Your products</h2></div><span>{own.length} listings</span></div>
      {own.length ? <div className="seller-products">{own.map(p => <article key={p.id}>
        <img src={p.image} alt={p.name}/><div className="listing-main">
          <div className="listing-badges"><StatusBadge status={p.status}/>{!p.isActive && <StatusBadge status="INACTIVE"/>}{p.stock === 0 && <StatusBadge status="OUT_OF_STOCK"/>}</div>
          <h3>{p.name}</h3><p>₹{p.price} · {p.radius} KM radius · {p.stock} available · {p.category}</p>
          <p>{p.description}</p>
          {p.status === 'REJECTED' && <div className="rejection-note"><b>Changes requested</b><p>{p.rejectionReason}</p><button className="btn btn-outline btn-sm" onClick={() => { dispatch({ type: 'product/resubmit', seller, id: p.id }); setNotice(`${p.name} resubmitted for review.`); }}>Resubmit for Review</button></div>}
        </div><div className="row-actions">
          {isBuyerEligible(p) && <Link title="View listing" aria-label={`View ${p.name}`} to={`/buyer/products/${p.id}`}><Eye/></Link>}
          <Link title="Edit listing" aria-label={`Edit ${p.name}`} to={`/seller/products/${p.id}/edit`}><Edit3/></Link>
          <button className="listing-toggle" onClick={() => { dispatch({ type: 'product/active', seller, id: p.id, isActive: !p.isActive }); setNotice(`${p.name} ${p.isActive ? 'deactivated' : 'reactivated'}.`); }}>{p.isActive ? 'Deactivate' : 'Reactivate'}</button>
          <button title="Delete listing" aria-label={`Delete ${p.name}`} onClick={() => { if (confirm(`Delete ${p.name}?`)) { dispatch({ type: 'product/delete', seller, id: p.id }); setNotice(`${p.name} deleted.`); } }}><Trash2/></button>
        </div>
      </article>)}</div> : <EmptyState title="Your shop has no products yet" description="Add your first product to submit it for admin review."/>}
    </section>
  </DashboardShell>;
}

const cats:Category[]=['Handmade','Home Decor','Gifts','Fashion','Jewellery','Crafts'];
export function ProductFormPage(){
  const { id } = useParams();
  const { seller } = useDemo();
  return <ProductForm key={`${seller}:${id ?? 'new'}`}/>;
}

function ProductForm(){
  const{id}=useParams(); const{state,dispatch,seller}=useDemo(); const nav=useNavigate();
  const existing=state.products.find(p=>p.id===id && p.seller===seller);
  const initial=useMemo(()=>existing??{name:'',description:'',category:'Handmade' as Category,price:'',stock:'',seller,radius:2 as const,image:'https://images.unsplash.com/photo-1452860606245-08befc0ff44b?auto=format&fit=crop&w=900&q=85'},[existing,seller]);
  const[form,setForm]=useState(initial); const[errors,setErrors]=useState<Record<string,string>>({});
  if(id && !existing) return <DashboardShell role="seller"><EmptyState title="That listing was not found"/><Link className="btn btn-primary back-btn" to="/seller">Return to seller dashboard</Link></DashboardShell>;
  const set=(key:string,value:unknown)=>setForm(f=>({...f,[key]:value}));
  function chooseImage(e:ChangeEvent<HTMLInputElement>){const file=e.target.files?.[0];if(!file)return;if(!['image/jpeg','image/png'].includes(file.type)||file.size>5*1024*1024){setErrors(errors=>({...errors,image:'Choose a JPG or PNG image smaller than 5 MB.'}));return}const reader=new FileReader();reader.onload=()=>{set('image',String(reader.result));setErrors(errors=>({...errors,image:''}))};reader.onerror=()=>setErrors(errors=>({...errors,image:'Unable to read that image. Please try another file.'}));reader.readAsDataURL(file)}
  function submit(e:FormEvent){e.preventDefault();const next=validateProduct(form);setErrors(next);if(Object.keys(next).length)return;const product:Product={...form,seller,price:Number(form.price),stock:Number(form.stock),id:existing?.id??crypto.randomUUID(),distance:existing?.distance??1.4,rating:existing?.rating??4.8,verified:existing?.verified??true,isActive:existing?.isActive??true,status:'PENDING'};dispatch({type:existing?'product/update':'product/add',seller,product});nav('/seller',{state:{notice:existing?.status==='REJECTED'?'Changes saved. Resubmit when ready for another review.':'Product submitted for admin review.'}})}
  return <DashboardShell role="seller"><PageTop eyebrow={existing?'Update listing':'Create a listing'} title={existing?'Edit Product':'Add New Product'}/><p className="approval-help">Edits to approved products need admin review. Rejected products keep their reason until you resubmit.</p>{existing?.status === 'REJECTED' && <div className="rejection-note"><b>Changes requested</b><p>{existing.rejectionReason}</p></div>}<form className="product-form" onSubmit={submit} noValidate><section><div className="form-section-title"><PackagePlus/><div><h2>Product details</h2><p>Tell nearby buyers what makes this item special.</p></div></div><div className="form-grid"><label>Product Name<input value={form.name} onChange={e=>set('name',e.target.value)} placeholder="e.g. Handwoven Cotton Tote"/>{errors.name&&<small>{errors.name}</small>}</label><label>Category<select value={form.category} onChange={e=>set('category',e.target.value)}>{cats.map(c=><option key={c}>{c}</option>)}</select></label><label className="full">Description<textarea value={form.description} onChange={e=>set('description',e.target.value)} placeholder="Describe the materials, process and story behind your product..."/>{errors.description&&<small>{errors.description}</small>}</label><label>Price (₹)<input type="number" value={form.price} onChange={e=>set('price',e.target.value)}/>{errors.price&&<small>{errors.price}</small>}</label><label>Available Quantity<input type="number" value={form.stock} onChange={e=>set('stock',e.target.value)}/>{errors.stock&&<small>{errors.stock}</small>}</label><label className="full">Seller Location<input value="Indiranagar, Bengaluru" readOnly/></label></div></section><section><div className="form-section-title"><Upload/><div><h2>Product image</h2><p>Use a clear, naturally lit photo.</p></div></div>{errors.image&&<p className="form-error" role="alert">{errors.image}</p>}<div className="upload-box"><img src={form.image} alt="Product preview"/><div><b>Upload product image</b><p>Choose a JPG or PNG to preview locally.</p><label className="btn btn-outline upload-label">Choose image<input aria-label="Choose product image" type="file" accept="image/png,image/jpeg" onChange={chooseImage}/></label></div></div></section><section><div className="form-section-title"><div><h2>Selling radius</h2><p>How far should buyers be able to discover this product?</p></div></div><RadiusSelector value={form.radius} onChange={n=>set('radius',n)}/><div className="radius-note"><b>Your selected area: {form.radius} KM</b><span>Your product will only be discoverable to eligible buyers within your selected selling area.</span></div></section><div className="form-actions"><Link className="btn btn-outline" to="/seller">Cancel</Link><button className="btn btn-primary">{existing?.status === 'REJECTED' ? 'Save Changes' : 'Submit for Admin Approval'}</button></div></form></DashboardShell>
}
