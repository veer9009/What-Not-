import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import { DashboardShell, PublicHeader } from './Shared';

const logout=vi.fn();
vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{id:'1',name:'Reviewer',role:'SELLER'},logout})}));
afterEach(()=>{cleanup();vi.clearAllMocks();});

it('separates the professional provider workspace and never offers it to buyers or admins',()=>{
  const view=render(<MemoryRouter initialEntries={['/seller/professional#services']}><DashboardShell role="seller"><h1>Technical work</h1></DashboardShell></MemoryRouter>);
  const nav=screen.getByRole('navigation',{name:'Workspace navigation'});
  expect(screen.getByText('Professional Dashboard',{selector:'.workspace-label'})).toBeInTheDocument();
  expect(within(nav).getByRole('link',{name:'Services'})).toHaveAttribute('href','/seller/professional#services');
  expect(within(nav).getByRole('link',{name:'Services'})).toHaveAttribute('aria-current','location');
  expect(within(nav).getByRole('link',{name:'Creative Studio'})).toHaveAttribute('href','/seller/creative');
  expect(within(nav).getByRole('link',{name:'Projects'})).toHaveAttribute('href','/seller/professional#projects');
  view.unmount();
  render(<MemoryRouter initialEntries={['/buyer/professional']}><DashboardShell role="buyer"><h1>Technical services</h1></DashboardShell></MemoryRouter>);
  expect(screen.getByRole('link',{name:'Professional Services'})).toHaveAttribute('href','/buyer/professional');
  expect(document.querySelector('a[href="/seller/professional"]')).not.toBeInTheDocument();
});

it('exposes public destinations as accessible icon links without a hamburger',()=>{
  render(<MemoryRouter initialEntries={['/#real-estate']}><PublicHeader/></MemoryRouter>);
  const nav=screen.getByRole('navigation',{name:'Main navigation'});
  for(const label of ['Home','Marketplace','Property','Creative Services','Become a Seller','Login']){
    const link=within(nav).getByRole('link',{name:label});
    expect(link.querySelector('svg')).toHaveAttribute('aria-hidden','true');
  }
  expect(within(nav).getByRole('link',{name:'Property'})).toHaveAttribute('aria-current','location');
  expect(within(nav).getAllByRole('link').filter(a=>a.hasAttribute('aria-current'))).toHaveLength(1);
  expect(screen.queryByRole('button',{name:'Toggle navigation'})).not.toBeInTheDocument();
});

it('keeps nested buyer routes highlighted and all buyer destinations reachable',()=>{
  render(<MemoryRouter initialEntries={['/buyer/orders/42']}><DashboardShell role="buyer"><h1>Order</h1></DashboardShell></MemoryRouter>);
  const nav=screen.getByRole('navigation',{name:'Workspace navigation'});
  expect(within(nav).getByRole('link',{name:'Orders'})).toHaveAttribute('aria-current','page');
  for(const href of ['/buyer','/buyer/cart','/buyer/properties','/buyer/properties/saved','/buyer/properties/requests','/buyer/creative','/buyer/notifications','/buyer/profile','/buyer/addresses','/buyer/orders','/buyer/help']){
    expect([...nav.querySelectorAll('a')].some(a=>a.getAttribute('href')===href)).toBe(true);
  }
});

it('separates creative sections from product management and highlights a single hash target',()=>{
  render(<MemoryRouter initialEntries={['/seller/creative#enquiries']}><DashboardShell role="seller"><h1>Creative Studio</h1></DashboardShell></MemoryRouter>);
  expect(screen.getByText('Creative Studio',{selector:'.workspace-label'})).toBeInTheDocument();
  const nav=screen.getByRole('navigation',{name:'Workspace navigation'});
  for(const [label,hash] of [['Overview',''],['Provider Profile','#provider'],['Services','#services'],['Portfolio','#portfolio'],['Enquiries','#enquiries'],['Quotations','#quotations']]){
    expect(within(nav).getByRole('link',{name:label})).toHaveAttribute('href',`/seller/creative${hash}`);
  }
  expect(within(nav).getByRole('link',{name:'Enquiries'})).toHaveAttribute('aria-current','location');
  expect(nav.querySelectorAll('[aria-current]')).toHaveLength(1);
  expect(within(nav).getByRole('link',{name:'Seller Studio'})).toHaveAttribute('href','/seller');
  expect(within(nav).queryByRole('link',{name:'Add product'})).not.toBeInTheDocument();
  expect(within(nav).queryByRole('link',{name:'Availability'})).not.toBeInTheDocument();
});

