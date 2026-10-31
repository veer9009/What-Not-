import { MessageCircle } from 'lucide-react';
import { DashboardShell, PageTop } from '../components/Shared';
import { SUPPORT_PHONE, supportUrl } from '../utils/support';

export function HelpPage() {
  return <DashboardShell role="buyer">
    <PageTop eyebrow="Here to help" title="Help & Support"/>
    <section className="panel help-panel">
      <MessageCircle size={32} aria-hidden="true"/>
      <h2>Talk to What Not Support</h2>
      <p>Reach us on WhatsApp at <strong>{SUPPORT_PHONE}</strong>.</p>
      <p>We can help with:</p>
      <ul><li>Order and delivery issues</li><li>Seller and order concerns</li><li>Account issues</li><li>Product and listing concerns</li><li>General marketplace help</li></ul>
      <a className="btn btn-primary" href={supportUrl()} target="_blank" rel="noreferrer">Chat with What Not Support</a>
      <p className="approval-help">For help with a specific order, open its details and choose “Need help with this order?” to include your order reference.</p>
    </section>
  </DashboardShell>;
}
