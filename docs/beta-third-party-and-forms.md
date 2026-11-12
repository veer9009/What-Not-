# Third-party and collection-point audit

12 November 2026. References are repository paths; production services were not inspected.

## Third parties and outbound requests

| Service | Purpose/data sent | Loading trigger | Essential? / disclosure / consent implication | Decision |
| --- | --- | --- | --- | --- |
| Frontend API origin (`VITE_API_BASE_URL`) | Auth credentials/bearer token; relevant marketplace requests | Explicit forms, authenticated reads; localhost default | Core; public config, disclose operator/hosting; secure actual origin and HTTPS before launch | Keep; origin, deployment TLS and hosting ownership are owner gates |
| PostgreSQL/hosting/backups | Persist listed categories in data inventory | Backend service requests | Core processor infrastructure; vendor/geography/access/logging/retention unknown | Keep architecture; production evidence required |
| SMTP vendor | Recipient email, generic title/body, hashed event Message-ID | Outbox worker only if configured, disabled by default | Transactional; disclose actual processor; no marketing delivery found; TLS config must be verified | Keep optional transactional facility; vendor and production settings unknown |
| Unsplash image CDN | IP, UA/browser network metadata and image path | Public/sample catalogue/landing images load automatically | Optional sample imagery; rights/cookie/response evidence unknown | Retained pending owner rights/replacement decision; referrer suppressed; release blocker |
| Seller-selected HTTP(S) image hosts | Browser request/IP, URL; no backend image proxy/fetch | Product image render | Display function; arbitrary host tracking/malware/content risk remains; users do not choose each host | Keep current workflow; no referrer, credential-bearing image URLs rejected; host policy/HTTPS/proxy needs separate decision |
| Google Fonts stylesheet and font CDN | Former automatic IP/browser/referrer requests | CSS import on every page | Nonessential typography; licensing/provenance unresolved | Removed import; native CSS fallbacks, no new font files |
| WhatsApp `wa.me` | Phone destination plus generic message or order ID; third party then processes chosen conversation | User clicks outbound link | Optional help; disclose external service; no WhatsApp SDK or automatic tracking found | Keep existing repository phone, pending owner confirmation; `noreferrer`; not named grievance mechanism |
| Provider portfolio hosts | URL, browser metadata after navigation | User opens explicit HTTP(S) link | Optional; caller-controlled link, credential URLs already rejected by Creative schema | Keep links, no embeds; user rights and malicious-link process require owner decision |
| Browser/OS geolocation | Browser-managed location request; precise point draft | Explicit Use current location action and permission | Optional functional choice; manual fallback; API sees only submitted coordinates | Keep; no map/geocoding third party in code |
| GA/GTM/Meta Pixel/Clarity/Hotjar/Mixpanel/Segment/ad SDKs/social/video/maps embeds/CDN scripts | None found in runtime source/index/build | Not present | No source analytics/marketing consent activation required | Do not add banner or tracking; hosting-injected code remains unknown |

No third-party image or font service was assumed to have a specific licence, no-cookie guarantee, country of processing or contractual status. Network/storage observations in automated browser checks cover legal routes and the tested local build, not provider response behaviour or production.

## Forms and actions

| Collection context | Required/optional, audience and findings | Fix / unresolved decision |
| --- | --- | --- |
| Registration | Name/email/phone/password and buyer/seller role. All required; phone used in fulfillment and uniqueness. No DOB/identity document/marketing opt-in | Account notice; no fabricated acceptance or extra checkbox. Whether phone is necessary for non-ordering property/Creative-only accounts requires product/schema decision; no migration |
| Login | Email/password; generic errors, password cleared after request; source/email abuse scope hashes | Sign-in notice; no auth storage persistence |
| Seller profile/dispatch | Shop/phone/coordinates; description optional; explicit dispatch confirmation, no implicit IP geolocation | Seller notice plus existing draft/permission explanation; repeated account/shop phone remains an existing business-contact field |
| Saved address/default | Postal fields and precise coordinates; line 2 optional, default choice unchecked | Notice explains sharing/retained history. Existing label/input validation and unique shared error IDs. No deletion promised |
| Product create/edit | Name/description/price/quantity/category/radius; image URL optional | Public-content/IP/external-host notice; new credential URL rejection; native required fields and validation; food category absent |
| Checkout | Select owned saved address; current prices checked, totals and zero current delivery fee shown, independent seller orders | Collection notice and cancellation-policy link before action. Backend price/stock/ownership/idempotency remain authoritative; no new payment fields |
| Order completion/cancel/dispute/support | Lifecycle status action, no extra personal details; support URL only order ID | Existing confirmation deadline and persisted dispute retained. Requests for damage/wrong goods outside not-received dispute use support; formal process missing |
| Property profile/listing | Public name/capacity, optional phone sharing defaults false; price/title/description/locality/private address | Context notice and existing keep-address-out-of-public-text warning. Fixed editor to preload saved sharing preference and support withdrawal, sending only three editable fields. Revocation cannot erase prior recipients’ copies |
| Property enquiry/reply/visit/save/report | Message, proposed time, reason/explanation; `other` requires explanation; save can be removed | Notice identifies participant/admin sharing. Backend private-location gates preserved; no proof upload/DOB added |
| Creative provider/service | Display name/bio, title/description/category/pricing/amount, remote/locality, optional links/active choice | Notice describes public listings/private messages. Remote/active checked defaults are service settings, not consent to marketing; all portfolios are outbound links |
| Creative enquiry/quote/accept/delivery/completion | Brief, terms/amount, scoped UUID recovery, accepted snapshots | Notice warns of private draft storage and admin access. No external work-file upload or payment; cancellation not implemented |
| Creative review | Only owning buyer after completion; 1–5 rating and text; one review per engagement | Keep actual relationship-backed reviews. Default 5-star choice may steer ratings; flagged product decision, not silently rewritten under this audit |
| Product moderation/rejection | Required bounded reason for rejection; approve version check; inline form autoFocus | Existing labels/error alerts. Cancel/rejection form focus restoration deserves manual AT testing; no modal/focus trap introduced |
| Admin operations/moderation | Investigation reason for private fulfillment reads, account actions, takedown/resolution; audit reason can contain personal data | Existing backend active-ADMIN gates and audited reads retained; operators must minimise free-text reasons and have retention/access policy |
| Support/grievance | No backend public complaint form. Existing outbound WhatsApp general/order link | Public contact page states missing formal officer/channel; does not invent complaint submission, tracking or redress promises |

No hidden checkout fee, urgency countdown, advertisement or pre-checked optional marketing consent was found. No all-purpose consent checkbox was added. Native `required` plus programmatic names remain in forms; shared inputs visibly identify required fields. More accessible custom text-area errors, user-authored alt descriptions and a complete manual screen-reader pass remain open, as does a multilingual notice decision.
