import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

export function LegalFooter() {
  return <footer className="legal-footer"><nav aria-label="Legal and support">
    <Link to="/privacy">Privacy Policy</Link><Link to="/terms">Terms &amp; Conditions</Link>
    <Link to="/cookies">Cookie Policy</Link><Link to="/refunds">Refund / Cancellation Policy</Link>
    <Link to="/contact">Contact</Link><Link to="/support">Grievance / Support</Link>
  </nav><p>Controlled beta. Policies contain outstanding owner decisions.</p></footer>;
}
export function CollectionNotice({label,children}:{label:string;children:ReactNode}) {
  return <p className="collection-notice" aria-label={`${label} privacy notice`}>{children} <Link to="/privacy">Read the privacy notice</Link>.</p>;
}
