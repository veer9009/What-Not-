import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import type { ReactNode } from 'react';
import { BuyerCreativePage, SellerCreativePage } from './CreativePages';
import { creativeApi } from '../api/creative';
import { ApiError } from '../api/client';
vi.mock('../components/Shared',()=>({DashboardShell:({children}:{children:ReactNode})=><main>{children}</main>,PageTop:({title}:{title:string})=><h1>{title}</h1>}));
vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{id:'1'}})}));
vi.mock('../api/creative',()=>({creativeApi:{listings:vi.fn(),own:vi.fn(),rfqs:vi.fn(),engagements:vi.fn(),provider:vi.fn(),complete:vi.fn(),deliver:vi.fn(),create:vi.fn(),update:vi.fn(),enquire:vi.fn(),respond:vi.fn(),responses:vi.fn()}}));
beforeEach(()=>{vi.mocked(creativeApi.listings).mockResolvedValue([]);vi.mocked(creativeApi.own).mockResolvedValue([]);vi.mocked(creativeApi.rfqs).mockResolvedValue([]);vi.mocked(creativeApi.provider).mockResolvedValue(null);});
afterEach(()=>{cleanup();sessionStorage.clear();vi.clearAllMocks();});
it('buyer confirms delivered work and reloads authoritative completion',async()=>{
  vi.mocked(creativeApi.engagements).mockResolvedValueOnce([{id:'9007199254740993',rfq_id:'1',response_id:'2',title:'Logo',terms:'Final files',amount:'120',currency:'INR',status:'DELIVERED'}]).mockResolvedValue([{id:'9007199254740993',rfq_id:'1',response_id:'2',title:'Logo',terms:'Final files',amount:'120',currency:'INR',status:'COMPLETED',reviewed:true}]);
  vi.mocked(creativeApi.complete).mockResolvedValue({} as never);
  render(<BuyerCreativePage/>);fireEvent.click(await screen.findByRole('button',{name:'Confirm received and complete'}));
  await waitFor(()=>expect(creativeApi.complete).toHaveBeenCalledWith('9007199254740993'));
  expect(await screen.findByText(/COMPLETED/)).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Submit review'})).not.toBeInTheDocument();
});
it('seller sees delivery action and cannot confirm buyer receipt',async()=>{
  vi.mocked(creativeApi.engagements).mockResolvedValue([{id:'3',rfq_id:'1',response_id:'2',title:'Logo',terms:'Final files',amount:'120',currency:'INR',status:'ACCEPTED'}]);
  render(<SellerCreativePage/>);expect(await screen.findByRole('button',{name:'Mark delivered'})).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Confirm received and complete'})).not.toBeInTheDocument();
});

it('creates and edits multiple portfolio links on separate real lines',async()=>{
  const listing={id:'44',provider_id:'2',title:'Design',description:'A brand',category:'Video Editing',pricing:'FIXED' as const,amount:'100',currency:'INR' as const,remote:true,locality:null,portfolio:['https://example.test/one','https://example.test/two'],is_active:true,status:'PENDING',rejection_reason:null};
  vi.mocked(creativeApi.provider).mockResolvedValue({id:'2',user_id:'3',display_name:'Studio',bio:'Design'});
  vi.mocked(creativeApi.engagements).mockResolvedValue([]);
  vi.mocked(creativeApi.own).mockResolvedValue([listing]);
  vi.mocked(creativeApi.create).mockResolvedValue(listing);vi.mocked(creativeApi.update).mockResolvedValue(listing);
  render(<SellerCreativePage/>);
  fireEvent.change(await screen.findByLabelText('Title'),{target:{value:'Design'}});
  fireEvent.change(screen.getByLabelText('Description'),{target:{value:'A brand'}});
  fireEvent.change(screen.getByLabelText('Amount (INR)'),{target:{value:'100'}});
  fireEvent.change(screen.getByLabelText(/Portfolio or video/),{target:{value:'https://example.test/one\nhttps://example.test/two'}});
  fireEvent.click(screen.getByRole('button',{name:'Submit for review'}));
  await waitFor(()=>expect(creativeApi.create).toHaveBeenCalledWith(expect.objectContaining({portfolio:listing.portfolio})));
  fireEvent.click(await screen.findByRole('button',{name:'Edit and submit for review'}));
  expect(screen.getByLabelText(/Portfolio or video/)).toHaveValue(listing.portfolio.join('\n'));
  fireEvent.click(screen.getByRole('button',{name:'Submit for review'}));
  await waitFor(()=>expect(creativeApi.update).toHaveBeenCalledWith('44',expect.objectContaining({portfolio:listing.portfolio})));
});

