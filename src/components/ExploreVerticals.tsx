import { ArrowRight, HousePlus, Palette, ShoppingBasket } from 'lucide-react';
import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

// Presentation only: these examples are not product records or API payloads.
export function ExploreVerticals({live=false}:{live?:boolean}) {
  const location = useLocation();
  useEffect(() => {
    if (location.hash === '#homemade-catalogue') {
      document.getElementById('homemade-catalogue')?.scrollIntoView?.({ block: 'start' });
    }
  }, [location.hash, location.key]);
  return <section className="explore-verticals" id="explore" aria-labelledby="explore-heading">
    <div className="section-heading"><div>
      <h2 id="explore-heading">Explore Nearby</h2>
    </div></div>
    <div className="vertical-grid">
      <article className="vertical-card" id="homemade" aria-labelledby="homemade-heading">
        <div className="vertical-card-top"><ShoppingBasket size={28} aria-hidden="true"/><span className="scope-badge">{live?'Nearby products':'Sample catalogue'}</span></div>
        <h3 id="homemade-heading">Homemade</h3>
        <p>Homemade food, handmade products and crafts.</p>
        <ul className="vertical-examples"><li>Homemade Food</li><li>Homemade Products / Crafts</li></ul>
        <p className="vertical-limit">{live?'Choose your location to discover eligible handmade products. Food-specific listing and compliance tools are coming soon.':'Food and crafts discovery is a sample preview. Food-specific availability, delivery and compliance tools are coming soon.'}</p>
        <Link className="text-link vertical-action" to={live?'/buyer#homemade-catalogue':'/buyer/samples#homemade-catalogue'}>{live?'Explore nearby Homemade':'Explore Homemade samples'} <ArrowRight size={16}/></Link>
      </article>
      <article className="vertical-card" id="real-estate" aria-labelledby="real-estate-heading">
        <div className="vertical-card-top"><HousePlus size={28} aria-hidden="true"/><span className="scope-badge">Controlled beta</span></div>
        <h3 id="real-estate-heading">Real Estate</h3>
        <p>Local properties for sale.</p>
        <ul className="vertical-examples"><li>Residential</li><li>Commercial</li><li>Land/Plots</li></ul>
        <p className="vertical-limit">Sale listings, enquiries and appointment requests. Ownership and legal documents are not verified by this app.</p>
        <Link className="btn btn-outline vertical-action" to="/buyer/properties">Explore sale properties</Link>
      </article>
      <article className="vertical-card" id="creative-services" aria-labelledby="creative-heading">
        <div className="vertical-card-top"><Palette size={28} aria-hidden="true"/><span className="scope-badge">Controlled beta</span></div>
        <h3 id="creative-heading">Creative Services</h3>
        <p>Video editing, VFX and creative services.</p>
        <ul className="vertical-examples"><li>Video editing</li><li>Travel video editing</li><li>Influencer reel editing</li><li>VFX service</li></ul>
        <p className="vertical-limit">Browse services, request a quote and confirm completed work. No payment or escrow is collected.</p>
        <Link className="btn btn-outline vertical-action" to="/buyer/creative">Explore Creative Services</Link>
      </article>
    </div>
  </section>;
}
