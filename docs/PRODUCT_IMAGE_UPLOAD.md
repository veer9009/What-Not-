# Product image upload — local and S3

Implemented in the existing React/FastAPI marketplace. No migration is needed:
`product_images.image_url` stores either the unchanged hosted HTTP(S) URL or an
internal `whatnot-upload:<uuid>.webp` reference. The existing primary-image index,
product relationship and seller authorization remain in use. No application
database migration, .env change, AWS access, deployment, commit or push was made.

## Seller flow

Choose files in Add/Edit Product. Previews and primary selection are local drafts
until Submit/Save. The form first saves product details, then applies image edits
sequentially with per-file transfer progress and a processing state. Each confirmed
operation is retained for ordinary partial-failure retries; a confirmed product ID
is reused so an image failure does not create a second product. Image changes on
an approved product return it to PENDING. Rejected reasons remain until resubmission.

JPG/JPEG, PNG and WebP are supported. The limit is **5 MiB (5,242,880 bytes)** per
input and normalized file, **five images total**, counting existing hosted rows.
Server-side decoding permits only static JPEG/PNG/WebP, at most 8000 pixels per
side and 16 million pixels total. Original MIME, extension and filename are not
trusted. The original is never stored: a verified, fully decoded, correctly oriented
pixel-only WebP is written without EXIF, GPS, XMP, ICC or other inherited metadata.
Animation, malformed files, unsupported formats, decompression warnings and
oversized content are rejected. Browser validation is only an early convenience.

Transfer progress reaching 100% means the server may still be inspecting/storing
the image. A product and its image operations are separate transactions: Cancel
or network loss cannot roll back operations already accepted by the server.
After an ambiguous network outcome, reload the product before retrying to avoid
uploading the same file twice. There is no cross-resource exactly-once guarantee.

## API compatibility and authorization

Old product create/update JSON `image_url` remains accepted. Responses keep
`image_url` as the primary display URL and add `images` entries with `id`,
`image_url`, `is_primary` and `sort_order`. An unchanged managed primary URL echoed
by a legacy PATCH preserves its private reference instead of persisting an
expiring link. Existing hosted URLs remain unchanged and are not downloaded,
rewritten or deleted by this feature.

New endpoints under `/api/v1`:

| Method / path | Body / result |
| --- | --- |
| GET `/products/{product_id}/images` | Owned image list |
| POST `/products/{product_id}/images` | Raw file bytes; 201 ProductResponse |
| POST `/products/{product_id}/images/{image_id}/replace` | Raw file bytes; 200 ProductResponse, same image ID |
| POST `/products/{product_id}/images/{image_id}/remove` | JSON `{}`; 200 ProductResponse |
| POST `/products/{product_id}/images/{image_id}/primary` | JSON `{}`; 200 ProductResponse |
| GET `/product-images/{generated_key}?token=...` | Verified, private image delivery |

Management requires the existing Bearer authentication, active SELLER role, beta
admission and product ownership. Ownership is checked before reading/decoding the
upload; mutation rechecks it under the existing user/product locks. The five-image
limit is checked under the product lock. The previous primary flag is flushed
before setting a new one, preserving the partial unique index. Image edits update
the product timestamp used by moderation's optimistic concurrency check.

Errors: 401 missing/invalid authentication, 403 role/ownership, 404 absent image or
invalid delivery capability, 409 five-image limit, 413 upload size, 422 invalid
content, 429 upload quota, 503 private storage unavailable. Driver/provider details
and original image metadata are not returned. Uploads/replacements use the existing
durable quota infrastructure: 30 per seller per hour by default; tests bypass quotas
using the existing test-environment rule.

## Private storage and controlled delivery

Neither local storage nor S3 is mounted as public static hosting. Delivery links
are purpose-specific capabilities, signed with a domain-separated key derived
from the existing JWT secret. They expire after 15 minutes by default; an access
token cannot be used as an image capability. Anyone holding a valid link can view
that image until expiry, subject to the live attachment/product-active/owner-active
and seller-role checks. Treat links as sensitive, particularly for pending listings.
Do not log query strings in reverse-proxy/access logs; redact the `token` query
parameter. Links carry no user data. Responses use no-store, no-referrer and nosniff.

Removing/replacing an image revokes the old link through its attachment check,
even before the old token expires. Deactivating a product or suspending its seller
also prevents delivery. An already downloaded image cannot be recalled. Refreshing
the product retrieves fresh links after expiry; clients should not persist signed
URLs as durable image identifiers. Use the image IDs for management.