it.each([false,true])('retries an ambiguous enquiry using its original payload and key after remount=%s',async(remount)=>{
  const listing={id:'44',provider_id:'2',title:'Design',description:'A brand',category:'Video Editing',pricing:'FIXED' as const,amount:'100',currency:'INR' as const,remote:true,locality:null,portfolio:[],is_active:true,status:'APPROVED',rejection_reason:null};
  vi.mocked(creativeApi.listings).mockResolvedValue([listing]);vi.mocked(creativeApi.engagements).mockResolvedValue([]);
  vi.mocked(creativeApi.enquire).mockRejectedValueOnce(new ApiError(0,'Connection lost')).mockResolvedValue({id:'9',listing_id:'44',buyer_id:'1',brief:'Original'});
  render(<BuyerCreativePage/>);const brief=await screen.findByLabelText('Describe the work you need');
  fireEvent.change(brief,{target:{value:'Original'}});fireEvent.click(screen.getByRole('button',{name:'Send private enquiry'}));
  await screen.findByText('Connection lost');
  if(remount){cleanup();render(<BuyerCreativePage/>);await screen.findByRole('button',{name:'Retry original enquiry'});}
  fireEvent.change(brief,{target:{value:'Changed after failure'}});fireEvent.click(screen.getByRole('button',{name:/Retry original enquiry|Send private enquiry/}));
  await waitFor(()=>expect(creativeApi.enquire).toHaveBeenCalledTimes(2));
  const calls=vi.mocked(creativeApi.enquire).mock.calls;
  expect(calls[0][1]).toBe('Original');expect(calls[1]).toEqual(calls[0]);expect(calls[0][2]).toMatch(/^[a-f0-9-]{36}$/);
});

it.each([false,true])('retries an ambiguous provider quote with its original amount and terms after remount=%s',async(remount)=>{
  vi.mocked(creativeApi.rfqs).mockResolvedValue([{id:'44',listing_id:'2',buyer_id:'1',brief:'Logo please'}]);
  vi.mocked(creativeApi.responses).mockResolvedValue([]);vi.mocked(creativeApi.engagements).mockResolvedValue([]);
  vi.mocked(creativeApi.respond).mockRejectedValueOnce(new ApiError(0,'Quote connection lost')).mockResolvedValue({id:'9',rfq_id:'44',terms:'Original scope',amount:'100',currency:'INR'});
  render(<SellerCreativePage/>);
  const terms=await screen.findByLabelText('Scope and delivery terms');const amount=screen.getByLabelText('Quote (INR)');
  fireEvent.change(terms,{target:{value:'Original scope'}});fireEvent.change(amount,{target:{value:'100'}});
  fireEvent.click(screen.getByRole('button',{name:'Send quote'}));await screen.findByText('Quote connection lost');
  if(remount){cleanup();render(<SellerCreativePage/>);await screen.findByRole('button',{name:'Retry original quote'});}
  fireEvent.change(terms,{target:{value:'Changed'}});fireEvent.change(amount,{target:{value:'999'}});
  fireEvent.click(screen.getByRole('button',{name:'Retry original quote'}));
  await waitFor(()=>expect(creativeApi.respond).toHaveBeenCalledTimes(2));
  const calls=vi.mocked(creativeApi.respond).mock.calls;
  expect(calls[0].slice(0,3)).toEqual(['44','Original scope','100']);expect(calls[1]).toEqual(calls[0]);expect(calls[0][3]).toMatch(/^[a-f0-9-]{36}$/);
});
