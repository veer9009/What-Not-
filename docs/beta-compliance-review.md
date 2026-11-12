# What Not? pre-beta compliance and trust review

Review date: **12 November 2026**, Asia/Calcutta. Source-level engineering/privacy/accessibility review for independent repository-owner and legal review. **No deployment, AWS operation, application-database query/migration, commit or push was performed.** Database tests used only the existing harness’s generated localhost PostgreSQL clusters. No real credentials or legal/business facts were added.

## 1. Executive summary

**B. NOT READY — BLOCKERS REMAIN.** Bounded technical fixes, public policy drafts, notices and evidence are available for review. Missing operator/grievance identity, child eligibility, retention/request handling, processor/production evidence and image rights prevent release approval. Passing automated tests does not establish legal compliance or authorise deployment.

The review covered the React route/component/form/state/API surfaces; FastAPI routes, schemas, authentication, dependencies, services/repositories, models, migrations 0001–0008, mail/workers and logging; runtime assets and config examples; and existing unit/persistence/browser tests. Historical reports were cross-checked against implementation; several contain superseded claims about checkout or missing verticals. No secret environment files or real user records were read. This is not an independent production penetration test or exhaustive legal opinion.

## 2. Files changed

| Files | Purpose |
| --- | --- |
| `index.html` | Valid document, English language, viewport, title and no-referrer metadata |
| `src/App.tsx` | Six public legal/contact routes, global footer, keyboard skip link |
| `src/config/business.ts` | Central public contact facts and empty business/grievance fields |
| `src/pages/LegalPages.tsx` | Repository-grounded Privacy, Terms, Cookie, Refund/Cancellation and Contact/Grievance drafts |
| `src/components/LegalNavigation.tsx` | Legal footer and reusable collection notices |
| `src/components/ApiStates.tsx` | Unique field error IDs, visible required indicator |
| `src/components/Shared.tsx` | Clear sample ratings, remove sample verification badge, no-referrer images, pressed-state radius buttons, named nav/main target |
| `src/pages/LoginPages.tsx` | Sign-in/registration notices and main landmark |
| `src/pages/AddressPage.tsx`, `SellerPages.tsx`, `CartPage.tsx` | Address/seller/product/checkout notices and cancellation link; correct stale vertical-availability wording |
| `src/pages/PropertyPages.tsx`, `CreativePages.tsx` | Purpose/audience notices; restore the saved property phone-sharing setting and send only editable fields on withdrawal |
| `src/pages/LandingPage.tsx`, `BuyerPages.tsx` | Image referrer suppression, landing main target, remove sample-detail verification badge |
| `src/styles/index.css` | Remove Google Fonts fetch, targeted footer/WhatsApp contrast, legal typography, focus and reduced-motion handling |
| `src/utils/support.ts` | Reuse central support configuration; preserve encoded order-reference-only message |
| `backend/app/schemas/product.py` | Reject embedded credentials in create/update image URLs |
| `backend/app/services/mappers.py`, `discovery.py` | Safely omit credential-bearing/invalid legacy images from read responses |
| `backend/tests/test_product_schemas.py`, `test_beta_privacy.py` | Six new credential/legacy-response regression cases |
| `src/Compliance.test.tsx` | Eleven new route/notice/keyboard/error/image/trust tests |
| `src/BusinessScope.test.tsx` | Assert corrected availability copy; category restrictions retained |
| `src/pages/CreativePages.test.tsx` | Supply router context for the new real privacy link; all workflow/retry assertions retained |
| `src/pages/PropertyPages.test.tsx` | Regression for accurate saved sharing state, withdrawal and minimal write payload |
| `scripts/beta_browser_smoke.mjs` | Extend existing isolated browser suite with 24 legal/viewport combinations, AX names, tab/Enter and zoom checks |
| `scripts/compliance_contrast.mjs`, `compliance_notices.mjs` | Reproducible targeted contrast and direct-runtime licence evidence |
| `docs/beta-data-flow-inventory.md` | Pre-implementation inventory |
| `docs/beta-third-party-and-forms.md` | Detailed integration and collection-point matrices |
| `docs/COOKIE_CONSENT_DECISION.md` | Storage classification and conditional banner decision |
| `docs/BUSINESS_OWNER_INPUT_REQUIRED.md` | Owner/legal/operational decisions and gates |
| `docs/COPYRIGHT_ASSET_AUDIT.md`, `THIRD_PARTY_NOTICES.txt` | Asset provenance gaps and copied installed dependency notices |
| `docs/beta-contrast-results.json` | Computed source-token contrast evidence |
| `docs/superpowers/plans/2026-11-12-beta-compliance.md`, this report | Scope, work checklist and release review |

