import { afterEach, expect, it, vi } from 'vitest';
import { uploadBinary, setAccessToken, getAccessToken } from './client';
class Request {
  static last: Request;
  upload = { onprogress: null as null | ((event: { lengthComputable:boolean; loaded:number; total:number }) => void) };
  headers: Record<string,string> = {}; status = 200; responseText = '{"id":3}'; withCredentials = false;
  onload: (()=>void) | null = null; onerror: (()=>void) | null = null; onabort: (()=>void) | null = null; ontimeout: (()=>void) | null = null; timeout = 0;
  abort = vi.fn(()=>this.onabort?.());
  open = vi.fn(); send = vi.fn(); setRequestHeader(key:string,value:string) { this.headers[key]=value; }
  constructor() { Request.last=this; }
}
afterEach(()=>{setAccessToken(null);vi.unstubAllGlobals();});
it('uploads raw files with bearer credentials and real progress',async()=>{
  vi.stubGlobal('XMLHttpRequest',Request);setAccessToken('token');const progress=vi.fn();const file=new File(['image'],'a.png',{type:'image/png'});
  const pending=uploadBinary('/products/3/images',file,progress);const request=Request.last;
  expect(request.open.mock.calls[0][1]).toContain('/api/v1/products/3/images');expect(request.headers.Authorization).toBe('Bearer token');expect(request.headers['Content-Type']).toBe('image/png');expect(request.send).toHaveBeenCalledWith(file);expect(request.withCredentials).toBe(false);
  request.upload.onprogress?.({lengthComputable:true,loaded:2,total:5});expect(progress).toHaveBeenCalledWith(40);request.onload?.();expect(await pending).toEqual({id:'3'});
});
it('rejects a stale upload response without clearing a newer session',async()=>{
  vi.stubGlobal('XMLHttpRequest',Request);setAccessToken('old');const pending=uploadBinary('/products/3/images',new File(['a'],'a.jpg'));setAccessToken('new');Request.last.status=401;Request.last.onload?.();await expect(pending).rejects.toThrow(/session changed/i);expect(getAccessToken()).toBe('new');
});
it('expires a rejected upload token and hides internal response details',async()=>{
  vi.stubGlobal('XMLHttpRequest',Request);setAccessToken('old');const pending=uploadBinary('/products/3/images',new File(['a'],'a.jpg'));Request.last.status=401;Request.last.responseText='private traceback';Request.last.onload?.();await expect(pending).rejects.toThrow(/session expired/i);expect(getAccessToken()).toBeNull();
});
it('aborts a pending upload when its signal is cancelled',async()=>{
  vi.stubGlobal('XMLHttpRequest',Request);const controller=new AbortController();
  const pending=uploadBinary('/products/3/images',new File(['a'],'a.jpg'),undefined,controller.signal);
  controller.abort();await expect(pending).rejects.toMatchObject({name:'AbortError'});expect(Request.last.abort).toHaveBeenCalledOnce();
});
it('does not start an upload with an already cancelled signal',async()=>{
  vi.stubGlobal('XMLHttpRequest',Request);const controller=new AbortController();controller.abort();
  await expect(uploadBinary('/products/3/images',new File(['a'],'a.jpg'),undefined,controller.signal)).rejects.toMatchObject({name:'AbortError'});
});
it('bounds upload duration and reports timeout without exposing response details',async()=>{
  vi.stubGlobal('XMLHttpRequest',Request);const pending=uploadBinary('/products/3/images',new File(['a'],'a.jpg'));
  expect(Request.last.timeout).toBe(120000);Request.last.ontimeout?.();await expect(pending).rejects.toThrow(/timed out/i);
});
it('explains image content rejection safely',async()=>{
  vi.stubGlobal('XMLHttpRequest',Request);const pending=uploadBinary('/products/3/images',new File(['a'],'a.jpg'));
  Request.last.status=422;Request.last.responseText='private image decoder traceback';Request.last.onload?.();await expect(pending).rejects.toThrow(/valid JPG, PNG or WebP/i);
});
