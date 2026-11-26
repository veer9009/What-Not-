import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { WishlistProvider } from '../state/WishlistContext';
import { WishlistPage } from './WishlistPage';
import { WishlistButton } from '../components/WishlistButton';
const mocks=vi.hoisted(()=>({list:vi.fn(),save:vi.fn(),dispatch:vi.fn(),auth:{user:{id:'1',role:'BUYER'},sessionKey:1}}));
vi.mock('../api/wishlist',()=>({wishlistApi:{list:mocks.list,set:mocks.save}}));
vi.mock('../state/AuthContext',()=>({useAuth:()=>mocks.auth}));
vi.mock('../state/DemoContext',()=>({useDemo:()=>({state:{cart:[],placements:[]},dispatch:mocks.dispatch})}));
vi.mock('../components/Shared',()=>({DashboardShell:({children}:{children:React.ReactNode})=><div>{children}</div>,PageTop:({title}:{title:string})=><h1>{title}</h1>,EmptyState:({title}:{title:string})=><h2>{title}</h2>}));
const product={id:'9007199254740993',seller_id:'2',name:'Clay cup',description:'Cup',price:'99.50',stock_quantity:3,category:'HOME',delivery_radius_km:3,image_url:null,shop_name:'Local potter',is_verified:false};
function view(){return <MemoryRouter><WishlistProvider><WishlistPage/></WishlistProvider></MemoryRouter>}
beforeEach(()=>{vi.clearAllMocks();mocks.auth.user.id='1';mocks.auth.sessionKey=1;mocks.save.mockResolvedValue({saved:false});});
it('shows current products, adds to cart without placing an order, and removes a saved ID',async()=>{
 mocks.list.mockResolvedValue({items:[{product_id:product.id,available:true,product}],count:1});render(view());
 expect(await screen.findByText('Clay cup')).toBeInTheDocument();expect(screen.getByText('Local potter')).toBeInTheDocument();expect(screen.getByText('\u20b999.50')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Add Clay cup to cart'}));expect(mocks.dispatch).toHaveBeenCalledWith({type:'cart/add-discovered',product});
 mocks.list.mockResolvedValue({items:[],count:0});fireEvent.click(screen.getByRole('button',{name:'Remove Clay cup from Wishlist'}));await waitFor(()=>expect(mocks.save).toHaveBeenCalledWith(product.id,false));expect(await screen.findByText('Your Wishlist is empty')).toBeInTheDocument();
});
it('does not expose unavailable metadata and permits removing the opaque ID',async()=>{
 mocks.list.mockResolvedValue({items:[{product_id:'7',available:false,product:{...product,name:'Restricted secret'}}],count:1});render(view());
 expect(await screen.findByText('Product unavailable')).toBeInTheDocument();expect(screen.queryByText('Restricted secret')).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:/Add .* to cart/})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Remove unavailable product from Wishlist'}));await waitFor(()=>expect(mocks.save).toHaveBeenCalledWith('7',false));
});
it('discards an earlier account response after session changes',async()=>{
 let finish!:(value:unknown)=>void;mocks.list.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve})).mockResolvedValue({items:[],count:0});const rendered=render(view());
 mocks.auth.user.id='2';mocks.auth.sessionKey=2;rendered.rerender(view());expect(await screen.findByText('Your Wishlist is empty')).toBeInTheDocument();
 finish({items:[{product_id:product.id,available:true,product}],count:1});await waitFor(()=>expect(screen.queryByText('Clay cup')).not.toBeInTheDocument());
});
it('shares saved state between heart controls and suppresses repeat writes while pending',async()=>{
 mocks.list.mockResolvedValue({items:[],count:0});let finish!:(value:unknown)=>void;mocks.save.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
 render(<MemoryRouter><WishlistProvider><WishlistButton id={product.id} name="Clay cup"/><WishlistButton id={product.id} name="Clay cup"/></WishlistProvider></MemoryRouter>);
 const buttons=await screen.findAllByRole('button',{name:'Save Clay cup to Wishlist'});await waitFor(()=>expect(buttons[0]).toBeEnabled());expect(mocks.list).toHaveBeenCalledTimes(1);fireEvent.click(buttons[0]);fireEvent.click(buttons[1]);expect(mocks.save).toHaveBeenCalledTimes(1);expect(mocks.save).toHaveBeenCalledWith(product.id,true);
 mocks.list.mockResolvedValue({items:[{product_id:product.id,available:true,product}],count:1});finish({saved:true});await waitFor(()=>expect(screen.getAllByRole('button',{name:'Remove Clay cup from Wishlist'})).toHaveLength(2));
});
it('disables adding an out of stock saved product',async()=>{
 mocks.list.mockResolvedValue({items:[{product_id:product.id,available:true,product:{...product,stock_quantity:0}}],count:1});render(view());expect(await screen.findByText('Out of stock')).toBeInTheDocument();expect(screen.getByRole('button',{name:'Add Clay cup to cart'})).toBeDisabled();
});
