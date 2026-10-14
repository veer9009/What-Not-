import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { setAccessToken } from './api/client';

function open(path = '/', role?: 'BUYER' | 'SELLER') {
  if (role) setAccessToken('scope-test');
  const fetcher = vi.fn(async (input: string) => {
    const path = new URL(input).pathname;
    const body = path.endsWith('/auth/me')
      ? { id: 1, name: 'Ravi', email: 'ravi@example.test', role }
      : path.endsWith('/sellers/me') ? { id: 2, shop_name: 'Ravi Studio' } : [];
    return new Response(JSON.stringify(body), { status: 200 });
  });
  vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
  return fetcher;
}

afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });

describe('What Not? business scope', () => {
  it.each(['/', '/buyer'])('presents the three verticals and exact descriptions at %s', async path => {
    open(path, path === '/buyer' ? 'BUYER' : undefined);
    const explore = await screen.findByRole('region', { name: 'Explore What Not?' });
    for (const [name, description] of [
      ['Homemade', 'Discover homemade food, handmade products and local creations.'],
      ['Real Estate', 'Discover local properties available for rent or sale.'],
      ['Creative Services', 'Find video editors, VFX artists and creative professionals.'],
    ]) {
      expect(within(explore).getByRole('heading', { name })).toBeInTheDocument();
      expect(within(explore).getByText(description)).toBeInTheDocument();
    }
    expect(within(explore).getByRole('link', { name: 'Explore Homemade samples' })).toHaveAttribute('href', '/buyer#homemade-catalogue');
  });

  it('keeps property and creative previews separate from product commerce', () => {
    const fetcher = open();
    const property = screen.getByRole('article', { name: 'Real Estate' });
    const creative = screen.getByRole('article', { name: 'Creative Services' });
    expect(within(property).getByText('Coming soon')).toBeInTheDocument();
    expect(within(creative).getByText('Coming soon')).toBeInTheDocument();
    expect(within(property).getByText('Example rental property')).toBeInTheDocument();
    expect(within(property).getByText('Example sale property')).toBeInTheDocument();
    for (const name of ['Video editing', 'Travel video editing', 'Influencer reel editing', 'VFX service']) {
      expect(within(creative).getByText(name)).toBeInTheDocument();
    }
    for (const card of [property, creative]) {
      expect(within(card).getByText(/Illustrative examples only/)).toBeInTheDocument();
      expect(within(card).queryByRole('link')).not.toBeInTheDocument();
      within(card).getAllByRole('button').forEach(button => expect(button).toBeDisabled());
    }
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('exposes all verticals through the collapsible public navigation', async () => {
    open();
    const toggle = screen.getByRole('button', { name: 'Toggle navigation' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    for (const [name, id] of [['Homemade', 'homemade'], ['Real Estate', 'real-estate'], ['Creative Services', 'creative-services']]) {
      expect(within(nav).getByRole('link', { name })).toHaveAttribute('href', `/#${id}`);
    }
    await userEvent.click(within(nav).getByRole('link', { name: 'Creative Services' }));
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('labels sample products individually and removes fabricated live trust claims', () => {
    open();
    expect(screen.queryByText('Verified local sellers')).not.toBeInTheDocument();
    expect(screen.queryByText('2,400+ neighbours')).not.toBeInTheDocument();
    const products = document.querySelectorAll('.product-card');
    expect(products.length).toBeGreaterThan(0);
    products.forEach(card => expect(within(card as HTMLElement).getByText('Sample')).toBeInTheDocument());
  });

  it('scrolls to the Homemade catalogue when its buyer card is selected', async () => {
    open('/buyer', 'BUYER');
    const catalogue = await screen.findByRole('region', { name: 'Homemade samples' });
    const scroll = vi.fn();
    catalogue.scrollIntoView = scroll;
    await userEvent.click(screen.getByRole('link', { name: 'Explore Homemade samples' }));
    expect(scroll).toHaveBeenCalledWith({ block: 'start' });
  });

  it('offers food and crafts samples without property/service products or backend discovery', async () => {
    const fetcher = open('/buyer', 'BUYER');
    await screen.findByRole('heading', { name: 'Homemade samples' });
    await userEvent.click(screen.getByRole('button', { name: 'Homemade Food' }));
    expect(screen.getByRole('heading', { name: 'Homemade Laddus' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Handmade Candle Set' })).not.toBeInTheDocument();
    expect(document.querySelectorAll('.product-card')).toHaveLength(1);
    await userEvent.click(screen.getByRole('link', { name: /View product/ }));
    expect(screen.getByRole('button', { name: 'Contact unavailable for samples' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: /Add to Cart/ }));
    await userEvent.click(screen.getByRole('link', { name: /View cart/ }));
    expect(screen.getByRole('button', { name: 'Checkout unavailable' })).toBeDisabled();
    expect(screen.getByText(/Sample catalogue.*geography/)).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledOnce();
    expect(String(fetcher.mock.calls[0][0])).toMatch(/\/auth\/me$/);
  });

  it('keeps seller creation within the existing product API categories', async () => {
    open('/seller/products/new', 'SELLER');
    await screen.findByLabelText('Product Name');
    expect(screen.getByText(/Real Estate and Creative Services listing tools are coming soon/)).toBeInTheDocument();
    const categories = screen.getByRole('combobox');
    expect(within(categories).getAllByRole('option').map(option => (option as HTMLOptionElement).value))
      .toEqual(['Handmade', 'Home Decor', 'Gifts', 'Fashion', 'Jewellery', 'Crafts']);
    expect(within(categories).queryByRole('option', { name: 'Homemade Food' })).not.toBeInTheDocument();
    expect(within(categories).queryByRole('option', { name: 'Real Estate' })).not.toBeInTheDocument();
    expect(within(categories).queryByRole('option', { name: 'Creative Services' })).not.toBeInTheDocument();
  });
});
