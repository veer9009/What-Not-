# Product image upload implementation

Implement the user's supplied upload requirements in the existing application.
Reuse product_images; no migration, existing-database writes, .env edits or AWS
access. Preserve hosted URLs and old product request/response fields.

- [x] Test and implement bounded content inspection/re-encoding and private local/S3 adapters.
- [x] Test and implement owned-product list/upload/replace/remove/primary endpoints,
  five-image limit under product lock, moderation reset, signed read delivery.
- [x] Replace seller URL entry with file previews, per-file progress/errors,
  removal/replacement and primary selection; preserve legacy display and retry
  partial saves without duplicate products.
- [x] Run backend unit, isolated PostgreSQL, focused frontend, full relevant suite
  and build; review final diff; document configuration, limitations and checklist.

Design choices: a maximum of five existing+new images per product; 5 MiB input
limit; JPG/PNG/WebP content only; static decoded image limits; metadata-free WebP
output; raw binary authenticated uploads avoid multipart buffering. Private objects
are served through the API using expiring purpose-specific capability tokens and
live attachment checks. Local private directory is never mounted as static files.
S3 uses the normal SDK credential chain/IAM role and private server-encrypted
objects. A removed/replaced object's old read link is revoked by the attachment
check; private unreferenced objects are retained pending documented offline cleanup
to avoid deleting data before a database transaction commits.

Verification: 382 backend unit tests passed; the PostgreSQL upload/authorization/
marketplace run passed 101 tests and the final upload-only run passed 11. The full
frontend run passed 328 tests, and the final TypeScript/Vite build passed. See
`docs/PRODUCT_IMAGE_UPLOAD.md` for exact commands, configuration, file inventory,
manual checks and the existing database-schema blocker. No live AWS or application
database upload check was performed.
