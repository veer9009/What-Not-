# Five-user pilot acceptance test plan

Prepared 15 November 2026. **NOT EXECUTED on deployed HTTPS; NO-GO pending evidence and owner approval.** This plan does not authorize a deployment, production data import, mail send, migration or original-database write. Use a new isolated staging target and synthetic data first. No real payment, private identity document or precise home location is needed for acceptance testing.

## Scope and five identities

Exactly five participant identities include the administrator/operator: buyer B1, buyer B2, seller S1, seller S2 and admin A1. Real account identifiers and recovery contacts belong in a private access register, not this file. No sixth recovery account is implied. A1 must be provisioned through the reviewed trusted operator process; registration cannot select ADMIN. The synthetic sixth local smoke account is not approved for import. Recovery needs an owner-approved secure operator process because password reset is not implemented.

| Identity | Purpose | Synthetic fixtures |
| --- | --- | --- |
| B1 | Main checkout, appointment and Creative buyer | Two owned saved addresses; one within and one outside test delivery boundary |
| B2 | Independent buyer and adversarial ownership checks | Distinct address, orders, notifications, RFQs and visits |
| S1 | Main shop, property creator and Creative provider | Products at radii 1/2/3 km, property sale listing and Creative service |
| S2 | Independent seller/provider; cross-owner checks | Distinct shop/products/property/service and private conversations |
| A1 | Moderation, audited investigation and operations | Out-of-band contact-verification evidence and reasoned admin actions |

Use separate browser profiles/devices so tokens, carts and drafts cannot leak between participants. At least one real Android Chrome and one iOS Safari session over the actual approved HTTPS hostname are required, plus a current desktop browser. Record exact OS/browser versions and viewport. Desktop emulation is additional evidence, not a replacement for mobile geolocation and touch testing.

Implemented scope is Homemade ordering, property sale listing/enquiry/visit workflows, Creative service enquiry/quote/engagement workflows, notifications and reasoned admin operations. Sample pages remain samples; sample food is not an orderable food workflow. There is no platform payment, escrow, payout, refund, COD status or direct-UPI verification implementation. Parties may arrange matters directly; the app does not verify such transactions. There are no upload or password-reset features. Creative work files are not delivered through the app. Do not accept a demo of an invented facility as a passing test.

Live Homemade discovery returns locality candidates based on seller/product delivery radius; seller radii support integer 1/2/3 km. The buyer 1/2/3 km selector applies to sample discovery, not the live API. Exact delivery eligibility is checked at checkout. Owner must accept and disclose this scope before pilot; if live buyer radius filtering is required, the gate fails until implemented and tested. PIN entry filters the signed-in user's own saved addresses; it is not geocoding and cannot invent a location from an unknown PIN.

## Preconditions and test discipline

1. Release owner names the witness, approves exact artifact/configuration and staging target, and confirms the original DB is excluded. Target identity guards, isolated backups and reviewed revision `0008` precede write tests.
2. Whole-site perimeter covers HTML, APIs and public property/Creative listing reads. Exactly the five identities are admitted. Synthetic unauthenticated clients need no sixth account.
3. HTTPS chain/hostname, proxy routing/headers/host/CORS/IP trust, private DB and production configuration gates pass; no public API/dev server ports.
4. Approve business/privacy/support/eligibility decisions, manual verification procedure, mail scope and user instructions. Existing legal pages are drafts with missing owner inputs; no acceptance timestamp workflow exists.
5. Operator controls maintenance, timer schedules, backups and alerts; a new-target restore rehearsal meets owner-approved numeric RPO/RTO from the [backup plan](PRODUCTION_BACKUP_RECOVERY.md). Record default grace/reconfirmation settings without changing production solely to accelerate tests.
6. Record release hash, schema, sanitized fixture references, UTC start/end, device/browser, actor and witness for every case. Never store tokens, raw API payloads, passwords, mail bodies, coordinates or personal addresses in evidence. Use cropped/redacted screenshots and route/status summaries.

