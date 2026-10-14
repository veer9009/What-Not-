import { ArrowRight, House, Film, Utensils } from 'lucide-react';
import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

// Presentation only: these examples are not product records or API payloads.
export function ExploreVerticals() {
  const location = useLocation();
  useEffect(() => {
    if (location.hash === '#homemade-catalogue') {
      document.getElementById('homemade-catalogue')?.scrollIntoView?.({ block: 'start' });
    }
  }, [location.hash, location.key]);
  return <section className="explore-verticals" id="explore" aria-labelledby="explore-heading">
    <div className="section-heading"><div>
      <p className="eyebrow">Three ways to discover local</p>
      <h2 id="explore-heading">Explore What Not?</h2>
      <p className="verticals-intro">Homemade creations, places to call home, and talent for your next story.</p>
    </div></div>
    <div className="vertical-grid">
      <article className="vertical-card" id="homemade" aria-labelledby="homemade-heading">
        <div className="vertical-card-top"><Utensils size={28} aria-hidden="true"/><span className="scope-badge">Sample catalogue</span></div>
        <h3 id="homemade-heading">Homemade</h3>
        <p>Discover homemade food, handmade products and local creations.</p>
        <ul className="vertical-examples"><li>Homemade Food</li><li>Homemade Products / Crafts</li></ul>
        <p className="vertical-limit">Food and crafts discovery is a sample preview. Food-specific availability, delivery and compliance tools are coming soon.</p>
        <Link className="text-link vertical-action" to="/buyer#homemade-catalogue">Explore Homemade samples <ArrowRight size={16}/></Link>
      </article>
      <article className="vertical-card" id="real-estate" aria-labelledby="real-estate-heading">
        <div className="vertical-card-top"><House size={28} aria-hidden="true"/><span className="scope-badge">Coming soon</span></div>
        <h3 id="real-estate-heading">Real Estate</h3>
        <p>Discover local properties available for rent or sale.</p>
        <ul className="vertical-examples"><li>Example rental property</li><li>Example sale property</li></ul>
        <p className="vertical-limit">Illustrative examples only. Property listings and enquiries are not available yet.</p>
        <button className="btn btn-outline vertical-action" disabled>Property listings coming soon</button>
      </article>
      <article className="vertical-card" id="creative-services" aria-labelledby="creative-heading">
        <div className="vertical-card-top"><Film size={28} aria-hidden="true"/><span className="scope-badge">Coming soon</span></div>
        <h3 id="creative-heading">Creative Services</h3>
        <p>Find video editors, VFX artists and creative professionals.</p>
        <ul className="vertical-examples"><li>Video editing</li><li>Travel video editing</li><li>Influencer reel editing</li><li>VFX service</li></ul>
        <p className="vertical-limit">Illustrative examples only. Portfolios, bookings and creative requests are not available yet.</p>
        <button className="btn btn-outline vertical-action" disabled>Creative requests coming soon</button>
      </article>
    </div>
  </section>;
}
