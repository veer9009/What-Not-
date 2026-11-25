import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SellerCreativePage } from './CreativePages';
import { creativeApi } from '../api/creative';

vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{id:'1',name:'Creator',role:'SELLER'},logout:vi.fn()})}));
vi.mock('../api/creative',()=>({creativeApi:{own:vi.fn(),provider:vi.fn(),rfqs:vi.fn(),engagements:vi.fn(),responses:vi.fn()}}));
afterEach(()=>{cleanup();vi.clearAllMocks();});

it('targets real provider, services, portfolio, enquiry and quotation content from its own navigation',async()=>{
  vi.mocked(creativeApi.provider).mockResolvedValue({id:'2',user_id:'1',display_name:'Creator',bio:'Editing'});
  vi.mocked(creativeApi.own).mockResolvedValue([{id:'3',provider_id:'2',title:'Film editing',description:'Editing',category:'VFX',pricing:'FIXED',amount:'100',currency:'INR',remote:true,locality:null,portfolio:['https://example.test/film'],is_active:true,status:'APPROVED',rejection_reason:null}]);
  vi.mocked(creativeApi.rfqs).mockResolvedValue([{id:'4',listing_id:'3',buyer_id:'5',brief:'A short film'}]);
  vi.mocked(creativeApi.responses).mockResolvedValue([{id:'6',rfq_id:'4',terms:'Final cut',amount:'100',currency:'INR'}]);
  vi.mocked(creativeApi.engagements).mockResolvedValue([]);
  render(<MemoryRouter initialEntries={['/seller/creative']}><SellerCreativePage/></MemoryRouter>);
  await screen.findByRole('button',{name:'Save provider profile'});
  const nav=screen.getByRole('navigation',{name:'Workspace navigation'});
  for(const [name,id] of [['Provider Profile','provider'],['Services','services'],['Portfolio','portfolio'],['Enquiries','enquiries'],['Quotations','quotations']]){
    const link=within(nav).getByRole('link',{name});
    expect(link).toHaveAttribute('href',`/seller/creative#${id}`);
    const target=document.getElementById(id);expect(target).not.toBeNull();
    expect(target?.textContent?.trim().length).toBeGreaterThan(0);
  }
  expect(within(document.getElementById('portfolio')!).getByRole('link',{name:/Film editing/})).toHaveAttribute('href','https://example.test/film');
  expect(within(document.getElementById('quotations')!).getByRole('button',{name:'Send quote'})).toBeInTheDocument();
  fireEvent.click(within(nav).getByRole('link',{name:'Quotations'}));
  expect(within(nav).getByRole('link',{name:'Quotations'})).toHaveAttribute('aria-current','location');
  expect(nav.querySelectorAll('[aria-current]')).toHaveLength(1);
});

it('offers only reachable workspace destinations while Creative content is unavailable',async()=>{
  vi.mocked(creativeApi.own).mockRejectedValue(new Error('Unavailable'));
  render(<MemoryRouter initialEntries={['/seller/creative']}><SellerCreativePage/></MemoryRouter>);
  const nav=screen.getByRole('navigation',{name:'Workspace navigation'});
  expect(within(nav).queryByRole('link',{name:'Provider Profile'})).not.toBeInTheDocument();
  await screen.findByRole('button',{name:'Try again'});
  expect(within(nav).queryByRole('link',{name:'Services'})).not.toBeInTheDocument();
  expect(within(nav).getByRole('link',{name:'Overview'})).toBeInTheDocument();
  expect(within(nav).getByRole('link',{name:'Seller Studio'})).toBeInTheDocument();
});
