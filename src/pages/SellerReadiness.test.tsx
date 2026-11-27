import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ProductFormPage, SellerDashboard, SellerProfilePage } from './SellerPages';
import { ApiError } from '../api/client';
import { sellersApi, setDispatchLocation, setPublicDiscovery } from '../api/sellers';
import { productsApi } from '../api/products';
import type { Product, Shop } from '../api/types';

vi.mock('../state/AuthContext', () => ({ useAuth: () => ({ user: { id: '1', name: 'Maker', role: 'SELLER' }, logout: vi.fn() }) }));
vi.mock('../api/sellers', () => ({ sellersApi: { me: vi.fn(), create: vi.fn(), update: vi.fn() }, setDispatchLocation: vi.fn(), setPublicDiscovery: vi.fn(), revokePublicDiscovery: vi.fn() }));

const saved: Shop = { id:'2', user_id:'1', shop_name:'Maker', phone:'100', description:null, latitude:'19', longitude:'72', is_verified:false, dispatch_location_confirmed_at:'2026-11-23T00:00:00Z', public_discovery_latitude:'19', public_discovery_longitude:'72', public_discovery_confirmed_at:'2026-11-23T00:00:00Z', public_discovery_consent_version:'public-discovery-v1' };
const product: Product = { id:'3', seller_id:'2', name:'Vase', description:'Handmade', price:'100', stock_quantity:2, category:'Crafts', delivery_radius_km:2, image_url:null, status:'APPROVED', rejection_reason:null, is_active:true };
let current: Shop | null;
beforeEach(() => {
  current = { ...saved };
  vi.mocked(sellersApi.me).mockImplementation(async () => { if (!current) throw new ApiError(404, 'Missing'); return { ...current }; });
  vi.mocked(sellersApi.create).mockImplementation(async body => current = { ...saved, ...body, dispatch_location_confirmed_at:null, public_discovery_confirmed_at:null, public_discovery_latitude:null, public_discovery_longitude:null, public_discovery_consent_version:null });
  vi.mocked(sellersApi.update).mockImplementation(async body => {
    const moved = (body.latitude !== undefined && Number(body.latitude)!==Number(current!.latitude))
      || (body.longitude !== undefined && Number(body.longitude)!==Number(current!.longitude));
    current = {...current!, ...body};
    if (moved) current = {...current, dispatch_location_confirmed_at:null, public_discovery_latitude:null, public_discovery_longitude:null, public_discovery_confirmed_at:null, public_discovery_consent_version:null};
    return current;
  });
  vi.mocked(setDispatchLocation).mockImplementation(async point => current = { ...current!, latitude:String(point.latitude), longitude:String(point.longitude), dispatch_location_confirmed_at:saved.dispatch_location_confirmed_at });
  vi.mocked(setPublicDiscovery).mockImplementation(async point => current = { ...current!, public_discovery_latitude:String(point.latitude), public_discovery_longitude:String(point.longitude), public_discovery_confirmed_at:saved.public_discovery_confirmed_at, public_discovery_consent_version:'public-discovery-v1' });
  vi.spyOn(productsApi, 'own').mockResolvedValue([product]);
});
afterEach(() => { vi.clearAllMocks(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });
async function profile() { render(<MemoryRouter><SellerProfilePage/></MemoryRouter>); await screen.findByRole('button', {name:'Save profile'}); }
it('keeps the Products navigation target actionable before a shop is created',async()=>{
  current=null;
  render(<MemoryRouter initialEntries={['/seller#products']}><SellerDashboard/></MemoryRouter>);
  await screen.findByRole('heading',{name:'Set up your seller profile'});
  const target=document.getElementById('products');
  expect(target).not.toBeNull();
  expect(target).toHaveTextContent('Create seller profile');
});
function submit() { fireEvent.submit(screen.getByRole('button', {name:'Save profile'}).closest('form')!); }
function consent() {
  fireEvent.click(screen.getByRole('checkbox', {name:/I confirm this is where I send products from/i}));
  fireEvent.click(screen.getByRole('checkbox', {name:/I agree to use this point for public discovery/i}));
}

it('sets up profile, dispatch and explicitly shared discovery in one save, without automatic GPS or sharing', async () => {
  current = null;
  const gps = vi.fn((success:PositionCallback) => success({coords:{latitude:19,longitude:72,accuracy:10}} as GeolocationPosition));
  vi.stubGlobal('navigator', {geolocation:{getCurrentPosition:gps}});
  await profile();
  expect(gps).not.toHaveBeenCalled();
  expect(screen.queryByLabelText('Latitude')).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Shop name'), {target:{value:'Maker'}});
  fireEvent.change(screen.getByLabelText('Phone'), {target:{value:'100'}});
  fireEvent.click(screen.getByRole('button', {name:'Use Current Location'}));
  await screen.findByText(/Shop location selected/i);
  expect(setDispatchLocation).not.toHaveBeenCalled(); expect(setPublicDiscovery).not.toHaveBeenCalled();
  consent(); submit();
  await waitFor(() => expect(setPublicDiscovery).toHaveBeenCalledWith({latitude:19,longitude:72}));
  expect(sellersApi.create).toHaveBeenCalledOnce();
  expect(setDispatchLocation).toHaveBeenCalledOnce();
  expect(await screen.findByText(/Shop location saved.*every product/i)).toBeInTheDocument();
});

it('requires explicit dispatch confirmation and never publishes a private point without consent', async () => {
  current = {...saved, dispatch_location_confirmed_at:null, public_discovery_confirmed_at:null, public_discovery_consent_version:null};
  await profile(); submit();
  expect(await screen.findByRole('alert')).toHaveTextContent(/confirm.*send products/i);
  expect(sellersApi.update).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('checkbox', {name:/I confirm this is where I send products from/i}));
  submit();
  await waitFor(() => expect(setDispatchLocation).toHaveBeenCalledOnce());
  expect(setPublicDiscovery).not.toHaveBeenCalled();
  expect(await screen.findByText(/Shop location saved.*every product/i)).toBeInTheDocument();
  expect(screen.getByText(/No public discovery point confirmed/i)).toBeInTheDocument();
});

