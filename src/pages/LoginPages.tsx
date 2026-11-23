import { CollectionNotice } from '../components/LegalNavigation';
import { LoginDiscoveryPanel } from '../components/LoginDiscoveryPanel';
import '../styles/login-discovery.css';
import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Logo } from '../components/Shared';
import { ErrorNotice, Field } from '../components/ApiStates';
import { authApi } from '../api/auth';
import { ApiError, errorMessage } from '../api/client';
import { roleHome, useAuth } from '../state/AuthContext';
import { useMounted } from '../state/useMounted';
import type { Registration } from '../api/types';
const roles=['buyer','seller'];
export function LoginPage({administration=false}:{administration?:boolean}){
  const {role}=useParams();const nav=useNavigate();const auth=useAuth();const mounted=useMounted();
  const [query]=useSearchParams();const services=!administration&&query.get('intent')==='services';
  const destination=(accountRole:Parameters<typeof roleHome>[0])=>services&&accountRole!=='ADMIN'?(accountRole==='SELLER'?'/seller/creative':'/register?intent=services'):roleHome(accountRole);
  const [email,setEmail]=useState('');const [password,setPassword]=useState('');const [error,setError]=useState('');const [fields,setFields]=useState<Record<string,string>>({});const [busy,setBusy]=useState(false);
  if(!administration&&role!==undefined&&!roles.includes(role))return <Navigate to="/login" replace/>;
  if(auth.user)return <Navigate to={destination(auth.user.role)} replace/>;
  async function submit(event:FormEvent){event.preventDefault();if(busy)return;const submittedPassword=password;setPassword('');if(!email.trim()||!submittedPassword){setError('Enter your email and password to continue.');return;}setBusy(true);setError('');setFields({});try{const current=await auth.login(email,submittedPassword);if(mounted.current)nav(destination(current.role),{replace:true});}catch(reason){if(mounted.current){setError(errorMessage(reason));if(reason instanceof ApiError)setFields(reason.fields);}}finally{if(mounted.current)setBusy(false);}}
  const loginForm = <form onSubmit={submit} noValidate>
    {administration?<><h1>What Not? Administration</h1><p>Authorized administrators only</p></>:<><h2>Welcome back</h2><p>Use your registered email and password.</p></>}
    <Field label={administration?'Email':'Email address'} name="email" type="email" value={email} onChange={setEmail} maxLength={320} error={fields.email}/>
    <Field label="Password" name="password" type="password" value={password} onChange={setPassword} maxLength={128} error={fields.password}/>
    {(error||auth.error)&&<ErrorNotice message={error||auth.error}/>}
    <button className="btn btn-primary wide" disabled={busy}>{busy?'Signing in...':'Sign in'}</button>
    {!administration&&<div className="login-account-links"><Link className="text-link" to="/forgot-password">Forgot password?</Link><Link className="text-link" to="/register?role=buyer">Create Buyer Account</Link><Link className="text-link" to="/register?role=seller">Become a seller</Link><Link className="text-link" to="/register?intent=services">Offer your services</Link></div>}
    <CollectionNotice label="Sign-in">Your email and password are sent to the API for authentication. Security rate limits use account and request-source information.</CollectionNotice><small>Sessions restore securely after reload and expire automatically. Buyer and seller sessions last up to 8 hours; administrator sessions last up to 15 minutes.</small>
  </form>;
  if(administration)return <main id="main-content" tabIndex={-1} className="login-page"><div className="login-brand"><Logo/></div><div className="login-form-wrap admin-login-form">{loginForm}</div></main>;
  return <main id="main-content" tabIndex={-1} className="login-split community-login"><LoginDiscoveryPanel/><div className="login-form-wrap"><Link to="/">Back home</Link>{loginForm}</div></main>;
}
export function RegisterPage(){
  const [query]=useSearchParams();
  const auth=useAuth();const services=query.get('intent')==='services';
  const fixedRole=services||query.get('role')==='seller'?'SELLER':query.get('role')==='buyer'?'BUYER':undefined;
  const title=services?'Service Provider Registration':fixedRole==='SELLER'?'Create Seller Account':fixedRole==='BUYER'?'Create Buyer Account':'Create account';
  const signIn=services?'/login?intent=services':'/login';
  const [form,setForm]=useState<Registration>({name:'',email:'',phone:'',password:'',role:query.get('role')==='seller'?'SELLER':'BUYER'});const [error,setError]=useState('');const [fields,setFields]=useState<Record<string,string>>({});const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);
  const set=(key:keyof Registration,value:string)=>setForm(current=>({...current,[key]:value}));
  async function submit(event:FormEvent){event.preventDefault();if(busy||auth.user)return;setBusy(true);setError('');setFields({});setNotice('');const payload={...form,role:fixedRole??form.role};try{await authApi.register(payload);setNotice(services?'Account created. Sign in to set up your provider profile and submit services for review.':payload.role==='SELLER'?'Account created. Sign in, then create your complete seller profile.':'Account created. Sign in to access your buyer account.');}catch(reason){setError(reason instanceof ApiError&&reason.status===409?'This email or phone is already registered. Sign in to your existing account.':errorMessage(reason));if(reason instanceof ApiError)setFields(reason.fields);}finally{setForm(current=>({...current,password:''}));setBusy(false);}}
  if(auth.user)return <main id="main-content" tabIndex={-1} className="login-split community-login"><LoginDiscoveryPanel/><div className="login-form-wrap register-form"><h2>{services?'Offer your services':'Your account'}</h2>{services&&auth.user.role==='SELLER'?<><p>Use your existing account to create your provider profile. Service listings require administrator approval.</p><Link to="/seller/creative">Open your creative studio</Link></>:<><p>{services&&auth.user.role==='BUYER'?'Buyer-to-provider enrollment is not yet supported. Your buyer account and permissions remain unchanged. Please do not create another account.':'You are already signed in.'}</p><Link to={roleHome(auth.user.role)}>Return to your workspace</Link></>}</div></main>;
  return <main id="main-content" tabIndex={-1} className="login-split community-login"><LoginDiscoveryPanel/>
    <div className="login-form-wrap register-form"><Link to={signIn}>Back to sign in</Link>
      <form onSubmit={submit}><h2>{title}</h2>
        <p>{services?'Use your seller account to offer VFX and video editing services. After sign-in, add your provider profile, category, portfolio, pricing and service area in your creative studio. Listings require administrator approval.':'Seller accounts need a complete shop profile after sign-in.'}</p>
        {services&&<p>Already registered? <Link to={signIn}>Sign in to your existing account</Link>. Buyer-to-provider enrollment is not yet supported; please do not create another account.</p>}
        <CollectionNotice label="Account">We collect your name, email, phone and password for your account and delivery contact. Age eligibility and the formal grievance process remain owner decisions before beta admission.</CollectionNotice>
        {(['name','email','phone','password'] as const).map(key=><Field key={key} name={key} label={{name:'Name',email:'Email address',phone:'Phone',password:'Password'}[key]} type={key==='password'?'password':key==='email'?'email':'text'} value={form[key]} onChange={value=>set(key,value)} required maxLength={{name:120,email:320,phone:32,password:128}[key]} error={fields[key]}/>)}
        {!fixedRole&&<label>Account type<select value={form.role} onChange={event=>set('role',event.target.value)}><option value="BUYER">Buyer</option><option value="SELLER">Seller</option></select></label>}
        <p>Password: 8-128 characters. Spaces are preserved.</p>{error&&<ErrorNotice message={error}/>}
        {notice&&<p className="success-note" role="status">{notice} <Link to={signIn}>Sign in</Link></p>}
        <button className="btn btn-primary wide" disabled={busy}>{busy?'Creating account...':'Create account'}</button>
      </form>
    </div></main>;
}
