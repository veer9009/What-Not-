import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import { DemoProvider } from './state/DemoContext';

function open(path: string) { return render(<MemoryRouter initialEntries={[path]}><DemoProvider><App /></DemoProvider></MemoryRouter>); }

describe('moderation and purchase UI', () => {
  it('removes an inactive product from landing promotions as well as discovery', async () => {
    const user = userEvent.setup();
    open('/seller');
    await user.selectOptions(screen.getByLabelText('Demo shop'), 'Glow Local Co.');
    await user.click(screen.getByRole('button', { name: /deactivate/i }));
    await user.click(screen.getByRole('link', { name: /back to marketplace/i }));
    expect(screen.queryByText('Handmade Candle Set')).not.toBeInTheDocument();
  });
  it('keeps an empty demo shop selectable after its final listing is deleted', async () => {
    const user = userEvent.setup();
    const confirmation = vi.spyOn(window, 'confirm').mockReturnValue(true);
    try {
      open('/seller');
      await user.selectOptions(screen.getByLabelText('Demo shop'), 'Glow Local Co.');
      await user.click(screen.getByRole('button', { name: /delete handmade candle set/i }));
      expect(screen.getByText('Your shop has no products yet')).toBeInTheDocument();
      await user.selectOptions(screen.getByLabelText('Demo shop'), 'Mitti & Thread Studio');
      expect(screen.getByRole('option', { name: 'Glow Local Co.' })).toBeInTheDocument();
      await user.selectOptions(screen.getByLabelText('Demo shop'), 'Glow Local Co.');
      await user.click(screen.getByRole('link', { name: /add new product/i }));
      expect(screen.getByRole('heading', { name: 'Add New Product' })).toBeInTheDocument();
    } finally { confirmation.mockRestore(); }
  });
  it('starts with a blank form when navigating directly from editing to adding', async () => {
    open('/seller/products/teddy/edit');
    expect(screen.getByLabelText('Product Name')).toHaveValue('Handmade Teddy Bear');
    await userEvent.click(screen.getByRole('link', { name: /^add product$/i }));
    expect(screen.getByLabelText('Product Name')).toHaveValue('');
    expect(screen.getByLabelText('Available Quantity')).toHaveValue(null);
  });
  it('previews a locally selected product image', async () => {
    open('/seller/products/new');
    const file = new File(['local image'], 'product.png', { type: 'image/png' });
    await userEvent.upload(screen.getByLabelText('Choose product image'), file);
    await screen.findByAltText('Product preview');
    await vi.waitFor(() => expect(screen.getByAltText('Product preview').getAttribute('src')).toMatch(/^data:image\/png;base64,/));
  });
  it('creates a pending listing, lets the admin approve it, and then shows it to buyers', async () => {
    const user = userEvent.setup();
    open('/seller/products/new');
    await user.type(screen.getByLabelText('Product Name'), 'Local Cotton Scarf');
    await user.type(screen.getByLabelText('Description'), 'Handwoven cotton scarf from our studio.');
    await user.type(screen.getByLabelText('Price (₹)'), '250');
    await user.type(screen.getByLabelText('Available Quantity'), '2');
    await user.click(screen.getByRole('button', { name: /submit for admin approval/i }));
    expect(screen.getByRole('status')).toHaveTextContent(/submitted for admin review/i);
    expect(screen.getByText('Pending', { selector: '.status' })).toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: /back to marketplace/i }));
    await user.click(screen.getByRole('link', { name: /^login$/i }));
    await user.click(screen.getByRole('link', { name: /continue as admin/i }));
    await user.type(screen.getByLabelText(/email/i), 'admin@example.com');
    await user.type(screen.getByLabelText(/password/i), 'demo');
    await user.click(screen.getByRole('button', { name: /enter admin demo/i }));
    const listing = screen.getByText('Local Cotton Scarf').closest('article')!;
    expect(within(listing).getByText('Seller: Mitti & Thread Studio')).toBeInTheDocument();
    await user.click(within(listing).getByRole('button', { name: /approve/i }));
    expect(screen.getByRole('status')).toHaveTextContent(/approved/i);
    await user.click(screen.getByRole('link', { name: /back to marketplace/i }));
    await user.click(screen.getByRole('link', { name: /explore nearby/i }));
    expect(screen.getByText('Local Cotton Scarf')).toBeInTheDocument();
  }, 20000);
  it('requires a rejection reason and shows it to the selected seller before resubmission', async () => {
    const user = userEvent.setup();
    open('/admin');
    expect(screen.getByText(/Lightweight hammered brass/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^reject$/i }));
    await user.click(screen.getByRole('button', { name: /confirm rejection/i }));
    expect(screen.getByText(/enter a rejection reason/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/rejection reason/i), 'Please use a clearer photo');
    await user.click(screen.getByRole('button', { name: /confirm rejection/i }));
    expect(screen.getByRole('status')).toHaveTextContent(/rejected/i);
    await user.click(screen.getByRole('link', { name: /back to marketplace/i }));
    await user.click(screen.getByRole('link', { name: /start selling/i }));
    await user.type(screen.getByLabelText(/email/i), 'seller@example.com');
    await user.type(screen.getByLabelText(/password/i), 'demo');
    await user.click(screen.getByRole('button', { name: /enter seller demo/i }));
    await user.selectOptions(screen.getByLabelText(/demo shop/i), 'Aarika Jewellery');
    expect(screen.getByText('Please use a clearer photo')).toBeInTheDocument();
    expect(screen.queryByText('Handmade Teddy Bear')).not.toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: /edit brass moon earrings/i }));
    expect(screen.getByText('Please use a clearer photo')).toBeInTheDocument();
    const description = screen.getByLabelText('Description');
    await user.clear(description);
    await user.type(description, 'Updated description with clear materials and finish.');
    await user.click(screen.getByRole('button', { name: /save changes/i }));
    expect(screen.getByText('Rejected', { selector: '.status' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /resubmit for review/i }));
    expect(screen.queryByText('Please use a clearer photo')).not.toBeInTheDocument();
    expect(screen.getByText('Pending', { selector: '.status' })).toBeInTheDocument();
  }, 20000);
  it('hides pending listings on direct buyer URLs', () => {
    open('/buyer/products/earrings');
    expect(screen.queryByRole('heading', { name: 'Brass Moon Earrings' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /add to cart/i })).not.toBeInTheDocument();
  });
  it('hides rejected listings on direct buyer URLs', () => {
    open('/buyer/products/basket');
    expect(screen.queryByRole('heading', { name: 'Palm Leaf Basket' })).not.toBeInTheDocument();
  });
  it('blocks editing another demo shop', () => {
    open('/seller/products/candles/edit');
    expect(screen.getByText(/listing was not found/i)).toBeInTheDocument();
  });
  it('lets a seller deactivate and reactivate their listing', async () => {
    open('/seller');
    await userEvent.click(screen.getByRole('button', { name: /deactivate/i }));
    expect(screen.getByText('Inactive', { selector: '.status' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /reactivate/i }));
    expect(screen.queryByText('Inactive', { selector: '.status' })).not.toBeInTheDocument();
  });
  it('creates and displays separate seller orders at checkout', async () => {
    const user = userEvent.setup();
    open('/buyer/products/teddy');
    await user.click(screen.getByRole('button', { name: /add to cart/i }));
    await user.click(screen.getByRole('link', { name: /back to nearby finds/i }));
    const candleCard = screen.getByText('Handmade Candle Set').closest('article')!;
    await user.click(within(candleCard).getByRole('link', { name: /view product/i }));
    await user.click(screen.getByRole('button', { name: /add to cart/i }));
    await user.click(screen.getByRole('link', { name: /view cart/i }));
    expect(screen.getByText(/2 separate seller orders/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /proceed to checkout/i }));
    expect(screen.getByRole('heading', { name: /demo orders placed/i })).toBeInTheDocument();
    expect(screen.getAllByText(/order total/i)).toHaveLength(2);
    expect(screen.queryByRole('button', { name: /proceed to checkout/i })).not.toBeInTheDocument();
  });
});
