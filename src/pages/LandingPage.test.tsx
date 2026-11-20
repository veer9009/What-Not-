import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it } from 'vitest';
import { LandingPage } from './LandingPage';
import { DemoProvider } from '../state/DemoContext';

function open(){return render(<MemoryRouter><DemoProvider><LandingPage/></DemoProvider></MemoryRouter>);}

it('presents the approved neighborhood headline and supporting copy with a local hero asset',()=>{
  open();
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent('Local life. More possibilities.');
  expect(screen.getByText('Buy homemade products, discover properties, find local services, and support talent in your neighborhood.')).toBeInTheDocument();
  const art=screen.getByRole('img',{name:/Miniature 3D neighborhood/});
  expect(art.getAttribute('src')).toMatch(/neighborhood-world/);
  expect(art).toHaveAttribute('width');expect(art).toHaveAttribute('height');
  expect(art).toHaveAttribute('fetchpriority','high');
  expect(document.querySelector('.hero-collage')).toBeNull();
});

it('keeps category and CTA destinations while clearly disclosing current beta limits',()=>{
  open();
  const categories=screen.getByRole('region',{name:'Explore What Not?'});
  for(const [name,path] of [['Homemade Products','/buyer/samples#homemade-catalogue'],['Real Estate','/buyer/properties'],['Creative Services','/buyer/creative']]){
    const card=within(categories).getByRole('article',{name});
    expect(within(card).getByRole('link')).toHaveAttribute('href',path);
  }
  expect(screen.getByRole('link',{name:'Explore What Not?'})).toHaveAttribute('href','#explore');
  expect(screen.getByRole('link',{name:'Seller sign in'})).toHaveAttribute('href','/login/seller');
  expect(screen.getByText(/Sample catalogue: geography/)).toBeInTheDocument();
  expect(screen.getByText(/Ownership and legal documents are not verified/)).toBeInTheDocument();
  expect(screen.getByText(/No payment or escrow is collected/)).toBeInTheDocument();
});

it('removes homepage food imagery without removing sample labels or sample product links',()=>{
  open();
  expect(screen.queryByRole('img',{name:'Homemade Laddus'})).toBeNull();
  expect(screen.queryByRole('heading',{name:'Homemade Laddus'})).toBeNull();
  expect(document.querySelector('img[src*="photo-1601050690597"]')).toBeNull();
  const cards=document.querySelectorAll('.product-card');expect(cards.length).toBeGreaterThan(0);
  cards.forEach(card=>expect(within(card as HTMLElement).getByText('Sample')).toBeInTheDocument());
});
