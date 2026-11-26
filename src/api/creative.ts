import { api, identifier } from './client';
export interface Provider {id:string;user_id:string;display_name:string;bio:string}
export type ServiceDomain='CREATIVE'|'PROFESSIONAL';
export interface ServiceInput {domain?:ServiceDomain;title:string;description:string;category:string;pricing:'FIXED'|'STARTING'|'HOURLY'|'QUOTATION';amount:string|null;currency:'INR';remote:boolean;locality:string|null;portfolio:string[];is_active:boolean}
export interface CreativeListing extends ServiceInput {id:string;provider_id:string;status:string;rejection_reason:string|null;updated_at?:string;provider_name?:string;provider_verification?:string;review_count?:number;rating_average?:string|null}
export interface ServiceDashboard {active_services:number;pending_approvals:number;new_enquiries:number;submitted_quotations:number;ongoing_projects:number;completed_projects:number}
export interface ServiceReview {id:string;engagement_id:string;listing_id:string;rating:number;comment:string;created_at:string}
export interface ServiceFilters {q?:string;category?:string;remote?:boolean}
export interface Quote {id:string;rfq_id:string;terms:string;amount:string;currency:string}
export interface RFQ {id:string;listing_id:string;buyer_id:string;brief:string}
export interface Engagement {id:string;rfq_id:string;response_id:string;title:string;terms:string;amount:string;currency:string;reviewed?:boolean;status:'ACCEPTED'|'DELIVERED'|'COMPLETED'}
const path=(id:string)=>identifier(id);
const query=(offset:number,domain:ServiceDomain,filters:ServiceFilters={},limit=50)=>{const params=new URLSearchParams({offset:String(offset),limit:String(limit),domain});if(filters.q)params.set('q',filters.q);if(filters.category)params.set('category',filters.category);if(filters.remote!==undefined)params.set('remote',String(filters.remote));return params.toString();};
export const creativeApi={
  listings:(offset=0,domain:ServiceDomain='CREATIVE',filters:ServiceFilters={},limit=50)=>api<CreativeListing[]>(`/creative/listings?${query(offset,domain,filters,limit)}`),
  own:(offset=0,domain:ServiceDomain='CREATIVE')=>api<CreativeListing[]>(`/creative/listings/mine?${query(offset,domain)}`),
  dashboard:(domain:ServiceDomain)=>api<ServiceDashboard>(`/creative/dashboard?domain=${domain}`),
  reviews:(domain:ServiceDomain)=>api<ServiceReview[]>(`/creative/reviews?domain=${domain}`),
  provider:()=>api<Provider|null>('/creative/provider'),
  saveProvider:(body:{display_name:string;bio:string})=>api<Provider>('/creative/provider',{method:'POST',body}),
  create:(body:ServiceInput)=>api<CreativeListing>('/creative/listings',{method:'POST',body}),
  update:(id:string,body:ServiceInput)=>api<CreativeListing>(`/creative/listings/${path(id)}`,{method:'PATCH',body}),
  resubmit:(id:string)=>api<CreativeListing>(`/creative/listings/${path(id)}/resubmit`,{method:'POST'}),
  enquire:(id:string,brief:string,request_key:string)=>api<RFQ>(`/creative/listings/${path(id)}/rfqs`,{method:'POST',body:{brief,request_key}}),
  rfqs:(offset=0,domain:ServiceDomain='CREATIVE')=>api<RFQ[]>(`/creative/rfqs?${query(offset,domain)}`),
  responses:(id:string)=>api<Quote[]>(`/creative/rfqs/${path(id)}/responses`),
  respond:(id:string,terms:string,amount:string,request_key:string)=>api<Quote>(`/creative/rfqs/${path(id)}/responses`,{method:'POST',body:{terms,amount,currency:'INR',request_key}}),
  accept:(id:string)=>api<Engagement>(`/creative/responses/${path(id)}/accept`,{method:'POST'}),
  engagements:(offset=0,domain:ServiceDomain='CREATIVE')=>api<Engagement[]>(`/creative/engagements?${query(offset,domain)}`),
  deliver:(id:string)=>api<Engagement>(`/creative/engagements/${path(id)}/deliver`,{method:'POST'}),
  complete:(id:string)=>api<Engagement>(`/creative/engagements/${path(id)}/complete`,{method:'POST'}),
  review:(id:string,rating:number,text:string)=>api(`/creative/engagements/${path(id)}/review`,{method:'POST',body:{rating,text}}),
};
