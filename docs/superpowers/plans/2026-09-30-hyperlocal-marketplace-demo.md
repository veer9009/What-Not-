# Hyperlocal Marketplace Frontend Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, responsive React frontend demo that communicates hyperlocal product discovery across buyer, seller, and admin roles.

**Architecture:** A Vite React application uses React Router for page navigation and a typed context store for products, cart items, and moderation actions. Feature-focused page and component modules consume centralized mock data; CSS provides the responsive visual system and map-free radius illustration.

**Tech Stack:** React, Vite, TypeScript, React Router, Lucide React, Vitest, Testing Library, CSS

**Spec:** `docs/superpowers/specs/2026-09-30-hyperlocal-marketplace-demo-design.md`

## Global Constraints

- Frontend demo only: no backend, database, real authentication, payment gateway, geolocation, or map API.
- Use React, Vite, and TypeScript with reusable components and separate mock data.
- Use handmade/local products; do not use grocery products.
- Required selling-radius values are exactly 1 KM, 2 KM, and 3 KM.
- WhatsApp contact uses `+91 80800 98882` and the exact approved pre-filled message.
- Deliver a mobile-first, desktop-compatible, professional interface with accessible controls and restrained motion.

## Review Focus

- Empty search/filter results show a resettable empty state rather than a broken grid.
- An out-of-area product is labeled and cannot be added or bought.
- Invalid or blank login and product-form input shows inline validation without navigation or state mutation.
- Seller deletion and admin moderation update all dependent views consistently.
- Missing product IDs show a useful not-found state with a working return route.

---

### Task 1: Application Foundation and Typed Demo Domain

**Files:**
- Create: `package.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.app.json`, `index.html`
- Create: `src/main.tsx`, `src/App.tsx`, `src/types.ts`, `src/data/mockData.ts`
- Create: `src/state/DemoContext.tsx`, `src/state/demoReducer.ts`, `src/state/demoReducer.test.ts`

**Interfaces:**
- Produces: `Product`, `CartItem`, `ProductStatus`, `DemoState`, `DemoAction`, `useDemo()` and a reducer supporting add/edit/delete/moderate product and cart operations.

- [ ] Write reducer tests for cart quantity bounds, seller CRUD, and approve/reject transitions.
- [ ] Run `npm test -- --run src/state/demoReducer.test.ts` and verify the new suite initially fails.
- [ ] Scaffold Vite configuration, typed models, handmade-product mock data, router shell, and the context reducer.
- [ ] Run the reducer suite and verify it passes.

### Task 2: Visual System and Shared Application Components

**Files:**
- Create: `src/styles/index.css`
- Create: `src/components/PublicHeader.tsx`, `src/components/DashboardLayout.tsx`
- Create: `src/components/ProductCard.tsx`, `src/components/StatusBadge.tsx`
- Create: `src/components/RadiusSelector.tsx`, `src/components/RadiusVisual.tsx`
- Create: `src/components/EmptyState.tsx`, `src/components/WhatsAppButton.tsx`, `src/components/Toast.tsx`
- Test: `src/components/shared.test.tsx`

**Interfaces:**
- Consumes: `Product` and route configuration from Task 1.
- Produces: reusable marketplace navigation, dashboard layout, product display, radius controls, feedback, and WhatsApp link components.

- [ ] Write component tests for radius selection, product metadata, and the exact encoded WhatsApp destination.
- [ ] Run `npm test -- --run src/components/shared.test.tsx` and verify failure.
- [ ] Implement design tokens, typography, layout primitives, accessibility states, responsive breakpoints, and shared components.
- [ ] Run shared-component tests and verify they pass.

### Task 3: Public Landing and Role Login Flows

**Files:**
- Create: `src/pages/LandingPage.tsx`, `src/pages/RoleSelectionPage.tsx`, `src/pages/LoginPage.tsx`
- Test: `src/pages/publicFlows.test.tsx`
- Modify: `src/App.tsx`

**Interfaces:**
- Consumes: public header, radius visual, WhatsApp component, mock products.
- Produces: routes `/`, `/login`, and `/login/:role`; non-empty credentials navigate to the role dashboard.

