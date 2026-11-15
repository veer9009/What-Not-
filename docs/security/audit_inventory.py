"""Render the audit route inventory from retained, redacted runtime evidence."""
import json
from pathlib import Path

directory = Path(__file__).resolve().parent
routes = json.loads((directory / 'evidence/runtime-baseline.json').read_text())['routes']
roles = {'Public': 'Public', 'CurrentUser': 'Active admitted account',
         'Buyer': 'BUYER', 'Seller': 'SELLER', 'Admin': 'ADMIN',
         'OrderActor': 'BUYER / SELLER'}


def scope(route):
    path, role = route['path'], route['role']
    if role == 'Admin':
        return 'Admin role; target record; reason/timestamp where required'
    if path.startswith('/api/v1/addresses'):
        return 'Authenticated owner only; used delivery fields immutable'
    if path.startswith('/api/v1/notifications'):
        return 'Recipient only, including read actions and counts'
    if path.startswith('/api/v1/sellers'):
        return 'Own seller profile/shop/products/dispatch location'
    if path.startswith('/api/v1/discovery'):
        return 'Buyer; owned address or transient point; approved eligible listing'
    if path.startswith('/api/v1/orders'):
        return 'Owning buyer/shop owner; server totals and transition/fulfillment state checks'
    if path.startswith('/api/v1/properties'):
        if role == 'Public':
            return 'Approved unexpired active-owner public projection; no private address'
        if path.endswith('/location'):
            return 'Creator or reasoned ADMIN; visit route: owning buyer, confirmed future appointment'
        return 'Own listing/profile; enquiry/visit participants; buyer-owned saves/reports'
    if path.startswith('/api/v1/creative'):
        return ('Approved active listing and active provider only' if role == 'Public' else
                'Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads')
    if path.endswith('/auth/me'):
        return 'Own identity; fresh DB role/activity/admission'
    if '/auth/' in path:
        return 'Public credentials; allowlist/quota; registration cannot assign ADMIN'
    if path.endswith('/ready'):
        return 'Public schema/backlog aggregates; restriction recommended'
    if '/products' in path:
        return 'Public legacy GET returns 501' if role == 'Public' else 'Own seller product; moderation required'
    return 'Minimal process health; no DB'


rows = [
    '# Authorization matrix', '',
    'Date: 14 November 2026. Baseline `5da76c8`.', '',
    f'All {len(routes)} application routes inspected; '
    f'{sum(r.get("missing_token_status") == 401 for r in routes)} protected routes '
    'returned 401 without a token. Probes used an unbound session override, so no '
    'database could be read or written. These checks establish authentication '
    'enforcement, not exhaustive object/role branch coverage.', '',
    '| Method | Endpoint | Actor | Object / business restriction | Missing token | Source |',
    '| --- | --- | --- | --- | --- | --- |',
]
for route in routes:
    rows.append(f'| {route["method"]} | `{route["path"]}` | {roles[route["role"]]} | '
                f'{scope(route)} | {route.get("missing_token_status", "N/A")} | '
                f'`{route["file"]}:{route["line"]}` |')
rows.extend([
    '', '## Authorization evidence and limitations', '',
    'Backend tests independently exercise cross-seller products, cross-buyer orders, '
    'addresses and notifications; forged token roles; account suspension/role changes; '
    'admin moderation and stale review timestamps; server price/stock/quantity and '
    'idempotency; delivery confirmation/disputes; private property appointments; '
    'Creative quote/engagement/review ownership. See SECURITY_TEST_RESULTS.md.', '',
    'Service enforcement: services/products.py, moderation.py, orders.py, '
    'addresses.py, notifications.py, properties.py and creative.py. API role aliases '
    'resolve through api/dependencies.py to DB-loaded activity/admission/role. '
    'IDs are selectors, never proof of ownership. Lists are participant-scoped.', '',
    'Seller self-approval is denied by ADMIN-only dependencies and DB roles. '
    'Approved product edits reset review; property and Creative edits require review. '
    'Production public property/Creative browse is intentionally outside the '
    'account allowlist. It must not be mistaken for a fully private pilot site.', '',
    'Orders expose ordinary snapshots without delivery contact; fulfillment reads '
    'apply lifecycle restrictions. Admin fulfillment requires an investigation reason '
    'and audit record. Property expiry intentionally retains confirmed future '
    'appointment access; sold/takedown/suspension revokes it. Creative ADMIN read '
    'paths are privileged by design, not available to normal accounts.', '',
    'No file-upload, payment-status, password-reset, refresh-token or backend logout '
    'route exists: NOT APPLICABLE for absent workflows. Documentation routes are '
    'framework-generated and outside these 86 business routes; their public exposure '
    'was probed separately. Positive/negative role combinations for every route are '
    'not all separately automated; source review is not a claim otherwise.',
])
(directory / 'AUTHORIZATION_MATRIX.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
print('Authorization matrix written:', len(routes), 'routes')
