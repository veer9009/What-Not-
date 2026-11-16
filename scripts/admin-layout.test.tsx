// Test fixtures only: real components, mocked HTTP, no application records created.
import { writeFileSync } from 'node:fs';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, it, vi } from 'vitest';
import { AdminOperationsPage, CreativeModerationPage } from '../src/pages/AdminOperations';

vi.mock('../src/state/AuthContext',()=>({useAuth:()=>({user:{role:'ADMIN',name:'UI test operator'},logout:vi.fn()})}));
afterEach(()=>vi.unstubAllGlobals());

it.each(['creative-populated','creative-empty','operations-populated','operations-empty'])('exports real %s UI markup for offline geometry and screenshots',async scenario=>{
  const empty=scenario.endsWith('empty');
  const base={id:2,name:'Synthetic test account',email:'test-only-long-address@example.invalid',phone:'1000000000',role:'BUYER',is_active:true,phone_verified_at:null,email_verified_at:null};
  const service={id:3,provider_id:4,title:'Synthetic service fixture',description:'Offline UI test content. This service is not stored or offered in the marketplace.',category:'Design',pricing:'FIXED',amount:'100.00',remote:true,portfolio:[],status:'PENDING',updated_at:'2026-11-01T12:00:00Z'};
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const path=new URL(input,location.origin).pathname.replace('/api/v1','');
    const body=path==='/admin/users'?(empty?[]:[base,{...base,id:5,name:'Synthetic suspended seller with a long display name',role:'SELLER',is_active:false,phone_verified_at:'2026-11-01',email_verified_at:'2026-11-01'},{...base,id:6,name:'Synthetic operator',role:'ADMIN'}]):
      path==='/admin/orders'?(empty?[]:[{id:7,buyer_id:2,seller_id:5,status:'DELIVERY_DISPUTED',total:'100.00',items:[{name:'Test item',quantity:1,product_id:10}]},{id:8,buyer_id:2,seller_id:5,status:'PREPARING',total:'200.00',items:[]}]):
      path==='/admin/audit'?(empty?[]:[{id:1,action:'USER_TRANSITION',entity_type:'order',entity_id:7,actor_id:6,reason:'Synthetic audit fixture; no audit record created.',created_at:'2026-11-01T12:00:00Z'}]):
      path==='/admin/operations'?{email_provider_enabled:false,outbox_counts:empty?{}:{PENDING:2,SENT:3,FAILED:1},oldest_pending_at:null}:
      empty?[]:[service,{...service,id:9,title:'Synthetic approved service',status:'APPROVED'}];
    return new Response(JSON.stringify(body),{status:200});
  }));
  render(<MemoryRouter>{scenario.startsWith('creative')?<CreativeModerationPage/>:<AdminOperationsPage/>}</MemoryRouter>);
  await screen.findByRole(empty?'heading':'button',{name:scenario.startsWith('creative')?(empty?'No services on this page':'Approve Synthetic service fixture'):(empty?'No accounts on this page':'Suspend Synthetic test account')});
  writeFileSync(`docs/security/evidence/admin-${scenario}.html`,document.body.innerHTML);
});
