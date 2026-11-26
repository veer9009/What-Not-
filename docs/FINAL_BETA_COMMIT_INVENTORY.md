# Final beta source inventory — shopping completion, UI polish and client discovery

Reviewed candidate: 186 files; approved code-backup selection: 183 files. Preserved payment milestone `a57f5e067611660bcb9000241b8ef5a992bae86f`. The verification snapshot preceded staging/commit/push. The user subsequently authorized a separate GitHub backup branch; merge and deployment remain unauthorized.

## Candidate files

| State | File |
| --- | --- |
| Modified | `backend/app/api/routes/creative.py` |
| Modified | `backend/app/api/routes/orders.py` |
| Modified | `backend/app/api/routes/payments.py` |
| Modified | `backend/app/api/routes/properties.py` |
| Modified | `backend/app/core/config.py` |
| Modified | `backend/app/db/schema.py` |
| Modified | `backend/app/main.py` |
| Modified | `backend/app/models/__init__.py` |
| Modified | `backend/app/models/creative.py` |
| Modified | `backend/app/models/payment.py` |
| Modified | `backend/app/schemas/creative.py` |
| Modified | `backend/app/schemas/discovery.py` |
| Modified | `backend/app/schemas/order.py` |
| Modified | `backend/app/services/creative.py` |
| Modified | `backend/app/services/discovery.py` |
| Modified | `backend/app/services/mappers.py` |
| Modified | `backend/app/services/orders.py` |
| Modified | `backend/app/services/payments.py` |
| Modified | `backend/persistence_schema_runner.py` |
| Modified | `backend/tests/persistence/test_beta_resume.py` |
| Modified | `backend/tests/persistence/test_creative.py` |
| Modified | `backend/tests/persistence/test_creative_migration.py` |
| Modified | `backend/tests/persistence/test_order_creation.py` |
| Modified | `backend/tests/persistence/test_order_geography.py` |
| Modified | `backend/tests/persistence/test_payment_concurrency.py` |
| Modified | `backend/tests/persistence/test_payments.py` |
| Modified | `backend/tests/session_integration/test_refresh_migration_chain.py` |
| Modified | `backend/tests/test_admin_bootstrap.py` |
| Modified | `backend/tests/test_creative_schemas.py` |
| Modified | `backend/tests/test_public_discovery.py` |
| Modified | `backend/tests/test_recovery_migration.py` |
| Modified | `package.json` |
| Modified | `pnpm-lock.yaml` |
| Modified | `scripts/buyer-layout.test.tsx` |
| Modified | `scripts/discovery-layout.test.tsx` |
| Modified | `scripts/sage-layout.test.tsx` |
| Modified | `src/App.test.tsx` |
| Modified | `src/App.tsx` |
| Modified | `src/BetaFlows.test.tsx` |
| Modified | `src/BetaResume.test.tsx` |
| Modified | `src/BusinessScope.test.tsx` |
| Modified | `src/Checkout.test.tsx` |
| Modified | `src/DeliverySupport.test.tsx` |
| Modified | `src/LocationDiscovery.test.tsx` |
| Modified | `src/Marketplace.test.tsx` |
| Modified | `src/PaymentRoutes.test.tsx` |
| Modified | `src/api/client.test.ts` |
| Modified | `src/api/client.ts` |
| Modified | `src/api/creative.test.ts` |
| Modified | `src/api/creative.ts` |
| Modified | `src/api/discovery.ts` |
| Modified | `src/api/payments.ts` |
| Modified | `src/api/properties.ts` |
| Modified | `src/api/types.ts` |
| Modified | `src/components/DispatchLocation.test.tsx` |
| Modified | `src/components/DispatchLocation.tsx` |
| Modified | `src/components/ExploreVerticals.tsx` |
| Modified | `src/components/LocationPicker.test.tsx` |
| Modified | `src/components/LocationPicker.tsx` |
| Modified | `src/components/MobileNavigation.test.tsx` |
| Modified | `src/components/MobileNavigation.tsx` |
| Modified | `src/components/PublicDiscoveryLocation.test.tsx` |
| Modified | `src/components/Shared.tsx` |
| Modified | `src/components/ShopProfileForm.tsx` |
| Modified | `src/components/Sidebar.test.tsx` |
| Modified | `src/location/geolocation.test.ts` |
| Modified | `src/location/geolocation.ts` |
| Modified | `src/pages/AddressLocation.test.tsx` |
| Modified | `src/pages/AddressPage.tsx` |
| Modified | `src/pages/AdminOperations.test.tsx` |
| Modified | `src/pages/AdminOperations.tsx` |
| Modified | `src/pages/CartPage.tsx` |
| Modified | `src/pages/CreativePages.test.tsx` |
| Modified | `src/pages/CreativePages.tsx` |
| Modified | `src/pages/DiscoveryPages.tsx` |
| Modified | `src/pages/LandingPage.test.tsx` |
| Modified | `src/pages/LandingPage.tsx` |
| Modified | `src/pages/LegalPages.tsx` |
| Modified | `src/pages/NotificationsPage.tsx` |
| Modified | `src/pages/OrderNavigation.test.tsx` |
| Modified | `src/pages/OrderPages.tsx` |
| Modified | `src/pages/PaymentsPage.test.tsx` |
| Modified | `src/pages/PaymentsPage.tsx` |
| Modified | `src/pages/SellerPayments.test.tsx` |
| Modified | `src/pages/SellerPayments.tsx` |
| Modified | `src/pages/SellerProfileLocation.test.tsx` |
| Modified | `src/pages/SellerReadiness.test.tsx` |
| Modified | `src/styles/homepage.css` |
| Modified | `src/styles/index.css` |
| New | `backend/alembic/versions/0014_service_domains.py` |
| New | `backend/alembic/versions/0015_shopping_completion.py` |
| New | `backend/app/api/routes/checkout.py` |
| New | `backend/app/api/routes/wishlist.py` |
| New | `backend/app/models/shopping.py` |
| New | `backend/app/schemas/checkout.py` |
| New | `backend/app/services/checkout.py` |
| New | `backend/app/services/payment_settings.py` |
| New | `backend/app/services/wishlist.py` |
| New | `backend/tests/persistence/test_client_discovery_search.py` |
| New | `backend/tests/persistence/test_final_shopping.py` |
| New | `backend/tests/persistence/test_final_shopping_concurrency.py` |
| New | `backend/tests/persistence/test_final_shopping_migration.py` |
| New | `backend/tests/test_final_shopping_contract.py` |
| New | `docs/CLIENT_DISCOVERY_RULES.md` |
| New | `docs/FINAL_BETA_COMMIT_INVENTORY.md` |
| New | `docs/FINAL_BETA_RELEASE_REPORT.md` |
| New | `docs/PROPOSED_REFUND_POLICY.md` |
| New | `src/api/checkout.test.ts` |
| New | `src/api/checkout.ts` |
| New | `src/api/homeListings.test.ts` |
| New | `src/api/homeListings.ts` |
| New | `src/api/paymentSettings.ts` |
| New | `src/api/wishlist.test.ts` |
| New | `src/api/wishlist.ts` |
| New | `src/assets/categories/creative-256.png` |
| New | `src/assets/categories/creative.png` |
| New | `src/assets/categories/homemade-256.png` |
| New | `src/assets/categories/homemade.png` |
| New | `src/assets/categories/professional-256.png` |
| New | `src/assets/categories/professional.png` |
| New | `src/assets/categories/real-estate-256.png` |
| New | `src/assets/categories/real-estate.png` |
| New | `src/assets/service-categories/advertisement-production-256.png` |
| New | `src/assets/service-categories/ai-and-automation-256.png` |
| New | `src/assets/service-categories/animation-and-vfx-256.png` |
| New | `src/assets/service-categories/api-development-and-integration-256.png` |
| New | `src/assets/service-categories/audit-icons.mjs` |
| New | `src/assets/service-categories/audit-icons.ps1` |
| New | `src/assets/service-categories/cloud-and-devops-256.png` |
| New | `src/assets/service-categories/crm-and-erp-solutions-256.png` |
| New | `src/assets/service-categories/custom-software-development-256.png` |
| New | `src/assets/service-categories/cybersecurity-services-256.png` |
| New | `src/assets/service-categories/digital-marketing-256.png` |
| New | `src/assets/service-categories/e-commerce-development-256.png` |
| New | `src/assets/service-categories/export-icons.ps1` |
| New | `src/assets/service-categories/fashion-design-256.png` |
| New | `src/assets/service-categories/graphic-design-256.png` |
| New | `src/assets/service-categories/influencer-reel-editing-256.png` |
| New | `src/assets/service-categories/it-consulting-256.png` |
| New | `src/assets/service-categories/logo-and-branding-design-256.png` |
| New | `src/assets/service-categories/mobile-application-development-256.png` |
| Excluded audit output | `src/assets/service-categories/originals/audit-white-128.png` |
| Excluded audit output | `src/assets/service-categories/originals/audit-white-64.png` |
| New | `src/assets/service-categories/originals/creative-sheet-original.png` |
| New | `src/assets/service-categories/originals/creative-sheet-transparent.png` |
| Excluded audit output | `src/assets/service-categories/originals/photography-white-audit.png` |
| New | `src/assets/service-categories/originals/professional-sheet-original.png` |
| New | `src/assets/service-categories/originals/professional-sheet-transparent.png` |
| New | `src/assets/service-categories/photography-256.png` |
| New | `src/assets/service-categories/portfolio-development-256.png` |
| New | `src/assets/service-categories/promotional-video-production-256.png` |
| New | `src/assets/service-categories/software-maintenance-256.png` |
| New | `src/assets/service-categories/travel-video-editing-256.png` |
| New | `src/assets/service-categories/vfx-256.png` |
| New | `src/assets/service-categories/video-editing-256.png` |
| New | `src/assets/service-categories/videography-256.png` |
| New | `src/assets/service-categories/website-development-256.png` |
| New | `src/components/NotificationBell.tsx` |
| New | `src/components/OrderPaymentPanel.test.tsx` |
| New | `src/components/OrderPaymentPanel.tsx` |
| New | `src/components/PublicSidebarServices.test.tsx` |
| New | `src/components/WishlistButton.tsx` |
| New | `src/pages/AdminDomainEntry.test.tsx` |
| New | `src/pages/CheckoutPage.css` |
| New | `src/pages/CheckoutPage.test.tsx` |
| New | `src/pages/CheckoutPage.tsx` |
| New | `src/pages/DiscoveryPages.pagination.test.tsx` |
| New | `src/pages/MarketplaceHome.test.tsx` |
| New | `src/pages/MarketplaceHome.tsx` |
| New | `src/pages/NotificationsPage.test.tsx` |
| New | `src/pages/OrderExperience.test.tsx` |
| New | `src/pages/PaymentSettingsPages.test.tsx` |
| New | `src/pages/PaymentSettingsPages.tsx` |
| New | `src/pages/ServiceCatalog.css` |
| New | `src/pages/ServiceCatalog.test.tsx` |
| New | `src/pages/ServiceCatalog.tsx` |
| New | `src/pages/ServiceStartup.test.tsx` |
| New | `src/pages/WishlistPage.test.tsx` |
| New | `src/pages/WishlistPage.tsx` |
| New | `src/state/WishlistContext.tsx` |
| New | `src/state/checkoutBatchRecovery.test.ts` |
| New | `src/state/checkoutBatchRecovery.ts` |
| New | `src/state/notificationEvents.ts` |
| New | `src/styles/marketplace-home.css` |
| New | `src/styles/mobile-navigation-polish.css` |
| New | `src/styles/shopping-completion.css` |

