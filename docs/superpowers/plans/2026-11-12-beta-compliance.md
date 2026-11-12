# Beta compliance review implementation plan

Goal: deliver the requested source audit, bounded fixes, truthful policy drafts, tests and release blockers for independent review.

Architecture: preserve React Router/FastAPI marketplace contracts. Centralise substantiated contact facts and explicit missing-value labels. Public legal routes and global footer use existing design tokens. No database schema changes, deployment, AWS, application DB access, commits or pushes.

Spec: the user's 20-step pre-beta compliance/trust-gate request; pre-change inventory in `docs/beta-data-flow-inventory.md`.

Review focus: logged-out direct policy access; accurate terminal-state contact boundaries; failed-request recovery without duplicate purchases; no invented legal identity/age/refund promises; keyboard/mobile access and verified contrast.

- [x] Inspect route/component/API/model/migration/service/test surfaces and record data flows before product edits.
- [x] Add regression tests for legal routes/navigation and clear owner-input markers; shared-field accessible error associations; external-image disclosure/referrer control; truthful sample trust signals.
- [x] Add `src/config/business.ts`, `src/pages/LegalPages.tsx`, shared collection notice/footer, document semantics, unique field errors and targeted contrast fixes. Preserve the existing support phone as an unverified repository-supplied contact; never promote it to a grievance officer.
- [x] Test any concrete API minimisation changes before fixing them; preserve server authorisation and order/visit semantics.
- [x] Document cookie decision, third parties, forms, copyright provenance uncertainty, business/legal decisions and all 33 required final-report sections.
- [x] Run full frontend/backend suites, production build and existing isolated real-browser flows plus legal/mobile/keyboard checks; inspect final diff and record precise results/limitations.

Stop on unresolved business/legal/asset decisions: record blockers, retain visibly incomplete policy drafts, do not fabricate a decision or classify ready. The user has already authorised implementation/testing; execute inline in the existing clean workspace without committing.

Review ledger: rejected credential-bearing image writes, then added safe legacy-read projection after reproducing two read failures. All six backend regressions were red before fixing. Repeated-field error IDs, public legal routes, notices and skip target were tested red first. Contrast failures in footer/icon and then control borders were reproduced with the stylesheet-driven script. No owner/legal choice was guessed; classification remains B. Test evidence and remaining decisions live in `docs/beta-compliance-review.md`.

Final review also reproduced the misleading saved phone-sharing control. The editor now restores saved state using only editable fields, with a strict withdrawal-payload regression and real-browser persistence assertions. The browser harness now waits for authoritative seller delivery state before the buyer read and scopes completion assertions to order status, fixing a captured test race without longer timeouts or weaker assertions.
