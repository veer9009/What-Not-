import { Check, SlidersHorizontal, X } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { DashboardShell, Metric, PageTop, StatusBadge } from '../components/Shared';
import { useDemo } from '../state/DemoContext';
import { isBuyerEligible } from '../utils/products';

export function AdminDashboard() {
  const { state, dispatch } = useDemo();
  const pending = state.products.filter(p => p.status === 'PENDING');
  const [commission, setCommission] = useState(8);
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  function reject(e: FormEvent) {
    e.preventDefault();
    if (!reason.trim()) { setError('Enter a rejection reason so the seller knows what to change.'); return; }
    const product = pending.find(p => p.id === rejectId);
    if (!product) { setError('This product is no longer pending. Refresh the review queue.'); return; }
    dispatch({ type: 'product/status', role: 'admin', id: product.id, status: 'REJECTED', rejectionReason: reason });
    setNotice(`${product.name} rejected. The reason is available to the seller.`);
    setRejectId(null); setReason(''); setError('');
  }
  return <DashboardShell role="admin">
    <PageTop eyebrow="Platform command centre" title="Marketplace overview" action={<span className="live-pill">● Demo data live</span>}/>
    {notice && <p className="success-note" role="status">{notice}</p>}
    <div className="metrics-grid admin-metrics"><Metric label="Total Buyers" value="2,418" note="+12.4% this month"/><Metric label="Total Sellers" value="186" note="34 verified"/><Metric label="Active Products" value={state.products.filter(isBuyerEligible).length}/><Metric label="Pending Approvals" value={pending.length} note="Needs attention"/><Metric label="Orders" value={state.orders.length} note="Demo orders"/><Metric label="Platform Revenue" value="₹42.8k" note="Placeholder"/></div>
    <div className="admin-columns"><section className="panel"><div className="panel-head"><div><p className="eyebrow">Moderation queue</p><h2>Pending Product Approvals</h2></div><span>{pending.length} waiting</span></div>
      {pending.length ? <div className="approval-list">{pending.map(p => <article key={p.id}>
        <img src={p.image} alt={p.name}/><div className="approval-copy"><StatusBadge status={p.status}/>{!p.isActive && <StatusBadge status="INACTIVE"/>}<h3>{p.name}</h3><p>Seller: {p.seller}</p><p>Category: {p.category}</p>
          <div className="approval-facts"><span>₹{p.price}</span><span>{p.radius} KM radius</span><span>{p.stock} in stock</span></div><p>{p.description}</p>
        </div><div className="approval-actions">
          <button className="approve" onClick={() => { dispatch({ type: 'product/status', role: 'admin', id: p.id, status: 'APPROVED' }); setNotice(`${p.name} approved. Eligible buyers can now discover it.`); if (rejectId === p.id) setRejectId(null); }}><Check/> Approve</button>
          <button className="reject" onClick={() => { setRejectId(p.id); setReason(''); setError(''); }}><X/> Reject</button>
        </div>
        {rejectId === p.id && <form className="rejection-form" onSubmit={reject} noValidate>
          <label htmlFor={`reason-${p.id}`}>Rejection reason</label><textarea id={`reason-${p.id}`} value={reason} onChange={e => { setReason(e.target.value); setError(''); }} aria-invalid={Boolean(error)} aria-describedby={error ? `reason-error-${p.id}` : undefined} autoFocus placeholder="Explain what the seller should improve..."/>
          {error && <p className="form-error" role="alert" id={`reason-error-${p.id}`}>{error}</p>}
          <div className="form-actions"><button type="button" className="btn btn-outline btn-sm" onClick={() => { setRejectId(null); setReason(''); setError(''); }}>Cancel</button><button className="btn btn-primary btn-sm">Confirm Rejection</button></div>
        </form>}
      </article>)}</div> : <div className="empty compact"><Check/><h3>Approval queue is clear</h3><p>All submitted products have been reviewed.</p></div>}
    </section><aside className="commission-card"><i><SlidersHorizontal/></i><p className="eyebrow">Configurable placeholder</p><h2>Margin / Commission</h2><p>Preview a future platform fee. No financial logic is active in this demo.</p><label>Default commission <b>{commission}%</b><input type="range" min="0" max="20" value={commission} onChange={e => setCommission(Number(e.target.value))}/></label><div><span>Financial calculations</span><StatusBadge status="PENDING"/></div><button className="btn btn-dark wide" onClick={() => alert('Demo setting saved')}>Save demo setting</button></aside></div>
  </DashboardShell>;
}
