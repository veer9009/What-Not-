import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {expect,it,vi} from 'vitest';
import {PublicSidebar} from './Shared';
vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:null})}));
it.each([['/creative-services','Creative Services'],['/professional-services','Professional Services']])('highlights the public service domain at %s',(path,label)=>{
 render(<MemoryRouter initialEntries={[path]}><PublicSidebar/></MemoryRouter>);
 expect(screen.getByRole('link',{name:label})).toHaveAttribute('aria-current','page');
});