it('keeps seller products and existing delivery controls reachable without changing logout',()=>{
  render(<MemoryRouter initialEntries={['/seller']}><DashboardShell role="seller"><h1>Seller</h1></DashboardShell></MemoryRouter>);
  const nav=screen.getByRole('navigation',{name:'Workspace navigation'});
  expect(within(nav).getByRole('link',{name:'Products'})).toHaveAttribute('href','/seller#products');
  expect(within(nav).getByRole('link',{name:'Shop Profile'})).toHaveAttribute('href','/seller/profile');
  expect(nav.querySelectorAll('a[href="/seller/profile"]')).toHaveLength(1);
  expect(within(nav).getByRole('link',{name:'Creative Studio'})).toHaveAttribute('href','/seller/creative');
  fireEvent.click(screen.getByRole('button',{name:'Log out'}));
  expect(logout).toHaveBeenCalledOnce();
});

it('moves keyboard focus to a public category when its sidebar link is selected',()=>{
  render(<MemoryRouter><PublicHeader/><main><section id="real-estate"><h2>Sale properties</h2></section></main></MemoryRouter>);
  fireEvent.click(within(screen.getByRole('navigation',{name:'Main navigation'})).getByRole('link',{name:'Property'}));
  expect(document.getElementById('real-estate')).toHaveFocus();
});

it('returns to the selected section when its same sidebar link is activated again',()=>{
  render(<MemoryRouter><PublicHeader/><main><section id="real-estate"><h2>Sale properties</h2></section><button>Elsewhere</button></main></MemoryRouter>);
  const link=within(screen.getByRole('navigation',{name:'Main navigation'})).getByRole('link',{name:'Property'});
  fireEvent.click(link);
  screen.getByRole('button',{name:'Elsewhere'}).focus();
  fireEvent.click(link);
  expect(document.getElementById('real-estate')).toHaveFocus();
});

it('highlights Products when editing an existing product',()=>{
  render(<MemoryRouter initialEntries={['/seller/products/42/edit']}><DashboardShell role="seller"><h1>Edit</h1></DashboardShell></MemoryRouter>);
  const nav=screen.getByRole('navigation',{name:'Workspace navigation'});
  expect(within(nav).getByRole('link',{name:'Products'})).toHaveAttribute('aria-current','page');
  expect(nav.querySelectorAll('[aria-current]')).toHaveLength(1);
});

it('restores Home scroll and focus on repeated selection and browser history navigation',()=>{
  const scroll=vi.spyOn(window,'scrollTo').mockImplementation(()=>{});
  function History(){const navigate=useNavigate();return <><button onClick={()=>navigate(-1)}>Back</button><button onClick={()=>navigate(1)}>Forward</button></>;}
  render(<MemoryRouter><PublicHeader/><main id="main-content" tabIndex={-1}><section id="real-estate">Properties</section><History/></main></MemoryRouter>);
  const nav=screen.getByRole('navigation',{name:'Main navigation'});
  fireEvent.click(within(nav).getByRole('link',{name:'Property'}));
  expect(document.getElementById('real-estate')).toHaveFocus();
  fireEvent.click(within(nav).getByRole('link',{name:'Home'}));
  expect(document.getElementById('main-content')).toHaveFocus();
  expect(scroll).toHaveBeenCalledWith({top:0,left:0,behavior:'instant'});
  fireEvent.click(screen.getByRole('button',{name:'Back'}));
  expect(document.getElementById('real-estate')).toHaveFocus();
  fireEvent.click(screen.getByRole('button',{name:'Forward'}));
  expect(document.getElementById('main-content')).toHaveFocus();
  fireEvent.click(within(nav).getByRole('link',{name:'Home'}));
  expect(scroll).toHaveBeenCalledTimes(3);
  scroll.mockRestore();
});

it('restores Creative Overview without moving focus on ordinary content updates',()=>{
  const scroll=vi.spyOn(window,'scrollTo').mockImplementation(()=>{});
  const content=<><section id="quotations">Quotes</section><input aria-label="Draft"/></>;
  const {rerender}=render(<MemoryRouter initialEntries={['/seller/creative#quotations']}><DashboardShell role="seller"><div>{content}<p>Original</p></div></DashboardShell></MemoryRouter>);
  fireEvent.click(within(screen.getByRole('navigation',{name:'Workspace navigation'})).getByRole('link',{name:'Overview'}));
  expect(document.getElementById('main-content')).toHaveFocus();
  screen.getByLabelText('Draft').focus();
  rerender(<MemoryRouter initialEntries={['/seller/creative#quotations']}><DashboardShell role="seller"><div>{content}<p>Updated</p></div></DashboardShell></MemoryRouter>);
  expect(screen.getByLabelText('Draft')).toHaveFocus();
  expect(scroll).toHaveBeenCalledOnce();scroll.mockRestore();
});