Statuses are NOT VERIFIED, PASS, FAIL or BLOCKED. PASS requires actual expected behavior plus private evidence reference and witness/date. A local mocked unit test does not change these HTTPS UAT statuses. Negative tests should assert denial and unchanged victim data, using only synthetic accounts. Never load test, send spam, brute force or disable quotas on the production pilot.

## Acceptance matrix

Every row starts NOT VERIFIED; add separate evidence per device/actor where required. Status codes may be 403 or 404 for protected objects according to the implemented contract; the invariant is no unauthorized data or mutation, not a guessed universal code.

| ID / actors | Test and expected result | Acceptance evidence required | Status |
| --- | --- | --- | --- |
| P01 / all, anonymous | Five admitted identities can reach the gated site; nonparticipants cannot browse HTML/API/public listings directly. CORS alone is not accepted as a gate. | Allowed/denied HTTPS route/status matrix, perimeter review, witness/date | NOT VERIFIED |
| P02 / B1,B2,S1,S2,A1 | Correct login/me roles; wrong password generic denial; duplicate registration rejected; selected BUYER/SELLER registration only; ADMIN role injection forbidden. Sequence selected registration without creating an extra admitted identity. | Redacted role/status record and unchanged total identity roster | NOT VERIFIED |
| P03 / all | Missing/forged/expired token denied; expiration/reload requires sign-in; logout clears in-memory token. Explain copied-token validity until expiry and tab-draft persistence; no password-reset promise. | Session state observations, expiry settings, approved recovery exercise reference | NOT VERIFIED |
| P04 / A1,B2,S2 | Suspend/reactivate nonadmin with reason; existing suspended token denied, listings/actions reflect inactive party; no API self/elevated admin suspension. Never strand the only administrator. | Audit action/reason reference and denial/recovery statuses | NOT VERIFIED |
| P05 / B1,B2 | Create/edit/default owned addresses; invalid fields/coordinates denied; B2 cannot list/read/change B1 addresses by identifier. Historical-order delivery fields remain protected; replacement address works. | Owned versus foreign outcomes; no victim mutation | NOT VERIFIED |
| P06 / mobile B1,B2 | Explicit-click geolocation success, denied permission, timeout, unavailable/unsupported, cancellation/navigation. Manual coordinates and own saved-address selection work; no automatic fabricated fallback. No location prompt before click. | Real-device results for every branch; sanitized browser observations | NOT VERIFIED |
| P07 / B1 | Known PIN lists only matching own saved addresses; foreign/unknown PIN returns no invented location. Clearing location removes live results. No precise coordinates in routine telemetry or browser persistence. | UI result and redacted storage/log inspection | NOT VERIFIED |
| P08 / S1,S2,A1 | Create own shop/dispatch profile/products; integer radii 1/2/3 accepted, other/bool/fraction values rejected. Pending products hidden; approval/rejection/reason, edit/resubmit and takedown enforced; S2 cannot edit S1. | Lifecycle/audit references, visibility and ownership denials | NOT VERIFIED |
| P09 / B1,B2 | Live locality discovery search/detail only eligible approved active in-stock candidates, up to implemented page bound; no dispatch coordinates/exact distance. Samples clearly separate; sample radius selector does not claim live filtering. | Live/sample comparison and explicit owner scope acceptance | NOT VERIFIED |
| P10 / B1,S1 | Live detail→cart→saved-address checkout; quantity/server price/stock enforced; seller-separated orders; delivery fee zero/current no-payment disclosure. Exact inside/outside/boundary eligibility checked using synthetic points privately. | Order refs, stock deltas, rejection/accepted outcomes; no coordinates in shared evidence | NOT VERIFIED |
| P11 / B1,S1 | Price/availability change before checkout requires correct refreshed consent; insufficient stock/invalid quantity/foreign address/changed payload denied. Double click and lost-response retry reuse original idempotency key and produce one order/effect. | Order count/stock invariants, retry reference, no duplicate notification effect | NOT VERIFIED |
| P12 / B1,S1 | Owning seller accepts→prepares→dispatches→delivers; buyer confirms. Invalid actor/state transitions denied; cancel/reject in allowed states restores stock once. Cancellation after preparation needs investigation and does not automatically restock. | Transition matrix, stock invariants and completed/terminal state | NOT VERIFIED |
| P13 / B1,B2,S1,S2,A1 | Cross-buyer/seller order list/detail/status/fulfillment denied. Assigned seller receives only allowed name/phone/postal information in eligible accepted-through-delivery/dispute states, no coordinates; access ends on completed/cancelled/rejected. Admin investigation requires reason and audit. | Lifecycle access matrix, redacted fields-present/absent list, audit reference | NOT VERIFIED |
| P14 / B1,S1,A1 | Buyer persists delivery dispute; auto-complete excludes disputed delivery; reasoned admin resolution preserves lifecycle/stock rules. Separately eligible undisputed delivery completes after persisted deadline when worker runs. Legacy completion never labelled buyer confirmation. | Isolated target worker exit/count, deadline/state/audit references | NOT VERIFIED |
| P15 / all | Notifications recipient-only; list/unread/mark-read cannot affect another user's notification. Pagination/empty/loading/error/retry states work. Read is not deletion. | Before/after recipient counts and foreign-object denials | NOT VERIFIED |
| P16 / A1,consenting users | Manual email/phone verification only after genuine out-of-band check; reason and timestamp audit. No OTP/email verification automation, identity/title guarantee or upload implied. | Private check reference and sanitized audit action/time | NOT VERIFIED |
| P17 / A1 | Admin-only users/orders/audit/Operations inaccessible to other roles; missing reason rejected for protected actions. Operations counts match aggregate fixtures, with no recipients/bodies. | Cross-role denial matrix and aggregate reconciliation | NOT VERIFIED |
| P18 / S1,S2,A1 | Property owner/agent profile, category/locality/price listing→pending→moderation→approved; own edit/resubmit/reconfirm/sold and admin hide/reject reason rules. S2 cannot manage S1 property; public view omits exact address. | Listing state/audit/visibility matrix | NOT VERIFIED |
| P19 / B1,B2,S1 | Browse/filter/detail/save/unsave/report property; buyer enquiry and creator reply private to parties; S2/B2 cannot read or reply to B1/S1 conversation. Admin report disposition reason recorded. | Saved state, party denials and report/audit references | NOT VERIFIED |
| P20 / B1,B2,S1,A1 | Request visit→accept/reject/propose alternate→buyer accept alternate/reconfirm/cancel as applicable. Precise location only creator, reasoned admin or confirmed-future eligible buyer. Test pending, alternate, expired appointment, cancelled, suspended actor and unrelated buyer denial. | Appointment transition/access matrix, reasoned admin audit | NOT VERIFIED |
| P21 / B1,S1,A1 | Material property edit suspends confirmation until reconfirmation; sold/takedown cancels active visits/closes enquiries and revokes access. Listing expiry blocks new requests/hides browse but preserves existing confirmed future appointments under current policy. Phone sharing opt-in/off respects participant eligibility. | Private-location/phone revocation matrix and expiry-worker evidence | NOT VERIFIED |
| P22 / S1,S2,A1 | Creative provider profile and category/pricing listing→review→approve/reject/takedown/edit/resubmit; stale approval version denied. Public listings omit private briefs/quotes; S2 cannot change S1 service. | Listing/version/audit outcomes and cross-owner denials | NOT VERIFIED |
| P23 / B1,B2,S1,S2 | Buyer RFQ→own provider response/quote→buyer accepts→engagement scope/price snapshot. Foreign buyer/provider list/read/respond/accept denied; self/invalid/duplicate acceptance follows implemented constraints. | Party authorization and accepted snapshot references | NOT VERIFIED |
| P24 / B1,S1 | Provider marks delivery; only buyer confirms completion; review only after buyer completion, bounded valid review once. Other actors and premature review/completion denied. No upload/payment/refund/cancellation functionality invented. | Engagement/review state and denial matrix | NOT VERIFIED |
| P25 / B1,S1 | Creative enquiry/quote and checkout uncertain-response retries survive same-tab navigation/reload without duplicates. Successful resolution/new request clears appropriate draft; account switches isolate drafts. Shared-device logout warning matches tab retention. | Redacted sessionStorage key-only inspection and entity-count invariants | NOT VERIFIED |
| P26 / B1,B2,A1 | Quotas tested bounded on isolated production-mode staging: auth 20/15min per source and email, discovery 60/hour/account, address 10/day/account, checkout 20/day/account unless approved config differs. 429/Retry-After behavior and recovery; failed business writes still consume applicable durable quota. Distinct users behind proxy do not share an accidental global auth bucket. | Actual budgets, observed codes/retry headers, independent-user recovery; no stress test | NOT VERIFIED |
| P27 / all | API unavailable, DB/storage 503, timeout/offline and validation/conflict failures show safe useful messages; no raw SQL/stack/secret. Loading disables duplicate submits; retry/reload/back navigation preserve correct state. | Per-flow safe error/recovery observations and sanitized server logs | NOT VERIFIED |
| P28 / all mobile | Touch targets, keyboard/focus/labels, error announcement, scroll/no clipping at narrow widths; login/forms/cart/moderation/property appointment/Creative quote/notification work. Date/deadline/timezone displays understandable. | Real-device screenshots redacted, browser/version and human accessibility notes | NOT VERIFIED |
| P29 / A1,consenting mailboxes | Real TLS SMTP enabled scope: trigger generic notification, worker scheduled run, receipt, lease/backoff/FAILED handling in isolated fault tests, missed-run alarm. Readiness/zero exit alone not receipt evidence; bounded duplicate-send window disclosed. Alternatively explicit in-app-only scope/backlog approval before release. | Redacted recipient alias, event ref, worker exit, receipt time, alert acknowledgement | NOT VERIFIED |
| P30 / A1 | HTTPS health/readiness independently checked; wrong-host/origin/proxy spoof denied; docs disabled/restricted; no env/git files; security headers/caching appropriate; backup/restore and incident drill evidence complete. | Deployment/security/monitoring gate references, witness/date | NOT VERIFIED |
| P31 / all,owner | Privacy/terms/refund/cookie/contact navigation and external image/portfolio/WhatsApp disclosures match implementation; support ownership/monitoring, privacy request/retention/eligibility and accepted terms process approved. Do not treat draft pages or manual contact check as compliance certification. | Owner decision record and participant acknowledgement evidence | NOT VERIFIED |

