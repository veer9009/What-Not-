// Offline layout evidence: render real components using synthetic API responses.
import { writeFileSync } from 'node:fs';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { PropertyManagePage } from '../src/pages/PropertyPages';
import { propertiesApi } from '../src/api/properties';
vi.mock('../src/state/AuthContext',()=>({useAuth:()=>({user:{role:'SELLER',name:'QA seller'}})}));
afterEach(()=>vi.restoreAllMocks());
it('exports actual property forms for offline Chrome geometry checks',async()=>{
  vi.spyOn(propertiesApi,'mine').mockResolvedValue([]);
  vi.spyOn(propertiesApi,'profile').mockResolvedValue({display_name:'QA owner',capacity:'OWNER',share_contact:false});
  render(<MemoryRouter><PropertyManagePage/></MemoryRouter>);
  await screen.findByRole('form',{name:'Create sale listing'});
  await waitFor(()=>expect(screen.getByLabelText('Public display name')).toHaveValue('QA owner'));
  writeFileSync('docs/security/evidence/property-layout-fixture.html',document.body.innerHTML);
});
