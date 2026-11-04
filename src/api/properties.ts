import { api, identifier } from './client';
export interface PropertyListing { id:string; creator_id:string; title:string;description:string;category:string;price:string;locality:string;status:string;expires_at:string;updated_at:string;rejection_reason:string|null;capacity:string;display_name:string }
export interface PropertyDraft { title:string;description:string;category:string;price:string;locality:string;private_address:string }
export interface PropertyProfile { display_name:string;capacity:'OWNER'|'AGENT';share_contact:boolean }
export interface Enquiry { id:string;property_id:string;message:string;response:string|null;status:string;creator_contact?:string }
export interface Visit { id:string;property_id:string;scheduled_at:string;status:string;reason:string|null;creator_contact?:string }
export interface PropertyReport { id:string;property_id:string;reason:string;explanation:string;disposition:string }
const path=(id:string)=>`/properties/${identifier(id)}`;
export const propertiesApi={
  list:(offset=0,locality='',category='')=>api<PropertyListing[]>(`/properties?offset=${offset}&limit=30&locality=${encodeURIComponent(locality)}&category=${encodeURIComponent(category)}`,{auth:false}),
  detail:(id:string)=>api<PropertyListing>(path(id),{auth:false}),
  mine:(offset=0)=>api<PropertyListing[]>(`/properties/mine?offset=${offset}&limit=30`),
  saved:(offset=0)=>api<PropertyListing[]>(`/properties/saved?offset=${offset}&limit=30`),
  profile:()=>api<PropertyProfile|null>('/properties/profile'),
  saveProfile:(body:PropertyProfile)=>api<PropertyProfile>('/properties/profile',{method:'POST',body}),
  create:(body:PropertyDraft)=>api<PropertyListing>('/properties',{method:'POST',body}),
  edit:(id:string,body:PropertyDraft)=>api<PropertyListing>(path(id),{method:'PATCH',body}),
  command:(id:string,action:string,body:unknown={})=>api(path(id)+'/'+action,{method:'POST',body}),
  requests:(offset=0)=>api<{enquiries:Enquiry[];visits:Visit[]}>(`/properties/requests?offset=${offset}&limit=30`),
  reply:(id:string,message:string)=>api(`/properties/enquiries/${identifier(id)}/reply`,{method:'POST',body:{message}}),
  visitAction:(id:string,action:string,scheduled_at?:string)=>api(`/properties/visits/${identifier(id)}/action`,{method:'POST',body:{action,...(scheduled_at?{scheduled_at}:{})}}),
  visitLocation:(id:string)=>api<{address:string}>(`/properties/visits/${identifier(id)}/location`,{method:'POST'}),
  location:(id:string,reason?:string)=>api<{address:string}>(path(id)+'/location',{method:'POST',body:{reason}}),
  queue:(offset=0)=>api<PropertyListing[]>(`/properties/admin/queue?offset=${offset}&limit=30`),
  reports:(offset=0)=>api<PropertyReport[]>(`/properties/admin/reports?offset=${offset}&limit=30`),
  resolve:(id:string,disposition:string,reason:string,takedown:boolean)=>api(`/properties/admin/reports/${identifier(id)}`,{method:'POST',body:{disposition,reason,takedown}}),
};
