import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../App';
import { setAccessToken } from '../api/client';

afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();vi.useRealTimers();vi.restoreAllMocks();});
function open(handler:(path:string,body:Record<string,string>)=>[number,unknown]|Promise<[number,unknown]>){
  const requests=vi.fn(async(input:string,options:RequestInit)=>{
    const path=new URL(input,location.origin).pathname.replace('/api/v1','');
    const [status,body]=path==='/auth/refresh'?[401,{}]:await handler(path,JSON.parse(String(options.body||'{}')));
    return new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
  });
  vi.stubGlobal('fetch',requests);
  const view=render(<MemoryRouter initialEntries={['/forgot-password']}><App/></MemoryRouter>);
  return {...view,requests};
}
const requestResponse={message:'If this account is eligible, a recovery code will be sent.',challenge:'opaque-challenge',resend_after:60};
async function requestCode(){
  fireEvent.change(screen.getByLabelText('Email address'),{target:{value:'person@example.test'}});
  await userEvent.click(screen.getByRole('button',{name:'Request code'}));
  await screen.findByLabelText('Verification code');
}
it('completes email, code and new password steps without persisting recovery secrets',async()=>{
  const localWrite=vi.spyOn(Storage.prototype,'setItem');
  open(path=>[200,path.endsWith('/request')?requestResponse:path.endsWith('/verify')?{reset_token:'memory-token'}:{message:'Password changed. Existing sessions have been revoked.'}]);
  expect(screen.getByRole('heading',{name:'Reset your password'})).toBeInTheDocument();
  await requestCode();
  expect(screen.getByRole('status')).toHaveTextContent('If this account is eligible');
  expect(screen.getByRole('button',{name:/Resend code in 60s/})).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Verification code'),{target:{value:'123456'}});
  await userEvent.click(screen.getByRole('button',{name:'Verify code'}));
  fireEvent.change(await screen.findByLabelText('New password'),{target:{value:'a-new-password'}});
  fireEvent.change(screen.getByLabelText('Confirm new password'),{target:{value:'a-new-password'}});
  await userEvent.click(screen.getByRole('button',{name:'Change password'}));
  expect(await screen.findByRole('heading',{name:'Password changed'})).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('Existing sessions have been revoked.');
  expect(screen.getByRole('link',{name:'Return to sign in'})).toHaveAttribute('href','/login');
  expect(screen.queryByLabelText('New password')).toBeNull();
  expect(localWrite).not.toHaveBeenCalled(); localWrite.mockRestore();
  expect(location.search).not.toMatch(/opaque-challenge|memory-token/);
});
it.each(['wrong','expired'])('keeps a %s code failure retryable without advancing',async()=>{
  open(path=>path.endsWith('/request')?[200,requestResponse]:[400,{detail:'invalid'}]);
  await requestCode(); await userEvent.type(screen.getByLabelText('Verification code'),'123456');
  await userEvent.click(screen.getByRole('button',{name:'Verify code'}));
  expect(await screen.findByRole('alert')).toHaveTextContent(/invalid|expired/i);
  expect(screen.queryByLabelText('New password')).toBeNull();
  expect(screen.getByLabelText('Verification code')).toHaveValue('');
});
it('clears password inputs immediately when submitting a reset that later fails',async()=>{
  let rejectReset:((result:[number,unknown])=>void)|undefined;
  open(path=>path.endsWith('/request')?[200,requestResponse]:path.endsWith('/verify')?[200,{reset_token:'memory-token'}]:new Promise(resolve=>{rejectReset=resolve;}));
  await requestCode(); await userEvent.type(screen.getByLabelText('Verification code'),'123456');
  await userEvent.click(screen.getByRole('button',{name:'Verify code'}));
  await userEvent.type(await screen.findByLabelText('New password'),'a-new-password');
  await userEvent.type(screen.getByLabelText('Confirm new password'),'a-new-password');
  await userEvent.click(screen.getByRole('button',{name:'Change password'}));
  expect(screen.getByLabelText('New password')).toHaveValue('');
  expect(screen.getByLabelText('Confirm new password')).toHaveValue('');
  await act(async()=>rejectReset?.([400,{detail:'invalid'}]));
  expect(await screen.findByRole('alert')).toBeInTheDocument();
});
it('aborts pending requests when leaving recovery',async()=>{
  let pendingSignal:AbortSignal|undefined;
  open(()=>new Promise(()=>{}));
  const original=fetch;vi.stubGlobal('fetch',vi.fn((input:string,options:RequestInit)=>{pendingSignal=options.signal as AbortSignal;return original(input,options);}));
  await userEvent.type(screen.getByLabelText('Email address'),'person@example.test');
  await userEvent.click(screen.getByRole('button',{name:'Request code'}));
  await userEvent.click(screen.getByRole('link',{name:'Back to sign in'}));
  await waitFor(()=>expect(pendingSignal?.aborted).toBe(true));
});
it('enables resend after cooldown and replaces the challenge after a new request',async()=>{
  let requestCount=0;
  vi.useFakeTimers();
  const {requests}=open(path=>[200,path.endsWith('/request')?{...requestResponse,challenge:`challenge-${++requestCount}`}:{reset_token:'memory-token'}]);
  fireEvent.change(screen.getByLabelText('Email address'),{target:{value:'person@example.test'}});
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Request code'}));});
  for(let second=0;second<60;second++)await act(async()=>{await vi.advanceTimersByTimeAsync(1000);});
  expect(screen.getByRole('button',{name:'Resend code'})).toBeEnabled();
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Resend code'}));});
  expect(screen.getByRole('button',{name:'Resend code in 60s'})).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Verification code'),{target:{value:'123456'}});
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Verify code'}));});
  expect(screen.getByLabelText('New password')).toBeInTheDocument();
  const verification=requests.mock.calls.find(([input])=>String(input).endsWith('/verify'));
  expect(JSON.parse(String(verification?.[1].body))).toEqual({challenge:'challenge-2',otp:'123456'});
});
