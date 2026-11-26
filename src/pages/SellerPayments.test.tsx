import { fireEvent, render, screen, within, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Profiler } from 'react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { PaymentsPage } from './PaymentsPage';
import { paymentsApi, type PaymentRecord } from '../api/payments';
import { ApiError } from '../api/client';

vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{role:'SELLER',id:'1',name:'Reviewer'},logout:vi.fn()})}));
vi.mock('../api/payments',()=>({paymentsApi:{summary:vi.fn(),list:vi.fn(),metrics:vi.fn(),method:vi.fn(),report:vi.fn(),confirm:vi.fn()}}));
const record:PaymentRecord={order_id:'9007199254740993',seller_id:'2',seller_name:'Local maker',amount:'549.00',currency:'INR',order_status:'ACCEPTED',order_date:'2026-11-24T00:00:00Z',method:'UPI',status:'PENDING',reference:'REF-'+ 'A'.repeat(96),reported_at:null,confirmed_at:null,can_select_method:false,can_report:false,can_confirm:true};
beforeEach(()=>{vi.mocked(paymentsApi.summary).mockResolvedValue({currency:'INR',order_value:'10000.00',confirmed_collections:'5000.00',pending_cod_collections:'3000.00',upi_awaiting_verification:'2000.00',platform_revenue:'0.00',scope:'ALL_OWNED_ORDERS'});vi.mocked(paymentsApi.list).mockResolvedValue({items:[record],has_more:false});});
afterEach(()=>{vi.clearAllMocks();vi.unstubAllGlobals();});
function open(){render(<MemoryRouter><PaymentsPage/></MemoryRouter>);}
function summary(){return screen.getByRole('region',{name:'Payment summary on this page'});}
function unavailable(){expect(within(summary()).getAllByText('Unavailable')).toHaveLength(3);expect(within(summary()).queryByText(/INR/)).not.toBeInTheDocument();}

it('keeps summary cards and record structure visible during initial loading',()=>{
  vi.mocked(paymentsApi.list).mockReturnValue(new Promise(()=>{}));open();
  unavailable();
  expect(screen.getByRole('region',{name:'Payment-related orders'})).toHaveAttribute('aria-busy','true');
  expect(screen.getByRole('status')).toHaveTextContent('Loading payment records');
  expect(screen.getByText(/up to 50/)).toBeInTheDocument();
  expect(screen.queryByText('Needs Review')).not.toBeInTheDocument();
});

it('shows a successful empty page as zero and explains the next action',async()=>{
  vi.mocked(paymentsApi.list).mockResolvedValue({items:[],has_more:false});open();
  await screen.findByRole('heading',{name:'No payment records on this page'});
  expect(within(summary()).getAllByText('INR 0.00')).toHaveLength(3);
  expect(screen.getByRole('link',{name:'View orders'})).toHaveAttribute('href','/seller/orders');
  expect(screen.queryByRole('button',{name:'Review collection'})).not.toBeInTheDocument();
});

