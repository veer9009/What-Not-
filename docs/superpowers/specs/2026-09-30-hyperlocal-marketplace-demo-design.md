# Hyperlocal Marketplace Frontend Demo Design

## Purpose

Build a polished client-facing frontend demonstration of a hyperlocal marketplace that connects nearby buyers with local makers, artisans, small businesses, and workers. The demo must communicate the business model clearly, especially seller-defined discovery radiuses, while remaining entirely frontend-only.

## Scope

The application will include three clearly separated roles: buyer, seller, and admin. It will use realistic mock data and local in-memory state. It will not include a backend, database, real authentication, payment processing, live geolocation, or a map API.

The application will demonstrate:

- A public marketplace landing page
- Role selection and separate mock login experiences
- Buyer product discovery, radius filtering, search, product details, and cart UI
- Seller metrics, listing management, and product submission
- Admin metrics, product moderation, and placeholder commission settings
- A visual explanation of seller radius and buyer eligibility
- WhatsApp contact access on all major screens

## Technical Approach

Use React, Vite, and TypeScript. Use client-side routing for distinct screens and React state for simulated interactions. Keep mock content and reusable UI primitives separate from page components so the project can later connect to REST APIs and persistent storage without replacing the presentation layer.

No production infrastructure or third-party service integration is part of this demo.

## Visual Direction

The interface will use a warm, locally crafted marketplace identity with an ivory base, terracotta accents, forest green actions, and charcoal text. Typography will pair an expressive display face with a clean sans-serif interface face. Cards will use rounded corners, fine borders, soft shadows, generous whitespace, and consistent iconography.

Photography will focus on handmade goods such as teddy bears, pottery, candles, bags, jewellery, and crafts. Motion will be limited to useful hover, focus, panel, and navigation transitions.

The public and buyer views will feel editorial and product-focused. Seller screens will feel like a friendly business workspace. Admin screens will use a denser, clearly distinct operations-console layout.

## Application Architecture

### Routing

The route structure will cover:

- `/` — landing page
- `/login` — role selection
- `/login/buyer`, `/login/seller`, `/login/admin` — separate demo logins
- `/buyer` — buyer dashboard and product discovery
- `/buyer/products/:id` — product detail
- `/buyer/cart` — cart and checkout presentation
- `/seller` — seller dashboard and listings
- `/seller/products/new` — add-product form
- `/seller/products/:id/edit` — edit-product form
- `/admin` — admin dashboard and moderation

Demo login forms accept any non-empty credentials and navigate to the relevant dashboard.

### Shared State

A top-level demo store will own:

- Product records and moderation status
- Buyer cart items
- Search, category, and radius filter state where appropriate
- Seller add, edit, and delete actions
- Admin approve and reject actions

The state resets on a full page reload unless lightweight local persistence is simple and beneficial. Persistence is not required for the client demonstration.

### Component Boundaries

Reusable components will include:

- Public header and dashboard sidebars
- Product card and product grid
- Role login shell
- Metric cards and status badges
- Radius selector and radius visualization
- Search and category controls
- Empty-state panel and notification/toast feedback
- Confirmation modal for destructive mock actions
- Floating WhatsApp contact button

Pages will compose these components and contain only page-level orchestration. Mock product, seller, user, and metric data will live in dedicated data modules.

## Experience Design

### Landing Page

The landing page will open with the required “Discover What's Made Around You” message, primary discovery and seller calls to action, and a curated handmade-product composition. It will explain the four-step business model: sell locally, set a radius, discover nearby, and support local.

A prominent radius-story section will depict a seller at the center of nested 1 KM, 2 KM, and 3 KM zones with eligible nearby buyers. This will be a styled visual rather than a real map.

### Buyer Experience

The buyer dashboard will show location context, search, category filters, and 1/2/3 KM radius controls. Filtering will update visible mock products based on their distances. Product cards will show photography, seller, price, distance, rating, and verification.

Product details will show stock, description, distance, seller radius, verification, and actionable Add to Cart, Buy Now, and Contact Seller controls. Products beyond their seller's radius will clearly show “Outside seller's delivery area” and disable purchasing actions.

The cart will support quantity adjustment, item removal, totals, and a UI-only checkout action with clear demo messaging.

### Seller Experience

The seller dashboard will show required summary metrics and listings with approved, pending, and rejected states. Sellers can add, edit, inspect, and delete mock listings.

The product form will collect the required fields, provide image-preview behavior, and make the selling-radius rule prominent. New and edited submissions will enter pending approval to demonstrate moderation.

### Admin Experience

The admin dashboard will use a darker navigation treatment and denser information hierarchy. It will show platform metrics, a pending-approval queue, and navigation placeholders for buyers, sellers, products, approvals, orders, commission, and settings.

Approve and reject actions will update shared mock product state immediately. Commission settings will be visibly configurable but will not perform financial calculations.

### WhatsApp Contact

All major screens will include a bottom-right WhatsApp-style button with a subtle “Need help?” tooltip. It will open a `wa.me` link for `+91 80800 98882` with the message: “Hi, I would like to know more about your local marketplace.” This link supports WhatsApp Web on desktop and the installed app where supported on mobile.

## Responsive Behaviour

The experience will be mobile-first. Navigation collapses on smaller screens, dashboard sidebars become compact mobile navigation, grids reduce to one column, and forms stack vertically. Tap targets will remain accessible. Desktop layouts will use wider grids and split views without stretching readable content excessively.

## Error and Empty States

Searches and filters with no matches will produce a polished empty state with a reset action. Forms will show inline validation for required values and invalid numbers. Mock operations will provide visible success or failure feedback. Missing product routes will provide a useful return path.

## Accessibility

Semantic elements, labeled form fields, keyboard-visible focus states, descriptive button labels, sufficient contrast, and reduced-motion support will be included. Images will have useful alternative text.

## Verification

Completion requires:

- A successful production build
- Navigation checks for every major route
- Buyer search, category, radius, details, cart, and out-of-area checks
- Seller add, edit, and delete checks
- Admin approve and reject checks
- Responsive checks at mobile and desktop widths
- Verification of the WhatsApp URL and pre-filled message

## Deferred Work

Backend APIs, PostgreSQL, secure authentication, real geolocation, payments, order processing, production commission logic, live maps, deployment, and Docker are intentionally deferred.