it('clears draft confirmations when the selected shop location changes', async () => {
  current = {...saved, dispatch_location_confirmed_at:null, public_discovery_confirmed_at:null};
  await profile(); consent();
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(success:PositionCallback)=>success({coords:{latitude:20,longitude:72,accuracy:10}} as GeolocationPosition)}});
  fireEvent.click(screen.getByRole('button',{name:'Use Current Location'}));
  await screen.findByText(/Shop location selected/i);
  expect(screen.getByRole('checkbox', {name:/I confirm this is where I send products from/i})).not.toBeChecked();
  expect(screen.getByRole('checkbox', {name:/I agree to use this point for public discovery/i})).not.toBeChecked();
  submit(); expect(await screen.findByRole('alert')).toHaveTextContent(/confirm.*send products/i);
  expect(setPublicDiscovery).not.toHaveBeenCalled();
});

it('retries partial first-time setup without creating another shop or confirming dispatch again', async () => {
  current = null; await profile();
  fireEvent.change(screen.getByLabelText('Shop name'), {target:{value:'Maker'}});
  fireEvent.change(screen.getByLabelText('Phone'), {target:{value:'100'}});
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(success:PositionCallback)=>success({coords:{latitude:19,longitude:72,accuracy:10}} as GeolocationPosition)}});
  fireEvent.click(screen.getByRole('button',{name:'Use Current Location'}));
  await screen.findByText(/Shop location selected/i);
  consent(); vi.mocked(setPublicDiscovery).mockRejectedValueOnce(new ApiError(503,'Unavailable'));
  submit(); expect(await screen.findByRole('alert')).toHaveTextContent(/profile was saved/i);
  submit(); await waitFor(() => expect(setPublicDiscovery).toHaveBeenCalledTimes(2));
  expect(sellersApi.create).toHaveBeenCalledOnce(); expect(setDispatchLocation).toHaveBeenCalledOnce();
});

it('keeps saved confirmation and public consent for an ordinary profile edit', async () => {
  await profile();
  fireEvent.change(screen.getByLabelText('Shop name'), {target:{value:'New shop name'}});
  submit(); await waitFor(() => expect(sellersApi.update).toHaveBeenCalledOnce());
  expect(setDispatchLocation).not.toHaveBeenCalled(); expect(setPublicDiscovery).not.toHaveBeenCalled();
});

