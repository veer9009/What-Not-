# Rehearsal constraint validation investigation

15 November 2026. **Confirmed validator false rejection; no database constraint defect found in the 12 mismatches. No continuation executed.**

## Verified identities and migration state

Configuration was checked before connecting. The first source checks verified database/server identity through PostgreSQL; its catalog then verified both expected target OIDs before target connections opened. Each target connection independently rechecked its identity before inspecting schema. All connections enforced `default_transaction_read_only=on` and checked `transaction_read_only=on`.

Server: `127.0.0.1:5432`, PostgreSQL **17.11**, primary; database ownership matched the expected application role.

| Database | OID | Public tables | Revision | Four migration-0009 public-point columns |
|---|---:|---:|---|---|
| `whatnot_app_dev` | 41069 | 24 | `0008` | Absent |
| `whatnot_0009_rehearsal_20261115_f24a8f87` | 51678 | 24 | `0008` | Absent |
| `whatnot_0009_rollback_20261115_f24a8f87` | 51679 | 0 | No version table | Absent |

**Migration 0009 did not execute in the stopped rehearsal.** Both restored/source versions remain `0008`, all four new columns are absent, and the previous execution stopped before the migration call. The rollback target remains empty.

## Exact failed check and root cause

`docs/security/rehearse_0009_migration.py:136` records `pg_get_constraintdef()` text. `compare_schema()` at line 144 uses `require(before == after)` at line 146. The post-restore call at line 383 therefore rejects semantically equivalent expression trees whose deparsed strings differ. The migration call is later, at line 456, and was never reached.

Catalog comparison examined **108 constraints**: **96 exact textual matches**, **12 equivalent expression differences**. All constraint names and compared metadata match: constraint type, validation, deferrability/deferred state, inheritance/local flags, referenced column names/types/collations/nullability. There were no missing or renamed constraints. These 12 CHECK constraints remain validated on both databases.

Representative exact source definition:

```sql
CHECK (((status)::text = ANY ((ARRAY['ACCEPTED'::character varying, 'DELIVERED'::character varying, 'COMPLETED'::character varying])::text[])))
```

Representative exact restored definition:

```sql
CHECK (((status)::text = ANY (ARRAY[('ACCEPTED'::character varying)::text, ('DELIVERED'::character varying)::text, ('COMPLETED'::character varying)::text])))
```

The source casts the constant varchar array to a text array; the restored expression casts each varchar constant to text before constructing that array. For these unbounded built-in casts, identical literal lists, identical columns/collations, and the same text equality/ANY operation, the accepted inputs are identical. This is an equivalent cast representation, not a naming difference or weakened constraint. NULL behavior is also unchanged; separate NOT NULL metadata matches.

All twelve exact expected/actual definitions are preserved in `docs/security/evidence/0009-constraint-investigation.json` under `differences`:

| Table | Constraint |
|---|---|
| creative_engagements | ck_creative_engagements_status |
| creative_listings | ck_creative_listings_category |
| creative_listings | ck_creative_listings_pricing |
| creative_listings | ck_creative_listings_status |
| email_outbox | ck_email_outbox_state |
| orders | ck_orders_status |
| products | ck_products_status |
| property_listings | ck_property_listings_category |
| property_listings | ck_property_listings_status |
| property_profiles | ck_property_profiles_capacity |
| property_visits | ck_property_visits_status |
| users | ck_users_role |

## Evidence and tests executed

Read-only diagnostic command, from repository root:

```powershell
& .\backend\.venv\Scripts\python.exe -u .\docs\security\investigate_0009_constraints.py
```

Exit **0 / PASS**. Queries used `pg_constraint`, `pg_class`, `pg_namespace`, `pg_attribute`, `pg_get_constraintdef()` and `format_type()`. Only catalog/schema values were reported; no credentials, user rows or password hashes were retrieved for this investigation.

The diagnostic structurally recognizes only the two observed expression forms, preserving column, literal values/order, operator and unrestricted cast types. For each pair it then executes synthetic SELECT-only evaluations against PostgreSQL:

- **260 cases PASS:** every allowed literal, invalid input, NULL, empty string, whitespace, Unicode, lowercase and padded variants. Zero differences in three-valued Boolean results or CHECK acceptance (`IS NOT FALSE`). Finite examples supplement the narrow structural equivalence check; they are not a general SQL equivalence proof.
- **72 negative recognizer assertions PASS:** changed literal, changed column, changed operator, bounded varchar cast, `NOT VALID`, and unknown expression rejected for each pair. These are mutations of in-memory strings, not database constraints.

Existing guard unit tests were independently rerun:

```powershell
& .\backend\.venv\Scripts\python.exe -m pytest .\docs\security\test_0009_rehearsal.py -q
```

Exit **0**, **28 passed in 3.87s**. No database fixtures used.

## Smallest proposed correction — not applied

Keep exact comparison as the default. For CHECK definitions that differ, permit only the two narrowly recognized varchar-array/per-element-text forms when their structural signatures and all enforcement/column/collation metadata match. Reject all unknown expressions, other casts, literal/operator changes, missing constraints and flag differences. Keep existing column/index/data/identity checks intact; do not broadly remove casts, punctuation or constraint checks.

The diagnostic contains a prototype recognizer and the 72 rejection assertions. Before integrating it into the rehearsal validator, add focused unit coverage for escaped SQL literals, changed literal ordering, empty/NULL array elements, explicit collation, bounded casts and non-CHECK constraints, retaining fail-closed behavior. No application or existing rehearsal-validator code was changed here.

No corrective DDL, data rewrite, restore or database recreation is indicated. Any future continuation must independently verify the already-restored OID 51678 at `0008` and must not rerun its restore. The current resume path rejects nonempty targets; changing that requires a separately reviewed continuation path. The empty rollback target remains available for the previously planned test.

## Decision and scope

**Investigation PASS. Original migration remains NO-GO pending successful rehearsal, rollback and readiness checks.** The constraint mismatch itself is explained; migration compatibility has not yet been demonstrated. No databases were modified, restored, dropped or migrated; no credentials, services, application code or original rehearsal code changed. No continuation was attempted.

Files created in this investigation: this report, `docs/security/investigate_0009_constraints.py`, and `docs/security/evidence/0009-constraint-investigation.json`. The earlier stopped-rehearsal report and evidence remain unchanged as historical execution records.
