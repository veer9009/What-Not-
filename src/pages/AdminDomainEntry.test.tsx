import { render,screen,waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach,expect,it,vi } from 'vitest';
import App from '../App';
import { setAccessToken } from '../api/client';
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it('opens Professional moderation directly from its category destination',async()=>{
 setAccessToken('synthetic-admin-domain');const paths:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async(input:string)=>{const path=new URL(input,location.origin).pathname+new URL(input,location.origin).search;paths.push(path);return new Response(JSON.stringify(path.endsWith('/auth/me')?{id:1,name:'Admin',email:'admin@example.test',role:'ADMIN'}:path.endsWith('/notifications/unread-count')?{count:0}:[]));}));
 render(<MemoryRouter initialEntries={['/admin/creative?domain=PROFESSIONAL']}><App/></MemoryRouter>);
 expect(await screen.findByLabelText('Service domain')).toHaveValue('PROFESSIONAL');
 await waitFor(()=>expect(paths.some(path=>path.includes('/creative/admin/listings?')&&path.includes('domain=PROFESSIONAL'))).toBe(true));
 expect(paths.some(path=>path.includes('domain=CREATIVE'))).toBe(false);
});