it('shows revoked public consent after a partial move and retains a safe retry', async () => {
  await profile();
  expect(screen.getByText('Public discovery point confirmed.')).toBeInTheDocument();
  vi.stubGlobal('navigator',{geolocation:{getCurrentPosition:(success:PositionCallback)=>success({coords:{latitude:20,longitude:72,accuracy:10}} as GeolocationPosition)}});
  fireEvent.click(screen.getByRole('button',{name:'Use Current Location'}));
  await screen.findByText(/Shop location selected/i);
  fireEvent.click(screen.getByRole('checkbox', {name:/I confirm this is where I send products from/i}));
  vi.mocked(setDispatchLocation).mockRejectedValueOnce(new ApiError(503,'Unavailable'));
  submit();
  expect(await screen.findByRole('alert')).toHaveTextContent(/profile was saved/i);
  expect(screen.queryByText('Public discovery point confirmed.')).not.toBeInTheDocument();
  expect(screen.getByText(/No public discovery point confirmed/i)).toBeInTheDocument();
  expect(current!.public_discovery_confirmed_at).toBeNull();
  submit(); await waitFor(() => expect(setDispatchLocation).toHaveBeenCalledTimes(2));
  expect(setPublicDiscovery).not.toHaveBeenCalled();
  expect(sellersApi.create).not.toHaveBeenCalled();
});

it('explains missing shop setup instead of equating product approval with discovery', async () => {
  current = {...saved, public_discovery_confirmed_at:null, public_discovery_consent_version:null};
  render(<MemoryRouter><SellerDashboard/></MemoryRouter>);
  expect(await screen.findByRole('link', {name:'Complete shop location'})).toHaveAttribute('href','/seller/profile');
  expect(screen.getByText(/Choose a public shop point and give permission/i)).toBeInTheDocument();
  expect(screen.getByText('Discovery ready').parentElement).toHaveTextContent('0');
});

it('counts only approved active stocked listings after complete location setup', async () => {
  vi.mocked(productsApi.own).mockResolvedValue([product, {...product,id:'4',stock_quantity:0}, {...product,id:'5',status:'PENDING'}, {...product,id:'6',is_active:false}]);
  render(<MemoryRouter><SellerDashboard/></MemoryRouter>);
  const metric = await screen.findByText('Discovery ready');
  expect(metric.parentElement).toHaveTextContent('1');
  expect(screen.getByText(/Buyers must be within range.*checkout/i)).toBeInTheDocument();
  expect(screen.queryByRole('link', {name:'Complete shop location'})).not.toBeInTheDocument();
});

it('creates multiple products using one saved shop configuration without location prompts or writes', async () => {
  const create = vi.spyOn(productsApi,'create').mockResolvedValue(product);
  render(<MemoryRouter initialEntries={['/seller']}><Routes><Route path="/seller" element={<SellerDashboard/>}/><Route path="/seller/products/new" element={<ProductFormPage/>}/></Routes></MemoryRouter>);
  function page() {
    const main=document.getElementById('main-content')!;
    expect(main).toHaveRole('main');
    return within(main);
  }
  // Sidebar navigation is unrelated to this flow; query the current main and
  // reuse the returned action instead of finding it again before the next click.
  let add=await waitFor(()=>page().getByRole('link', {name:'Add New Product'}));
  for (let attempt=0; attempt<2; attempt++) {
    fireEvent.click(add);
    const button = await waitFor(()=>page().getByRole('button', {name:'Submit for Admin Approval'}));
    expect(screen.queryByLabelText('Latitude')).not.toBeInTheDocument();
    fireEvent.submit(button.closest('form')!);
    // Navigation replaces main, so resolve the live landmark on every retry.
    add=await waitFor(()=>page().getByRole('link', {name:'Add New Product'}));
  }
  expect(create).toHaveBeenCalledTimes(2);
  expect(setDispatchLocation).not.toHaveBeenCalled(); expect(setPublicDiscovery).not.toHaveBeenCalled();
});
