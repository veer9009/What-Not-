import { expect, it } from 'vitest';
import { browserRoute } from '../../scripts/phase7_network.mjs';

const config={ui:'http://127.0.0.1:51001',api:'http://127.0.0.1:51002'};
it('permits only owned origins and redirects an arbitrary baked API to the disposable server',()=>{
  expect(browserRoute(config.ui+'/assets/index.js',config)).toEqual({action:'continue'});
  expect(browserRoute(config.api+'/api/v1/auth/login',config)).toEqual({action:'continue'});
  expect(browserRoute('http://127.0.0.1:8000/api/v1/auth/login',config)).toEqual({action:'redirect',url:config.api+'/api/v1/auth/login'});
  expect(browserRoute('https://existing.example.com/api/v1/auth/login',config)).toEqual({action:'redirect',url:config.api+'/api/v1/auth/login'});
  expect(browserRoute('https://existing.example.com/other',config)).toEqual({action:'block'});
  expect(browserRoute('http://127.0.0.1:5432/other',config)).toEqual({action:'block'});
  expect(browserRoute('data:text/plain,other',config)).toEqual({action:'block'});
});
