import { ArrowRight, Film, HeartHandshake, House, PackageOpen, Search, Sparkles, Store } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ProductCard, PublicHeader, RadiusVisual } from '../components/Shared';
import { DemoNotice } from '../components/ApiStates';
import neighborhood480 from '../assets/homepage/neighborhood-world-480.webp';
import neighborhood768 from '../assets/homepage/neighborhood-world-768.webp';
import neighborhood976 from '../assets/homepage/neighborhood-world-976.webp';
import neighborhoodFallback from '../assets/homepage/neighborhood-world.jpg';
import '../styles/homepage.css';
import { useDemo } from '../state/DemoContext';
import { isBuyerEligible } from '../utils/products';

export function LandingPage() {
  const { state } = useDemo();
  const featured = state.products.filter(product => isBuyerEligible(product) && product.category !== 'Homemade Food').slice(0,4);
  return <div className="site neighborhood-home"><PublicHeader/><main id="main-content" tabIndex={-1}>
    <section className="hero neighborhood-hero" id="home" aria-labelledby="neighborhood-title">
      <div className="hero-copy"><p className="neighborhood-kicker"><Store size={18} aria-hidden="true"/> Your neighborhood marketplace</p>
        <h1 id="neighborhood-title">Local life. <br/><em>More possibilities.</em></h1>
        <p className="hero-sub">Buy homemade products, discover properties, find local services, and support talent in your neighborhood.</p>
        <div className="hero-actions"><a className="btn btn-primary" href="#explore">Explore What Not? <ArrowRight size={18} aria-hidden="true"/></a><Link className="btn btn-outline" to="/login/seller">Seller sign in</Link></div>
        <p className="hero-scope">Approved beta accounts can order Homemade products, enquire about sale properties and request creative work.</p>
      </div>
      <picture className="neighborhood-art"><source type="image/webp" srcSet={`${neighborhood480} 480w, ${neighborhood768} 768w, ${neighborhood976} 976w`} sizes="(max-width: 900px) calc(100vw - 32px), (max-width: 1280px) 56vw, 720px"/><img src={neighborhoodFallback} width={976} height={596} alt="Miniature 3D neighborhood with a homemade shop, a house, a services toolbox, and a central location pin" fetchPriority="high" loading="eager" decoding="async" referrerPolicy="no-referrer"/></picture>
    </section>
    <HomepageCategories/>
    <aside className="homepage-notice" aria-label="Marketplace beta notice"><span className="homepage-beta-label">Controlled beta</span><DemoNotice/></aside>
    <section className="trust-strip"><span>Homemade food & crafts</span><i>✦</i><span>Sale properties · controlled beta</span><i>✦</i><span>Creative talent · controlled beta</span></section>
    <section className="section" id="featured"><div className="section-heading"><div><p className="eyebrow">Homemade · sample catalogue</p><h2>Small batches. Thoughtful creations.</h2></div><Link className="text-link" to="/buyer">Explore Homemade samples <ArrowRight size={16}/></Link></div><div className="product-grid">{featured.map(p=><ProductCard key={p.id} product={p}/>)}</div></section>
    <section className="how-section" id="how"><div className="section-heading centered"><div><p className="eyebrow">What you can do today</p><h2>Get to know What Not?</h2><p>Account access is limited to approved beta testers.</p></div></div><div className="steps">{[[PackageOpen,'01','Manage your products','Sellers can create a shop profile and submit products for admin review.'],[Search,'02','Explore Homemade samples','Browse local listings and use a saved address to check delivery availability.'],[Sparkles,'03','Find your next possibility','Enquire about sale properties or request quotes for Creative Services.'],[HeartHandshake,'04','Manage existing orders','Signed-in buyers and sellers can view their own order history. Checkout creates independent seller orders; no payment is collected.']].map(([Icon,n,t,d])=><article className="step" key={String(t)}><span>{String(n)}</span><i><Icon/></i><h3>{String(t)}</h3><p>{String(d)}</p></article>)}</div></section>
    <section className="radius-story"><div><p className="eyebrow light">Sample distance preview</p><h2>Local discovery.<br/>Controlled beta.</h2><p>Makers can save their intended selling radius. Live discovery uses coarse locality areas. Exact delivery eligibility is checked at checkout; this illustration uses sample distances.</p><div className="radius-flow"><b>SAMPLE SELLER</b><span>→</span><b>1 / 2 / 3 KM</b><span>→</span><b>SAMPLE BUYERS</b></div><Link className="btn btn-light" to="/buyer">Explore locality discoveries</Link></div><RadiusVisual/></section>
    <section className="seller-cta"><div><p className="eyebrow">For homemade makers</p><h2>Your craft deserves<br/>a local audience.</h2><p>Create your seller profile and submit handmade products for review. Approved, active products appear in locality discovery.</p><Link className="btn btn-primary" to="/login/seller">Become a seller <ArrowRight size={18}/></Link></div></section>
  </main><footer><LogoFooter/><p>Homemade. Real Estate. Creative Services.</p><small>© 2026 What Not?. Sample catalogue with authenticated account workflows.</small></footer></div>;
}
function LogoFooter(){return <div className="footer-logo">N <span>What Not?</span></div>}

// Homepage-only presentation: shared buyer categories and workflows stay unchanged.
function HomepageCategories(){
  return <section className="explore-verticals neighborhood-categories" id="explore" aria-label="Explore What Not?">
    <div className="section-heading"><div><p className="eyebrow">Explore What Not?</p><h2 id="explore-heading">Discover what’s around you.</h2></div></div>
    <div className="neighborhood-category-grid">
      <article className="neighborhood-category" id="homemade" aria-labelledby="homemade-heading"><div className="neighborhood-category-heading"><span className="neighborhood-category-icon"><Store size={26} aria-hidden="true"/></span><h3 id="homemade-heading">Homemade Products</h3><ArrowRight size={20} aria-hidden="true"/></div><p>Discover homemade food, handmade products and local creations.</p><span className="scope-badge">Sample catalogue</span><p className="neighborhood-category-limit">Food and crafts discovery is a sample preview. Food-specific availability, delivery and compliance tools are coming soon.</p><Link className="text-link" to="/buyer/samples#homemade-catalogue">Explore Homemade samples <ArrowRight size={16} aria-hidden="true"/></Link></article>
      <article className="neighborhood-category" id="real-estate" aria-labelledby="real-estate-heading"><div className="neighborhood-category-heading"><span className="neighborhood-category-icon"><House size={26} aria-hidden="true"/></span><h3 id="real-estate-heading">Real Estate</h3><ArrowRight size={20} aria-hidden="true"/></div><p>Discover local properties available for sale.</p><span className="scope-badge">Controlled beta</span><p className="neighborhood-category-limit">Sale listings, enquiries and appointment requests. Ownership and legal documents are not verified by this app.</p><Link className="text-link" to="/buyer/properties">Explore sale properties <ArrowRight size={16} aria-hidden="true"/></Link></article>
      <article className="neighborhood-category" id="creative-services" aria-labelledby="creative-heading"><div className="neighborhood-category-heading"><span className="neighborhood-category-icon"><Film size={26} aria-hidden="true"/></span><h3 id="creative-heading">Creative Services</h3><ArrowRight size={20} aria-hidden="true"/></div><p>Find video editors, VFX artists and creative professionals.</p><span className="scope-badge">Controlled beta</span><p className="neighborhood-category-limit">Browse services, request a quote and confirm completed work. No payment or escrow is collected.</p><Link className="text-link" to="/buyer/creative">Explore Creative Services <ArrowRight size={16} aria-hidden="true"/></Link></article>
    </div>
  </section>;
}
