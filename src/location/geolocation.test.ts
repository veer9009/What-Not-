import { afterEach, describe, expect, it, vi } from 'vitest';
import { acquireLocation } from './geolocation';

afterEach(()=>{vi.useRealTimers();vi.unstubAllGlobals();});

describe('explicit location acquisition', () => {
  it('returns six-place coordinates with a finite fresh-position timeout', async () => {
    const result = await acquireLocation({ getCurrentPosition(success, _error, options) {
      expect(options?.timeout).toBe(20000);
      expect(options?.maximumAge).toBe(0);
      expect(options?.enableHighAccuracy).toBe(true);
      success({ coords: { latitude: 19.12345678, longitude: 72.12345678, accuracy: 24.5 } } as GeolocationPosition);
    }});
    expect(result).toEqual({latitude:19.123457, longitude:72.123457, accuracyMeters:24.5});
  });
  it.each([undefined, NaN, Infinity, -1])('does not invent accuracy when the provider reports %s', async accuracy => {
    const result = await acquireLocation({getCurrentPosition(success) {
      success({coords:{latitude:0,longitude:0,accuracy}} as GeolocationPosition);
    }});
    expect(result).toEqual({latitude:0,longitude:0,accuracyMeters:null});
  });
  it.each([[1,'denied'],[2,'unavailable'],[3,'timeout'],[99,'unavailable']])('sanitizes browser error %s', async (code, expected) => {
    await expect(acquireLocation({getCurrentPosition(_success, error) {
      error?.({code, message:'sensitive browser error'} as GeolocationPositionError);
    }})).rejects.toMatchObject({code:expected});
  });
  it('supports browsers without geolocation', async () => {
    await expect(acquireLocation(null)).rejects.toMatchObject({code:'unsupported'});
  });
  it('explains insecure contexts before requesting permission', async()=>{
    vi.stubGlobal('isSecureContext',false);
    const getCurrentPosition=vi.fn();
    await expect(acquireLocation({getCurrentPosition})).rejects.toMatchObject({code:'insecure'});
    expect(getCurrentPosition).not.toHaveBeenCalled();
  });
  it('bounds permission waits even when the browser never invokes a callback',async()=>{
    vi.useFakeTimers();
    const result=expect(acquireLocation({getCurrentPosition:vi.fn()})).rejects.toMatchObject({code:'timeout'});
    await vi.advanceTimersByTimeAsync(30000);
    await result;
    expect(vi.getTimerCount()).toBe(0);
  });
  it('cancels an abandoned request and clears its deadline',async()=>{
    vi.useFakeTimers();
    const controller=new AbortController();
    const result=expect(acquireLocation({getCurrentPosition:vi.fn()},controller.signal)).rejects.toMatchObject({name:'AbortError'});
    controller.abort();await result;
    expect(vi.getTimerCount()).toBe(0);
  });
  it('ignores a late position after the overall deadline',async()=>{
    vi.useFakeTimers();let success!:PositionCallback;
    const result=expect(acquireLocation({getCurrentPosition(callback){success=callback;}})).rejects.toMatchObject({code:'timeout'});
    await vi.advanceTimersByTimeAsync(30000);await result;
    success({coords:{latitude:0,longitude:0}} as GeolocationPosition);
    expect(vi.getTimerCount()).toBe(0);
  });
  it('sanitizes a browser security exception when accessing geolocation',async()=>{
    vi.stubGlobal('navigator',{get geolocation(){throw new DOMException('private browser detail','SecurityError');}});
    await expect(acquireLocation()).rejects.toMatchObject({code:'denied'});
  });
  it.each([[NaN,0],[0,Infinity],[91,0],[0,-181]])('rejects invalid acquired coordinates', async (latitude, longitude) => {
    await expect(acquireLocation({getCurrentPosition(success) {
      success({coords:{latitude,longitude}} as GeolocationPosition);
    }})).rejects.toMatchObject({code:'invalid'});
  });
});
