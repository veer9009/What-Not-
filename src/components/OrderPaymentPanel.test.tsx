import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { ApprovedUPIInstructions, OrderPaymentPanel, OrderReceipt } from './OrderPaymentPanel';
import { paymentsApi } from '../api/payments';
vi.mock('../api/payments',()=>({paymentsApi:{get:vi.fn(),instructions:vi.fn(),report:vi.fn(),confirm:vi.fn()}}));
const payment={order_id:'1',seller_id:'2',seller_name:'Fixture seller',amount:'250.00',currency:'INR' as const,order_status:'PLACED',order_date:'2026-11-25T00:00:00Z',method:'COD' as const,status:'PENDING' as const,reference:null,reported_at:null,confirmed_at:null,can_select_method:false,can_report:false,can_confirm:false};
afterEach(()=>vi.clearAllMocks());
it('does not copy a destination revoked since instructions were loaded',async()=>{
 const write=vi.fn();Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:write}});
 vi.mocked(paymentsApi.instructions).mockResolvedValueOnce({available:true,reason:null,upi_id:'isolated@upi',account_holder_name:'Isolated test seller',amount:'250.00',currency:'INR',upi_uri:'upi://pay?pa=isolated%40upi&pn=Isolated+test+seller&am=250.00&cu=INR',verification_label:'Admin reviewed; not bank verified'}).mockResolvedValue({available:false,reason:'Destination approval revoked.',upi_id:null,account_holder_name:null,amount:'250.00',currency:'INR',upi_uri:null,verification_label:null});
 render(<ApprovedUPIInstructions orderId="1" amount="250.00"/>);
 fireEvent.click(await screen.findByRole('button',{name:'Copy UPI ID'}));
 await waitFor(()=>expect(vi.mocked(paymentsApi.instructions).mock.calls.length).toBeGreaterThanOrEqual(2));
 expect(write).not.toHaveBeenCalled();
 expect(await screen.findByText('Destination approval revoked.')).toBeInTheDocument();
});
it('removes an approved destination when focus revalidation reports revocation',async()=>{
  vi.mocked(paymentsApi.instructions).mockResolvedValueOnce({available:true,reason:null,upi_id:'isolated@upi',account_holder_name:'Isolated test seller',amount:'250.00',currency:'INR',upi_uri:'upi://pay?pa=isolated%40upi&pn=Isolated+test+seller&am=250.00&cu=INR',verification_label:'Admin reviewed; not bank verified'}).mockResolvedValue({available:false,reason:'Destination approval revoked.',upi_id:null,account_holder_name:null,amount:'250.00',currency:'INR',upi_uri:null,verification_label:null});
  render(<ApprovedUPIInstructions orderId="1" amount="250.00"/>);
  await screen.findByRole('img',{name:'Seller payment QR code'});
  fireEvent(window,new Event('focus'));
  expect(await screen.findByText('Destination approval revoked.')).toBeInTheDocument();
  expect(screen.queryByRole('img',{name:'Seller payment QR code'})).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Open UPI app'})).not.toBeInTheDocument();
});
it('shows exact COD payable separately from delivery and never claims an unpaid receipt proves payment',async()=>{
  vi.mocked(paymentsApi.get).mockResolvedValue(payment);
  render(<MemoryRouter><OrderPaymentPanel orderId="1" role="buyer"/></MemoryRouter>);
  expect(await screen.findByText('INR 250.00 payable on delivery')).toBeInTheDocument();
  expect(screen.getByText(/Payment remains pending until the seller confirms actual receipt/)).toBeInTheDocument();
  expect(paymentsApi.instructions).not.toHaveBeenCalled();
  expect(screen.queryByRole('img',{name:/QR/})).not.toBeInTheDocument();
});
it('never generates a QR or exposes a destination when prepaid UPI is disabled',async()=>{
  vi.mocked(paymentsApi.get).mockResolvedValue({...payment,method:'UPI'});
  vi.mocked(paymentsApi.instructions).mockResolvedValue({available:false,reason:'Prepaid UPI disabled pending business approval.',upi_id:null,account_holder_name:null,amount:'250.00',currency:'INR',upi_uri:null,verification_label:null});
  render(<MemoryRouter><OrderPaymentPanel orderId="1" role="buyer"/></MemoryRouter>);
  expect(await screen.findByText('Prepaid UPI disabled pending business approval.')).toBeInTheDocument();
  expect(screen.queryByRole('img',{name:/QR/})).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Open UPI app'})).not.toBeInTheDocument();
});
it('renders a local QR for an approved exact-amount URI, and reports only after explicit buyer attestation',async()=>{
  vi.mocked(paymentsApi.get).mockResolvedValue({...payment,method:'UPI',can_report:true});
  vi.mocked(paymentsApi.instructions).mockResolvedValue({available:true,reason:null,upi_id:'isolated@upi',account_holder_name:'Isolated test seller',amount:'250.00',currency:'INR',upi_uri:'upi://pay?pa=isolated%40upi&pn=Isolated+test+seller&am=250.00&cu=INR',verification_label:'Admin reviewed; not bank verified'});
  vi.mocked(paymentsApi.report).mockResolvedValue({...payment,method:'UPI',status:'BUYER_REPORTED'});
  render(<MemoryRouter><OrderPaymentPanel orderId="1" role="buyer"/></MemoryRouter>);
  await screen.findByRole('img',{name:'Seller payment QR code'});
  expect(screen.getByRole('button',{name:'Open UPI app'})).not.toHaveAttribute('href');
  expect(screen.getByRole('button',{name:'I Have Paid'})).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox',{name:'I sent this payment directly to the seller'}));
  fireEvent.click(screen.getByRole('button',{name:'I Have Paid'}));
  await waitFor(()=>expect(paymentsApi.report).toHaveBeenCalledWith('1',null));
});
it('labels the order receipt and preserves independent payment status on cancelled orders',()=>{
  const order={id:'1',buyer_id:'3',seller_id:'2',status:'CANCELLED' as const,subtotal:'250.00',delivery_fee:'0.00',total:'250.00',items:[{product_id:'4',seller_id:'2',name:'Fixture item',quantity:1,unit_price:'250.00'}]};
  render(<OrderReceipt order={order} payment={payment}/>);
  expect(screen.getByRole('heading',{name:'Order receipt'})).toBeInTheDocument();
  expect(screen.getByText('Not proof of payment. This is not a tax invoice.')).toBeInTheDocument();
  expect(screen.getByText(/Cancellation does not confirm a refund/)).toBeInTheDocument();
  expect(screen.getByText('Fixture seller')).toBeInTheDocument();
});
