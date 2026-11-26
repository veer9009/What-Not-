import { creativeApi,type CreativeListing } from './creative';
import { propertiesApi,type PropertyListing } from './properties';
import { discoveryApi,type DiscoverySource,type DiscoveryRadius,type BuyerProduct } from './discovery';

export type HomeKind='PRODUCT'|'CREATIVE'|'PROFESSIONAL'|'PROPERTY';
export interface HomeListing {id:string;kind:HomeKind;title:string;description?:string;image:string|null;price:string|null;pricing:string|null;rating:string|null;reviews:number|null;distance:number|null;locality:string|null;href:string}
export interface HomeSearch {query:string;locality:string;remote:string;source:DiscoverySource|null;radius:DiscoveryRadius;buyer:boolean;page?:number;kind?:string}
export interface HomeResults {items:HomeListing[];errors:string[];hasNext?:boolean}
export type PublicPages=Map<string,Promise<unknown[]>>;
const price=(value:unknown)=>typeof value==='string'&&/^\d+(?:\.\d{1,2})?$/.test(value)&&Number(value)>0?value:null;
function image(value:unknown){
 if(typeof value!=='string'||!value)return null;
 try{const url=new URL(value,window.location.origin);return ['http:','https:'].includes(url.protocol)&&!url.username&&!url.password?value:null;}catch{return null;}
}
function service(row:CreativeListing,kind:'CREATIVE'|'PROFESSIONAL'):HomeListing {
 const actualRating=row.rating_average!=null&&Number.isFinite(Number(row.rating_average))&&Number(row.rating_average)>=0&&Number(row.rating_average)<=5&&Number(row.review_count)>0;
 return {id:row.id,kind,title:row.title,image:(row.portfolio??[]).find(url=>image(url)&&/\.(png|jpe?g|webp|avif|gif)(?:\?|$)/i.test(url))??null,price:row.pricing==='QUOTATION'?null:price(row.amount),pricing:row.pricing,rating:actualRating?String(row.rating_average):null,reviews:actualRating?row.review_count!:null,distance:null,locality:row.remote?'Remote':row.locality,href:`/${kind==='CREATIVE'?'creative-services':'professional-services'}?q=${encodeURIComponent(row.title)}`};
}
function property(row:PropertyListing):HomeListing {return {id:row.id,kind:'PROPERTY',title:row.title,image:null,price:price(row.price),pricing:null,rating:null,reviews:null,distance:null,locality:row.locality,href:`/buyer/properties/${row.id}`};}
function product(row:BuyerProduct):HomeListing {return {id:row.id,kind:'PRODUCT',title:row.name,image:image(row.image_url),price:price(row.price),pricing:null,rating:null,reviews:null,distance:null,locality:null,href:`/buyer/products/${row.id}`};}
export async function loadHomeListings(search:HomeSearch,publicPages:PublicPages=new Map()):Promise<HomeResults>{
 const offset=(search.page??0)*30,q=search.query.trim();
 function cached<T>(kind:string,load:()=>Promise<T[]>):Promise<T[]>{const key=JSON.stringify([kind,offset,q,search.locality,search.remote]);let pending=publicPages.get(key);if(!pending){pending=load();publicPages.set(key,pending);if(publicPages.size>12)publicPages.delete(publicPages.keys().next().value!);}return pending as Promise<T[]>;}
 const filters={...(search.query.trim()?{q:search.query.trim()}:{}),...(search.remote?{remote:search.remote==='true'}:{})};
 const sources=[
  {kind:'PRODUCT',label:'Homemade products',load:()=>search.buyer&&search.source?discoveryApi.list(search.source,search.radius,{offset,limit:30,q}):Promise.resolve([]),map:(rows:BuyerProduct[])=>rows.filter(row=>`${row.name} ${row.description} ${row.shop_name}`.toLowerCase().includes(q.toLowerCase())).map(row=>({...product(row),description:row.description}))},
  {kind:'CREATIVE',label:'Creative Services',load:()=>cached('CREATIVE',()=>creativeApi.listings(offset,'CREATIVE',filters,30)),map:(rows:CreativeListing[])=>rows.map(row=>({...service(row,'CREATIVE'),description:row.description}))},
  {kind:'PROFESSIONAL',label:'Professional Services',load:()=>cached('PROFESSIONAL',()=>creativeApi.listings(offset,'PROFESSIONAL',filters,30)),map:(rows:CreativeListing[])=>rows.map(row=>({...service(row,'PROFESSIONAL'),description:row.description}))},
  {kind:'PROPERTY',label:'Properties',load:()=>cached('PROPERTY',()=>propertiesApi.list(offset,search.locality,'',{q,limit:30})),map:(rows:PropertyListing[])=>rows.filter(row=>`${row.title} ${row.description??''} ${row.locality??''}`.toLowerCase().includes(q.toLowerCase())).map(row=>({...property(row),description:row.description}))},
 ];
 let hasNext=false;
 const results=await Promise.allSettled(sources.map(async source=>{if(search.kind&&search.kind!=='ALL'&&search.kind!==source.kind)return [];const rows=await source.load();if(!Array.isArray(rows))throw Error('Invalid listing response');if(rows.length===30)hasNext=true;return source.map(rows as never);}));
 const items:HomeListing[]=[],errors:string[]=[];
 const buckets=results.map((result,index)=>{if(result.status==='fulfilled')return result.value;errors.push(`${sources[index].label} could not be loaded.`);return [];});
 for(let index=0;buckets.some(bucket=>index<bucket.length);index++)for(const bucket of buckets)if(bucket[index])items.push(bucket[index]);
 return {items,errors,hasNext};
}
