// Export actual UI with synthetic records for offline browser layout inspection.
import { mkdirSync, writeFileSync } from 'node:fs';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { LandingPage } from '../src/pages/LandingPage';
import { LoginPage, RegisterPage } from '../src/pages/LoginPages';
import { ProductForm, SellerProfilePage, SellerDashboard } from '../src/pages/SellerPages';
import { AdminDashboard } from '../src/pages/AdminDashboard';
import { DemoProvider } from '../src/state/DemoContext';
import { DashboardShell } from '../src/components/Shared';
import { ListingImage } from '../src/components/ListingImage';

const authState=vi.hoisted(()=>({signedIn:true}));
vi.mock('../src/state/AuthContext', () => ({ roleHome:(role:string)=>`/${role.toLowerCase()}`, useAuth: () => ({ user: authState.signedIn?{id:'1',name:'Layout reviewer',role:'SELLER'}:null, logout:vi.fn(), login:vi.fn() }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const folder = 'docs/security/evidence/sage';
mkdirSync(folder, { recursive:true });
const save = (name:string) => writeFileSync(`${folder}/${name}.html`,document.body.innerHTML);

it('exports homepage, authentication, product form, and long listing details', () => {
  const cases = [
    ['home', <DemoProvider><LandingPage/></DemoProvider>],
    ['login', <Routes><Route path="/login/:role" element={<LoginPage/>}/></Routes>], ['register', <RegisterPage/>],
    ['product-form', <DashboardShell role="seller"><ProductForm/></DashboardShell>],
    ['product-detail', <DashboardShell role="buyer"><div className="product-detail"><div className="detail-image"><ListingImage src={null} alt="Handcrafted vase"/></div><div className="detail-copy"><p className="eyebrow">Crafts · Nearby locality</p><h1>Handcrafted ceramic vase with a deliberately long descriptive product name</h1><p>Local artisan with a long shop name</p><strong className="detail-price">₹12,500</strong><p>A synthetic description for testing long content and image alignment.</p><div className="detail-actions"><button className="btn btn-primary">Add to Cart</button></div></div></div></DashboardShell>],
  ] as const;
  for(const [name, element] of cases) {
    authState.signedIn=!['login','register'].includes(name);
    render(<MemoryRouter initialEntries={['/login/buyer']}>{element}</MemoryRouter>);
    expect(document.querySelector('h1,h2')).not.toBeNull(); save(name); cleanup();
  }
});

it('exports seller location setup, seller dashboard, and product moderation', async () => {
  authState.signedIn=true;
  const product={id:'3',seller_id:'2',name:'Handmade vase with a long descriptive product name',description:'Synthetic listing used only for offline layout review.',price:'250.00',stock_quantity:5,category:'Crafts',delivery_radius_km:2,image_url:null,status:'PENDING',is_active:true};
  vi.stubGlobal('fetch',vi.fn(async (input:string) => {
    const path = new URL(input,location.origin).pathname;
    const body = path.endsWith('/sellers/me') ? null : path.includes('/products') ? [product] : [];
    return new Response(JSON.stringify(body));
  }));
  for(const [name,element,title] of [
    ['seller-location',<SellerProfilePage/>,'Create seller profile'],
    ['seller-dashboard',<SellerDashboard/>,'Set up your seller profile'],
    ['admin-products',<AdminDashboard/>,'Pending Product Approvals'],
  ] as const) {
    render(<MemoryRouter>{element}</MemoryRouter>);
    await screen.findByRole('heading',{name:title}); save(name); cleanup();
  }
});