Files have generated immutable names. Local keys cannot traverse directories;
symlink/reparse paths are rejected and Unix permissions use directory 0700/file
0600. On Windows, the host account/directory ACL must remain private; chmod is not
a substitute for Windows ACL policy. Keep development storage out of shared folders
or public web roots. The default directory is git-ignored, not a static Vite asset.

Unreferenced blobs can remain after removals, replacements or database rollback.
They are private and inaccessible through delivery because no live row references
them. This intentionally avoids deleting objects before a database commit or
breaking a previous image when a transaction fails. Monitor capacity and use the
offline cleanup procedure below; no automatic bucket deletion/lifecycle rule is
installed by this change.

## Configuration — no existing .env was edited

Install backend dependencies with the existing virtual environment:

```powershell
Set-Location 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

| Setting | Local default / requirement |
| --- | --- |
| `WHAT_NOT_IMAGE_STORAGE` | `local`; choose `s3` for deployment |
| `WHAT_NOT_IMAGE_LOCAL_DIRECTORY` | `backend/.private-product-images`; writable private persistent directory |
| `WHAT_NOT_IMAGE_DELIVERY_ORIGIN` | `http://127.0.0.1:8000`; exact externally reachable API origin, no path/query/credentials |
| `WHAT_NOT_IMAGE_URL_TTL_SECONDS` | `900`, allowed 60–3600 |
| `WHAT_NOT_IMAGE_UPLOAD_HOURLY_LIMIT` | `30`, allowed 1–200 |
| `WHAT_NOT_IMAGE_S3_BUCKET` | Required for `s3` |
| `WHAT_NOT_IMAGE_S3_REGION` | Recommended explicit bucket region |
| `WHAT_NOT_JWT_SECRET_KEY` | Existing authentication key; required for signed managed-image links |

Local mode needs no AWS configuration. Production local storage fails closed;
configure S3 explicitly before using uploads in production. Production S3 delivery
requires an HTTPS API origin. The frontend uses its existing `VITE_API_BASE_URL`;
no S3 browser endpoint or bucket CORS is needed because traffic goes through the API.

For S3, provision a private bucket with all Block Public Access settings enabled,
Bucket Owner Enforced ownership, no public bucket policy, and server-side encryption.
The adapter writes with AES256 server-side encryption, no public ACL, and an
immutable conditional put. Use the normal boto3 credential chain, preferably the
deployment IAM role. Do not add credentials to source or browser settings. Limit
the application role to GetObject/PutObject on that bucket's `product-images/*`
prefix; reserve List/Delete for a separate cleanup role if used. SDK connect/read
timeouts and retries are bounded. No S3 or production call was executed here.

Set reverse-proxy request-body and body-read timeout limits in deployment. The
application reads at most 5 MiB per upload, but a proxy should reject excess bodies
before buffering them. Bound request concurrency to available decoder memory;
16-megapixel images require several decoded buffers. Monitor quotas, latency,
storage capacity and orphan growth. Backup product metadata and private blobs
together. Changing storage adapters requires copying referenced objects with their
same generated keys; changing the setting alone does not move existing files.

## Offline orphan cleanup

Stop all image writes first. Take a consistent database/blob backup, then export
the exact live references from `product_images` with the `whatnot-upload:` prefix.
Inventory only this application's private directory or S3 `product-images/`
prefix. Compare valid generated keys against the live reference set; never infer
ownership from arbitrary filenames. Produce a dry-run list of unreferenced objects
older than a suitable grace/backup window, inspect it, and obtain operator approval
before physical deletion. Never apply an age-only lifecycle rule to all product
images: old objects can still be referenced. Cleanup tooling/deletion was not run.

## Manual testing checklist

1. Confirm `/api/v1/ready` is healthy on the intended local database. The earlier
   `0008` versus `0009` schema mismatch is unchanged by this frontend/storage work.
   No migration was applied to repair it; follow the separate backup/rehearsal plan.
2. Log in as a seller, create a product, choose JPG/PNG/WebP files, preview them,
   choose a primary and Submit. Check progress, reload Edit Product and the seller
   dashboard, and verify the images persisted.
3. Add images up to five including a hosted legacy image; verify the sixth is
   rejected. Replace one while at five, remove the primary, and choose another.
4. Edit an approved product image and verify status returns to PENDING. Confirm
   legacy hosted image displays and old `image_url` clients still work.