- [ ] Write route tests for required landing copy, role choices, invalid-login validation, and successful role navigation.
- [ ] Run the public-flow tests and verify failure.
- [ ] Implement the editorial landing page, four-step business explanation, featured products, radius story, role selection, and distinct login treatments.
- [ ] Run public-flow tests and verify they pass.

### Task 4: Buyer Discovery, Details, and Cart

**Files:**
- Create: `src/pages/buyer/BuyerDashboard.tsx`, `src/pages/buyer/ProductDetailsPage.tsx`, `src/pages/buyer/CartPage.tsx`
- Create: `src/utils/products.ts`, `src/utils/products.test.ts`
- Test: `src/pages/buyer/buyerFlows.test.tsx`
- Modify: `src/App.tsx`

**Interfaces:**
- Consumes: products/cart from `useDemo()`, shared product and radius components.
- Produces: `/buyer`, `/buyer/products/:id`, and `/buyer/cart`; `filterProducts(products, query, category, radius)`.

- [ ] Write utility tests for text/category/radius filtering, including zero matches and boundary distances.
- [ ] Run product utility tests and verify failure.
- [ ] Implement filtering and the buyer marketplace with search, categories, radius controls, location, and empty-state reset.
- [ ] Write flow tests for details, missing IDs, out-of-area purchase prevention, add-to-cart, quantities, removal, totals, and UI-only checkout.
- [ ] Implement product details and cart pages, then run buyer tests and verify all pass.

### Task 5: Seller Workspace and Listing Management

**Files:**
- Create: `src/pages/seller/SellerDashboard.tsx`, `src/pages/seller/ProductFormPage.tsx`
- Create: `src/components/ProductForm.tsx`, `src/utils/validation.ts`, `src/utils/validation.test.ts`
- Test: `src/pages/seller/sellerFlows.test.tsx`
- Modify: `src/App.tsx`

**Interfaces:**
- Consumes: product CRUD actions from `useDemo()` and shared dashboard components.
- Produces: `/seller`, `/seller/products/new`, `/seller/products/:id/edit`; required-field and positive-number validation.

- [ ] Write validation tests for blank fields, invalid price/quantity, and valid submissions; run and verify failure.
- [ ] Implement validation, seller metrics, listing states, mock deletion confirmation, and the reusable add/edit form.
- [ ] Write flow tests verifying new and edited listings become pending and deletion updates the dashboard.
- [ ] Run seller tests and verify they pass.

### Task 6: Admin Operations Console

**Files:**
- Create: `src/pages/admin/AdminDashboard.tsx`
- Test: `src/pages/admin/adminFlows.test.tsx`
- Modify: `src/App.tsx`, `src/styles/index.css`

**Interfaces:**
- Consumes: moderation actions and product state from `useDemo()`.
- Produces: `/admin` with metrics, navigation sections, approval queue, status updates, and commission placeholder.

- [ ] Write tests that approve and reject pending products and verify queue/metric updates.
- [ ] Run admin tests and verify failure.
- [ ] Implement the distinct admin shell, overview metrics, approval actions, table/cards, and non-financial commission setting placeholder.
- [ ] Run admin tests and verify they pass.

### Task 7: Integration, Responsive Polish, and Delivery Verification

**Files:**
- Modify: `src/App.tsx`, `src/styles/index.css`, and affected page/component files
- Create: `src/App.test.tsx`, `README.md`

**Interfaces:**
- Consumes: all routes and feature modules.
- Produces: complete responsive demo with fallback route and setup documentation.

- [ ] Write an application smoke test covering every major route and persistent WhatsApp access.
- [ ] Run the full test suite and fix only integration defects revealed by it.
- [ ] Audit mobile/desktop layouts, keyboard focus, reduced motion, empty/error states, and copy against the spec.
- [ ] Run `npm run build` and verify a successful production build with no TypeScript errors.
- [ ] Run `npm test -- --run` and verify the complete test suite passes.
- [ ] Document install, development, test, and build commands in `README.md`.

