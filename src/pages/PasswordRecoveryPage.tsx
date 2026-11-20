import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '../api/auth';
import { ApiError, errorMessage } from '../api/client';
import { ErrorNotice, Field } from '../components/ApiStates';
import { LoginDiscoveryPanel } from '../components/LoginDiscoveryPanel';
import '../styles/login-discovery.css';
import '../styles/password-recovery.css';

const requestNotice='If this account is eligible, a recovery code will be sent. Check your email and enter the code below.';
type Step='email'|'code'|'password'|'complete';

export function PasswordRecoveryPage(){
  const [step,setStep]=useState<Step>('email');
  const [email,setEmail]=useState('');const [otp,setOtp]=useState('');
  const [password,setPassword]=useState('');const [confirmation,setConfirmation]=useState('');
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const [remaining,setRemaining]=useState(0);
  const secrets=useRef({challenge:'',resetToken:''});
  const request=useRef<AbortController|null>(null);
  const heading=useRef<HTMLHeadingElement>(null);
  useEffect(()=>()=>{request.current?.abort();secrets.current={challenge:'',resetToken:''};},[]);
  useEffect(()=>{heading.current?.focus();},[step]);
  useEffect(()=>{if(!remaining)return;const timer=window.setTimeout(()=>setRemaining(value=>Math.max(0,value-1)),1000);return()=>window.clearTimeout(timer);},[remaining]);
  function begin(){request.current?.abort();const controller=new AbortController();request.current=controller;setBusy(true);setError('');return controller;}
  function failure(reason:unknown,controller:AbortController){
    if(controller.signal.aborted)return;
    setError(errorMessage(reason));
    if(reason instanceof ApiError&&reason.status===429)setRemaining(Math.max(60,reason.retryAfter||0));
  }
  async function sendCode(event?:FormEvent){
    event?.preventDefault();if(busy||(!event&&remaining>0))return;
    if(!email.trim()||!/^\S+@\S+\.\S+$/.test(email.trim())){setError('Enter a valid email address.');return;}
    const controller=begin();
    try{
      const result=await authApi.requestPasswordRecovery(email.trim(),controller.signal);
      if(controller.signal.aborted)return;
      secrets.current={challenge:result.challenge,resetToken:''};setOtp('');setNotice(requestNotice);
      setRemaining(Math.max(60,result.resend_after));setStep('code');
    }catch(reason){failure(reason,controller);}finally{if(!controller.signal.aborted)setBusy(false);}
  }
  async function verify(event:FormEvent){
    event.preventDefault();if(busy)return;
    const code=otp.trim();setOtp('');if(!/^\d{6}$/.test(code)){setError('Enter the six-digit verification code.');return;}
    const controller=begin();
    try{
      const result=await authApi.verifyPasswordRecovery(secrets.current.challenge,code,controller.signal);
      if(controller.signal.aborted)return;
      secrets.current={challenge:'',resetToken:result.reset_token};setNotice('');setStep('password');
    }catch(reason){failure(reason,controller);}finally{if(!controller.signal.aborted)setBusy(false);}
  }
  async function reset(event:FormEvent){
    event.preventDefault();if(busy)return;
    const submittedPassword=password;const matching=submittedPassword===confirmation;
    setPassword('');setConfirmation('');
    if(submittedPassword.length<8||submittedPassword.length>128){setError('Use a password between 8 and 128 characters.');return;}
    if(!matching){setError('The passwords do not match. Enter both passwords again.');return;}
    const controller=begin();
    try{
      const result=await authApi.resetPassword(secrets.current.resetToken,submittedPassword,controller.signal);
      if(controller.signal.aborted)return;
      secrets.current={challenge:'',resetToken:''};setEmail('');setOtp('');setNotice(result.message);setStep('complete');
    }catch(reason){failure(reason,controller);}finally{if(!controller.signal.aborted)setBusy(false);}
  }
  function restart(){request.current?.abort();secrets.current={challenge:'',resetToken:''};setOtp('');setPassword('');setConfirmation('');setError('');setNotice('');setBusy(false);setStep('email');}
  return <main id="main-content" tabIndex={-1} className="login-split community-login password-recovery-page">
    <LoginDiscoveryPanel/>
    <div className="login-form-wrap"><Link to="/login">Back to sign in</Link>
      <form onSubmit={step==='email'?sendCode:step==='code'?verify:reset} noValidate>
        <h2 ref={heading} tabIndex={-1}>{step==='complete'?'Password changed':'Reset your password'}</h2>
        {step!=='complete'&&<ol className="recovery-steps" aria-label="Password recovery steps">{(['email','code','password'] as const).map((value,index)=><li key={value} aria-current={step===value?'step':undefined}>{index+1}. {['Email','Verify code','New password'][index]}</li>)}</ol>}
        {step==='email'&&<><p>Enter the email address you use to sign in.</p><Field label="Email address" name="email" type="email" value={email} onChange={setEmail} maxLength={320}/></>}
        {notice&&<p className="success-note" role="status">{notice}</p>}
        {step==='code'&&<><label><span>Verification code</span><input aria-label="Verification code" name="otp" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={otp} onChange={event=>setOtp(event.target.value)}/></label><p>Codes expire after five minutes. You can request a new code if needed.</p></>}
        {step==='password'&&<><p>Use 8–128 characters. Spaces are preserved.</p><Field label="New password" name="new-password" type="password" value={password} onChange={setPassword} maxLength={128}/><Field label="Confirm new password" name="confirm-password" type="password" value={confirmation} onChange={setConfirmation} maxLength={128}/></>}
        {error&&<ErrorNotice message={error}/>}
        {step!=='complete'&&<button className="btn btn-primary wide" disabled={busy}>{busy?'Please wait…':step==='email'?'Request code':step==='code'?'Verify code':'Change password'}</button>}
        {step==='code'&&<><button type="button" className="btn btn-outline wide" disabled={busy||remaining>0} onClick={()=>void sendCode()}>{busy?'Please wait…':remaining>0?`Resend code in ${remaining}s`:'Resend code'}</button><button type="button" className="text-link recovery-restart" onClick={restart}>Use another email</button></>}
        {step==='password'&&<button type="button" className="text-link recovery-restart" onClick={restart}>Request a new code</button>}
        {step==='complete'&&<Link className="btn btn-primary wide" to="/login">Return to sign in</Link>}
      </form>
    </div>
  </main>;
}
