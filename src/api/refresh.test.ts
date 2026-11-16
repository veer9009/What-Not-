import { afterEach, expect, it, vi } from 'vitest';
import { api, getAccessToken, setAccessToken } from './client';
import { authApi } from './auth';
const user={id:'1',name:'Buyer',email:'buyer@example.test',role:'BUYER'};
const reply=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status});
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it.each([{...user,id:'2'},{...user,role:'SELLER'}])('rejects renewal into a different account or role: %j',async changed=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(reply({access_token:'original',token_type:'bearer',expires_in:900,user})).mockResolvedValueOnce(reply({access_token:'other-account',token_type:'bearer',expires_in:900,user:changed})));
  await authApi.login('buyer@example.test','synthetic-test-password');
  await expect(authApi.refresh()).rejects.toMatchObject({status:401});expect(getAccessToken()).toBeNull();
});
it('preserves a session when refresh fails temporarily and permits retry',async()=>{
  setAccessToken('current');
  const fetcher=vi.fn().mockRejectedValueOnce(new TypeError('offline')).mockResolvedValueOnce(reply({access_token:'renewed',token_type:'bearer',expires_in:900,user}));
  vi.stubGlobal('fetch',fetcher);
  await expect(authApi.refresh()).rejects.toThrow(/Unable to reach/);
  expect(getAccessToken()).toBe('current');
  await authApi.refresh();expect(getAccessToken()).toBe('renewed');
});
it('shares one rotating cookie request across concurrent unauthorized reads',async()=>{
  setAccessToken('old');let release!:(response:Response)=>void;
  const fetcher=vi.fn((url:string,options:RequestInit)=>url.endsWith('/auth/refresh')?new Promise<Response>(resolve=>{release=resolve;}):Promise.resolve(reply({},new Headers(options.headers).get('Authorization')==='Bearer renewed'?200:401)));
  vi.stubGlobal('fetch',fetcher);const reads=[api('/orders'),api('/addresses')];
  await vi.waitFor(()=>expect(release).toBeTypeOf('function'));
  expect(fetcher.mock.calls.filter(([url])=>url.endsWith('/auth/refresh'))).toHaveLength(1);
  release(reply({access_token:'renewed',token_type:'bearer',expires_in:900,user}));
  await Promise.all(reads);expect(fetcher).toHaveBeenCalledTimes(5);
});
it('retries an unauthorized request only once',async()=>{
  setAccessToken('old');
  const fetcher=vi.fn((url:string)=>Promise.resolve(url.endsWith('/auth/refresh')?reply({access_token:'renewed',token_type:'bearer',expires_in:900,user}):reply({},401)));
  vi.stubGlobal('fetch',fetcher);await expect(api('/orders')).rejects.toMatchObject({status:401});
  expect(fetcher).toHaveBeenCalledTimes(3);expect(getAccessToken()).toBeNull();
});
it('sends cookie credentials and CSRF proof only to cookie auth endpoints',async()=>{
  const fetcher=vi.fn(async(_url:string,_options:RequestInit)=>reply({access_token:'renewed',token_type:'bearer',expires_in:900,user}));vi.stubGlobal('fetch',fetcher);
  await authApi.refresh();await api('/orders');
  expect(fetcher.mock.calls[0][1]).toMatchObject({credentials:'include',method:'POST'});
  expect(new Headers(fetcher.mock.calls[0][1].headers).get('X-WhatNot-CSRF')).toBe('1');
  expect(new Headers(fetcher.mock.calls[0][1].headers).has('Authorization')).toBe(false);
  expect(fetcher.mock.calls[1][1].credentials).toBe('omit');
  expect(new Headers(fetcher.mock.calls[1][1].headers).has('X-WhatNot-CSRF')).toBe(false);
});
it('queues server logout after an in-flight login and rejects the stale login',async()=>{
  let release!:(response:Response)=>void;
  const fetcher=vi.fn((url:string)=>url.endsWith('/auth/login')?new Promise<Response>(resolve=>{release=resolve;}):Promise.resolve(reply({})));
  vi.stubGlobal('fetch',fetcher);const login=authApi.login('buyer@example.test','synthetic-test-password').catch(error=>error);
  await vi.waitFor(()=>expect(release).toBeTypeOf('function'));const logout=authApi.logout();
  expect(fetcher).toHaveBeenCalledTimes(1);release(reply({access_token:'stale',token_type:'bearer',expires_in:900,user}));
  await expect(login).resolves.toMatchObject({status:0});await logout;
  expect(fetcher.mock.calls.map(([url])=>url)).toEqual(['/api/v1/auth/login','/api/v1/auth/logout']);expect(getAccessToken()).toBeNull();
});
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it('restores a fresh page using cookie credentials and CSRF header',async()=>{
  const fetcher=vi.fn(async(_url:string,_options:RequestInit)=>reply({access_token:'restored',token_type:'bearer',expires_in:900,user}));vi.stubGlobal('fetch',fetcher);
  await authApi.refresh();expect(getAccessToken()).toBe('restored');
  expect(fetcher.mock.calls[0][1]).toMatchObject({credentials:'include',method:'POST'});
  expect(new Headers(fetcher.mock.calls[0][1].headers).get('X-WhatNot-CSRF')).toBe('1');
});
it('coalesces protected 401 renewal and retries the same mutation body once',async()=>{
  setAccessToken('old');let renewals=0;
  vi.stubGlobal('fetch',vi.fn(async(url:string,options:RequestInit)=>{
    if(url.endsWith('/auth/refresh')){renewals++;return reply({access_token:'new',token_type:'bearer',expires_in:900,user});}
    return new Headers(options.headers).get('Authorization')==='Bearer new'?reply({ok:true}):reply({},401);
  }));
  expect(await Promise.all([api('/orders',{method:'POST',body:{quantity:1},idempotencyKey:'same'}),api('/addresses')])).toEqual([{ok:true},{ok:true}]);
  expect(renewals).toBe(1);expect(getAccessToken()).toBe('new');
});
it('logout clears locally before revocation and pending refresh cannot revive it',async()=>{
  setAccessToken('old');let finish!:(value:Response)=>void;
  vi.stubGlobal('fetch',vi.fn((url:string)=>url.endsWith('/auth/refresh')?new Promise<Response>(resolve=>{finish=resolve;}):Promise.resolve(new Response(null,{status:204}))));
  const renewing=authApi.refresh();await vi.waitFor(()=>expect(finish).toBeTypeOf('function'));
  const logout=authApi.logout();expect(getAccessToken()).toBeNull();finish(reply({access_token:'late',token_type:'bearer',expires_in:900,user}));
  await renewing.catch(()=>{});await logout;expect(getAccessToken()).toBeNull();
});
