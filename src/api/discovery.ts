import { api, identifier, ApiError } from './client';
import type { Category, Id } from './types';
import type { Coordinates } from '../location/geolocation';

export type DiscoverySource = {address_id:Id} | {location:Coordinates};
export type DiscoveryRadius = 1|2|3;
export interface BuyerProduct {
  id:Id;seller_id:Id;name:string;description:string;price:string;stock_quantity:number;
  category:Category;delivery_radius_km:1|2|3;image_url:string|null;
  shop_name:string;is_verified:boolean;delivery_eligibility?:'CONFIRMED_AT_CHECKOUT';
}
function sourceBody(source:DiscoverySource,radius:DiscoveryRadius):string {
  if(!Number.isInteger(radius)||![1,2,3].includes(radius))throw new ApiError(422,'Choose a discovery radius of 1, 2 or 3 km.');
  // An ID is validated decimal digits, emitted as a JSON integer without JS number rounding.
  return 'address_id' in source ? `{"address_id":${identifier(source.address_id)},"radius_km":${radius}}` : JSON.stringify({...source,radius_km:radius});
}
export const discoveryApi = {
  list:(source:DiscoverySource,radius:DiscoveryRadius=3)=>api<BuyerProduct[]>('/discovery/products',{method:'POST',bodyText:sourceBody(source,radius)}),
  detail:(id:Id,source:DiscoverySource,radius:DiscoveryRadius=3)=>api<BuyerProduct>(`/discovery/products/${identifier(id)}`,{method:'POST',bodyText:sourceBody(source,radius)}),
};
