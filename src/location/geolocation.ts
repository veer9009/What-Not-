// Coordinate sources (manual, device, future address search) share this boundary.
export interface Coordinates { latitude: number; longitude: number }
export type LocationErrorCode = 'denied' | 'unavailable' | 'timeout' | 'unsupported' | 'invalid';
const messages: Record<LocationErrorCode,string> = {
  denied:'Location permission was denied. Enter coordinates manually or select a saved address.',
  unavailable:'Your position is unavailable. You can enter coordinates manually.',
  timeout:'Location request timed out. Try again or enter coordinates manually.',
  unsupported:'Browser geolocation is unavailable. Enter coordinates manually or select a saved address.',
  invalid:'Enter a valid latitude (-90 to 90) and longitude (-180 to 180).',
};
export class LocationError extends Error {
  constructor(public code: LocationErrorCode) { super(messages[code]); this.name='LocationError'; }
}
export function coordinates(latitude:number, longitude:number): Coordinates {
  if (!Number.isFinite(latitude)||!Number.isFinite(longitude)||Math.abs(latitude)>90||Math.abs(longitude)>180) throw new LocationError('invalid');
  return {latitude:Number(latitude.toFixed(6)),longitude:Number(longitude.toFixed(6))};
}
export function acquireLocation(provider: Pick<Geolocation,'getCurrentPosition'>|null|undefined = globalThis.navigator?.geolocation): Promise<Coordinates> {
  return new Promise((resolve,reject)=>{
    if(!provider){reject(new LocationError('unsupported'));return;}
    try {
      provider.getCurrentPosition(position=>{
        try {resolve(coordinates(position.coords.latitude,position.coords.longitude));}
        catch {reject(new LocationError('invalid'));}
      },error=>reject(new LocationError(error.code===1?'denied':error.code===3?'timeout':'unavailable')),
      {timeout:10000,maximumAge:0});
    } catch {reject(new LocationError('unavailable'));}
  });
}
