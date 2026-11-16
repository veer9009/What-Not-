import { fireEvent,render,screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach,it,expect,vi } from 'vitest';
import App from '../App';
import { setAccessToken } from '../api/client';

afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});

it('requires an investigation reason and sends only authorized account action fields',async()=>{
  setAccessToken('admin-test');const writes:unknown[]=[];let active=true;
  vi.stubGlobal('fetch',vi.fn(async(input:string,options:RequestInit)=>{
    const path=new URL(input, location.origin).pathname.replace('/api/v1','');
    if(options.method==='PATCH'){const body=JSON.parse(String(options.body));writes.push(body);active=body.is_active;}
    const data=path==='/auth/me'?{id:1,name:'Operator',email:'admin@example.com',role:'ADMIN'}:
      path==='/admin/users'?[{id:2,name:'Buyer',email:'buyer@example.com',phone:'9000000000',role:'BUYER',is_active:active}]:
      path==='/admin/operations'?{email_provider_enabled:false,outbox_counts:{PENDING:1},oldest_pending_at:null}:[];
    return new Response(JSON.stringify(data),{status:200});
  }));
  render(<MemoryRouter initialEntries={['/admin/operations']}><App/></MemoryRouter>);
  await userEvent.click(await screen.findByRole('button',{name:'Suspend Buyer'}));
  expect(writes).toHaveLength(0);
  expect(await screen.findByRole('alert')).toHaveTextContent(/reason/i);
  fireEvent.change(screen.getByLabelText('Investigation reason'),{target:{value:'Investigated abuse case'}});
  await userEvent.click(screen.getByRole('button',{name:'Suspend Buyer'}));
  expect(writes).toHaveLength(0);
  await userEvent.click(screen.getByRole('button',{name:'Confirm suspension'}));
  await screen.findByRole('button',{name:'Reactivate Buyer'});
  expect(writes).toEqual([{is_active:false,reason:'Investigated abuse case'}]);
});

it.each([['BUYER','/admin/operations'],['SELLER','/admin/operations'],['BUYER','/admin/creative'],['SELLER','/admin/creative']])('keeps %s out of %s without requesting protected data',async(role,path)=>{
  setAccessToken('role-test');
  const requests:string[]=[];
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const requestPath=new URL(input, location.origin).pathname.replace('/api/v1','');
    requests.push(requestPath);
    return new Response(JSON.stringify({id:2,name:'Test user',email:'test@example.test',role}),{status:200});
  }));
  render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
  await screen.findByRole('heading',{name:'This page is not available for your account.'});
  expect(requests).toEqual(['/auth/me']);
});

it('approves the exact creative listing version the admin reviewed',async()=>{
  setAccessToken('admin-test');const writes:unknown[]=[];
  const updated_at='2026-11-03T12:00:00.123456Z';
  vi.stubGlobal('fetch',vi.fn(async(input:string,options:RequestInit)=>{
    const path=new URL(input, location.origin).pathname.replace('/api/v1','');
    if(options.method==='POST')writes.push(JSON.parse(String(options.body)));
    const data=path==='/auth/me'?{id:1,name:'Operator',email:'admin@example.com',role:'ADMIN'}:
      [{id:3,provider_id:2,title:'Video editing',description:'A creative service',category:'Video Editing',pricing:'FIXED',amount:'100.00',currency:'INR',remote:true,locality:null,portfolio:[],is_active:true,status:writes.length?'APPROVED':'PENDING',updated_at}];
    return new Response(JSON.stringify(data),{status:200});
  }));
  render(<MemoryRouter initialEntries={['/admin/creative']}><App/></MemoryRouter>);
  await userEvent.click(await screen.findByRole('button',{name:'Approve Video editing'}));
  await screen.findByRole('status');
  expect(writes).toEqual([{status:'APPROVED',expected_updated_at:updated_at}]);
});
