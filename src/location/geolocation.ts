// Coordinate sources (manual, device, future address search) share this boundary.
export interface Coordinates { latitude: number; longitude: number }
// Browser accuracy is a quality estimate in metres, never an API coordinate.
export interface AcquiredLocation extends Coordinates { accuracyMeters: number | null }
export type LocationErrorCode = 'denied' | 'unavailable' | 'timeout' | 'unsupported' | 'insecure' | 'invalid';
const messages: Record<LocationErrorCode,string> = {
  denied:'Location permission was denied. Allow location in your browser and device settings, then try again or select a saved address.',
  unavailable:'Your position is unavailable. Check your device location settings and try again or select a saved address.',
  timeout:'Location request timed out. Try again or select a saved address.',
  unsupported:'Browser geolocation is unavailable. Select a saved address.',
  insecure:'Current location requires HTTPS or localhost. Open the secure site or select a saved address.',
  invalid:'The device returned an invalid location. Try again.',
};
export class LocationError extends Error {
  constructor(public code: LocationErrorCode) { super(messages[code]); this.name='LocationError'; }
}
export function coordinates(latitude:number, longitude:number): Coordinates {
  if (!Number.isFinite(latitude)||!Number.isFinite(longitude)||Math.abs(latitude)>90||Math.abs(longitude)>180) throw new LocationError('invalid');
  return {latitude:Number(latitude.toFixed(6)),longitude:Number(longitude.toFixed(6))};
}
export function acquireLocation(provider?: Pick<Geolocation,'getCurrentPosition'>|null, signal?:AbortSignal): Promise<AcquiredLocation> {
  return new Promise((resolve,reject)=>{
    if(signal?.aborted){reject(new DOMException('Location request cancelled','AbortError'));return;}
    if(globalThis.isSecureContext===false){reject(new LocationError('insecure'));return;}
    let timer:ReturnType<typeof setTimeout>|undefined;
    let settled=false;
    function cleanup(){clearTimeout(timer);signal?.removeEventListener('abort',cancel);}
    function fail(error:Error){if(settled)return;settled=true;cleanup();reject(error);}
    function cancel(){fail(new DOMException('Location request cancelled','AbortError'));}
    try {
      const geolocation=provider===undefined?globalThis.navigator?.geolocation:provider;
      if(!geolocation||typeof geolocation.getCurrentPosition!=='function'){fail(new LocationError('unsupported'));return;}
      // Browser timeout excludes permission/visibility waits. Bound the whole
      // interaction too, and ignore callbacks after cancellation or expiry.
      timer=setTimeout(()=>fail(new LocationError('timeout')),30000);
      signal?.addEventListener('abort',cancel,{once:true});
      geolocation.getCurrentPosition(position=>{
        if(settled)return;
        try {
          const point=coordinates(position.coords.latitude,position.coords.longitude);
          const accuracy=position.coords.accuracy;
          const accuracyMeters=Number.isFinite(accuracy)&&accuracy>=0?accuracy:null;
          settled=true;cleanup();resolve({...point,accuracyMeters});
        } catch {fail(new LocationError('invalid'));}
      },error=>fail(new LocationError(error.code===1?'denied':error.code===3?'timeout':'unavailable')),
      {enableHighAccuracy:true,timeout:20000,maximumAge:0});
    } catch(error) {fail(new LocationError(error instanceof DOMException&&error.name==='SecurityError'?'denied':'unavailable'));}
  });
}
