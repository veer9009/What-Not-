import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { setAccessToken } from './api/client';

function open(path = '/', role?: 'BUYER' | 'SELLER') {
  if (role) setAccessToken('scope-test');
  const fetcher = vi.fn(async (input: string) => {
    const path = new URL(input, location.origin).pathname;
    const body = path.endsWith('/auth/me')
      ? { id: 1, name: 'Ravi', email: 'ravi@example.test', role }
      : path.endsWith('/sellers/me') ? { id: 2, shop_name: 'Ravi Studio' } : path.endsWith('/wishlist') ? {items:[],count:0} : path.endsWith('/notifications/unread-count') ? {count:0} : [];
    return new Response(JSON.stringify(body), { status: 200 });
  });
  vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
  return fetcher;
}

afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });

describe('What Not? business scope', () => {
  it.each(['/', '/buyer'])('presents four separate verticals and concise descriptions at %s', async path => {
    open(path, path === '/buyer' ? 'BUYER' : undefined);
    const explore = await screen.findByRole('region', { name: path==='/'?'Explore What Not?':'Explore Nearby' });
    for (const [name, description] of [
      ['Homemade', 'Homemade food, handmade products and crafts.'],
      ['Real Estate', 'Local properties for sale.'],
      ['Creative Services', 'Video editing, VFX and creative services.'],
      ['Professional Services', 'Software, cloud and technical expertise.'],
    ]) {
      const shortName=path==='/'?({ 'Creative Services':'Creative','Professional Services':'Professional'}[name]??name):name;
      expect(within(explore).getByRole('heading', { name: shortName })).toBeInTheDocument();
      expect(within(explore).getByText(description)).toBeInTheDocument();
    }
    expect(within(explore).getByRole('link', { name: 'Explore nearby Homemade' })).toHaveAttribute('href', path === '/buyer' ? '/buyer#homemade-catalogue' : '/buyer');
  });

  it('links sale properties and creative work separately from product commerce', async () => {
    const fetcher = open();
    const property = await screen.findByRole('article', { name: 'Real Estate' });
    const creative = screen.getByRole('article', { name: 'Creative Services' });
    expect(screen.getByText(/Controlled beta\. Homemade/)).toBeInTheDocument();
    expect(within(property).queryByText(/rental/i)).not.toBeInTheDocument();
    expect(within(property).getByRole('link')).toHaveAttribute('href','/buyer/properties');
    expect(within(creative).getByRole('link')).toHaveAttribute('href','/creative-services');
    expect(screen.getByText(/legal documents are not verified/)).toBeInTheDocument();
    expect(screen.getByText(/no payment or escrow/)).toBeInTheDocument();
    expect(fetcher.mock.calls.every(([url])=>/\/(auth\/refresh|creative\/listings\?|properties\?)/.test(String(url)))).toBe(true);
  });

  it('exposes all verticals through permanent accessible public navigation', async () => {
    open();
    expect(screen.queryByRole('button', { name: 'Toggle navigation' })).not.toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    for (const [name, id] of [['Marketplace', 'homemade'], ['Property', 'real-estate'], ['Creative Services', 'creative-services']]) {
      expect(within(nav).getByRole('link', { name })).toHaveAttribute('href', `/#${id}`);
    }
    await userEvent.click(within(nav).getByRole('link', { name: 'Creative Services' }));
    expect(within(nav).getByRole('link',{name:'Creative Services'})).toHaveAttribute('aria-current','location');
    expect(document.getElementById('creative-services')).toHaveFocus();
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
    const catalogue = await screen.findByRole('region', { name: 'Nearby Homemade products' });
    const scroll = vi.fn();
    catalogue.scrollIntoView = scroll;
    await userEvent.click(screen.getByRole('link', { name: 'Explore nearby Homemade' }));
    expect(scroll).toHaveBeenCalledWith({ block: 'start' });
  });

  it('offers food and crafts samples without property/service products or backend discovery', async () => {
    const fetcher = open('/buyer/samples', 'BUYER');
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
    expect(fetcher.mock.calls.filter(([url])=>String(url).endsWith('/auth/me'))).toHaveLength(1);
    expect(fetcher.mock.calls.every(([url])=>/\/(auth\/me|notifications\/unread-count|wishlist)$/.test(String(url)))).toBe(true);
    expect(String(fetcher.mock.calls[0][0])).toMatch(/\/auth\/me$/);
  });

  it('keeps seller creation within the existing product API categories', async () => {
    open('/seller/products/new', 'SELLER');
    await screen.findByLabelText('Product Name');
    expect(screen.getByText(/Use the property and Creative Services workspaces/)).toBeInTheDocument();
    const categories = screen.getByRole('combobox');
    expect(within(categories).getAllByRole('option').map(option => (option as HTMLOptionElement).value))
      .toEqual(['Handmade', 'Home Decor', 'Gifts', 'Fashion', 'Jewellery', 'Crafts']);
    expect(within(categories).queryByRole('option', { name: 'Homemade Food' })).not.toBeInTheDocument();
    expect(within(categories).queryByRole('option', { name: 'Real Estate' })).not.toBeInTheDocument();
    expect(within(categories).queryByRole('option', { name: 'Creative Services' })).not.toBeInTheDocument();
  });
});