## Execution order and stop rules

Run perimeter/auth/ownership first, then addresses/location, shop/checkout/lifecycle, property, Creative and notifications/admin. Test worker/fault scenarios only on the isolated target. Finish with actual HTTPS/mobile, safe logs/alerts and recovery evidence. Admit the five participants gradually in staffed hours only after staging acceptance and release authorization; do not silently widen scope.

Stop immediately for cross-account data exposure, unauthorized mutation, incorrect price/stock/duplicate checkout, precise-location leak, failed restore, unavailable operator/recovery access, invalid TLS or unknown target. Preserve redacted evidence and gate traffic/writers through the incident procedure. All Critical/High defects block GO. Medium/Low exceptions require named owner acceptance, mitigation, scope and expiry; a missing required device/SMTP/privacy/perimeter check cannot be silently marked PASS.

## Final acceptance record

| Gate | Owner / evidence / date | Current result |
| --- | --- | --- |
| Exact artifact/config, schema and five-person private roster | Pending | NOT VERIFIED |
| All required matrix cases and real mobile HTTPS witnessed | Pending | NOT VERIFIED |
| Security/perimeter/transport, recovery and monitoring gates | Pending | NOT VERIFIED |
| Live discovery scope, mail scope and business/privacy decisions | Pending | NOT VERIFIED |
| Defect/exception register with no open Critical/High | Pending | NOT VERIFIED |
| Release-owner GO and staffed pilot window | Pending | NO-GO |

At pilot end review errors, disputes, quota/backlog trends and feedback; reconcile direct arrangements without claiming payment verification. Record access closure and approved retention/request handling. Five-user acceptance does not approve public launch.
