import { api, identifier } from './client';
import type { Category, Id } from './types';
import type { Coordinates } from '../location/geolocation';

export type DiscoverySource = {address_id:Id} | {location:Coordinates};
export interface BuyerProduct {
  id:Id;seller_id:Id;name:string;description:string;price:string;stock_quantity:number;
  category:Category;delivery_radius_km:1|2|3;image_url:string|null;
  shop_name:string;is_verified:boolean;distance_km:number;
}
function sourceBody(source:DiscoverySource):string {
  // An ID is validated decimal digits, emitted as a JSON integer without JS number rounding.
  return 'address_id' in source ? `{"address_id":${identifier(source.address_id)}}` : JSON.stringify(source);
}
export const discoveryApi = {
  list:(source:DiscoverySource)=>api<BuyerProduct[]>('/discovery/products',{method:'POST',bodyText:sourceBody(source)}),
  detail:(id:Id,source:DiscoverySource)=>api<BuyerProduct>(`/discovery/products/${identifier(id)}`,{method:'POST',bodyText:sourceBody(source)}),
};
