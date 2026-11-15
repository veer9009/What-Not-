# Authorization matrix

Date: 14 November 2026. Baseline `5da76c8`.

All 86 application routes inspected; 77 protected routes returned 401 without a token. Probes used an unbound session override, so no database could be read or written. These checks establish authentication enforcement, not exhaustive object/role branch coverage.

| Method | Endpoint | Actor | Object / business restriction | Missing token | Source |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/addresses` | Active admitted account | Authenticated owner only; used delivery fields immutable | 401 | `backend/app/api/routes/addresses.py:14` |
| POST | `/api/v1/addresses` | Active admitted account | Authenticated owner only; used delivery fields immutable | 401 | `backend/app/api/routes/addresses.py:19` |
| GET | `/api/v1/addresses/{address_id}` | Active admitted account | Authenticated owner only; used delivery fields immutable | 401 | `backend/app/api/routes/addresses.py:25` |
| PATCH | `/api/v1/addresses/{address_id}` | Active admitted account | Authenticated owner only; used delivery fields immutable | 401 | `backend/app/api/routes/addresses.py:30` |
| POST | `/api/v1/addresses/{address_id}/default` | Active admitted account | Authenticated owner only; used delivery fields immutable | 401 | `backend/app/api/routes/addresses.py:36` |
| GET | `/api/v1/admin/products/pending` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:21` |
| POST | `/api/v1/admin/products/{product_id}/approve` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:26` |
| POST | `/api/v1/admin/products/{product_id}/reject` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:31` |
| GET | `/api/v1/admin/users` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:41` |
| PATCH | `/api/v1/admin/users/{user_id}/active` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:46` |
| POST | `/api/v1/admin/users/{user_id}/verify` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:51` |
| GET | `/api/v1/admin/orders` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:56` |
| POST | `/api/v1/admin/orders/{order_id}/resolve` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:64` |
| POST | `/api/v1/admin/orders/{order_id}/fulfillment` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:69` |
| POST | `/api/v1/admin/products/{product_id}/takedown` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:74` |
| GET | `/api/v1/admin/audit` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:79` |
| GET | `/api/v1/admin/operations` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/admin.py:87` |
| POST | `/api/v1/auth/register` | Public | Public credentials; allowlist/quota; registration cannot assign ADMIN | N/A | `backend/app/api/routes/auth.py:24` |
| POST | `/api/v1/auth/login` | Public | Public credentials; allowlist/quota; registration cannot assign ADMIN | N/A | `backend/app/api/routes/auth.py:33` |
| GET | `/api/v1/auth/me` | Active admitted account | Own identity; fresh DB role/activity/admission | 401 | `backend/app/api/routes/auth.py:45` |
| GET | `/api/v1/creative/listings` | Public | Approved active listing and active provider only | N/A | `backend/app/api/routes/creative.py:22` |
| GET | `/api/v1/creative/listings/mine` | SELLER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:26` |
| GET | `/api/v1/creative/provider` | SELLER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:30` |
| POST | `/api/v1/creative/provider` | SELLER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:34` |
| POST | `/api/v1/creative/listings` | SELLER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:38` |
| PATCH | `/api/v1/creative/listings/{listing_id}` | SELLER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:42` |
| POST | `/api/v1/creative/listings/{listing_id}/resubmit` | SELLER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:46` |
| GET | `/api/v1/creative/admin/listings` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/creative.py:50` |
| POST | `/api/v1/creative/admin/listings/{listing_id}/moderate` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/creative.py:54` |
| POST | `/api/v1/creative/listings/{listing_id}/rfqs` | BUYER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:58` |
| GET | `/api/v1/creative/rfqs` | Active admitted account | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:62` |
| GET | `/api/v1/creative/rfqs/{rfq_id}/responses` | Active admitted account | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:66` |
| POST | `/api/v1/creative/rfqs/{rfq_id}/responses` | SELLER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:70` |
| POST | `/api/v1/creative/responses/{response_id}/accept` | BUYER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:74` |
| GET | `/api/v1/creative/engagements` | Active admitted account | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:78` |
| POST | `/api/v1/creative/engagements/{engagement_id}/deliver` | SELLER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:85` |
| POST | `/api/v1/creative/engagements/{engagement_id}/complete` | BUYER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:89` |
| POST | `/api/v1/creative/engagements/{engagement_id}/review` | BUYER | Own provider/listing; private RFQ/quote/engagement participants; permitted ADMIN reads | 401 | `backend/app/api/routes/creative.py:93` |
| POST | `/api/v1/discovery/products` | BUYER | Buyer; owned address or transient point; approved eligible listing | 401 | `backend/app/api/routes/discovery.py:14` |
| POST | `/api/v1/discovery/products/{product_id}` | BUYER | Buyer; owned address or transient point; approved eligible listing | 401 | `backend/app/api/routes/discovery.py:22` |
| GET | `/api/v1/health` | Public | Minimal process health; no DB | N/A | `backend/app/api/routes/health.py:13` |
| GET | `/api/v1/ready` | Public | Public schema/backlog aggregates; restriction recommended | N/A | `backend/app/api/routes/health.py:19` |
| GET | `/api/v1/notifications` | Active admitted account | Recipient only, including read actions and counts | 401 | `backend/app/api/routes/notifications.py:11` |
| GET | `/api/v1/notifications/unread-count` | Active admitted account | Recipient only, including read actions and counts | 401 | `backend/app/api/routes/notifications.py:17` |
| PATCH | `/api/v1/notifications/read-all` | Active admitted account | Recipient only, including read actions and counts | 401 | `backend/app/api/routes/notifications.py:22` |
| PATCH | `/api/v1/notifications/{notification_id}/read` | Active admitted account | Recipient only, including read actions and counts | 401 | `backend/app/api/routes/notifications.py:27` |
| GET | `/api/v1/orders` | BUYER / SELLER | Owning buyer/shop owner; server totals and transition/fulfillment state checks | 401 | `backend/app/api/routes/orders.py:16` |
| POST | `/api/v1/orders` | BUYER | Owning buyer/shop owner; server totals and transition/fulfillment state checks | 401 | `backend/app/api/routes/orders.py:27` |
| GET | `/api/v1/orders/{order_id}` | BUYER / SELLER | Owning buyer/shop owner; server totals and transition/fulfillment state checks | 401 | `backend/app/api/routes/orders.py:36` |
| PATCH | `/api/v1/orders/{order_id}/status` | BUYER / SELLER | Owning buyer/shop owner; server totals and transition/fulfillment state checks | 401 | `backend/app/api/routes/orders.py:41` |
| GET | `/api/v1/orders/{order_id}/fulfillment` | BUYER / SELLER | Owning buyer/shop owner; server totals and transition/fulfillment state checks | 401 | `backend/app/api/routes/orders.py:46` |
| GET | `/api/v1/products` | Public | Public legacy GET returns 501 | N/A | `backend/app/api/routes/products.py:13` |
| POST | `/api/v1/products` | SELLER | Own seller product; moderation required | 401 | `backend/app/api/routes/products.py:18` |
| GET | `/api/v1/products/{product_id}` | Public | Public legacy GET returns 501 | N/A | `backend/app/api/routes/products.py:24` |
| PATCH | `/api/v1/products/{product_id}` | SELLER | Own seller product; moderation required | 401 | `backend/app/api/routes/products.py:29` |
| PATCH | `/api/v1/products/{product_id}/activation` | SELLER | Own seller product; moderation required | 401 | `backend/app/api/routes/products.py:34` |
| POST | `/api/v1/products/{product_id}/resubmit` | SELLER | Own seller product; moderation required | 401 | `backend/app/api/routes/products.py:39` |
| GET | `/api/v1/properties` | Public | Approved unexpired active-owner public projection; no private address | N/A | `backend/app/api/routes/properties.py:13` |
| GET | `/api/v1/properties/profile` | SELLER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:19` |
| POST | `/api/v1/properties/profile` | SELLER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:21` |
| GET | `/api/v1/properties/mine` | SELLER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:23` |
| GET | `/api/v1/properties/saved` | BUYER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:26` |
| GET | `/api/v1/properties/requests` | Active admitted account | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:30` |
| GET | `/api/v1/properties/admin/queue` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/properties.py:32` |
| GET | `/api/v1/properties/admin/reports` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/properties.py:35` |
| POST | `/api/v1/properties/admin/reports/{id}` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/properties.py:38` |
| POST | `/api/v1/properties/enquiries/{id}/reply` | SELLER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:40` |
| POST | `/api/v1/properties/visits/{id}/action` | Active admitted account | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:42` |
| POST | `/api/v1/properties/visits/{id}/location` | BUYER | Creator or reasoned ADMIN; visit route: owning buyer, confirmed future appointment | 401 | `backend/app/api/routes/properties.py:44` |
| POST | `/api/v1/properties` | SELLER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:46` |
| GET | `/api/v1/properties/{id}` | Public | Approved unexpired active-owner public projection; no private address | N/A | `backend/app/api/routes/properties.py:49` |
| PATCH | `/api/v1/properties/{id}` | SELLER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:52` |
| POST | `/api/v1/properties/{id}/moderation` | ADMIN | Admin role; target record; reason/timestamp where required | 401 | `backend/app/api/routes/properties.py:55` |
| POST | `/api/v1/properties/{id}/sold` | SELLER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:58` |
| POST | `/api/v1/properties/{id}/reconfirm` | SELLER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:61` |
| POST | `/api/v1/properties/{id}/resubmit` | SELLER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:64` |
| POST | `/api/v1/properties/{id}/location` | Active admitted account | Creator or reasoned ADMIN; visit route: owning buyer, confirmed future appointment | 401 | `backend/app/api/routes/properties.py:67` |
| POST | `/api/v1/properties/{id}/enquiries` | BUYER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:69` |
| POST | `/api/v1/properties/{id}/visits` | BUYER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:71` |
| POST | `/api/v1/properties/{id}/save` | BUYER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:73` |
| POST | `/api/v1/properties/{id}/reports` | BUYER | Own listing/profile; enquiry/visit participants; buyer-owned saves/reports | 401 | `backend/app/api/routes/properties.py:75` |
| PATCH | `/api/v1/sellers/me/dispatch-location` | SELLER | Own seller profile/shop/products/dispatch location | 401 | `backend/app/api/routes/sellers.py:16` |
| POST | `/api/v1/sellers/me` | SELLER | Own seller profile/shop/products/dispatch location | 401 | `backend/app/api/routes/sellers.py:21` |
| GET | `/api/v1/sellers/me` | SELLER | Own seller profile/shop/products/dispatch location | 401 | `backend/app/api/routes/sellers.py:26` |
| PATCH | `/api/v1/sellers/me` | SELLER | Own seller profile/shop/products/dispatch location | 401 | `backend/app/api/routes/sellers.py:31` |
| GET | `/api/v1/sellers/me/products` | SELLER | Own seller profile/shop/products/dispatch location | 401 | `backend/app/api/routes/sellers.py:37` |

## Authorization evidence and limitations

Backend tests independently exercise cross-seller products, cross-buyer orders, addresses and notifications; forged token roles; account suspension/role changes; admin moderation and stale review timestamps; server price/stock/quantity and idempotency; delivery confirmation/disputes; private property appointments; Creative quote/engagement/review ownership. See SECURITY_TEST_RESULTS.md.

Service enforcement: services/products.py, moderation.py, orders.py, addresses.py, notifications.py, properties.py and creative.py. API role aliases resolve through api/dependencies.py to DB-loaded activity/admission/role. IDs are selectors, never proof of ownership. Lists are participant-scoped.

Seller self-approval is denied by ADMIN-only dependencies and DB roles. Approved product edits reset review; property and Creative edits require review. Production public property/Creative browse is intentionally outside the account allowlist. It must not be mistaken for a fully private pilot site.

Orders expose ordinary snapshots without delivery contact; fulfillment reads apply lifecycle restrictions. Admin fulfillment requires an investigation reason and audit record. Property expiry intentionally retains confirmed future appointment access; sold/takedown/suspension revokes it. Creative ADMIN read paths are privileged by design, not available to normal accounts.

No file-upload, payment-status, password-reset, refresh-token or backend logout route exists: NOT APPLICABLE for absent workflows. Documentation routes are framework-generated and outside these 86 business routes; their public exposure was probed separately. Positive/negative role combinations for every route are not all separately automated; source review is not a claim otherwise.
