import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { DashboardShell } from './Shared';
import { MobileNavigation, openMobileMenu } from './MobileNavigation';
import { Code2, Palette } from 'lucide-react';
vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{id:'1',name:'Long account name',role:'SELLER'},logout:vi.fn()})}));
beforeEach(()=>vi.stubGlobal('matchMedia',vi.fn(query=>({matches:query==='(max-width: 760px)',media:query,addEventListener:vi.fn(),removeEventListener:vi.fn()}))));
afterEach(()=>vi.unstubAllGlobals());
function open(role:'buyer'|'seller'|'admin',path:string){render(<MemoryRouter initialEntries={[path]}><DashboardShell role={role}><h1>Workspace</h1><section id="services">Services target</section><section id="quotations">Quotations target</section></DashboardShell></MemoryRouter>);}
function primary(){return within(screen.getByRole('navigation',{name:'Primary navigation'}));}
function more(){fireEvent.click(primary().getByRole('button',{name:'Profile'}));return screen.getByRole('dialog',{name:'More destinations'});}
it.each(['/creative-services','/professional-services'])('activates Explore for the public %s catalogue and preserves its distinct menu destination',path=>{
  render(<MemoryRouter initialEntries={[path]}><MobileNavigation items={[
    {href:'/#creative-services',label:'Creative Services',icon:Palette,matchPrefix:'/creative-services'},
    {href:'/#professional-services',label:'Professional Services',icon:Code2,matchPrefix:'/professional-services'},
  ]}/></MemoryRouter>);
  expect(primary().getByRole('link',{name:'Explore'})).toHaveAttribute('aria-current','page');
  expect(primary().getByRole('button',{name:'Profile'})).not.toHaveAttribute('aria-current');
  const dialog=more();
  expect(within(dialog).getByRole('link',{name:'Creative Services'})).toHaveAttribute('href','/#creative-services');
  expect(within(dialog).getByRole('link',{name:'Professional Services'})).toHaveAttribute('href','/#professional-services');
});
it('gives buyers five global actions and preserves cart, payments and separate service destinations',()=>{
  open('buyer','/buyer/orders/42');
  expect(primary().getAllByRole('link').map(a=>a.textContent)).toEqual(['Home','Explore','Orders']);
  expect(primary().getByRole('button',{name:'Create'})).toBeInTheDocument();
  expect(primary().getByRole('link',{name:'Orders'})).toHaveAttribute('aria-current','page');
  const dialog=more();
  expect(within(dialog).getByRole('link',{name:'Cart'})).toHaveAttribute('href','/buyer/cart');
  expect(within(dialog).getByRole('link',{name:'Payments'})).toHaveAttribute('href','/buyer/payments');
  expect(within(dialog).getByRole('link',{name:'Creative Services'})).toHaveAttribute('href','/buyer/creative');
  expect(within(dialog).getByRole('link',{name:'Professional Services'})).toHaveAttribute('href','/buyer/professional');
  expect(within(dialog).queryByRole('link',{name:'Creative Studio'})).not.toBeInTheDocument();
});
it('keeps seller payments active in Profile and restores focus and body scroll on Escape',()=>{
  open('seller','/seller/payments');const trigger=primary().getByRole('button',{name:'Profile'});trigger.focus();expect(trigger).toHaveAttribute('aria-current','page');
  const dialog=more();expect(document.body.style.overflow).toBe('hidden');
  expect(within(dialog).getByRole('link',{name:'Payments'})).toHaveAttribute('aria-current','page');
  expect(within(dialog).getByRole('link',{name:'Creative Studio'})).toHaveAttribute('href','/seller/creative');
  expect(within(dialog).getByRole('button',{name:'Log out'})).toBeInTheDocument();
  fireEvent.keyDown(dialog,{key:'Escape'});expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(trigger).toHaveFocus();expect(document.body.style.overflow).toBe('');
});
it('marks product creation active and offers separate existing seller creation workflows',()=>{
  open('seller','/seller/products/new');expect(primary().getByRole('button',{name:'Create'})).toHaveAttribute('aria-current','page');
  fireEvent.click(primary().getByRole('button',{name:'Create'}));const dialog=screen.getByRole('dialog',{name:'Create something local'});
  expect(within(dialog).getByRole('link',{name:'Add product'})).toHaveAttribute('href','/seller/products/new');
  expect(within(dialog).getByRole('link',{name:'Creative service'})).toHaveAttribute('href','/seller/creative#services');
  expect(within(dialog).getByRole('link',{name:'Professional service'})).toHaveAttribute('href','/seller/professional#services');
  expect(within(dialog).getByRole('link',{name:'Property listing'})).toHaveAttribute('href','/seller/properties');
});
it('keeps Creative section destinations active and closes Profile after navigation',()=>{
  open('seller','/seller/creative#services');const dialog=more();
  expect(within(dialog).getByRole('link',{name:'Services'})).toHaveAttribute('aria-current','location');
  expect(within(dialog).getByRole('link',{name:'Professional Dashboard'})).toHaveAttribute('href','/seller/professional');
  fireEvent.click(within(dialog).getByRole('link',{name:'Quotations'}));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(primary().getByRole('button',{name:'Profile'})).toHaveAttribute('aria-current','location');
});
it('contains Profile keyboard focus and does not expose buyer routes to Admin',()=>{
  open('admin','/admin/addresses');expect(primary().getByRole('link',{name:'Orders'})).toHaveAttribute('href','/admin/operations');const dialog=more();
  expect([...dialog.querySelectorAll('a')].every(a=>!a.getAttribute('href')?.startsWith('/buyer'))).toBe(true);
  const controls=[...dialog.querySelectorAll<HTMLElement>('a,button')];controls.at(-1)!.focus();fireEvent.keyDown(dialog,{key:'Tab'});expect(controls[0]).toHaveFocus();fireEvent.keyDown(dialog,{key:'Tab',shiftKey:true});expect(controls.at(-1)).toHaveFocus();
});
it.each(['buyer','admin'] as const)('does not grant %s seller create access',role=>{
  open(role,`/${role}`);fireEvent.click(primary().getByRole('button',{name:'Create'}));const dialog=screen.getByRole('dialog',{name:'Create something local'});
  expect([...dialog.querySelectorAll('a')].every(a=>!a.getAttribute('href')?.startsWith('/seller'))).toBe(true);
  expect(within(dialog).getByRole('link',{name:role==='admin'?'Open moderation workspace':'Register as a seller'})).toHaveAttribute('href',role==='admin'?'/admin':'/register?role=seller');
});
it('offers anonymous orders sign-in and seller guidance without seller write links',()=>{
  render(<MemoryRouter><MobileNavigation items={[]}/></MemoryRouter>);expect(primary().getByRole('link',{name:'Orders'})).toHaveAttribute('href','/login/buyer');
  fireEvent.click(primary().getByRole('button',{name:'Create'}));const dialog=screen.getByRole('dialog',{name:'Create something local'});
  expect(within(dialog).getByRole('link',{name:'Sign in as a seller'})).toHaveAttribute('href','/login/seller');expect([...dialog.querySelectorAll('a')].every(a=>!a.getAttribute('href')?.startsWith('/seller/'))).toBe(true);
});
it('opens Profile from the header event and restores header focus',()=>{
  render(<MemoryRouter><button onClick={openMobileMenu}>Header menu</button><MobileNavigation items={[]}/></MemoryRouter>);
  const trigger=screen.getByRole('button',{name:'Header menu'});trigger.focus();fireEvent.click(trigger);const dialog=screen.getByRole('dialog',{name:'More destinations'});fireEvent.keyDown(dialog,{key:'Escape'});expect(trigger).toHaveFocus();
});
it('contains Create keyboard focus and restores focus on Escape',()=>{
  open('seller','/seller');const trigger=primary().getByRole('button',{name:'Create'});trigger.focus();fireEvent.click(trigger);
  const dialog=screen.getByRole('dialog',{name:'Create something local'}),controls=[...dialog.querySelectorAll<HTMLElement>('a,button')];controls.at(-1)!.focus();fireEvent.keyDown(dialog,{key:'Tab'});expect(controls[0]).toHaveFocus();fireEvent.keyDown(dialog,{key:'Tab',shiftKey:true});expect(controls.at(-1)).toHaveFocus();fireEvent.keyDown(dialog,{key:'Escape'});expect(trigger).toHaveFocus();expect(document.body.style.overflow).toBe('');
});
