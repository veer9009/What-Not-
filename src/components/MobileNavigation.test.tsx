import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { DashboardShell } from './Shared';

vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{id:'1',name:'Long account name',role:'SELLER'},logout:vi.fn()})}));
beforeEach(()=>vi.stubGlobal('matchMedia',vi.fn(query=>({matches:query==='(max-width: 760px)',media:query,addEventListener:vi.fn(),removeEventListener:vi.fn()}))));
afterEach(()=>vi.unstubAllGlobals());
function open(role:'buyer'|'seller'|'admin',path:string){render(<MemoryRouter initialEntries={[path]}><DashboardShell role={role}><h1>Workspace</h1><section id="services">Services target</section><section id="portfolio">Portfolio target</section><section id="enquiries">Enquiries target</section></DashboardShell></MemoryRouter>);}

it('gives buyers five labelled primary destinations and keeps secondary payments in More',()=>{
  open('buyer','/buyer/orders/42');
  const nav=screen.getByRole('navigation',{name:'Primary navigation'});
  expect(within(nav).getAllByRole('link').map(a=>a.textContent)).toEqual(['Home','Explore','Cart','Orders']);
  expect(within(nav).getByRole('button',{name:'Account and more navigation'})).toHaveTextContent('Account');
  expect(within(nav).getByRole('link',{name:'Orders'})).toHaveAttribute('aria-current','page');
  fireEvent.click(screen.getByRole('button',{name:'Account and more navigation'}));
  const more=screen.getByRole('dialog',{name:'More destinations'});
  expect(within(more).getByRole('link',{name:'Payments'})).toHaveAttribute('href','/buyer/payments');
  expect(within(more).queryByRole('link',{name:'Creative Studio'})).not.toBeInTheDocument();
  expect(within(more).queryByRole('link',{name:'Payments & Transactions'})).not.toBeInTheDocument();
});

it('prioritizes seller payments and dismisses More with Escape and restored focus',()=>{
  open('seller','/seller/payments');
  const nav=screen.getByRole('navigation',{name:'Primary navigation'});
  expect(within(nav).getByRole('link',{name:'Payments'})).toHaveAttribute('aria-current','page');
  const trigger=within(nav).getByRole('button',{name:'More navigation'});trigger.focus();fireEvent.click(trigger);
  const dialog=screen.getByRole('dialog',{name:'More destinations'});
  expect(document.body.style.overflow).toBe('hidden');
  expect(within(dialog).getByRole('link',{name:'Creative Studio'})).toHaveAttribute('href','/seller/creative');
  fireEvent.keyDown(dialog,{key:'Escape'});
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(trigger).toHaveFocus();
  expect(document.body.style.overflow).toBe('');
});

it('keeps product creation in the seller Products primary section',()=>{
  open('seller','/seller/products/new');
  const nav=screen.getByRole('navigation',{name:'Primary navigation'});
  expect(within(nav).getByRole('link',{name:'Products'})).toHaveAttribute('aria-current','page');
  expect(within(nav).getByRole('button',{name:'More navigation'})).not.toHaveAttribute('aria-current');
});

it('keeps Creative Studio section navigation distinct and closes More after navigation',()=>{
  open('seller','/seller/creative#services');
  const nav=screen.getByRole('navigation',{name:'Primary navigation'});
  expect(within(nav).getAllByRole('link').map(a=>a.textContent)).toEqual(['Overview','Services','Enquiries','Portfolio']);
  expect(within(nav).getByRole('link',{name:'Services'})).toHaveAttribute('aria-current','location');
  fireEvent.click(screen.getByRole('button',{name:'More navigation'}));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('link',{name:'Quotations'}));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'More navigation'})).toHaveAttribute('aria-current','location');
});

it('contains keyboard focus in More and does not expose buyer routes to Admin',()=>{
  open('admin','/admin/addresses');
  fireEvent.click(screen.getByRole('button',{name:'More navigation'}));
  const dialog=screen.getByRole('dialog');
  expect([...dialog.querySelectorAll('a')].every(a=>!a.getAttribute('href')?.startsWith('/buyer'))).toBe(true);
  const controls=[...dialog.querySelectorAll<HTMLElement>('a,button')];
  controls.at(-1)!.focus();fireEvent.keyDown(dialog,{key:'Tab'});expect(controls[0]).toHaveFocus();
  fireEvent.keyDown(dialog,{key:'Tab',shiftKey:true});expect(controls.at(-1)).toHaveFocus();
});