No dependency, database model, migration or core marketplace lifecycle was redesigned.

## 3. Data inventory

See [pre-change data flows](beta-data-flow-inventory.md) for DATA → PURPOSE → COLLECTION → STORAGE → ACCESS → SHARING → RETENTION → DISCLOSURE. Categories include accounts/allowlist, shops/dispatch, delivery addresses, transient coordinates, public listings, orders/items, property enquiries/visits/saves/reports, Creative profiles/briefs/quotes/engagements/reviews, notifications/outbox, audit reasons and quota scopes. Schemas use restrictive writes; most retained domain rows have no erasure process. SHA-256 quota scopes are linkable pseudonyms, not anonymous data.

## 4. Data removed/minimised

Removed automatic Google Fonts stylesheet/font requests. Suppressed cross-origin image/page referrers with explicit attributes and document metadata. New image URL submissions cannot publish embedded credentials. Read mappers omit unsafe legacy image values without dropping the listing. No extra personal-data fields, DOB, proof documents, legal identity examples, consent records, analytics or subscriptions were collected. Existing account/contact/location fields remain because removal needs a workflow/schema decision; their retention and necessity are documented rather than assumed.

## 5. Privacy-policy implementation

`/privacy` explains actual account/location/order/property/Creative processing, shared delivery contact, optional property phone sharing, administrators, outbox/SMTP, logging, storage, external hosts and retention limitations. It does not promise erasure or correction endpoints that do not exist. Public listing APIs are disclosed even where UI entry requires login. Missing operator identity, formal grievance/privacy channel, processors, retention and adoption date remain visibly unresolved.

## 6. Terms implementation

`/terms` distinguishes the platform from sellers/owners/agents/providers and preserves seller-managed fulfilment, no platform funds/escrow, sale-only property connection, independent title/legal checks and the quote/accept/deliver/complete/review workflow. It covers accurate accounts, prohibited conduct, moderation, suspension, limited proposed operating permission for UGC, IP reports and statutory-rights preservation. Binding adoption, governing law/forum, eligibility and limitation language require counsel. Existing registration does **not** record terms acceptance; no acceptance history was fabricated.

## 7. Refund/cancellation implementation

`/refunds` describes PLACED/ACCEPTED cancellations, seller rejection of PLACED orders, stock restoration, later investigation and delivered-order disputes. It references the actual displayed auto-completion deadline instead of inventing a refund window. Property visit cancellation is distinct from a property purchase. Creative engagement cancellation/refund is absent. Cancellation does not move money; any direct-payment repayment needs the recipient, parties’ agreement and applicable remedies. No refund amount, deadline, fee or blanket exception was invented.

## 8. Cookie/storage inventory

See [storage decision](COOKIE_CONSENT_DECISION.md). Source sets no application cookies and uses no localStorage. JWT/cart/discovery are memory state. Necessary sessionStorage contains order original requests and Creative brief/quote recovery payloads with scoped retry keys. Successful reconciliation/reset clears entries; uncertain entries can survive logout/reload, and there is no TTL. Closing/restoring/duplicating tabs is browser-dependent. Clearing recovery data before checking history risks duplicate transactions; logout is not erasure.

## 9. Cookie-consent decision

