import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../App';
import { setAccessToken } from '../api/client';
import { authApi } from '../api/auth';
import approvedNeighborhood from '../assets/homepage/neighborhood-world.jpg';
import approvedNeighborhood480 from '../assets/homepage/neighborhood-world-480.webp';
import approvedNeighborhood976 from '../assets/homepage/neighborhood-world-976.webp';

afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();vi.restoreAllMocks();});
function open(path:string){
  vi.stubGlobal('fetch',vi.fn());
  const locate=vi.fn();vi.stubGlobal('navigator',{...navigator,geolocation:{getCurrentPosition:locate,watchPosition:locate}});
  render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);return locate;
}
it.each(['/login','/login/buyer','/login/seller'])('shows a unified login at %s without requesting location',path=>{
  const locate=open(path);
  expect(screen.getByRole('heading',{name:'Local possibilities, wherever you live.'})).toBeInTheDocument();
  const artwork=screen.getByTestId('login-discovery-art');
  expect(artwork).toHaveAttribute('aria-hidden','true');
  expect(artwork).toHaveTextContent('City');expect(artwork).toHaveTextContent('Town');expect(artwork).toHaveTextContent('Village');
  expect(artwork.querySelector('.login-india-map')).toBeNull();
  expect(screen.queryByText('How would you like to continue?')).toBeNull();
  expect(screen.getByText(/Illustration only/)).toBeInTheDocument();
  expect(screen.getByLabelText('Email address')).toHaveAttribute('type','email');
  expect(screen.getByLabelText('Password')).toHaveAttribute('type','password');
  expect(screen.getByRole('button',{name:'Sign in'})).toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Create Buyer Account'})).toHaveAttribute('href','/register?role=buyer');
  expect(screen.getByRole('link',{name:'Offer your services'})).toHaveAttribute('href','/register?intent=services');
  expect(screen.getByRole('link',{name:'Forgot password?'})).toHaveAttribute('href','/forgot-password');
  expect(screen.getByRole('link',{name:'Become a seller'})).toHaveAttribute('href','/register?role=seller');
  expect(within(screen.getByLabelText('Sign-in privacy notice')).getByText(/Security rate limits/)).toBeInTheDocument();
  expect(locate).not.toHaveBeenCalled();expect(fetch).not.toHaveBeenCalled();
});
it.each([['/register?role=admin','BUYER'],['/register','BUYER']])('defaults account type safely at %s',(path,role)=>{
  open(path); expect(screen.getByLabelText('Account type')).toHaveValue(role);
});
it.each(['/login','/login/buyer','/login/seller','/register','/register?role=seller','/register?role=buyer','/register?intent=services','/forgot-password'])('uses the same original approved neighborhood without geographical artwork at %s',path=>{
  open(path);
  const artwork=screen.getByTestId('login-discovery-art');
  const neighborhood=artwork.querySelector('picture img');
  expect(neighborhood).toHaveAttribute('src',approvedNeighborhood);
  expect(neighborhood).toHaveAttribute('width','976');
  expect(neighborhood).toHaveAttribute('height','596');
  expect(artwork.querySelector('source')).toHaveAttribute('srcset',expect.stringContaining(approvedNeighborhood480));
  expect(artwork.querySelector('source')).toHaveAttribute('srcset',expect.stringContaining(approvedNeighborhood976));
  expect(artwork.querySelectorAll('img')).toHaveLength(4);
  expect(artwork.querySelector('svg, canvas, iframe, object, embed, [class*="map"]')).toBeNull();
  for(const image of artwork.querySelectorAll('img'))expect(image.getAttribute('src')).not.toMatch(/india|boundary|district|country|state-map|discovery-neighborhood/i);
  expect(artwork).toHaveAttribute('aria-hidden','true');
});
it.each([['/register','BUYER'],['/register?role=seller','SELLER']])('preserves registration fields and submits the selected role at %s',async(path,role)=>{
  const register=vi.spyOn(authApi,'register').mockResolvedValue({} as Awaited<ReturnType<typeof authApi.register>>);
  open(path);
  for(const [label,value] of [['Name','Local Person'],['Email address','person@example.test'],['Phone','9000000000'],['Password','a valid password']]){
    expect(screen.getByLabelText(label)).toBeRequired();
    fireEvent.change(screen.getByLabelText(label),{target:{value}});
  }
  if(role==='SELLER')expect(screen.queryByRole('combobox',{name:'Account type'})).toBeNull();
  else expect(screen.getByRole('combobox',{name:'Account type'})).toHaveValue(role);
  expect(screen.queryByRole('option',{name:'Admin'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Create account'}));
  expect(await screen.findByRole('status')).toHaveTextContent('Account created. Sign in');
  expect(register).toHaveBeenCalledWith({name:'Local Person',email:'person@example.test',phone:'9000000000',password:'a valid password',role});
  expect(screen.getByLabelText('Password')).toHaveValue('');
  expect(screen.getByRole('link',{name:'Back to sign in'})).toHaveAttribute('href','/login');
});
it('keeps the approved shared illustration and clear progress through all three recovery steps',async()=>{
  vi.spyOn(authApi,'requestPasswordRecovery').mockResolvedValue({message:'Check your email.',challenge:'test-challenge',resend_after:60});
  vi.spyOn(authApi,'verifyPasswordRecovery').mockResolvedValue({reset_token:'test-reset-token'});
  open('/forgot-password');
  const originalArtwork=screen.getByTestId('login-discovery-art');
  const assertStep=(label:string)=>{
    expect(screen.getByTestId('login-discovery-art')).toBe(originalArtwork);
    expect(originalArtwork.querySelector('picture img')).toHaveAttribute('src',approvedNeighborhood);
    const steps=within(screen.getByRole('list',{name:'Password recovery steps'})).getAllByRole('listitem');
    expect(steps).toHaveLength(3);
    expect(steps.filter(item=>item.getAttribute('aria-current')==='step')).toHaveLength(1);
    expect(steps.find(item=>item.getAttribute('aria-current')==='step')).toHaveTextContent(label);
  };
  assertStep('Email');
  fireEvent.change(screen.getByLabelText('Email address'),{target:{value:'person@example.test'}});
  fireEvent.click(screen.getByRole('button',{name:'Request code'}));
  await screen.findByLabelText('Verification code');
  assertStep('Verify code');
  fireEvent.change(screen.getByLabelText('Verification code'),{target:{value:'123456'}});
  fireEvent.click(screen.getByRole('button',{name:'Verify code'}));
  await screen.findByLabelText('New password');
  assertStep('New password');
  expect(screen.getByLabelText('Confirm new password')).toBeInTheDocument();
});
it('keeps administration sign-in separate from the decorative public login panel',()=>{
  open('/admin/login');expect(screen.getByRole('heading',{name:'What Not? Administration'})).toBeInTheDocument();
  expect(screen.queryByTestId('login-discovery-art')).toBeNull();
  expect(screen.getByLabelText('Email')).toBeInTheDocument();
  expect(screen.queryByRole('link',{name:'Create account'})).toBeNull();
});
