# Cookie and browser-storage consent decision

12 November 2026. Decision applies to reviewed source, not uninspected hosting configuration.

**No cookie banner is implemented.** No optional analytics/advertising switch exists in this beta. A fake Accept all banner would misrepresent processing. Necessary request-recovery storage must work before a write to prevent duplicate orders/quotes. This is a technical classification, not a legal finding that all processing is exempt from consent.

| Mechanism/key | Category | Contents/purpose | Lifetime and clearing |
| --- | --- | --- | --- |
| Application cookies | None found | No `document.cookie`, Set-Cookie or cookie authentication; fetch uses `credentials: omit` | Hosting/CDN may differ; owner must verify |
| localStorage | None found in product code | Tests check that auth does not persist | Not used |
| JS memory | STRICTLY NECESSARY | Short-lived bearer token, authenticated identity, cart, current discovery source | Logout/expiry clears identity/cart; reload requires login |
| `whatnot:order-recovery:<buyer ID>` sessionStorage | STRICTLY NECESSARY | Retry UUID, seller/address/product IDs, quantities/expected price, cart IDs and seller label | Persist before transmission; remove on definitive reconciliation; uncertain attempts survive logout/reload; no TTL |
| `whatnot:creative-recovery:<user ID>:enquiry:<listing ID>` | STRICTLY NECESSARY | UUID and pending brief text | Successful retry or explicit reset clears; otherwise tab-session lifetime |
| `whatnot:creative-recovery:<user ID>:quote:<rfq ID>` | STRICTLY NECESSARY | UUID, scope/terms and amount | Same; account scoped, not encrypted, same-origin scripts can read |
| Browser geolocation permission | FUNCTIONAL, not an app cookie | User-requested browser/OS location; manual entry available | Browser-managed permission, app draft confirmed before use |
| External images | UNKNOWN third-party response/storage behaviour | Automatic image request exposes IP/browser network information; referrer now suppressed | Host/browser managed; response headers/cookie behaviour not verified |
| WhatsApp/portfolio links | FUNCTIONAL outbound navigation | Opens on user action; WhatsApp URL contains generic message or order reference | Third-party site handles any storage after navigation |
| Google Fonts | Removed | Former automatic stylesheet/font requests | No longer imported; system font fallbacks used |
| Analytics, marketing, embeds | None found | No GA/GTM/Meta/Clarity/Hotjar/Mixpanel/Segment, iframe/video/social/maps embed | No consent-gated optional code to activate |

Session storage can be copied/restored by browser features; do not promise guaranteed deletion on browser close. Logout deliberately does not discard unresolved retry keys: doing so risks duplicate transactions. Resolve history first, then use provided recovery controls or browser clear-site-data. Clearing site data is not database erasure.

Before beta: inspect actual response headers and outbound network traffic, hosting/CDN-added scripts/cookies, image hosts, CSP/referrer policy, and SMTP/vendor configuration. **Unknown production configuration is a release blocker**, not a reason to add a banner speculatively. If optional tracking is introduced, block it until a suitable affirmative decision, implement withdrawal, document vendors/purposes, and reassess applicable law. This task does not authorise such tracking.

Public disclosure: `/cookies` and `/privacy`. Source evidence: `src/api/client.ts`, `src/state/AuthContext.tsx`, `checkoutRecovery.ts`, `creativeRecovery.ts`, `src/location/geolocation.ts`, `src/styles/index.css`, `src/utils/support.ts`, `backend/app/main.py`.