No fake Accept all banner was added: the source has no optional analytics/marketing facility to activate. This does not establish the lawful basis of all personal-data processing or the behaviour of external image hosts. Actual hosting/CDN cookies and optional scripts remain unknown; source-level banner decision must be reassessed against the real deployment before release. No unknown configuration was guessed.

## 10. Analytics/tracking audit

Searched runtime source/index/config for GA, GTM, Meta/Facebook Pixel, Clarity, Hotjar, Mixpanel, Segment, advertising SDKs/pixels, maps, social/video embeds, external scripts/fonts, URLs and storage. None of those analytics/advertising SDKs or embeds was found. Google Fonts import was removed. Arbitrary image URLs can act as request beacons; referrer suppression does not stop IP observation or all browser cookies. A source scan cannot exclude hosting-injected tracking.

## 11. Third-party service inventory

See [service matrix](beta-third-party-and-forms.md): frontend API/hosting/database/backups (actual vendor unknown); SMTP (disabled by default, actual vendor unknown); Unsplash sample imagery; seller-selected image hosts; removed Google Fonts; WhatsApp outbound support; provider portfolio links; browser/OS geolocation. Each row records purpose, data, trigger, essentiality, disclosure/consent implications and keep/remove decision. No geocoder, payment gateway, escrow or private-document upload was found.

## 12. Form/consent audit

The [collection matrix](beta-third-party-and-forms.md) covers registration/login, shops/dispatch, addresses, listings, checkout, orders, property profile/enquiry/reply/visits/report, Creative profile/portfolio/enquiry/quote/review and admin actions. Added contextual notices at collection/workspace entry without meaningless consent checkboxes. Required shared fields identify their requirement; native labels/types/validation remain. Property contact sharing remains unchecked for a new profile; the editor now accurately restores a saved opt-in and lets its owner withdraw it, sending only display name/capacity/sharing fields. Remote/active service defaults are functionality settings. An approved notice/acceptance/withdrawal process is still a legal/business gate.

## 13. Accessibility findings/fixes

Added document language/viewport/title, main landmarks/skip targets, legal heading hierarchy, named legal/workspace navigation, native links and visible focus. Unique React IDs prevent repeated same-name form fields from describing the wrong error. `aria-pressed` exposes radius selection. Reduced-motion preferences disable smooth animation. Existing loading/status and error-alert patterns remain. No dialog was introduced; forms remain inline. Browser AX checks verify policy link/button names, not full screen-reader usability. No axe dependency was installed or claim of WCAG certification made.

## 14. Colour-contrast findings

Targeted sRGB ratios from actual styles: body **14.43:1**, muted on white **6.56:1**, muted on cream **6.23:1**, primary white text **5.29:1**, primary link on cream **5.02:1**, success **5.68:1**, warning **5.54:1**, error **6.45:1**. Small footer text improved **3.90 → 9.29:1**; WhatsApp icon improved **1.98 → 6.51:1**. Focus against white/soft background is **5.29/4.53:1**; footer focus **9.70:1**. Control boundaries improved from **1.49/1.41:1** against white/cream to **4.27/4.05:1**, using a targeted control-border token. All 16 targeted pairs meet their 4.5:1 text or 3:1 control thresholds. See [machine-readable results](beta-contrast-results.json). This does not measure every image overlay, hover/disabled state or all live rendered combinations.

## 15. Keyboard-navigation findings

Native button/link interaction preserved. Added first-stop skip link, main focus target and stronger input/textarea/select focus outline. Real Edge Tab/Enter confirms skipping to the legal main; policies reflow at 320/390/768/1280 and 200% CSS zoom. No focus trap is needed for the current inline forms/navigation. Manual screen-reader traversal, focus restoration after removed inline forms, long dashboard navigation and keyboard checks across every workflow remain review items. SPA-wide route-change focus management is not implemented.

## 16. Alt-text/image findings

All runtime `<img>` occurrences have existing product/title-based alt context; affected external images now suppress referrers. No invented description was generated for user images. Product titles are a fallback, not a reliable description of visual content. Some repeated hero/thumbnail/CTA imagery could be decorative; owner/accessibility review should settle intended information and optional seller-authored descriptions. CSS rings/system emoji need no external image attribution; icon-only controls have names. No property image upload or Creative embed exists.

