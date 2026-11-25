import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { PropertyRequestsPage } from './PropertyPages';
import { propertiesApi } from '../api/properties';
const account=vi.hoisted(()=>({role:'BUYER'}));
vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{...account,name:'Reviewer'},logout:vi.fn()})}));
afterEach(()=>vi.restoreAllMocks());
it.each(['BUYER','SELLER','ADMIN'])('offers only authorized property destinations to %s',async role=>{
  account.role=role;vi.spyOn(propertiesApi,'requests').mockResolvedValue({enquiries:[],visits:[]});
  render(<MemoryRouter><PropertyRequestsPage/></MemoryRouter>);
  await screen.findByText('No enquiries yet.');
  const nav=screen.getByRole('navigation',{name:'Property navigation'});
  const links=within(nav).getAllByRole('link');
  expect(links.every(a=>a.getAttribute('href')?.startsWith(`/${role.toLowerCase()}/`))).toBe(true);
  if(role!=='BUYER')expect(within(nav).queryByRole('link',{name:'Saved'})).not.toBeInTheDocument();
});
