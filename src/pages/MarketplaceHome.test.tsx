import { fireEvent,render,screen,waitFor,within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach,expect,it,vi } from 'vitest';
import { MarketplaceHomeContent } from './MarketplaceHome';
import { loadHomeListings } from '../api/homeListings';
import { propertiesApi } from '../api/properties';
const session=vi.hoisted(()=>({user:{id:'1',role:'BUYER',name:'Buyer'},sessionKey:1,loading:false}));
vi.mock('../state/AuthContext',()=>({useAuth:()=>session}));
const setRadius=vi.hoisted(()=>vi.fn());
vi.mock('../state/DiscoveryContext',()=>({useDiscovery:()=>({source:null,radius:3,setRadius})}));
vi.mock('../api/homeListings',()=>({loadHomeListings:vi.fn()}));
vi.mock('../api/properties',()=>({propertiesApi:{saved:vi.fn(),command:vi.fn()}}));
vi.mock('../components/WishlistButton',()=>({WishlistButton:({id,name}:{id:string;name:string})=><button data-id={id}>Save {name}</button>}));
const product={id:'4',kind:'PRODUCT' as const,title:'Real cookies',image:'/cookie.jpg',price:'249.00',pricing:null,rating:null,reviews:null,distance:null,locality:null,href:'/buyer/products/4'};
const property={...product,id:'8',kind:'PROPERTY' as const,title:'Real home',image:null,price:'7800000.00',href:'/buyer/properties/8'};
function open(){return render(<MemoryRouter><MarketplaceHomeContent/></MemoryRouter>);}
afterEach(()=>{vi.resetAllMocks();session.loading=false;session.user={id:'1',role:'BUYER',name:'Buyer'};});
it('waits for session restoration before loading public and owned listing sources',async()=>{
 session.loading=true;vi.mocked(loadHomeListings).mockResolvedValue({items:[product],errors:[]});vi.mocked(propertiesApi.saved).mockResolvedValue([]);
 const view=open();expect(loadHomeListings).not.toHaveBeenCalled();expect(propertiesApi.saved).not.toHaveBeenCalled();
 session.loading=false;view.rerender(<MemoryRouter><MarketplaceHomeContent/></MemoryRouter>);
 expect(await screen.findByRole('heading',{name:'Real cookies'})).toBeInTheDocument();
});
it('renders four short premium cards and genuine metadata without fabricated ratings or distances',async()=>{
 vi.mocked(loadHomeListings).mockResolvedValue({items:[product,property],errors:[]});vi.mocked(propertiesApi.saved).mockResolvedValue([]);open();
 const categories=screen.getByRole('region',{name:'Explore What Not?'});
 expect(within(categories).getAllByRole('img')).toHaveLength(4);
 for(const label of ['Homemade','Creative','Professional','Real Estate'])expect(within(categories).getByRole('heading',{name:label})).toBeInTheDocument();
 expect(await screen.findByRole('heading',{name:'Real cookies'})).toBeInTheDocument();
 expect(screen.getByRole('img',{name:'Real cookies'})).toHaveAttribute('src','/cookie.jpg');
 expect(screen.queryByText(/4\.8|0\.8 km/)).not.toBeInTheDocument();
 expect(screen.getByRole('link',{name:'View All'})).toHaveAttribute('href',expect.stringContaining('all=1'));
});
it('submits unified search and independently opens functional filters',async()=>{
 vi.mocked(loadHomeListings).mockResolvedValue({items:[product,property],errors:[]});vi.mocked(propertiesApi.saved).mockResolvedValue([]);open();
 await screen.findByRole('heading',{name:'Real cookies'});
 fireEvent.change(screen.getByRole('searchbox',{name:'Search products, services and properties'}),{target:{value:'cookies'}});
 fireEvent.submit(screen.getByRole('search',{name:'Search the marketplace'}));
 await waitFor(()=>expect(loadHomeListings).toHaveBeenLastCalledWith(expect.objectContaining({query:'cookies'}),expect.any(Map)));
 fireEvent.click(screen.getByRole('button',{name:'Filters'}));
 fireEvent.change(screen.getByLabelText('Listing type'),{target:{value:'PROPERTY'}});
 await waitFor(()=>expect(screen.queryByRole('heading',{name:'Real cookies'})).not.toBeInTheDocument());
 expect(screen.getByRole('heading',{name:'Real home'})).toBeInTheDocument();
});
it('uses the owned property save API and reflects persistence after refresh',async()=>{
 vi.mocked(loadHomeListings).mockResolvedValue({items:[property],errors:[]});vi.mocked(propertiesApi.saved).mockResolvedValueOnce([]).mockResolvedValue([({id:'8'} as any)]);vi.mocked(propertiesApi.command).mockResolvedValue({});open();
 fireEvent.click(await screen.findByRole('button',{name:'Save Real home'}));
 await waitFor(()=>expect(propertiesApi.command).toHaveBeenCalledWith('8','save',{saved:true}));
 expect(await screen.findByRole('button',{name:'Unsave Real home'})).toHaveAttribute('aria-pressed','true');
});
it('shows partial-source errors, supports retry and has an honest empty state',async()=>{
 vi.mocked(loadHomeListings).mockResolvedValue({items:[],errors:['Creative Services could not be loaded.']});vi.mocked(propertiesApi.saved).mockResolvedValue([]);open();
 expect(screen.getByRole('status')).toHaveTextContent(/Loading/);
 expect(await screen.findByText('Creative Services could not be loaded.')).toBeInTheDocument();
 expect(screen.getByRole('heading',{name:'No matching picks yet'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Refresh picks'}));await waitFor(()=>expect(loadHomeListings).toHaveBeenCalledTimes(2));
});
it('does not read owned property saves or expose buyer save actions to a seller',async()=>{
 session.user={id:'2',role:'SELLER',name:'Seller'};vi.mocked(loadHomeListings).mockResolvedValue({items:[product,property],errors:[]});open();
 await screen.findByRole('heading',{name:'Real home'});expect(propertiesApi.saved).not.toHaveBeenCalled();
 expect(screen.queryByRole('button',{name:'Save Real home'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Save Real cookies'})).not.toBeInTheDocument();
});
it('uses Discover Picks and overlays source badges on real images and placeholders beside save actions',async()=>{
 vi.mocked(loadHomeListings).mockResolvedValue({items:[product,property],errors:[]});vi.mocked(propertiesApi.saved).mockResolvedValue([]);open();
 expect(await screen.findByRole('heading',{name:'Discover Picks'})).toBeInTheDocument();
 const cards=screen.getAllByRole('listitem');
 expect(cards[0].querySelector('.home-pick-image .listing-category-badge')).toHaveTextContent('Homemade');
 expect(cards[1].querySelector('.home-pick-image .listing-category-badge')).toHaveTextContent('Real Estate');
 expect(within(cards[1]).getByRole('img',{name:'Real home: image unavailable'})).toBeInTheDocument();
 expect(within(cards[1]).getByRole('button',{name:'Save Real home'})).toBeInTheDocument();
});
it('requests the next bounded page from View All and resets page when searching',async()=>{
 vi.mocked(loadHomeListings).mockResolvedValue({items:[product],errors:[],hasNext:true});vi.mocked(propertiesApi.saved).mockResolvedValue([]);open();
 fireEvent.click(await screen.findByRole('link',{name:'View All'}));
 fireEvent.click(await screen.findByRole('button',{name:'Next discoveries'}));
 await waitFor(()=>expect(loadHomeListings).toHaveBeenLastCalledWith(expect.objectContaining({page:1}),expect.any(Map)));
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'cookies'}});fireEvent.submit(screen.getByRole('search',{name:'Search the marketplace'}));
 await waitFor(()=>expect(loadHomeListings).toHaveBeenLastCalledWith(expect.objectContaining({page:0,query:'cookies'}),expect.any(Map)));
});
it('returns to the first eligible product page when narrowing the Homemade radius',async()=>{
 vi.mocked(loadHomeListings).mockResolvedValue({items:[product],errors:[]});vi.mocked(propertiesApi.saved).mockResolvedValue([]);
 render(<MemoryRouter initialEntries={['/?all=1&kind=PRODUCT&page=1']}><MarketplaceHomeContent/></MemoryRouter>);
 await screen.findByRole('heading',{name:'Real cookies'});fireEvent.click(screen.getByRole('button',{name:'Filters'}));
 fireEvent.click(within(screen.getByRole('group',{name:'Homemade radius'})).getByRole('button',{name:'1 KM'}));
 expect(setRadius).toHaveBeenCalledWith(1);
 await waitFor(()=>expect(loadHomeListings).toHaveBeenLastCalledWith(expect.objectContaining({page:0}),expect.any(Map)));
});
