# Buyer address GPS and cart layout

Implement the user's specified UX in the existing React application. Reuse `acquireLocation` and coordinate validation; retain the existing address API and checkout state machine. No map or reverse geocoder is present or needed. Keep the changes in the existing working tree and preserve unrelated changes; no commits or migrations.

1. Add failing address tests for click-only GPS, success/error states, manual fallback/ranges, unsaved drafts, postal validation, cancellation/stale results and edit patch behavior.
2. Add address GPS detection with abort/unmount protection. Put manual coordinates in Advanced location details; retain postal fields, explicit save and privacy text. GPS failure preserves the existing draft.
3. Scope cart styles to a checkout workspace. Use a flexible list and 350px desktop summary, stack below 1100px, wrap product details and give quantity buttons touch space. Separate totals rows from other summary content. Keep checkout handlers/conditions unchanged.
4. Export real React address/cart markup with synthetic data for network-blocked Chrome geometry. Check summary width/position, field containment, disclosure state, mobile stacking and document/component overflow at 1440, 1280, 1024, 768, 390 and 320px.
5. Run new tests, existing address/discovery/checkout/privacy tests, full frontend tests and production build. Backend is unchanged; do not run persistence tests that migrate databases. Report results and physical GPS/browser checks still required.
