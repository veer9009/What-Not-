import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PublicServiceCatalog, ServiceCatalog, categories } from './ServiceCatalog';
import { creativeApi, type CreativeListing } from '../api/creative';
vi.mock('../api/creative',()=>({creativeApi:{listings:vi.fn()}}));
const auth = vi.hoisted(() => ({ loading: false }));
vi.mock('../state/AuthContext',()=>({useAuth:()=>auth}));
vi.mock('../components/Shared',()=>({PublicHeader:()=> <header>Public navigation</header>}));
afterEach(()=>{cleanup();vi.clearAllMocks();auth.loading=false;});
it('provides public navigation and a main landmark for the catalog',async()=>{
  vi.mocked(creativeApi.listings).mockResolvedValue([]);
  render(<MemoryRouter><PublicServiceCatalog domain="PROFESSIONAL"/></MemoryRouter>);
  expect(screen.getByText('Public navigation')).toBeInTheDocument();
  expect(screen.getByRole('main')).toHaveAttribute('id','main-content');
});
it('waits for authentication restoration before requesting public services', async()=>{
  auth.loading=true;
  vi.mocked(creativeApi.listings).mockResolvedValue([]);
  const view=render(<MemoryRouter><PublicServiceCatalog domain="CREATIVE"/></MemoryRouter>);
  expect(creativeApi.listings).not.toHaveBeenCalled();
  auth.loading=false;
  view.rerender(<MemoryRouter><PublicServiceCatalog domain="CREATIVE"/></MemoryRouter>);
  await waitFor(()=>expect(creativeApi.listings).toHaveBeenCalled());
});
it.each(['CREATIVE','PROFESSIONAL'] as const)('offers distinct local artwork and filters all %s categories',async domain=>{
  vi.mocked(creativeApi.listings).mockResolvedValue([]);
  render(<MemoryRouter><ServiceCatalog domain={domain}/></MemoryRouter>);
  await screen.findByText('No services match your search.');
  const sources=new Set<string>();
  // Traverse visible category roles once; repeated full-document role/name
  // queries spend the test budget recomputing jsdom styles for every button.
  const buttons=within(screen.getByLabelText(`${domain==='CREATIVE'?'Creative':'Professional'} Services categories`)).getAllByRole('button');
  expect(buttons).toHaveLength(categories[domain].length);
  for(const [index,category] of categories[domain].entries()){
    const button=buttons[index];
    expect(button).toHaveAccessibleName(category);
    const image=button.querySelector('img');
    expect(image).not.toBeNull();
    sources.add(image!.getAttribute('src')!);
    fireEvent.click(button);
    await waitFor(()=>expect(creativeApi.listings).toHaveBeenLastCalledWith(0,domain,expect.objectContaining({category})));
    expect(button).toHaveAttribute('aria-pressed','true');
  }
  expect(sources.size).toBe(categories[domain].length);
});
it('explains the private enquiry and focuses results from Post a Requirement',async()=>{
  vi.mocked(creativeApi.listings).mockResolvedValue([]);
  render(<MemoryRouter><ServiceCatalog domain="CREATIVE"/></MemoryRouter>);
  await screen.findByText('No services match your search.');
  expect(screen.getByText(/choose a service.*private enquiry/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Post a Requirement'}));
  expect(document.activeElement).toHaveAttribute('id','services-results');
});
it('pages on the server and resets the page when the remote filter changes',async()=>{
  const listing:CreativeListing={id:'1',provider_id:'2',title:'Example',description:'Description',category:'Photography',pricing:'QUOTATION',amount:null,currency:'INR',remote:true,locality:null,portfolio:[],is_active:true,status:'APPROVED',rejection_reason:null};
  vi.mocked(creativeApi.listings).mockImplementation(async offset=>offset===0?Array.from({length:50},(_,i)=>({...listing,id:String(i)})):[]);
  render(<MemoryRouter><ServiceCatalog domain="CREATIVE"/></MemoryRouter>);
  await screen.findByText('Page 1');
  fireEvent.click(screen.getByRole('button',{name:'Next page'}));
  await waitFor(()=>expect(creativeApi.listings).toHaveBeenLastCalledWith(50,'CREATIVE',expect.anything()));
  await screen.findByText('Page 2');
  fireEvent.change(screen.getByLabelText('Service location'),{target:{value:'true'}});
  await waitFor(()=>expect(creativeApi.listings).toHaveBeenLastCalledWith(0,'CREATIVE',expect.objectContaining({remote:true})));
});
it('focuses the chosen provider enquiry form',async()=>{
  vi.mocked(creativeApi.listings).mockResolvedValue([{id:'1',provider_id:'2',title:'Example',description:'Description',category:'Photography',pricing:'QUOTATION',amount:null,currency:'INR',remote:true,locality:null,portfolio:[],is_active:true,status:'APPROVED',rejection_reason:null}]);
  render(<MemoryRouter><ServiceCatalog domain="CREATIVE" enquiry={()=> <label>Private brief<textarea/></label>}/></MemoryRouter>);
  fireEvent.click(await screen.findByRole('button',{name:'Request Quotation'}));
  expect(screen.getByLabelText('Private brief')).toHaveFocus();
});
it('searches professional services on the server and resets pagination',async()=>{
  vi.mocked(creativeApi.listings).mockResolvedValue([]);
  render(<MemoryRouter><ServiceCatalog domain="PROFESSIONAL"/></MemoryRouter>);
  await screen.findByText('No services match your search.');
  fireEvent.change(screen.getByLabelText('Search services'),{target:{value:'cloud'}});
  await waitFor(()=>expect(creativeApi.listings).toHaveBeenLastCalledWith(0,'PROFESSIONAL',expect.objectContaining({q:'cloud'})));
});
it('clears technical filters when navigating to the creative catalogue',async()=>{
  vi.mocked(creativeApi.listings).mockResolvedValue([]);
  const view=render(<MemoryRouter><PublicServiceCatalog domain="PROFESSIONAL"/></MemoryRouter>);
  await screen.findByText('No services match your search.');
  fireEvent.change(screen.getByLabelText('Category'),{target:{value:'Cloud and DevOps'}});
  await waitFor(()=>expect(creativeApi.listings).toHaveBeenLastCalledWith(0,'PROFESSIONAL',expect.objectContaining({category:'Cloud and DevOps'})));
  view.rerender(<MemoryRouter><PublicServiceCatalog domain="CREATIVE"/></MemoryRouter>);
  await waitFor(()=>expect(creativeApi.listings).toHaveBeenLastCalledWith(0,'CREATIVE',expect.objectContaining({category:undefined})));
  expect(screen.getByLabelText('Category')).toHaveValue('');
});
