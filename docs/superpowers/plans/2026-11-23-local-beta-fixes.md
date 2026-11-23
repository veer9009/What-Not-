# Local beta fixes implementation plan

> **For agentic workers:** Use test-driven development for each focused change. Work in the existing checkout and preserve all prior changes. No commits or migration execution.

**Goal:** Complete seller-level location setup once, explain discovery readiness, align image proxy limits, and isolate frontend session tests.

**Architecture:** Reuse SellerProfile coordinates, confirmation and consent fields and existing seller APIs. Keep private dispatch separate from an explicitly consented public point. No schema changes. Test transport changes stay in test code.

**Spec:** User-provided LOCAL BETA FIXES: TASK A + B + C attachment, November 23, 2026.

## Constraints

- Local application/tests/templates/documentation only; no AWS, EC2, live endpoints, production secrets or data.
- Preserve product approval, stock, active-account, geography, consent and checkout checks.
- Preserve existing artwork and City/Town/Village theme; no seller approval policy changes.
- Never execute migrations or connect database-backed test fixtures that read existing credentials.

## Tasks

1. Add failing seller service tests for changed dispatch clearing public consent and same-point/profile-only updates preserving it. Fix the two existing seller mutation paths. Verify reuse and discovery exclusion with real services and in-memory test doubles.
2. Add failing UI tests for one-save onboarding, explicit dispatch/public consent, incomplete dashboard guidance, returning product creation without location prompts, partial-save retry and renewed consent after edits. Reuse existing APIs, keep technical coordinates in an expandable fallback, retain separate public-point management, and explain buyer-radius/checkout limits without claiming approval alone establishes visibility.
3. Add failing proxy-template tests. Scope 5 MiB to the existing raw image upload/replacement URI patterns; retain 256 KiB elsewhere and all access, proxy and rate controls. Inspect URL/storage/rendering without changing behavior that already works.
4. Add failing BroadcastChannel isolation tests, then install deterministic per-file in-memory transport before application imports. Preserve module-level application listeners, reset per-case peers/pending deliveries, and test actual API cross-tab logout without changing production transport.
5. Run focused backend tests without database fixtures, frontend location/auth/session/API/image/seller tests, TypeScript and production build. Run broader frontend coverage if feasible. Request independent read-only review; address confirmed findings and rerun affected checks.

## Review focus

- Partial onboarding failure must not create a duplicate shop or claim discovery is enabled.
- Consent must be explicit for the selected point and cleared when the draft/dispatch changes.
- Private dispatch coordinates must never enter buyer responses or be copied publicly without opt-in.
- Image regex locations must inherit proxy headers and preserve quotas/security headers.
- Test resets must not remove the application's module-level channel listener or disable cross-tab coverage.

## Deployment follow-up

Document the existing seller-verification policy gap without adding a new gate. EC2/Nginx syntax, real storage/origin, actual uploads/image HTTP results, deployed migration revision and browser discovery/responsive checks require separately authorized operator verification.
