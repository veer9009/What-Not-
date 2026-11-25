import { fireEvent, render, screen, within, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { PaymentsPage } from './PaymentsPage';
import { paymentsApi, type PaymentRecord } from '../api/payments';
import { ApiError } from '../api/client';
const account=vi.hoisted(()=>({role:'BUYER'}));
vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{...account,id:'1',name:'Reviewer'},logout:vi.fn()})}));
vi.mock('../api/payments',()=>({paymentsApi:{list:vi.fn(),metrics:vi.fn(),method:vi.fn(),report:vi.fn(),confirm:vi.fn()}}));
const record:PaymentRecord={order_id:'9007199254740993',seller_id:'2',seller_name:'Local maker',amount:'549.00',currency:'INR',order_status:'ACCEPTED',order_date:'2026-11-24T00:00:00Z',method:null,status:'NOT_RECORDED',reference:null,reported_at:null,confirmed_at:null,can_select_method:true,can_report:false,can_confirm:false};
beforeEach(()=>{account.role='BUYER';vi.mocked(paymentsApi.list).mockResolvedValue({items:[record],has_more:false});});
afterEach(()=>vi.clearAllMocks());
function open(){render(<MemoryRouter><PaymentsPage/></MemoryRouter>);}

it('records an explicit buyer method and never invents legacy payment details',async()=>{
  vi.mocked(paymentsApi.method).mockResolvedValue({...record,method:'COD',status:'PENDING',can_select_method:false});
  open();await screen.findByText('Local maker');
  expect(screen.getAllByText('Not recorded').length).toBeGreaterThan(0);
  expect(screen.getByText('INR 549.00')).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Review collection'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('radio',{name:/Cash on delivery/}));
  fireEvent.click(screen.getByRole('button',{name:'Record method'}));
  await waitFor(()=>expect(paymentsApi.method).toHaveBeenCalledWith('9007199254740993','COD'));
  await waitFor(()=>expect(screen.getByRole('heading',{name:`Order #${record.order_id}`})).toHaveFocus());
});

it('shows COD and direct UPI as labelled choices with short descriptions and icons',async()=>{
  open();await screen.findByText('Local maker');
  const choices=screen.getByRole('group',{name:'Payment method'});
  expect(within(choices).getByRole('radio',{name:/Cash on delivery/})).toBeInTheDocument();
  expect(within(choices).getByRole('radio',{name:/Direct UPI/})).toBeInTheDocument();
  expect(within(choices).getByText('Pay cash to your seller at delivery.')).toBeInTheDocument();
  expect(within(choices).getByText('Pay your seller directly; report payment after acceptance.')).toBeInTheDocument();
  expect(choices.querySelectorAll('svg[aria-hidden="true"]')).toHaveLength(2);
  fireEvent.click(within(choices).getByRole('radio',{name:/Direct UPI/}));
  fireEvent.submit(screen.getByRole('button',{name:'Record method'}).closest('form')!);
  await waitFor(()=>expect(paymentsApi.method).toHaveBeenCalledWith(record.order_id,'UPI'));
});

it('validates an optional UPI reference and reports it without claiming verification',async()=>{
  vi.mocked(paymentsApi.list).mockResolvedValue({items:[{...record,method:'UPI',status:'PENDING',can_select_method:false,can_report:true}],has_more:false});
  vi.mocked(paymentsApi.report).mockResolvedValue({...record,method:'UPI',status:'BUYER_REPORTED'});
  open();await screen.findByLabelText('Payment reference (optional)');
  fireEvent.change(screen.getByLabelText('Payment reference (optional)'),{target:{value:'<script>'}});
  fireEvent.click(screen.getByRole('checkbox',{name:'I sent this payment directly to the seller'}));
  fireEvent.submit(screen.getByRole('button',{name:'Report payment'}).closest('form')!);
  expect(paymentsApi.report).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Payment reference (optional)')).toHaveAttribute('aria-invalid','true');
  fireEvent.change(screen.getByLabelText('Payment reference (optional)'),{target:{value:'REF-123456789'}});
  fireEvent.submit(screen.getByRole('button',{name:'Report payment'}).closest('form')!);
  await waitFor(()=>expect(paymentsApi.report).toHaveBeenCalledWith(record.order_id,'REF-123456789'));
  await waitFor(()=>expect(screen.getByRole('heading',{name:`Order #${record.order_id}`})).toHaveFocus());
  expect(screen.getByText(/not bank verification/i)).toBeInTheDocument();
});

