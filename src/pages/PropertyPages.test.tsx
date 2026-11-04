import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { propertyDraft, reportReasons, PropertyDetailPage, PropertyRequestsPage, PropertyModerationPage } from './PropertyPages';
import { propertiesApi } from '../api/properties';
vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{role:'BUYER',name:'Buyer'},logout:vi.fn()})}));
afterEach(()=>vi.restoreAllMocks());
describe('property form contracts',()=>{
  it('keeps sale inputs separate from moderation and proof upload',()=>{
    expect(propertyDraft.category).toBe('Residential');
    expect(propertyDraft).not.toHaveProperty('status');
    expect(propertyDraft).not.toHaveProperty('proof_url');
  });
  it('offers the approved report reasons',()=>{
    expect(reportReasons).toEqual(['fake/misleading','wrong information','already sold','suspicious owner/agent','inappropriate content','other']);
  });
});

it('sends a private enquiry and keeps private address absent from public details',async()=>{
  vi.spyOn(propertiesApi,'detail').mockResolvedValue({id:'9',creator_id:'2',title:'Sale home',description:'Quiet house',category:'Residential',price:'100',locality:'Pune',status:'APPROVED',expires_at:'2040-01-01T00:00:00Z',updated_at:'2030-01-01T00:00:00Z',capacity:'OWNER',display_name:'Owner',rejection_reason:null});
  const command=vi.spyOn(propertiesApi,'command').mockResolvedValue({});
  render(<MemoryRouter initialEntries={['/buyer/properties/9']}><Routes><Route path="/buyer/properties/:id" element={<PropertyDetailPage/>}/></Routes></MemoryRouter>);
  await screen.findByText('Sale home');
  expect(screen.queryByText('Private postal address')).not.toBeInTheDocument();
  await userEvent.type(screen.getByLabelText('Enquiry'),'Is this available?');
  await userEvent.click(screen.getByRole('button',{name:'Send enquiry'}));
  await waitFor(()=>expect(command).toHaveBeenCalledWith('9','enquiries',{message:'Is this available?'}));
  expect(await screen.findByText('Saved.')).toBeInTheDocument();
});

it('shows a request failure and recovers on reload without revealing an address',async()=>{
  const requests=vi.spyOn(propertiesApi,'requests').mockRejectedValueOnce(new Error('Unavailable')).mockResolvedValue({enquiries:[],visits:[]});
  render(<MemoryRouter><PropertyRequestsPage/></MemoryRouter>);
  expect(await screen.findByRole('alert')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button',{name:'Reload requests'}));
  expect(await screen.findByText('No visits yet.')).toBeInTheDocument();
  expect(requests).toHaveBeenCalledTimes(2);
  expect(screen.queryByRole('button',{name:'View appointment address'})).not.toBeInTheDocument();
});

it('keeps an explicitly fetched appointment address visible until a visit state mutation',async()=>{
  const visit={id:'7',property_id:'9',scheduled_at:'2040-01-01T00:00:00Z',status:'CONFIRMED',reason:null};
  const requests=vi.spyOn(propertiesApi,'requests').mockResolvedValue({enquiries:[],visits:[visit]});
  vi.spyOn(propertiesApi,'visitLocation').mockResolvedValue({address:'123 Private appointment lane'});
  vi.spyOn(propertiesApi,'visitAction').mockImplementation(async()=>{requests.mockResolvedValue({enquiries:[],visits:[{...visit,status:'CANCELLED'}]});});
  render(<MemoryRouter><PropertyRequestsPage/></MemoryRouter>);
  await userEvent.click(await screen.findByRole('button',{name:'View appointment address'}));
  expect(await screen.findByText('Appointment address: 123 Private appointment lane')).toBeInTheDocument();
  expect(requests).toHaveBeenCalledTimes(1);
  await userEvent.click(screen.getByRole('button',{name:'Cancel visit'}));
  await waitFor(()=>expect(screen.queryByText(/Appointment address:/)).not.toBeInTheDocument());
});

it('approves only the exact property version shown in the moderation queue',async()=>{
  const updated_at='2030-01-01T00:00:00Z';
  vi.spyOn(propertiesApi,'queue').mockResolvedValue([{id:'9',creator_id:'2',title:'Pending home',description:'House',category:'Residential',price:'100',locality:'Pune',status:'PENDING',expires_at:'2040-01-01T00:00:00Z',updated_at,capacity:'AGENT',display_name:'Agent',rejection_reason:null}]);
  vi.spyOn(propertiesApi,'reports').mockResolvedValue([]);
  const command=vi.spyOn(propertiesApi,'command').mockResolvedValue({});
  render(<MemoryRouter><PropertyModerationPage/></MemoryRouter>);
  await userEvent.click(await screen.findByRole('button',{name:'APPROVED'}));
  await waitFor(()=>expect(command).toHaveBeenCalledWith('9','moderation',{status:'APPROVED',reason:null,expected_updated_at:updated_at}));
});