5. Try GIF/SVG, malformed/truncated bytes and >5 MiB files. Verify useful errors,
   preserved existing images, and no exposed provider/SQL details.
6. Interrupt a batch upload; retry confirmed partial failures on the same product.
   For uncertain network outcomes, reload first and inspect existing images.
7. Try image operations as another seller, buyer and anonymous client. All image
   management must be denied; image IDs from another product must return 404.
8. Open a signed link, remove/replace its image, then verify that old link fails.
   Verify missing/expired/tampered tokens fail and seller suspension blocks delivery.
9. Test leaving the form during an upload; no later queued images should start.

## Verification results

Tests use synthetic files, private temporary storage, mocked S3 and disposable
PostgreSQL, never the application DB. Commands below ran from the repository root
for frontend checks and from `backend` for Python checks.

| Check | Command | Result |
| --- | --- | --- |
| Backend unit suite | `.venv\Scripts\python.exe -m pytest -q --ignore=tests/persistence --tb=short` | 382 passed |
| PostgreSQL upload, authorization and marketplace services | `.venv\Scripts\python.exe -m pytest -q tests/persistence/test_product_images.py tests/persistence/test_authorization.py tests/persistence/test_services_marketplace.py --tb=short` | 101 passed |
| Final PostgreSQL upload suite, including concurrent cap and storage failure | `.venv\Scripts\python.exe -m pytest -q tests/persistence/test_product_images.py --tb=short` | 11 passed |
| Upload client, gallery and session safeguards | `npm.cmd test -- --run src/api/uploads.test.ts src/pages/ProductImages.test.tsx src/api/client.test.ts --maxWorkers=1 --testTimeout=20000 --reporter=json --outputFile=product-image-frontend-focused.json` | 32 passed before final legacy fallback regression additions |
| Final gallery regressions | `npm.cmd test -- --run src/pages/ProductImages.test.tsx --maxWorkers=1` | 11 passed, including both legacy URL-only response paths |
| Full frontend suite | `npm.cmd test -- --run --maxWorkers=2 --testTimeout=20000 --reporter=json --outputFile=product-image-frontend-final.json` | 328 passed, 0 failed; 52 reported suites |
| Final production build | `npm.cmd run build` | Passed TypeScript and Vite; 1942 modules |
| Whitespace check | `git diff --check` | Passed (line-ending notices only) |

The full frontend suite completed successfully, including the final legacy
regressions. An earlier run overlapped implementation changes and is retained only
as a diagnostic artifact, not final verification. No AWS integration or interactive upload against the existing local
application database was performed. Its known `0008`/`0009` mismatch remains a
manual-testing blocker. This upload implementation requires no schema migration.

Implementation references: [Pillow image verification and decoding](https://pillow.readthedocs.io/en/stable/reference/Image.html)
and [S3 PutObject conditional/encrypted writes](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html).

## Exact files changed for this upload task

```text
.gitignore
README.md
backend/DATABASE.md
backend/requirements.txt
backend/app/core/config.py
backend/app/main.py
backend/app/api/routes/admin.py
backend/app/api/routes/discovery.py
backend/app/api/routes/products.py
backend/app/api/routes/sellers.py
backend/app/api/routes/product_images.py
backend/app/schemas/product.py
backend/app/services/abuse.py
backend/app/services/discovery.py
backend/app/services/mappers.py
backend/app/services/products.py
backend/app/services/product_images.py
backend/app/storage/__init__.py
backend/app/storage/product_images.py
backend/tests/test_api_contracts.py
backend/tests/test_image_storage.py
backend/tests/test_image_tokens.py
backend/tests/test_product_image_contracts.py
backend/tests/test_product_image_compatibility.py
backend/tests/persistence/test_product_images.py
src/api/client.ts
src/api/products.ts
src/api/types.ts
src/api/uploads.test.ts
src/components/ProductImages.tsx
src/pages/SellerPages.tsx
src/pages/ProductImages.test.tsx
src/Marketplace.test.tsx
src/styles/product-images.css
docs/superpowers/plans/2026-11-15-product-image-upload.md
docs/PRODUCT_IMAGE_UPLOAD.md
```

Generated verification reports: `product-image-frontend-full.json`,
`product-image-frontend-focused.json`, and `product-image-frontend-final.json`.
The full report is the intermediate run; the final report is the later stable-code
run. Pre-existing seller-profile/diagnostic changes, reports, and untracked
`docs/security/evidence/` were preserved; they are not new upload-task changes.
