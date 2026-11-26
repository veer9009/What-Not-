import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BuyerDiscoveryPage } from './DiscoveryPages';
import { discoveryApi } from '../api/discovery';

vi.mock('../api/discovery',()=>({discoveryApi:{list:vi.fn()}}));
vi.mock('../api/addresses',()=>({addressesApi:{list:async()=>[]}}));
vi.mock('../state/DiscoveryContext',()=>({useDiscovery:()=>({source:{address_id:'1'},radius:3,choose:vi.fn(),setRadius:vi.fn()})}));
vi.mock('../components/Shared',()=>({DashboardShell:({children}:any)=><div>{children}</div>,PageTop:()=>null,RadiusSelector:()=>null,EmptyState:({title}:any)=><p>{title}</p>}));
vi.mock('../components/LocationPicker',()=>({LocationPicker:()=>null}));
vi.mock('../components/ExploreVerticals',()=>({ExploreVerticals:()=>null}));
vi.mock('../components/WishlistButton',()=>({WishlistButton:()=>null}));
vi.mock('../components/ListingImage',()=>({ListingImage:()=>null}));
afterEach(()=>{cleanup();vi.clearAllMocks();});

it('requests pages and searches from the server, resetting the offset',async()=>{
  vi.mocked(discoveryApi.list).mockImplementation(async (_source,_radius,options)=>options?.offset?[]:Array.from({length:100},(_,i)=>({id:String(i),seller_id:'1',name:`Product ${i}`,description:'',price:'1',stock_quantity:1,category:'OTHER',delivery_radius_km:3,image_url:null,shop_name:'Shop',is_verified:false} as any)));
  render(<MemoryRouter><BuyerDiscoveryPage/></MemoryRouter>);
  await screen.findByText('Product 0');
  expect(discoveryApi.list).toHaveBeenCalledWith({address_id:'1'},3);
  fireEvent.click(screen.getByRole('button',{name:'Next page'}));
  await waitFor(()=>expect(discoveryApi.list).toHaveBeenLastCalledWith({address_id:'1'},3,{offset:100,limit:100,q:undefined}));
  fireEvent.change(screen.getByLabelText('Search products'),{target:{value:'bread'}});
  await waitFor(()=>expect(discoveryApi.list).toHaveBeenLastCalledWith({address_id:'1'},3,{offset:0,limit:100,q:'bread'}));
});
