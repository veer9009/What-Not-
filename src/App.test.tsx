import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import App from './App';
import { DemoProvider } from './state/DemoContext';

function open(path:string){return render(<MemoryRouter initialEntries={[path]}><DemoProvider><App/></DemoProvider></MemoryRouter>)}

describe('marketplace demo routes',()=>{
  it('renders the required landing story and role entry points',()=>{
    open('/');
    expect(screen.getByRole('heading',{name:/Discover What's\s*Made\s*Around You/i})).toBeInTheDocument();
    expect(screen.getByRole('link',{name:/start selling/i})).toHaveAttribute('href','/login/seller');
  });
  it('validates blank buyer login before navigation',async()=>{
    open('/login/buyer');
    await userEvent.click(screen.getByRole('button',{name:/enter buyer demo/i}));
    expect(screen.getByText(/enter any sample email/i)).toBeInTheDocument();
  });
  it('filters buyer products by a one kilometre radius',async()=>{
    open('/buyer');
    await userEvent.click(screen.getByRole('button',{name:'1 KM'}));
    expect(screen.getByText('Handmade Candle Set')).toBeInTheDocument();
    expect(screen.queryByText('Decorative Clay Pot')).not.toBeInTheDocument();
  });
  it('keeps the exact WhatsApp help destination available',()=>{
    open('/admin');
    expect(screen.getByRole('link',{name:/chat with us on whatsapp/i})).toHaveAttribute('href','https://wa.me/918080098882?text=Hi%2C%20I%20would%20like%20to%20know%20more%20about%20your%20local%20marketplace.');
  });
});
