import { Link } from 'react-router-dom';
import { PublicHeader,ProductCard } from '../components/Shared';
import { DemoNotice } from '../components/ApiStates';
import { useDemo } from '../state/DemoContext';
import { useAuth } from '../state/AuthContext';
import { isBuyerEligible } from '../utils/products';
import { MarketplaceHomeContent } from './MarketplaceHome';

export function LandingPage(){
 const {state}=useDemo();const {user}=useAuth();
 const samples=state.products.filter(product=>isBuyerEligible(product)&&product.category!=='Homemade Food').slice(0,4);
 return <div className="site marketplace-home"><PublicHeader compact/><main id="main-content" tabIndex={-1}><MarketplaceHomeContent/>
  <details className="home-secondary"><summary>About these listings</summary><div className="home-about"><p>Controlled beta. Homemade delivery is seller-managed and checked at checkout. Prepaid UPI remains disabled pending approval.</p><p>Sale listings, enquiries and appointment requests. Ownership and legal documents are not verified by this app.</p><p>Creative and Professional Services have separate catalogues. Request a private quote; no payment or escrow is collected.</p><DemoNotice/></div></details>
  {(!user||user.role==='BUYER')&&<details className="home-secondary"><summary>Preview the sample catalogue</summary><section aria-label="Sample catalogue preview"><h2>Homemade samples</h2><p>Illustrative samples — not live inventory.</p><Link to="/buyer/samples">Open sample catalogue</Link><div className="product-grid">{samples.map(product=><ProductCard key={product.id} product={product}/>)}</div></section></details>}
  {(!user||user.role==='SELLER')&&<details className="home-secondary"><summary>For local makers</summary><p>Submit products and services through your existing seller workspace for review.</p><Link to={user?'/seller':'/login/seller'}>{user?'Open Seller Studio':'Seller sign in'}</Link></details>}
 </main></div>;
}
