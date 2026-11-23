import type { Shop } from '../api/types';

/** Seller guidance only. The discovery API remains authoritative for each buyer. */
export function shopDiscoveryIssues(shop: Shop): string[] {
  const issues: string[] = [];
  const point = (latitude: string | null | undefined, longitude: string | null | undefined) =>
    latitude != null && longitude != null && String(latitude).trim() !== '' && String(longitude).trim() !== ''
    && Number.isFinite(Number(latitude)) && Math.abs(Number(latitude)) <= 90
    && Number.isFinite(Number(longitude)) && Math.abs(Number(longitude)) <= 180;
  if (!shop.dispatch_location_confirmed_at || !point(shop.latitude, shop.longitude))
    issues.push('Confirm where you send products from.');
  if (!shop.public_discovery_confirmed_at || shop.public_discovery_consent_version !== 'public-discovery-v1'
      || !point(shop.public_discovery_latitude, shop.public_discovery_longitude))
    issues.push('Choose a public shop point and give permission for discovery.');
  return issues;
}
