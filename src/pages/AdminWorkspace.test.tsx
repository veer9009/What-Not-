import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { AdminOperationsPage, CreativeModerationPage } from './AdminOperations';

vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{role:'ADMIN',name:'Test operator'},logout:vi.fn()})}));
afterEach(()=>vi.unstubAllGlobals());
const account={id:2,name:'Test buyer',email:'buyer@example.test',phone:'1000000000',role:'BUYER',is_active:true,phone_verified_at:null,email_verified_at:null};
const service={id:3,provider_id:4,title:'Test service',description:'Service fixture for UI tests',category:'Design',pricing:'FIXED',amount:'100.00',remote:true,portfolio:[],status:'PENDING',updated_at:'2026-11-01T12:00:00Z'};
function open(page:'creative'|'operations', data: {users?:unknown[];services?:unknown[];orders?:unknown[];audit?:unknown[];status?:number}={}){
  const writes:{path:string;method:string;body:unknown}[]=[];
  const fetcher=vi.fn(async(input:string,options:RequestInit)=>{
    const path=new URL(input, location.origin).pathname.replace('/api/v1','');
    if(options.method!=='GET')writes.push({path,method:options.method!,body:JSON.parse(String(options.body))});
    const body=path==='/admin/users'?data.users??[account]:path==='/admin/orders'?data.orders??[]:
      path==='/admin/audit'?data.audit??[]:path==='/admin/operations'?{email_provider_enabled:false,outbox_counts:{PENDING:2,SENT:3},oldest_pending_at:null}:
      path==='/creative/admin/listings'?data.services??[service]:path.endsWith('/fulfillment')?
        {recipient_name:'Test buyer',phone:'1000000000',address_line1:'Private test address',city:'Test city',state:'Test state',pincode:'000000'}:{};
    return new Response(JSON.stringify(body),{status:data.status??200});
  });
  vi.stubGlobal('fetch',fetcher);
  const view=render(<MemoryRouter>{page==='creative'?<CreativeModerationPage/>:<AdminOperationsPage/>}</MemoryRouter>);
  return {writes,fetcher,...view};
}
it('shows a clear empty service queue with styled reason and refresh controls',async()=>{
  open('creative',{services:[]});
  await screen.findByRole('heading',{name:'No services on this page'});
  expect(screen.getByLabelText('Rejection or takedown reason')).toHaveAttribute('aria-describedby','service-reason-help');
  expect(screen.getByRole('button',{name:'Refresh services'})).toHaveClass('btn');
  expect(screen.getByRole('button',{name:'Previous services'})).toBeDisabled();
  expect(screen.getByRole('button',{name:'More services'})).toBeDisabled();
});
it('styles populated moderation cards and requires a reason plus explicit rejection confirmation',async()=>{
  const {writes}=open('creative');
  const reject=await screen.findByRole('button',{name:'Reject Test service'});
  expect(reject).toHaveClass('btn');
  fireEvent.click(reject);
  expect(await screen.findByRole('alert')).toHaveTextContent(/reason/i);
  fireEvent.change(screen.getByLabelText('Rejection or takedown reason'),{target:{value:'  Needs clearer scope  '}});
  reject.focus();
  fireEvent.click(reject);
  expect(writes).toHaveLength(0);
  fireEvent.click(screen.getByRole('button',{name:'Cancel confirmation'}));
  expect(reject).toHaveFocus();
  expect(writes).toHaveLength(0);
  fireEvent.click(reject);
  fireEvent.click(screen.getByRole('button',{name:'Confirm rejection'}));
  await waitFor(()=>expect(writes).toEqual([{path:'/creative/admin/listings/3/moderate',method:'POST',body:{status:'REJECTED',reason:'Needs clearer scope'}}]));
});
it('confirms service takedown and preserves the moderation payload',async()=>{
  const {writes}=open('creative',{services:[{...service,status:'APPROVED'}]});
  await screen.findByRole('button',{name:'Take down Test service'});
  fireEvent.change(screen.getByLabelText('Rejection or takedown reason'),{target:{value:'Investigated misleading service'}});
  fireEvent.click(screen.getByRole('button',{name:'Take down Test service'}));
  expect(writes).toHaveLength(0);
  fireEvent.click(screen.getByRole('button',{name:'Confirm takedown'}));
  await waitFor(()=>expect(writes[0].body).toEqual({status:'TAKEN_DOWN',reason:'Investigated misleading service'}));
});
it('shows service loading, sanitized errors and a working retry',async()=>{
  const data={status:503};
  open('creative',data);
  expect(screen.getByRole('status')).toHaveTextContent(/Loading/);
  await screen.findByRole('alert');
  data.status=200;
  fireEvent.click(screen.getByRole('button',{name:'Try again'}));
  await screen.findByRole('button',{name:'Approve Test service'});
});
it('organizes account identity and verification without offering admin account mutations',async()=>{
  open('operations',{users:[account,{...account,id:5,name:'Verified seller',role:'SELLER',is_active:false,phone_verified_at:'2026-01-01',email_verified_at:'2026-01-01'},
    {...account,id:6,name:'Operator',role:'ADMIN'}]});
  const card=await screen.findByRole('article',{name:'Test buyer'});
  expect(within(card).getByText('BUYER')).toBeInTheDocument();
  expect(within(card).getByText('Active')).toBeInTheDocument();
  expect(within(card).getByText('Phone not verified')).toBeInTheDocument();
  expect(within(card).getByText('Email not verified')).toBeInTheDocument();
  const verified=screen.getByRole('article',{name:'Verified seller'});
  expect(within(verified).getByText('Suspended')).toBeInTheDocument();
  expect(within(verified).getByText('Manual phone verification recorded')).toBeInTheDocument();
  expect(within(verified).getByRole('button',{name:'Reactivate Verified seller'})).toHaveClass('btn');
  expect(within(screen.getByRole('article',{name:'Operator'})).queryByRole('button')).not.toBeInTheDocument();
  expect(screen.getByRole('region',{name:'Email processing'})).toHaveClass('admin-email-status');
});
it('validates the investigation reason and confirms suspension without changing API fields',async()=>{
  const {writes}=open('operations');
  const suspend=await screen.findByRole('button',{name:'Suspend Test buyer'});
  fireEvent.click(suspend);
  await screen.findByRole('alert');
  expect(writes).toHaveLength(0);
  fireEvent.change(screen.getByLabelText('Investigation reason'),{target:{value:'  Investigated case  '}});
  fireEvent.click(suspend);
  expect(screen.getByLabelText('Investigation reason')).toBeDisabled();
  expect(writes).toHaveLength(0);
  fireEvent.click(screen.getByRole('button',{name:'Confirm suspension'}));
  await waitFor(()=>expect(writes).toEqual([{path:'/admin/users/2/active',method:'PATCH',body:{is_active:false,reason:'Investigated case'}}]));
});
it('keeps checked verification actions immediate and sends the investigation reason',async()=>{
  const {writes}=open('operations');
  await screen.findByRole('button',{name:'Record checked phone for Test buyer'});
  fireEvent.change(screen.getByLabelText('Investigation reason'),{target:{value:'Contact verified by operator'}});
  fireEvent.click(screen.getByRole('button',{name:'Record checked phone for Test buyer'}));
  await waitFor(()=>expect(writes[0]).toEqual({path:'/admin/users/2/verify',method:'POST',body:{channel:'phone',reason:'Contact verified by operator'}}));
});
it('confirms investigated cancellation and product takedown',async()=>{
  const order={id:7,buyer_id:2,seller_id:8,status:'PREPARING',total:'100',items:[]};
  const {writes}=open('operations',{orders:[order]});
  await screen.findByRole('button',{name:'Investigated cancellation #7'});
  fireEvent.change(screen.getByLabelText('Investigation reason'),{target:{value:'Investigated case'}});
  fireEvent.click(screen.getByRole('button',{name:'Investigated cancellation #7'}));
  expect(writes).toHaveLength(0);
  fireEvent.click(screen.getByRole('button',{name:'Confirm cancellation'}));
  await waitFor(()=>expect(writes[0]).toEqual({path:'/admin/orders/7/resolve',method:'POST',body:{action:'CANCEL_INVESTIGATED',reason:'Investigated case'}}));
  await screen.findByText('Action recorded and audited.');
  fireEvent.change(screen.getByLabelText('Product ID'),{target:{value:'9'}});
  fireEvent.click(screen.getByRole('button',{name:'Take down product'}));
  expect(writes).toHaveLength(1);
  fireEvent.click(screen.getByRole('button',{name:'Confirm takedown'}));
  await waitFor(()=>expect(writes[1]).toEqual({path:'/admin/products/9/takedown',method:'POST',body:{reason:'Investigated case'}}));
});
it('shows account and audit empty states without inventing records',async()=>{
  open('operations',{users:[],audit:[]});
  await screen.findByRole('heading',{name:'No accounts on this page'});
  expect(screen.getByText('No audit events on this page.')).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:/Suspend/})).not.toBeInTheDocument();
});
it('preserves audit evidence and reason-gated private delivery investigation',async()=>{
  const order={id:7,buyer_id:2,seller_id:8,status:'DELIVERY_DISPUTED',total:'100',items:[]};
  const {writes}=open('operations',{orders:[order],audit:[{id:1,actor_id:9,entity_type:'order',entity_id:7,action:'USER_TRANSITION',reason:'Existing investigated case',created_at:'2026-11-01T12:00:00Z'}]});
  const investigate=await screen.findByRole('button',{name:'Investigate delivery #7'});
  expect(screen.getByText('USER_TRANSITION')).toBeInTheDocument();
  expect(screen.getByText('Existing investigated case')).toBeInTheDocument();
  fireEvent.click(investigate);
  expect(writes).toHaveLength(0);
  fireEvent.change(screen.getByLabelText('Investigation reason'),{target:{value:'Delivery investigation'}});
  fireEvent.click(investigate);
  await waitFor(()=>expect(writes[0]).toEqual({path:'/admin/orders/7/fulfillment',method:'POST',body:{reason:'Delivery investigation'}}));
  expect(await screen.findByText('Private test address',{exact:false})).toBeInTheDocument();
});
it('preserves service pagination offsets and refresh requests',async()=>{
  const {fetcher}=open('creative',{services:Array.from({length:50},(_,i)=>({...service,id:10+i,title:`Service fixture ${i}`}))});
  await screen.findByRole('button',{name:'Approve Service fixture 0'});
  fireEvent.click(screen.getByRole('button',{name:'More services'}));
  await waitFor(()=>expect(fetcher.mock.calls.some(([url])=>new URL(url, location.origin).searchParams.get('offset')==='50')).toBe(true));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Previous services'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'Previous services'}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Previous services'})).toBeDisabled());
  const before=fetcher.mock.calls.length;
  await waitFor(()=>expect(screen.getByRole('button',{name:'Refresh services'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'Refresh services'}));
  await waitFor(()=>expect(fetcher.mock.calls.length).toBeGreaterThan(before));
});
