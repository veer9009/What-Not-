import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useResource } from './useResource';
describe('resource lifecycle',()=>{
  it('refuses an old reload after the route loader changes',async()=>{
    const first=vi.fn(async()=> 'order 5');const second=vi.fn(async()=> 'order 6');
    const view=renderHook(({loader})=>useResource(loader),{initialProps:{loader:first}});
    await waitFor(()=>expect(view.result.current.data).toBe('order 5'));const stale=view.result.current.reload;
    view.rerender({loader:second});await waitFor(()=>expect(view.result.current.data).toBe('order 6'));
    let accepted:boolean|undefined;await act(async()=>{accepted=await stale();});expect(accepted).toBe(false);expect(view.result.current.data).toBe('order 6');expect(first).toHaveBeenCalledOnce();
  });
  it('refuses reload after unmount',async()=>{
    const loader=vi.fn(async()=>[]);const view=renderHook(()=>useResource(loader));await waitFor(()=>expect(view.result.current.loading).toBe(false));const stale=view.result.current.reload;view.unmount();expect(await stale()).toBe(false);expect(loader).toHaveBeenCalledOnce();
  });
});