## 17. Reviews/claims removed or retained with evidence

`mockData.ts` contains six explicitly illustrative sample products with fabricated sellers/prices/distances/ratings. Existing catalogue-wide and per-card Sample labels remain; ratings now explicitly say **Sample rating:** and sample verification icons/badges were removed from cards/detail. These are not real testimonials. No replacement counts/statistics were added. Real seller verification boolean displays were retained as backend-supplied data, with policy warnings that moderation/account checks are not quality/title guarantees; owner must substantiate any verification programme. Creative reviews remain real relationship/state-gated records after buyer-confirmed completion, one per engagement; no public feed exists. Dashboard counts derive from returned data and can be page-bounded, not global statistics. No public #1, complete-security or refund guarantee was found. Stale seller “verticals coming soon” copy was corrected without changing workflow.

## 18. Business-information gaps

See [owner inputs](BUSINESS_OWNER_INPUT_REQUIRED.md). Legal entity, office, required registration/tax disclosures, grievance officer/designation/channel, privacy contact, monitored support, processors, retention rules and governing law/adoption date are absent or unverified. Empty config values render as Not supplied; every policy shows OWNER INPUT REQUIRED BEFORE PUBLIC LAUNCH. The existing WhatsApp phone was preserved from repository evidence, not invented or represented as a designated grievance officer.

## 19. Copyright/IP findings

See [asset audit](COPYRIGHT_ASSET_AUDIT.md). Six Unsplash CDN IDs lack recorded creator/licence/release evidence; ownership cannot be established from CDN URLs. They remain **unknown and release-blocking**, not declared licensed/unlicensed. Fonts are no longer fetched; no unverified binaries were copied. Local direct runtime licences were read and copied to `THIRD_PARTY_NOTICES.txt`; this is not a complete transitive licence opinion. Brand ownership, marketing authorship, UGC authority, client/subject permissions and Creative final-work rights require owner/legal confirmation. Proposed Terms grant only operating/display/moderation permission and do not transfer user copyright.

## 20. Children/minor findings

No established adult-only policy, age collection, age gate or parental-consent infrastructure was found. No DOB/identity check or arbitrary age checkbox was added. Allowlisting alone does not establish adulthood or lawful child-data handling. **Business/legal decision required before admission**, including handling of any pre-existing minor records, appropriate notices and verification. Drafts openly state the gap and do not claim an adult-only restriction is already enforced.

## 21. DPDP-related technical findings

Concrete gaps: operator/purpose notices needed adoption; lawful basis and meaningful consent/withdrawal need confirmation; account correction/export/erasure and retention/processor deletion lack workflows; grievance contact/handling and child eligibility remain unresolved; operational safeguards/incidents/languages/transfers need evidence. Purpose notices, location/contact minimisation, ownership controls, short-lived memory tokens and sanitized errors help technical review but do not close those requirements.

