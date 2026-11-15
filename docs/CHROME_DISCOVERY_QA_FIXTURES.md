# Proposed Chrome acceptance fixtures — approval required

Status: **approved by owner and initialized in Step 39**. Date: 15 November 2026. Destination OID **50640**, revision **0008**. Exactly the listed synthetic fixtures exist; independently verified real QA HTTP discovery returns 2 / 0 / 2 products. See `CHROME_DISCOVERY_ACCEPTANCE.md` for command outcomes, protected credentials and the provisioner's post-result native-exit anomaly. Do not rerun provisioning.

Target: `whatnot_chrome_qa_20261115`, separate from original `whatnot_app_dev`, protected rehearsal and rollback-only automated tests. The administrator created only this empty database; initialization subsequently verified OID 50640/ownership and absence of unexpected objects before any restore/write. It was never overwritten or recreated.

Schema source: verified isolated `whatnot_tests_20261115_a7e394c2`, OID 49265, revision 0008, with zero business rows. The approved initialization used `pg_dump --schema-only`; no table rows or sequence values were copied. Revision metadata 0008 was initialized in the new QA schema's fixture transaction. No Alembic migration/stamp command, original-data import or role privilege change occurred. New QA account passwords are Windows-user DPAPI-protected; existing credentials are unchanged.

Exact synthetic business fixtures proposed:

| Records | Values / behavior |
| --- | --- |
| 1 buyer | Name `Chrome QA Buyer`, email `chrome-buyer@example.com`, phone `qa-only-buyer`, active BUYER; new QA-only Argon2id password chosen privately, never a copied user credential |
| 1 seller user | Name `Chrome QA Seller`, email `chrome-seller@example.com`, phone `qa-only-seller`, active SELLER; new private QA-only Argon2id password |
| 1 seller profile | Shop `Chrome QA Maker`, synthetic dispatch latitude 0 / longitude 0, explicit confirmation timestamp, verified badge false; no real contact/location data |
| 1 positive product | `QA Nearby Vase`, description `Synthetic Chrome acceptance fixture`, category Crafts, price 250.00, stock 5, APPROVED, active, delivery radius 2 km, no external image |
| 1 positive product | `QA Nearby Basket`, same synthetic description/category, price 125.50, stock 4, APPROVED, active, delivery radius 1 km, no external image |
| 1 excluded product | `QA Pending Sample`, same synthetic description/category, price 99.00, stock 3, PENDING, active, delivery radius 3 km; must never appear in buyer discovery |
| 1 buyer-owned address | Label `QA Home`, line `Synthetic QA address only`, city/state `QA`, PIN `999999`, latitude 0 / longitude 0, default true. The PIN is an arbitrary test string, not a geocoded postal location. |

No admin, orders, payments, notifications or real data are required. Business totals: **2 users, 1 seller profile, 3 products, 1 address, 0 orders**. API login/discovery will legitimately write QA-only quota counters. Synthetic manual supported point `(0,0)` must return the two approved products; unsupported point `(1,1)` must return `[]`. These are not browser GPS values or real user locations.

The proposed approval covers creating this new database, copying only the verified isolated empty schema/revision, and inserting exactly these fixtures in an identity-checked transaction. It does not cover original/rehearsal modification, migrations, credential changes, deployment or automatic destructive cleanup. If a target already exists or identity/emptiness cannot be established, stop rather than overwrite it.
