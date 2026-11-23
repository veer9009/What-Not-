import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { LoginPage, RegisterPage } from './LoginPages';
import { authApi } from '../api/auth';

const state=vi.hoisted(()=>({user:null as null|{role:'BUYER'|'SELLER'|'ADMIN'},loading:false,error:'',login:vi.fn()}));
vi.mock('../state/AuthContext',()=>({useAuth:()=>state,roleHome:(role:string)=>`/${role.toLowerCase()}`}));
afterEach(()=>{state.user=null;vi.restoreAllMocks();});
function open(path:string){render(<MemoryRouter initialEntries={[path]}><RegisterPage/></MemoryRouter>);}

it.each([['/register?role=seller','Create Seller Account','SELLER'],['/register?role=buyer','Create Buyer Account','BUYER'],['/register?intent=services','Service Provider Registration','SELLER']])('fixes registration intent at %s',async(path,title,role)=>{
  const register=vi.spyOn(authApi,'register').mockResolvedValue({} as never);
  open(path);
  expect(screen.getByRole('heading',{name:title})).toBeInTheDocument();
  expect(screen.queryByRole('combobox',{name:'Account type'})).toBeNull();
  for(const [label,value] of [['Name','Local creator'],['Email address','creator@example.test'],['Phone','1234567890'],['Password','synthetic password']])fireEvent.change(screen.getByLabelText(label),{target:{value}});
  fireEvent.submit(screen.getByLabelText('Name').closest('form')!);
  expect(await screen.findByRole('status')).toHaveTextContent('Account created');
  expect(register).toHaveBeenCalledWith(expect.objectContaining({role}));
  if(path.includes('services'))expect(screen.getByRole('link',{name:'Sign in'})).toHaveAttribute('href','/login?intent=services');
});

it('offers the services journey from unified login',()=>{
  render(<MemoryRouter><LoginPage/></MemoryRouter>);
  expect(screen.getByRole('link',{name:'Offer your services'})).toHaveAttribute('href','/register?intent=services');
  expect(screen.getByRole('link',{name:'Create Buyer Account'})).toHaveAttribute('href','/register?role=buyer');
});

it('never asks existing buyers to register again or changes their role',()=>{
  state.user={role:'BUYER'};const register=vi.spyOn(authApi,'register');open('/register?intent=services');
  expect(screen.getByText(/buyer-to-provider enrollment is not yet supported/i)).toBeInTheDocument();
  expect(screen.queryByLabelText('Password')).toBeNull();expect(register).not.toHaveBeenCalled();
  expect(screen.getByRole('link',{name:'Return to your workspace'})).toHaveAttribute('href','/buyer');
});

it('offers existing sellers their existing studio',()=>{
  state.user={role:'SELLER'};open('/register?intent=services');
  expect(screen.getByRole('link',{name:'Open your creative studio'})).toHaveAttribute('href','/seller/creative');
  expect(screen.queryByLabelText('Password')).toBeNull();
});

it.each([['SELLER','Existing studio'],['BUYER','Enrollment unavailable'],['ADMIN','Administration']])('services login uses an allowlisted destination for %s',async(role,destination)=>{
  state.login.mockResolvedValue({role});
  render(<MemoryRouter initialEntries={['/login?intent=services&next=https://invalid.example/steal']}><Routes>
    <Route path="/login" element={<LoginPage/>}/><Route path="/seller/creative" element={<h1>Existing studio</h1>}/>
    <Route path="/register" element={<h1>Enrollment unavailable</h1>}/>
    <Route path="/admin" element={<h1>Administration</h1>}/>
  </Routes></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('Email address'),{target:{value:'synthetic@example.test'}});
  fireEvent.change(screen.getByLabelText('Password'),{target:{value:'synthetic password'}});
  fireEvent.click(screen.getByRole('button',{name:'Sign in'}));
  expect(await screen.findByRole('heading',{name:destination})).toBeInTheDocument();
});