Primary sources checked on the review date: [MeitY DPDP commencement Gazette](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf) stages commencement at publication, one year and eighteen months; the [2025 Rules Gazette](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf) also has phased commencement. Do not assume every provision is already in force on 12 November 2026. Counsel must confirm applicable provisions, publication dates, corrigenda and release-date obligations. [Department of Consumer Affairs rules index](https://consumeraffairs.gov.in/pages/consumer-protection-acts) supplies the e-commerce framework; [PIB’s 10 September 2026 announcement](https://www.pib.gov.in/newsite/erelcontent.aspx?lang=2&reg=48&relid=294532) describes amendments scheduled for 1 January 2027, including grievance transparency, search/sponsorship and seller disclosures. Assess applicability with counsel; these sources are not a legal-compliance conclusion.

## 22. Security/privacy leakage review

API authentication verifies token and active database user/role/admission; front-end hiding is not authority. Retained tested boundaries: owner-only saved addresses; coarse discovery without dispatch coordinates/phone/numeric point distance; scoped seller fulfillment only in eligible states, no coordinates; reasoned/audited admin private reads; property private address only for creator/admin/confirmed future buyer appointment; contact opt-in and state restrictions; participant/admin Creative enquiries/quotes; recipient-owned notifications; no raw SQL/passwords in handled errors. JWT has subject/time, not profile data; API no-store and credential-omitting fetch remain.

Fixed image credential publication in write validation and safe read projection, including legacy rows. No real records were inspected or rewritten. Remaining risks: arbitrary external image requests/HTTP URLs, optional SMTP settings and transport, uninspected hosting/access logs/backups, persistent personal free text, unsalted quota hashes, no pruning/erasure process, previously disclosed recipient copies and pending drafts on a shared tab. No schema migration or blanket change to recipient/state access was made.

## 23. Tests added

Twelve frontend cases: six direct unauthenticated routes/no protected fetch; registration notice/legal link/no fake consent; distinct repeated-field error association; sample trust/referrer attributes; authenticated policy availability; first keyboard skip stop; saved phone-sharing preference/withdrawal with only editable fields sent. Four backend schema cases reject username/password or username-only image credentials on create/update; two mapper/discovery cases ensure unsafe legacy rows omit the image without breaking listing reads. Existing browser harness now checks 24 policy/viewport combinations, AX control names, no storage on legal routes, keyboard Tab/Enter and 200% zoom, real property sharing opt-in/withdrawal persistence, then all original workflows.

Tests were run red before fixes: initial compliance file 10 failures; later skip test failed with the other 10 passing; image schema 4 failures with 47 passing; legacy response 2 failures with 2 passing; property sharing test failed because saved opt-in appeared unchecked, and a stricter payload assertion then caught server fields being sent by the first preload implementation. The final preload explicitly selects three editable fields. Final evidence below supersedes interim failures without hiding them.

## 24. Exact test commands

From repository root (logs are ignored local evidence):

```powershell
node node_modules/vitest/vitest.mjs run --pool=vmThreads --maxWorkers=1
npm.cmd run build
node scripts/compliance_contrast.mjs
node scripts/compliance_notices.mjs
git diff --check
```

From `backend`:

```powershell
$env:PATH = 'C:\Program Files\PostgreSQL\17\bin;' + $env:PATH
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -m pytest -q -s ../scripts/beta_browser_smoke.py
.\.venv\Scripts\python.exe -m pytest tests/test_beta_privacy.py tests/test_product_schemas.py -q
.\.venv\Scripts\python.exe -m compileall -q app alembic tests
.\.venv\Scripts\python.exe -m pip check
```

Full commands redirected `*>` to `audit-compliance-*.log` and propagated `$LASTEXITCODE`. PostgreSQL runs required sandbox escalation because the Windows restricted token prevented pg_ctl startup; the unmodified harness verifies its generated data directory and never consumes application DB settings. Migrations execute only inside disposable tests.

## 25. Exact test results

| Verification | Observed result |
| --- | --- |
| Initial backend sandbox baseline | 275 passed, 373 setup errors; pg_ctl restricted-token error 87; 60.23 s; no assertion failures claimed as passes |
| Same full baseline outside startup restriction | 648 passed, 214.02 s |
| Initial frontend baseline | 225 passed, 2 existing App auth-flow tests timed out at 5 s during concurrent baseline execution; 131.53 s |
| Interim compliance run | 9 passed, 1 failed due to test observing a node replaced by `/auth/me`; changed assertion to wait for live node |
| Interim frontend full run | 231 passed, 7 Creative component tests failed because their mocked shell removed Router context required by the new real privacy link; supplied MemoryRouter without weakening assertions |
| Final complete frontend suite | **239 passed, 28 files, 133.88 s**, exit 0 after the sharing fix and stricter minimal-payload regression; earlier border-adjusted suite 238 passed in 133.45 s |
| Targeted final image/legacy regressions | **55 passed, 0.34 s**, exit 0 |
| Full backend after final review fix | **654 passed, 128.34 s**, exit 0 |
| Existing real Edge/browser integration with legal additions | **1 passed, 60.50 s** initially; **1 passed, 68.37 s** after legacy-read fix; **1 passed, 113.95 s** after fixing the harness race; final phone-sharing build rerun recorded below |
| Browser rerun after border fix | Failed in **92.66 s** after legal checks passed: buyer fetched OUT_FOR_DELIVERY before the seller’s Mark delivered request committed. Harness now waits for authoritative seller Delivered status before navigating buyer and asserts scoped order status, rather than matching the tracking list’s ever-present Completed label. No timeout increase or workflow assertion removal |
| First final phone-sharing browser run | `test_real_edge_beta_workflows` failed in **60.50 s**, before the legal PASS marker, with only `Error: Uncaught`. Its previous evaluator discarded exception detail. Added exception-description diagnostics, a null-safe body-text wait and explicit completed-document/path/main readiness before direct-route checks. The original exception’s exact cause is unconfirmed; no product change was inferred from it |
| Final real Edge/browser integration, final build and sharing withdrawal | **1 passed, 64.51 s**, exit 0. All seven PASS stages include the 24 legal/viewport combinations, AX names/storage/keyboard/zoom, order privacy/lifecycle, persisted phone-sharing opt-in/withdrawal, property privacy/sold revocation, Creative workflow, discovery and checkout |
| Contrast | **16 targeted pairs passed**, exit 0; control-boundary additions first failed at 1.49/1.41:1 before CSS fix |
| Python compile / pip | Passed / No broken requirements found after legacy-read fix, exit 0 |
| Whitespace | `git diff --check` passed; only Git LF/CRLF conversion notices |

Baseline timeouts were reported, not removed or hidden. No timeout increase, disabled/deleted test or weakened authorisation assertion was used; final full suites include every test. A focused `-t` property regression run selected one test while other cases were temporarily filtered; they remain in the final full suite. One interim build caught an overly narrow OWNER-only type in the new test fixture; it was corrected to the existing PropertyProfile type. Logs all start with `audit-compliance-`; final evidence is in `backend-final.log`, `frontend-verified-final.log`, `build-final.log`, `browser-final-readiness.log`, plus earlier baseline/red/green logs. `browser-verified-final.log` retains the uninformative failed browser run. These are ignored local evidence, not tracked credentials or production records.

## 26. Production-build result

`npm.cmd run build` passed TypeScript project build plus Vite (9.61 s). Final frontend bundle: `index-D8ybDL06.js` **425.86 kB**, gzip **127.25 kB**; CSS `index-m-UgB1_1.css` **37.89 kB**, gzip **8.43 kB**; HTML **0.47 kB**. Build is local only. Direct-route rewrites were tested in the isolated SPA-serving harness; actual production hosting remains owner verification.

## 27. Regression findings and principal-engineer review

Reviewed final code diff, new policy/config files, test changes and report claims against data flows and actual state transitions.

| Severity | Finding / disposition |
| --- | --- |
| CRITICAL | No new unresolved critical code issue identified in reviewed changes; this is bounded review, not proof of absence |
| IMPORTANT — fixed | Credential-bearing product images could expose secrets. Four failing schema regressions, validation fix, green tests |
| IMPORTANT — fixed during review | New validation could make legacy listing reads fail. Two failing response/discovery regressions; safe image projection omits unsafe URL, retains listing; 55 targeted and 654 full backend tests pass |
| IMPORTANT — fixed during verification | Browser script navigated buyer before seller mutation commit; captured stale OUT_FOR_DELIVERY state. Added authoritative status wait and scoped completion/dispute assertion; final rerun recorded below |
| IMPORTANT — fixed during review | Property editor hid saved phone-sharing opt-in by initialising an empty profile. Failing regression; preload only three editable fields and verify withdrawal persistence. Final unit/browser evidence below |
| IMPORTANT — fixed during review | Faint control boundaries failed 3:1. Added failing stylesheet-driven checks, then targeted input/select/textarea/outlined-button/search borders; final contrast check passes |
| IMPORTANT — unresolved release gates | Identity/grievance/age/retention/processor/asset-rights gaps in sections 29–32; cannot be fixed by invented content or generic consent |
| MINOR | Manual AT/focus/alt-image decisions, partial custom error association, a default five-star Creative review choice, some historical/stale copy/reports and page-bounded metrics remain |
| INFORMATIONAL | Font rendering now uses native fallback; no redesign/new dependency. Recovery storage intentionally persists uncertain requests. Property expiry alone retains confirmed future visit access by existing tested rule |

Original browser assertions passed Homemade discovery/cart/checkout/fulfillment/progression/completion/dispute; buyer/seller outsider denial; property enquiry/reply/confirmed visit/private-address gate/sold revocation; Creative RFQ/quote/acceptance/delivery/buyer completion/review; admin resolution and notifications. Full backend tests cover moderation, authentication/authorisation, concurrency, workers and migration reversibility in disposable databases. Passing these does not verify production workers, monitoring or support staffing.

## 28. Remaining limitations

No production/network-header/vendor/log/backup inspection, application-data audit, live SMTP send, independent pen test, full accessibility scanner/manual screen-reader pass, legal translation or comprehensive transitive dependency vulnerability/licence audit. New browser checks are narrow AX/name/keyboard/reflow checks, not axe or WCAG certification; zoom uses CSS `zoom`. Source images remain external and ownership unproven. Existing unsupported profile erasure/correction and Creative cancellation were not redesigned. Policy drafts do not create operational handling or user acceptance.

## 29. Owner input required

Supply and substantiate the [owner-input checklist](BUSINESS_OWNER_INPUT_REQUIRED.md): actual operator/office/registration, support ownership, named grievance/privacy contacts/process, age policy, per-category retention/request/deletion plan, processors/locations/contracts, asset rights or approved replacements, vertical-specific responsibilities, remedies, legal adoption, security/accessibility/deployment evidence and staffed escalation. Review final diff and approve the controlled test population independently. No owner decision was inferred from an empty field.

## 30. Lawyer/legal-review items

Confirm release-date DPDP commencement/applicability and notices/processing grounds/withdrawal/rights/language/children/safeguards/transfers. Review e-commerce duties and upcoming amendments, real seller/platform disclosures and grievance timing/process; direct-payment remedies and cancellation rules; food admission/FSSAI-related duties before enabling food; owner/agent/RERA-related sale-listing obligations; Creative scope/copyright/portfolio permissions; operator identity/registration/tax disclosures, UGC operating permission, policy adoption/acceptance, limitation and law/forum. These are questions for qualified review, not findings that a specific registration or legal exemption applies.

## 31. Beta blockers

1. No verified operator identity or staffed formal grievance/privacy/request-handling mechanism.
2. Unresolved child eligibility/admission policy; allowlist is insufficient evidence.
3. No approved retention, correction/deletion/withdrawal or end-of-beta cleanup procedure, including processors/backups/audit/outbox/quota records.
4. External image rights and external-host privacy/security policy unresolved for visible assets.
5. Actual hosting/SMTP/processors, security/logging/storage/network configuration and support ownership unverified.
6. Draft policies/business/consumer/vertical responsibilities need owner/counsel adoption and independent release review.

These implement the request’s stop conditions: decisions were flagged rather than guessed. No deployment recommendation is issued.

## 32. Public-launch blockers

All beta blockers, plus production operational evidence, appropriate seller/provider/property disclosures and consumer-remedy processes, applicable upcoming rules, supported notice language/accessibility review, incident/rights/complaint operations, content/IP provenance and takedown handling, monitored delivery workers and a separately approved rollout. Food commerce remains outside the live supported category set until its own approved process exists. Remove visible draft gaps only after facts and operations are verified, not by hiding warnings.

## 33. Final release classification

**B. NOT READY — BLOCKERS REMAIN**

Source fixes and passing verification can support independent review. This review does not certify legal compliance or authorise deployment; the repository owner retains the final decision after independent business/legal/security/accessibility review.
