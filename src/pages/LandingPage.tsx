import { ArrowRight, HeartHandshake, PackageOpen, Search, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ProductCard, PublicHeader, RadiusVisual } from '../components/Shared';
import { DemoNotice } from '../components/ApiStates';
import { ExploreVerticals } from '../components/ExploreVerticals';
import { products } from '../data/mockData';
import { useDemo } from '../state/DemoContext';
import { isBuyerEligible } from '../utils/products';

export function LandingPage() {
  const { state } = useDemo();
  const featured = state.products.filter(isBuyerEligible).slice(0,4);
  const mainFeature = featured.find(p => p.id === 'clay-pot') ?? featured[0];
  const popularFeature = featured.find(p => p.id === 'candles') ?? featured[1] ?? featured[0];
  return <div className="site"><PublicHeader/><main><DemoNotice/>
    <section className="hero" id="home"><div className="hero-copy"><p className="kicker"><Sparkles size={16}/> Homemade. Real Estate. Creative Services.</p><h1>Local life.<br/><em>More possibilities.</em></h1><p className="hero-sub">Homemade food and crafts. A place to call home. Creative talent for your next story. Discover the three sides of What Not?</p><div className="hero-actions"><a className="btn btn-primary" href="#explore">Explore What Not? <ArrowRight size={18}/></a><Link className="btn btn-outline" to="/login/seller">Seller sign in</Link></div><p className="hero-scope">Explore Homemade samples today. Real Estate and Creative Services are coming soon.</p></div>
    <div className="hero-collage"><div className="collage-main"><img src={mainFeature?.image ?? products[1].image} alt={mainFeature?.name ?? 'Handcrafted clay pottery'}/><span className="photo-caption">Homemade sample<small>{mainFeature?.seller ?? 'Meet your local makers'}</small></span></div><div className="collage-small"><img src={popularFeature?.image ?? products[2].image} alt={popularFeature?.name ?? 'Handcrafted goods'}/></div><div className="floating-product"><span>Sample creation</span><strong>{popularFeature?.name ?? 'Meet your local makers'}</strong><b>{popularFeature ? `₹${popularFeature.price.toLocaleString('en-IN')}` : 'Explore samples'}</b></div></div></section>
    <ExploreVerticals/>
    <section className="trust-strip"><span>Homemade food & crafts</span><i>✦</i><span>Rent & sale · coming soon</span><i>✦</i><span>Creative talent · coming soon</span></section>
    <section className="section" id="featured"><div className="section-heading"><div><p className="eyebrow">Homemade · sample catalogue</p><h2>Small batches. Thoughtful creations.</h2></div><Link className="text-link" to="/buyer">Explore Homemade samples <ArrowRight size={16}/></Link></div><div className="product-grid">{featured.map(p=><ProductCard key={p.id} product={p}/>)}</div></section>
    <section className="how-section" id="how"><div className="section-heading centered"><div><p className="eyebrow">What you can do today</p><h2>Get to know What Not?</h2><p>Real account tools. An honest preview of what's ahead.</p></div></div><div className="steps">{[[PackageOpen,'01','Manage your products','Sellers can create a shop profile and submit products for admin review.'],[Search,'02','Explore Homemade samples','Preview food and handmade creations. Discovery and the basket use sample data.'],[Sparkles,'03','See what is coming','Property listings and creative service requests are planned; examples are illustrative.'],[HeartHandshake,'04','Manage existing orders','Signed-in buyers and sellers can view their own order history. Checkout is unavailable.']].map(([Icon,n,t,d])=><article className="step" key={String(t)}><span>{String(n)}</span><i><Icon/></i><h3>{String(t)}</h3><p>{String(d)}</p></article>)}</div></section>
    <section className="radius-story"><div><p className="eyebrow light">Sample distance preview</p><h2>Local discovery.<br/>Coming soon.</h2><p>Makers can save their intended selling radius. Real distance filtering and eligibility are not available yet; this Homemade catalogue uses sample distances.</p><div className="radius-flow"><b>SAMPLE SELLER</b><span>→</span><b>1 / 2 / 3 KM</b><span>→</span><b>SAMPLE BUYERS</b></div><Link className="btn btn-light" to="/buyer">Explore sample discoveries</Link></div><RadiusVisual/></section>
    <section className="seller-cta"><div><p className="eyebrow">For homemade makers</p><h2>Your craft deserves<br/>a local audience.</h2><p>Create your seller profile and submit handmade products for review. Live buyer discovery is coming soon.</p><Link className="btn btn-primary" to="/login/seller">Become a seller <ArrowRight size={18}/></Link></div><img src={products[1].image} alt="Sample handcrafted clay pottery"/></section>
  </main><footer><LogoFooter/><p>Homemade. Real Estate. Creative Services.</p><small>© 2026 What Not?. Sample catalogue with authenticated account workflows.</small></footer></div>;
}
function LogoFooter(){return <div className="footer-logo">N <span>What Not?</span></div>}
