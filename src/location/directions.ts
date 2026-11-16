import type { DeliveryLocation } from '../api/types';

export function deliveryDirections(point: DeliveryLocation | null | undefined): string | null {
  if (!point) return null;
  const parse = (value: unknown, max: number) => {
    if (typeof value !== 'string' || !/^-?\d+(?:\.\d+)?$/.test(value.trim())) return null;
    const number = Number(value);
    return Number.isFinite(number) && Math.abs(number) <= max ? number : null;
  };
  const latitude = parse(point.latitude, 90), longitude = parse(point.longitude, 180);
  if (latitude === null || longitude === null) return null;
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${latitude},${longitude}`)}`;
}