it('requires seller review and sends the reviewed status without allowing buyer reporting',async()=>{
  account.role='SELLER';
  vi.mocked(paymentsApi.list).mockResolvedValue({items:[{...record,method:'UPI',status:'BUYER_REPORTED',reference:'REF-123',can_select_method:false,can_report:false,can_confirm:true}],has_more:false});
  vi.mocked(paymentsApi.confirm).mockResolvedValue({...record,status:'SELLER_CONFIRMED'});
  open();fireEvent.click(await screen.findByRole('button',{name:'Review collection'}));
  expect(paymentsApi.confirm).not.toHaveBeenCalled();
  const confirmation=screen.getByRole('alertdialog');
  expect(within(confirmation).getByText(/Check your cash or UPI account/)).toBeInTheDocument();
  fireEvent.click(within(confirmation).getByRole('button',{name:'Cancel'}));
  expect(screen.getByRole('button',{name:'Review collection'})).toHaveFocus();
  fireEvent.click(screen.getByRole('button',{name:'Review collection'}));
  fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button',{name:'Confirm collected'}));
  await waitFor(()=>expect(paymentsApi.confirm).toHaveBeenCalledWith(record.order_id,'BUYER_REPORTED'));
  await waitFor(()=>expect(screen.getByRole('heading',{name:`Order #${record.order_id}`})).toHaveFocus());
  expect(screen.queryByRole('button',{name:'Report payment'})).not.toBeInTheDocument();
});

it('shows persisted admin metrics separately from platform revenue and permits no mutations',async()=>{
  account.role='ADMIN';vi.mocked(paymentsApi.metrics).mockResolvedValue({currency:'INR',order_count:1,order_value:'549.00',cod_order_value:'0.00',upi_order_value:'549.00',unrecorded_order_value:'0.00',buyer_reported_count:1,buyer_reported_value:'549.00',seller_confirmed_count:1,seller_confirmed_value:'549.00',pending_confirmation_count:0,cancelled_order_value:'0.00',cancelled_confirmed_value:'0.00',platform_revenue:'0.00'});
  open();await screen.findByText('Platform revenue');
  expect(within(screen.getByRole('region',{name:'Payment metrics'})).getByText(/Order value is not seller collections/)).toBeInTheDocument();
  for(const name of ['Record method','Report payment','Review collection'])expect(screen.queryByRole('button',{name})).not.toBeInTheDocument();
});

it('keeps a stale confirmation unconfirmed and requires refresh before review',async()=>{
  account.role='SELLER';
  vi.mocked(paymentsApi.list).mockResolvedValue({items:[{...record,method:'UPI',status:'PENDING',can_select_method:false,can_confirm:true}],has_more:false});
  vi.mocked(paymentsApi.confirm).mockRejectedValueOnce(new ApiError(409,'private backend details'));
  open();fireEvent.click(await screen.findByRole('button',{name:'Review collection'}));
  fireEvent.click(screen.getByRole('button',{name:'Confirm collected'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Refresh and review before retrying');
  expect(screen.queryByText('Seller confirmed')).not.toBeInTheDocument();
  expect(screen.queryByText(/private backend details/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Refresh payments'}));
  await waitFor(()=>expect(paymentsApi.list).toHaveBeenCalledTimes(2));
  expect(await screen.findByRole('button',{name:'Review collection'})).toBeEnabled();
});

it('uses server pagination and returns to the previous payment page',async()=>{
  vi.mocked(paymentsApi.list).mockImplementation(async offset=>({items:[{...record,order_id:offset?'52':'1'}],has_more:!offset}));
  open();await screen.findByRole('heading',{name:'Order #1'});
  expect(screen.getByRole('button',{name:'Previous page'})).toBeDisabled();
  fireEvent.click(screen.getByRole('button',{name:'Next page'}));
  await screen.findByRole('heading',{name:'Order #52'});
  await waitFor(()=>expect(screen.getByRole('heading',{name:'Order #52'})).toHaveFocus());
  expect(paymentsApi.list).toHaveBeenLastCalledWith(50);
  expect(screen.getByRole('button',{name:'Next page'})).toBeDisabled();
  fireEvent.click(screen.getByRole('button',{name:'Previous page'}));
  await screen.findByRole('heading',{name:'Order #1'});
  await waitFor(()=>expect(screen.getByRole('heading',{name:'Order #1'})).toHaveFocus());
  expect(paymentsApi.list).toHaveBeenLastCalledWith(0);
});

it('labels seller totals as the loaded page and keeps gross collections separate',async()=>{
  account.role='SELLER';
  vi.mocked(paymentsApi.list).mockResolvedValue({items:[{...record,method:'COD',status:'PENDING',can_select_method:false},{...record,order_id:'2',amount:'0.10',method:'UPI',status:'SELLER_CONFIRMED',can_select_method:false}],has_more:true});
  open();const summary=await screen.findByRole('region',{name:'Payment summary on this page'});
  expect(within(summary).getByRole('heading',{name:'On this page'})).toBeInTheDocument();
  expect(within(summary).getByText('INR 549.10')).toBeInTheDocument();
  expect(within(summary).getByText('INR 0.10')).toBeInTheDocument();
  expect(within(summary).getByText(/not your full account/)).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Next page'})).toBeEnabled();
});