## Preserved inherited exclusions

These eleven pre-existing untracked files remain byte-identical and are excluded from the proposed source candidate.

- `docs/LOCATION_UX_PROPOSAL.md`
- `docs/PROFESSIONAL_UX_REPORT.md`
- `docs/SELLER_PAYMENTS_CORRECTION_REPORT.md`
- `docs/UX_PAYMENTS_REPORT.md`
- `docs/superpowers/plans/2026-11-24-cod-upi-completion.md`
- `docs/superpowers/plans/2026-11-24-professional-ux.md`
- `docs/superpowers/plans/2026-11-24-seller-payments-correction.md`
- `docs/superpowers/plans/2026-11-24-ux-payments.md`
- `docs/superpowers/plans/2026-11-24-ux-step1.md`
- `docs/superpowers/specs/2026-11-24-professional-ux-design.md`
- `scripts/verify_ux_step1.mjs`

## Local verification artifacts

Ignored `.superpowers/` logs, database/schema fixtures, private credentials, screenshots under `docs/security/evidence/`, generated dist/node_modules and ignored npm lock are excluded. The canonical dependency lock is pnpm-lock.yaml. Migration0015 is additive; no existing payment record is rewritten. Review every source change before any separately approved integration.

Preservation/secret-pattern evidence: `.superpowers/client-discovery/candidate-preservation.json`. Pattern checks are supplementary and do not establish absence of all secrets.

## Authorized code-preservation backup — 26 November 2026

Branch: `release/beta-2026-11-26`. All 186 candidates were reviewed; 183 are selected. Three generated audit PNGs above are excluded as temporary verification output and remain locally intact. All 25 runtime icons, original source sheets, export/audit tooling and implemented application/test work remain selected. The eleven inherited exclusions remain unchanged and untracked. Secrets, credentials, environment files, dumps, private verification artifacts and ignored build/dependency output are excluded.

Read-only GitHub checks found no Actions workflows, repository webhooks, deployment environments, or Jenkins/Actions configuration on the remote default branch. No active local Git hooks were present. This is a code backup only; it does not approve production release, migration, merge, Jenkins or EC2 deployment. Complete regression suites are not repeated: the unchanged implementation already passed 602 frontend tests and 1,074 backend tests. Only backup documentation is updated. Original database0010 and disabled prepaid UPI are unchanged.

Use the branch commit and `git show --stat HEAD` for immutable backup identity. Local preservation/selection evidence is retained under ignored `.superpowers/client-discovery/backup-*.json`.
