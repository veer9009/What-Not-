import { afterEach, expect, it, vi } from 'vitest';
import { authApi } from './auth';
import { getAccessToken, onUnauthorized, setAccessToken } from './client';

afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it.each([
  ['request', {email:'buyer@example.test'}, {message:'If eligible, a code will be sent.',challenge:'opaque-challenge',resend_after:60}],
  ['verify', {challenge:'opaque-challenge',otp:'001234'}, {reset_token:'opaque-reset-token'}],
  ['reset', {reset_token:'opaque-reset-token',password:'A fresh password'}, {message:'Password updated. Sign in again.'}],
] as const)('sends the %s recovery request with CSRF and never bearer credentials',async(stage,body,result)=>{
  setAccessToken('previous-access');
  const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify(result)));vi.stubGlobal('fetch',fetcher);
  const controller=new AbortController();
  const response=stage==='request'?await authApi.requestPasswordRecovery(body.email,controller.signal):stage==='verify'?await authApi.verifyPasswordRecovery(body.challenge,body.otp,controller.signal):await authApi.resetPassword(body.reset_token,body.password,controller.signal);
  expect(response).toEqual(result);
  const [url,options]=fetcher.mock.calls[0];expect(url).toBe(`/api/v1/auth/password-recovery/${stage}`);
  expect(JSON.parse(options.body)).toEqual(body);expect(options.headers.get('X-WhatNot-CSRF')).toBe('1');
  expect(options.headers.has('Authorization')).toBe(false);expect(options.credentials).toBe('include');
  expect(options.cache).toBe('no-store');expect(options.signal).toBe(controller.signal);
});
it('clears local authentication only after a confirmed password reset',async()=>{
  const listener=vi.fn();const stop=onUnauthorized(listener);
  try{
    setAccessToken('old');vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({message:'Password updated. Sign in again.'}))));
    await authApi.resetPassword('reset-proof','A fresh password');expect(getAccessToken()).toBeNull();expect(listener).toHaveBeenCalledOnce();
    setAccessToken('still-active');vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('{}',{status:400})));
    await expect(authApi.resetPassword('expired','A fresh password')).rejects.toThrow(/invalid or expired/i);expect(getAccessToken()).toBe('still-active');
  }finally{stop();}
});
it('sanitizes recovery failures and preserves a bounded server cooldown',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'internal email and recovery secret'}),{status:429,headers:{'Retry-After':'45'}})));
  const error=await authApi.requestPasswordRecovery('buyer@example.test').catch(error=>error);
  expect(error.retryAfter).toBe(45);expect(error.message).not.toContain('internal');
});