it.each([503,401])('preserves unavailable summaries and a working Retry after HTTP %i',async status=>{
  const message=status===401?'Your session expired or your credentials are invalid. Please sign in again.':'The marketplace service is unavailable. Please try again later.';
  vi.mocked(paymentsApi.list).mockRejectedValueOnce(new ApiError(status,message));open();
  expect(await screen.findByRole('alert')).toHaveTextContent(message);unavailable();
  expect(screen.getByRole('region',{name:'Payment-related orders'})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Retry'}));
  await screen.findByRole('table',{name:'Payment records'});
  expect(paymentsApi.list).toHaveBeenCalledTimes(2);
  expect(within(summary()).getAllByText('INR 549.00')).toHaveLength(2);
});

it('withholds previously loaded totals throughout refresh and after refresh failure',async()=>{
  open();await screen.findByRole('table',{name:'Payment records'});
  let rejectRefresh!:(reason:unknown)=>void;
  vi.mocked(paymentsApi.list).mockReturnValueOnce(new Promise((_,reject)=>{rejectRefresh=reject;}));
  fireEvent.click(screen.getByRole('button',{name:'Refresh payments'}));
  unavailable();expect(screen.queryByRole('table')).not.toBeInTheDocument();
  rejectRefresh(new ApiError(503,'The marketplace service is unavailable. Please try again later.'));
  await screen.findByRole('alert');unavailable();
});

it('uses a desktop table with supported fields and keeps guidance after the records',async()=>{
  open();const table=await screen.findByRole('table',{name:'Payment records'});
  for(const label of ['Order','Amount','Method','Recorded status','Order date','Actions'])expect(within(table).getByRole('columnheader',{name:label})).toBeInTheDocument();
  expect(within(table).getByRole('heading',{name:'Order #9007199254740993'})).toBeInTheDocument();
  expect(within(table).getByText(record.reference!)).toBeInTheDocument();
  expect(within(table).getByRole('button',{name:'Review collection'})).toBeEnabled();
  const guidance=screen.getByText('Payment guidance and limitations').closest('details')!;
  expect(guidance).not.toHaveAttribute('open');
  expect(summary().compareDocumentPosition(table)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(table.compareDocumentPosition(guidance)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(within(summary()).getByText(/not your full account or all seller orders/)).toBeInTheDocument();
  expect(paymentsApi.metrics).not.toHaveBeenCalled();
});

it('renders one mobile record/action variant and preserves receipt review focus',async()=>{
  vi.stubGlobal('matchMedia',()=>({matches:true,addEventListener:vi.fn(),removeEventListener:vi.fn()}));
  open();await screen.findByRole('article',{name:'Order #9007199254740993'});
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  expect(screen.getAllByRole('button',{name:'Review collection'})).toHaveLength(1);
  fireEvent.click(screen.getByRole('button',{name:'Review collection'}));
  expect(within(screen.getByRole('alertdialog')).getByRole('button',{name:'Cancel'})).toHaveFocus();
  fireEvent.click(screen.getByRole('button',{name:'Cancel'}));
  expect(screen.getByRole('button',{name:'Review collection'})).toHaveFocus();
  expect(paymentsApi.confirm).not.toHaveBeenCalled();
});

it('never labels previous page financial values with the newly requested page number',async()=>{
  vi.mocked(paymentsApi.list).mockImplementation(offset=>offset?new Promise(()=>{}):Promise.resolve({items:[record],has_more:true}));
  const staleCommits:string[]=[];
  render(<MemoryRouter><Profiler id="payments" onRender={()=>{
    const page=document.querySelector('[aria-label="Payments pages"]')?.textContent??'';
    const totals=document.querySelector('[aria-label="Payment summary on this page"]')?.textContent??'';
    if(page.includes('Page 2')&&totals.includes('549.00'))staleCommits.push(totals);
  }}><PaymentsPage/></Profiler></MemoryRouter>);
  await screen.findByRole('table',{name:'Payment records'});
  fireEvent.click(screen.getByRole('button',{name:'Next page'}));
  await waitFor(()=>expect(paymentsApi.list).toHaveBeenLastCalledWith(50));
  expect(staleCommits).toEqual([]);unavailable();
});

it('gives desktop receipt review the full record width instead of the narrow actions cell',async()=>{
  open();fireEvent.click(await screen.findByRole('button',{name:'Review collection'}));
  const review=screen.getByRole('alertdialog');
  expect(review.closest('td')).toHaveAttribute('colspan','6');
  expect(within(review).getByRole('button',{name:'Cancel'})).toHaveFocus();
});

it('filters only loaded records by method without changing loaded-page financial totals',async()=>{
  vi.mocked(paymentsApi.list).mockResolvedValue({items:[{...record,order_id:'1',amount:'250.00',method:'COD'},{...record,order_id:'2',amount:'125.00',method:'UPI',status:'BUYER_REPORTED'}],has_more:true});
  open();await screen.findByRole('table',{name:'Payment records'});
  expect(within(summary()).getAllByText('INR 375.00')).toHaveLength(2);
  fireEvent.click(screen.getByRole('button',{name:'COD'}));
  expect(screen.getByRole('heading',{name:'Order #1'})).toBeInTheDocument();
  expect(screen.queryByRole('heading',{name:'Order #2'})).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'COD'})).toHaveAttribute('aria-pressed','true');
  expect(within(summary()).getAllByText('INR 375.00')).toHaveLength(2);
  fireEvent.click(screen.getByRole('button',{name:'UPI'}));
  expect(screen.getByRole('heading',{name:'Order #2'})).toBeInTheDocument();
  expect(screen.getByText('Payment reported')).toBeInTheDocument();
  expect(screen.getByText('Buyer report · unverified')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'All Payments'}));
  expect(screen.getAllByRole('heading',{name:/Order #/})).toHaveLength(2);
  expect(paymentsApi.list).toHaveBeenCalledTimes(1);
});

it('provides a useful empty method filter and resets to all loaded payments',async()=>{
  open();await screen.findByRole('table',{name:'Payment records'});
  fireEvent.click(screen.getByRole('button',{name:'COD'}));
  expect(screen.getByRole('heading',{name:'No COD records on this page'})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Show all payments'}));
  expect(screen.getByRole('heading',{name:'Order #9007199254740993'})).toBeInTheDocument();
  expect(within(summary()).getAllByText('INR 549.00')).toHaveLength(2);
});
it('shows server account totals separately from the loaded page and refreshes both',async()=>{
 open();const account=await screen.findByRole('region',{name:'All owned orders payment summary'});await within(account).findByText('INR 10000.00');expect(within(account).getByText('INR 5000.00')).toBeInTheDocument();expect(within(account).getByText('INR 3000.00')).toBeInTheDocument();expect(within(account).getByText('INR 2000.00')).toBeInTheDocument();expect(within(account).getByText('INR 0.00')).toBeInTheDocument();
 expect(within(summary()).getAllByText('INR 549.00')).toHaveLength(2);const calls=vi.mocked(paymentsApi.summary).mock.calls.length;fireEvent.click(screen.getByRole('button',{name:'Refresh payments'}));await waitFor(()=>expect(paymentsApi.summary).toHaveBeenCalledTimes(calls+1));
});
it('filters pending COD, awaiting UPI verification and confirmed records on this page',async()=>{
 vi.mocked(paymentsApi.list).mockResolvedValue({items:[{...record,order_id:'1',method:'COD'},{...record,order_id:'2',status:'BUYER_REPORTED'},{...record,order_id:'3',status:'SELLER_CONFIRMED',can_confirm:false},{...record,order_id:'4',method:'COD',order_status:'CANCELLED'}],has_more:false});open();await screen.findByRole('table',{name:'Payment records'});
 fireEvent.click(screen.getByRole('button',{name:'Pending collection'}));expect(screen.getAllByRole('heading',{name:/Order #/})).toHaveLength(1);expect(screen.getByRole('heading',{name:'Order #1'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Awaiting verification'}));expect(screen.getAllByRole('heading',{name:/Order #/})).toHaveLength(1);expect(screen.getByRole('heading',{name:'Order #2'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Confirmed received'}));expect(screen.getAllByRole('heading',{name:/Order #/})).toHaveLength(1);expect(screen.getByRole('heading',{name:'Order #3'})).toBeInTheDocument();expect(paymentsApi.list).toHaveBeenCalledTimes(1);
});
it('explains an empty status filter and restores the loaded records',async()=>{
 open();await screen.findByRole('table',{name:'Payment records'});fireEvent.click(screen.getByRole('button',{name:'Confirmed received'}));expect(screen.getByRole('heading',{name:'No matching payment records on this page'})).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Show all payments'}));expect(screen.getByRole('heading',{name:'Order #9007199254740993'})).toBeInTheDocument();
});
