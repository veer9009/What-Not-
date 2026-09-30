# Nearloom — Hyperlocal Marketplace Demo

A polished frontend-only concept demo for a local marketplace connecting buyers with nearby makers, artisans, and small businesses.

## Run locally

```bash
corepack pnpm install
corepack pnpm dev
```

Open the local URL shown by Vite. Use any non-empty email and password on the buyer, seller, or admin login screens.

## Verify

```bash
corepack pnpm test -- --run
corepack pnpm build
```

## Demo scope

- Buyer discovery, search, category and 1/2/3 KM radius filtering
- Product details, seller-area eligibility, cart and UI-only checkout
- Seller dashboard, add/edit/delete listing interactions and approval states
- Admin metrics, product approval/rejection and commission placeholder
- WhatsApp contact link for `+91 80800 98882`

All content and state are mocked in the browser. There is no backend, database, real authentication, geolocation, payment processing, or map integration.
