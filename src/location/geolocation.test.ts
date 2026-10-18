import { describe, expect, it } from 'vitest';
import { acquireLocation } from './geolocation';

describe('explicit location acquisition', () => {
  it('returns six-place coordinates with a finite fresh-position timeout', async () => {
    const result = await acquireLocation({ getCurrentPosition(success, _error, options) {
      expect(options?.timeout).toBe(10000);
      expect(options?.maximumAge).toBe(0);
      success({ coords: { latitude: 19.12345678, longitude: 72.12345678 } } as GeolocationPosition);
    }});
    expect(result).toEqual({latitude:19.123457, longitude:72.123457});
  });
  it.each([[1,'denied'],[2,'unavailable'],[3,'timeout'],[99,'unavailable']])('sanitizes browser error %s', async (code, expected) => {
    await expect(acquireLocation({getCurrentPosition(_success, error) {
      error?.({code, message:'sensitive browser error'} as GeolocationPositionError);
    }})).rejects.toMatchObject({code:expected});
  });
  it('supports browsers without geolocation', async () => {
    await expect(acquireLocation(null)).rejects.toMatchObject({code:'unsupported'});
  });
  it.each([[NaN,0],[0,Infinity],[91,0],[0,-181]])('rejects invalid acquired coordinates', async (latitude, longitude) => {
    await expect(acquireLocation({getCurrentPosition(success) {
      success({coords:{latitude,longitude}} as GeolocationPosition);
    }})).rejects.toMatchObject({code:'invalid'});
  });
});
