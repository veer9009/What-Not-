import { fireEvent,render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { LandingPage } from './LandingPage';
import { DemoProvider } from '../state/DemoContext';
import { DiscoveryProvider } from '../state/DiscoveryContext';
vi.mock('../api/homeListings',()=>({loadHomeListings:vi.fn().mockResolvedValue({items:[],errors:[]})}));

const session=vi.hoisted(()=>({user:null as {role:'SELLER'|'ADMIN'}|null}));
vi.mock('../state/AuthContext',()=>({useAuth:()=>session}));
afterEach(()=>{session.user=null;});

function open(){return render(<MemoryRouter><DiscoveryProvider><DemoProvider><LandingPage/></DemoProvider></DiscoveryProvider></MemoryRouter>);}

it('presents the approved compact home with four locally stored 3D category assets',()=>{
  open();
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent('Discover What Not?');
  const assets=within(screen.getByRole('region',{name:'Explore What Not?'})).getAllByRole('img');
  expect(assets).toHaveLength(4);
  assets.forEach(art=>{expect(art.getAttribute('src')).toMatch(/assets\/categories/);expect(art).toHaveAttribute('width');expect(art).toHaveAttribute('height');});
  expect(screen.getByRole('searchbox',{name:'Search products, services and properties'})).toBeInTheDocument();
  expect(document.querySelector('.hero-collage')).toBeNull();
});

it('keeps category and CTA destinations while clearly disclosing current beta limits',()=>{
  open();
  const categories=screen.getByRole('region',{name:'Explore What Not?'});
  for(const [name,path] of [['Homemade Products','/buyer'],['Real Estate','/buyer/properties'],['Creative Services','/creative-services'],['Professional Services','/professional-services']]){
    const card=within(categories).getByRole('article',{name});
    expect(within(card).getByRole('link')).toHaveAttribute('href',path);
  }
  fireEvent.click(screen.getByText('For local makers'));fireEvent.click(screen.getByText('About these listings'));
  expect(screen.getByRole('link',{name:'Seller sign in'})).toHaveAttribute('href','/login/seller');
  expect(screen.getByText(/Sample catalogue: geography/)).toBeInTheDocument();
  expect(screen.getByText(/Ownership and legal documents are not verified/)).toBeInTheDocument();
  expect(screen.getByText(/no payment or escrow is collected/)).toBeInTheDocument();
  expect(screen.getByText(/Prepaid UPI remains disabled pending approval/)).toBeInTheDocument();
});

it.each(['SELLER','ADMIN'] as const)('labels category actions for their %s workspace destinations',role=>{
  session.user={role};open();
  const categories=screen.getByRole('region',{name:'Explore What Not?'});
  const links=within(categories).getAllByRole('link');
  expect(links.map(link=>link.getAttribute('aria-label'))).toEqual(role==='SELLER'
    ?['Open Seller Studio','Open Creative Studio','Open Professional Dashboard','Manage sale properties']
    :['Review Homemade listings','Review Creative Services','Review Professional Services','Review sale properties']);
  links.forEach(link=>expect(link.getAttribute('href')).toMatch(role==='SELLER'?/^\/seller/:/^\/admin/));
});

it('removes homepage food imagery without removing sample labels or sample product links',()=>{
  open();
  expect(screen.queryByRole('img',{name:'Homemade Laddus'})).toBeNull();
  expect(screen.queryByRole('heading',{name:'Homemade Laddus'})).toBeNull();
  expect(document.querySelector('img[src*="photo-1601050690597"]')).toBeNull();
  const cards=document.querySelectorAll('.product-card');expect(cards.length).toBeGreaterThan(0);
  cards.forEach(card=>expect(within(card as HTMLElement).getByText('Sample')).toBeInTheDocument());
});
