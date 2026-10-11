# What Not? — Hyperlocal Marketplace Demo

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

## Product review workflow

- The seller's **Demo shop** selector switches mock shop identity. Inventory and edit actions belong to the selected shop. It is a demo control, not authentication.
- New products start `PENDING`. Editing an approved product sends it back to review. Sellers cannot set approval status through add/edit actions.
- Admin reviews the image, shop, category, description, price, stock and delivery radius. Rejection requires a nonblank reason.
- Rejected products retain the reason while the seller edits them. **Save Changes** saves the draft; **Resubmit for Review** returns it to `PENDING` and clears the old reason.
- Deactivation is independent of approval. Reactivation never bypasses review.
- Discovery, featured listings, buyer detail links, cart additions and checkout require `APPROVED`, active, in-stock products within their delivery radius. Distance remains the existing mock distance.
- Checkout groups the basket by seller, creates one mock order per shop, snapshots the purchased products, decreases stock and clears the cart. Delivery is ₹49 per seller order, shown before checkout.
- Product images are previewed locally (JPG/PNG, up to 5 MB). Listings, image previews and orders reset when the page reloads.

Run all tests with `npm.cmd test -- --run` on Windows, check TypeScript with `npx.cmd tsc -b`, and build with `npm.cmd run build`. No lint script or lint configuration is currently installed.

The next integration step is to agree on the product and order API contracts with the separately developed database layer. Keep ownership, moderation, eligibility and seller-order validation on the future server as well as in the UI.
