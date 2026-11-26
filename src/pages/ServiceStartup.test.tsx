import {cleanup,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,expect,it,vi} from 'vitest';
import {AuthProvider} from '../state/AuthContext';
import {getAccessToken,setAccessToken} from '../api/client';
import {PublicServiceCatalog} from './ServiceCatalog';
afterEach(()=>{cleanup();setAccessToken(null);vi.unstubAllGlobals();});
it.each(['CREATIVE','PROFESSIONAL'] as const)('restores authentication before starting the public %s request',async domain=>{
 setAccessToken(null);let restore!:(value:Response)=>void;const catalogues:string[]=[];
 const fetcher=vi.fn((input:string)=>{
  const url=new URL(String(input),location.origin);
  if(url.pathname.endsWith('/auth/refresh'))return new Promise<Response>(resolve=>{restore=resolve;});
  if(url.pathname.endsWith('/creative/listings')){catalogues.push(url.searchParams.get('domain')!);return Promise.resolve(new Response(JSON.stringify([{id:1,provider_id:2,domain,title:'Restored public service',description:'An approved service',category:domain==='CREATIVE'?'Photography':'IT Consulting',pricing:'QUOTATION',amount:null,currency:'INR',remote:true,locality:null,portfolio:[],status:'APPROVED',is_active:true,review_count:0,rating_average:null}])));}
  throw Error('Unexpected request: '+url.pathname);
 });vi.stubGlobal('fetch',fetcher);
 render(<MemoryRouter><AuthProvider><PublicServiceCatalog domain={domain}/></AuthProvider></MemoryRouter>);
 await waitFor(()=>expect(restore).toBeTypeOf('function'));expect(catalogues).toEqual([]);
 restore(new Response('{}',{status:401}));
 expect(await screen.findByRole('heading',{name:'Restored public service'})).toBeInTheDocument();
 expect(catalogues).toEqual([domain]);expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
it.each([
 ['CREATIVE','refresh'],['PROFESSIONAL','refresh'],
 ['CREATIVE','me'],['PROFESSIONAL','me'],
] as const)('loads public %s services after successful %s restoration',async(domain,method)=>{
 const buyer={id:1,name:'Buyer',email:'buyer@example.test',role:'BUYER'};
 const token=method==='refresh'?'restored-token':'existing-token';
 setAccessToken(method==='me'?token:null);
 let finish!:(value:Response)=>void;
 const requests:string[]=[];
 const json=(value:unknown)=>new Response(JSON.stringify(value),{status:200,headers:{'Content-Type':'application/json'}});
 vi.stubGlobal('fetch',vi.fn((input:string)=>{
  const url=new URL(String(input),location.origin);
  requests.push(url.pathname);
  if(url.pathname.endsWith(`/auth/${method}`))return new Promise<Response>(resolve=>{finish=resolve;});
  if(url.pathname.endsWith('/creative/listings')){expect(url.searchParams.get('domain')).toBe(domain);return Promise.resolve(json([{id:1,provider_id:2,domain,title:'Authenticated public service',description:'An approved service',category:domain==='CREATIVE'?'Photography':'IT Consulting',pricing:'QUOTATION',amount:null,currency:'INR',remote:true,locality:null,portfolio:[],status:'APPROVED',is_active:true,review_count:0,rating_average:null}]));}
  throw Error('Unexpected request: '+url.pathname);
 }));
 render(<MemoryRouter><AuthProvider><PublicServiceCatalog domain={domain}/></AuthProvider></MemoryRouter>);
 await waitFor(()=>expect(finish).toBeTypeOf('function'));
 expect(requests.filter(path=>path.endsWith('/creative/listings'))).toEqual([]);
 finish(json(method==='refresh'?{access_token:token,token_type:'bearer',expires_in:900,user:buyer}:buyer));
 expect(await screen.findByRole('heading',{name:'Authenticated public service'})).toBeInTheDocument();
 expect(getAccessToken()).toBe(token);
 expect(requests.filter(path=>path.endsWith('/creative/listings'))).toHaveLength(1);
 expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
