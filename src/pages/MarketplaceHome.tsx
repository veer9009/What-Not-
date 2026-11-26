import { useCallback,useEffect,useRef,useState,type FormEvent } from 'react';
import { Link,useSearchParams } from 'react-router-dom';
import { ArrowRight,ChevronRight,Heart,MapPin,Search,SlidersHorizontal,Star } from 'lucide-react';
import { useAuth } from '../state/AuthContext';
import { useDiscovery } from '../state/DiscoveryContext';
import { useResource } from '../state/useResource';
import { propertiesApi } from '../api/properties';
import { loadHomeListings,type HomeKind,type PublicPages } from '../api/homeListings';
import { errorMessage } from '../api/client';
import { WishlistButton } from '../components/WishlistButton';
import { RadiusSelector } from '../components/Shared';
import { ListingImage } from '../components/ListingImage';
import homemade from '../assets/categories/homemade-256.png';
import creative from '../assets/categories/creative-256.png';
import professional from '../assets/categories/professional-256.png';
import estate from '../assets/categories/real-estate-256.png';
import '../styles/marketplace-home.css';

const labels:Record<HomeKind,string>={PRODUCT:'Homemade',CREATIVE:'Creative',PROFESSIONAL:'Professional',PROPERTY:'Real Estate'};
export function PremiumCategories(){
 const {user}=useAuth();const seller=user?.role==='SELLER',admin=user?.role==='ADMIN';
 const cards=[
  {id:'homemade',label:'Homemade',full:'Homemade Products',description:'Homemade food, handmade products and crafts.',image:homemade,target:seller?'/seller':admin?'/admin':'/buyer',action:seller?'Open Seller Studio':admin?'Review Homemade listings':'Explore nearby Homemade'},
  {id:'creative-services',label:'Creative',full:'Creative Services',description:'Video editing, VFX and creative services.',image:creative,target:seller?'/seller/creative':admin?'/admin/creative':user?'/buyer/creative':'/creative-services',action:seller?'Open Creative Studio':admin?'Review Creative Services':'Explore Creative Services'},
  {id:'professional-services',label:'Professional',full:'Professional Services',description:'Software, cloud and technical expertise.',image:professional,target:seller?'/seller/professional':admin?'/admin/creative?domain=PROFESSIONAL':user?'/buyer/professional':'/professional-services',action:seller?'Open Professional Dashboard':admin?'Review Professional Services':'Explore Professional Services'},
  {id:'real-estate',label:'Real Estate',full:'Real Estate',description:'Local properties for sale.',image:estate,target:seller?'/seller/properties':admin?'/admin/properties':'/buyer/properties',action:seller?'Manage sale properties':admin?'Review sale properties':'Explore sale properties'},
 ];
 return <section id="explore" className="premium-categories" aria-label="Explore What Not?"><h2 className="sr-only">Explore Nearby</h2><div className="premium-category-grid">{cards.map(card=><article key={card.id} id={card.id} className={`premium-category ${card.id}`} aria-label={card.full}><Link to={card.target} aria-label={card.action}><img src={card.image} alt={`${card.label} 3D icon`} width={80} height={80} decoding="async" referrerPolicy="no-referrer"/><h3>{card.label}</h3><span className="category-arrow"><ChevronRight size={20} aria-hidden="true"/></span><span className="sr-only">{card.description}</span></Link></article>)}</div></section>;
}
async function savedPropertyIds(){
 const ids=new Set<string>();let offset=0;
 for(;;){const rows=await propertiesApi.saved(offset);if(!Array.isArray(rows))throw Error('Saved properties unavailable');const before=ids.size;rows.forEach(row=>ids.add(row.id));if(rows.length<30)return ids;if(ids.size===before)throw Error('Saved properties pagination unavailable');offset+=30;}
}
const priceText=(price:string)=>`₹${Number(price).toLocaleString('en-IN',{maximumFractionDigits:2})}`;
export function MarketplaceHomeContent(){
 const {loading}=useAuth();
 return loading?<p className="picks-state" role="status">Loading picks…</p>:<RestoredMarketplaceHomeContent/>;
}
function RestoredMarketplaceHomeContent(){
 const {user,sessionKey}=useAuth();const buyer=user?.role==='BUYER';const {source,radius,setRadius}=useDiscovery();const [params,setParams]=useSearchParams();
 const query=params.get('q')??'',rawKind=params.get('kind')??'ALL',kind=Object.hasOwn(labels,rawKind)?rawKind:'ALL',all=params.get('all')==='1';
 const [input,setInput]=useState(query),[filters,setFilters]=useState(false),[locality,setLocality]=useState(''),[remote,setRemote]=useState('');
 useEffect(()=>setInput(query),[query]);
 const rawPage=Number(params.get('page')??0),page=Number.isSafeInteger(rawPage)&&rawPage>=0&&rawPage<=1000000?rawPage:0;
 const publicKey=JSON.stringify([query,locality,remote,kind,user?.id,sessionKey]);
 const cache=useRef<{key:string;pages:PublicPages}>({key:'',pages:new Map()});if(cache.current.key!==publicKey)cache.current={key:publicKey,pages:new Map()};const publicPages=cache.current.pages;
 const identity=JSON.stringify([publicKey,page,source,radius,buyer]);
 const load=useCallback(async()=>({identity,results:await loadHomeListings({query,locality,remote,source,radius,buyer,page,kind},publicPages)}),[identity,query,locality,remote,source,radius,buyer,page,kind,publicPages]);
 const resource=useResource(load);const current=resource.data?.identity===identity?resource.data.results:null;
 const saved=useResource(useCallback(()=>buyer?savedPropertyIds():Promise.resolve(new Set<string>()),[buyer,user?.id,sessionKey]));
 const [pending,setPending]=useState<ReadonlySet<string>>(new Set()),[saveError,setSaveError]=useState('');const busy=useRef(new Set<string>()),scope=useRef('');scope.current=`${user?.id}:${sessionKey}`;
 async function toggleProperty(id:string){if(!buyer||saved.loading||saved.error||busy.current.has(id))return;const started=scope.current;busy.current.add(id);setPending(new Set(busy.current));setSaveError('');try{await propertiesApi.command(id,'save',{saved:!saved.data?.has(id)});if(scope.current===started)await saved.reload();}catch(reason){if(scope.current===started)setSaveError(errorMessage(reason));}finally{if(scope.current===started){busy.current.delete(id);setPending(new Set(busy.current));}}}
 function search(event:FormEvent){event.preventDefault();const next=new URLSearchParams(params);input.trim()?next.set('q',input.trim()):next.delete('q');next.delete('all');next.delete('page');setParams(next);}
 function selectKind(value:string){const next=new URLSearchParams(params);value==='ALL'?next.delete('kind'):next.set('kind',value);next.delete('page');setParams(next);}
 function goPage(value:number){const next=new URLSearchParams(params);value?next.set('page',String(value)):next.delete('page');next.set('all','1');setParams(next);}
 function resetPage(){if(page){const next=new URLSearchParams(params);next.delete('page');setParams(next);}}
 const items=(current?.items??[]).filter(item=>kind==='ALL'||item.kind===kind);const viewAll=new URLSearchParams(params);viewAll.set('all','1');
 return <div className="marketplace-home-content"><h1 className="sr-only">Discover What Not?</h1>
  <div className="home-search-row"><form className="unified-home-search" role="search" aria-label="Search the marketplace" onSubmit={search}><button type="submit" aria-label="Search"><Search size={25} aria-hidden="true"/></button><input type="search" maxLength={120} aria-label="Search products, services and properties" placeholder="Search for products, services, properties…" value={input} onChange={event=>setInput(event.target.value)}/></form><button type="button" className="home-filter-button" aria-label="Filters" aria-expanded={filters} aria-controls="home-search-filters" onClick={()=>setFilters(value=>!value)}><SlidersHorizontal size={25} aria-hidden="true"/></button></div>
  {filters&&<section id="home-search-filters" className="home-filters" aria-label="Search filters"><label>Listing type<select value={kind} onChange={event=>selectKind(event.target.value)}><option value="ALL">All listings</option>{Object.entries(labels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label>Property locality<input value={locality} maxLength={120} onChange={event=>{setLocality(event.target.value);resetPage();}}/></label><label>Service location<select value={remote} onChange={event=>{setRemote(event.target.value);resetPage();}}><option value="">Local and remote</option><option value="true">Remote</option><option value="false">Local</option></select></label>{buyer&&<RadiusSelector label="Homemade radius" value={radius} onChange={value=>{if(value!==radius){setRadius(value);resetPage();}}}/>} {(!user||buyer)&&<Link to="/buyer#homemade-catalogue">Set product location and radius</Link>}</section>}
  <PremiumCategories/>
  <section className="nearby-picks" id="nearby-picks" aria-labelledby="nearby-picks-title"><div className="picks-heading"><h2 id="nearby-picks-title"><MapPin size={26} aria-hidden="true"/>Discover Picks</h2><Link className="home-view-all" to={`/?${viewAll}#nearby-picks`} aria-label="View All">View All <ArrowRight size={20} aria-hidden="true"/></Link></div>
   {(!user||buyer&&!source)&&<p className="picks-location-note"><Link to="/buyer#homemade-catalogue">Set your location</Link> for Homemade picks. Services and properties use their listed area.</p>}
   {query&&<p className="home-result-query">Results for “{query}”</p>}
   {resource.loading||(!current&&!resource.error)?<p className="picks-state" role="status">Loading picks…</p>:resource.error?<div className="picks-state" role="alert">{resource.error}</div>:<>{current?.errors.map(error=><p className="home-source-error" role="alert" key={error}>{error}</p>)}{items.length?<div className={`nearby-picks-rail ${all?'all-picks':''}`} role="list" aria-label="Listing picks">{(all?items:items.slice(0,6)).map(item=><article className="home-pick-card" role="listitem" key={`${item.kind}:${item.id}`}><div className="home-pick-image"><span className={`listing-category-badge badge-${item.kind.toLowerCase()}`}>{labels[item.kind]}</span><ListingImage src={item.image} alt={item.title}/>{buyer&&item.kind==='PRODUCT'&&<WishlistButton id={item.id} name={item.title}/>} {buyer&&item.kind==='PROPERTY'&&<button className="property-save-heart" type="button" aria-label={`${saved.data?.has(item.id)?'Unsave':'Save'} ${item.title}`} aria-pressed={saved.data?.has(item.id)??false} disabled={saved.loading||!!saved.error||pending.has(item.id)} onClick={()=>void toggleProperty(item.id)}><Heart size={23} fill={saved.data?.has(item.id)?'currentColor':'none'} aria-hidden="true"/></button>}</div><div className="home-pick-body"><h3><Link to={item.href}>{item.title}</Link></h3>{item.description&&<p className="home-pick-description">{item.description}</p>}<p className="home-pick-price">{item.price?`${item.pricing==='STARTING'?'From ':''}${priceText(item.price)}${item.pricing==='HOURLY'?' / hour':''}`:item.pricing==='QUOTATION'?'Request a quote':'Price unavailable'}</p><div className="home-pick-meta">{item.rating!==null&&<span><Star size={15} fill="currentColor" aria-hidden="true"/>{item.rating} ({item.reviews})</span>}{item.distance!==null&&<span><MapPin size={14} aria-hidden="true"/>{item.distance} km</span>}{item.locality&&<span>{item.locality}</span>}</div></div></article>)}</div>:<div className="picks-state"><h3>No matching picks yet</h3><p>Try another search or choose your product location.</p></div>}</>}
   {(saveError||saved.error&&items.some(item=>item.kind==='PROPERTY'))&&<p role="alert" className="home-source-error">{saveError||'Saved property status is unavailable. Refresh to retry.'}</p>}
   <nav className="discovery-pagination" aria-label="Discover Picks pages" hidden={!all}><button type="button" disabled={resource.loading||page===0} onClick={()=>goPage(page-1)}>Previous discoveries</button><span aria-live="polite">Page {page+1}</span><button type="button" disabled={resource.loading||!current?.hasNext} onClick={()=>goPage(page+1)}>Next discoveries</button></nav><div className="picks-footer"><p>Homemade uses your selected radius. Other categories use their listed area or remote availability. Browse pages with View All.</p><button type="button" className="home-refresh" disabled={resource.loading} onClick={()=>{publicPages.clear();void resource.reload();if(buyer)void saved.reload();}}>Refresh picks</button></div>
  </section>
 </div>;
}
