# Public-point live radius implementation plan

**Goal:** Live buyer-selectable 1/2/3 km backend discovery using explicitly consented public seller points.

**Spec:** `docs/LIVE_RADIUS_DISCOVERY_VERIFICATION.md`; owner approved the public-point contract and QA-only additive migration.

**Architecture:** Add nullable public coordinates/confirmation/version, seller-owned explicit confirmation/revocation, exact shared list/detail radius checks before pagination. Keep existing coarse private-dispatch candidate gate and exact checkout enforcement. Frontend keeps radius in memory alongside confirmed source, remounts results on either change and sends strict radius in POST bodies.

**Constraints:** Only QA OID 50640 may be mutated. No original/rehearsal changes, destructive operations, dependency installation, deployment, commit or push. Never auto-copy private coordinates. QA public fixture confirmation awaits separate requested approval. Existing original server is not restarted or contacted.

- [x] Write failing strict-radius/consent and frontend regression tests.
- [x] Add migration 0009, model fields and seller-owned confirmation/revocation API/UI. Verify database check constraints and revocation semantics.
- [x] Add strict source radius default 3; enforce public radius and product radius, preserve availability and private coarse gate. Exclude unset/missing/invalid public points. Test boundaries, pagination and private-point indistinguishability.
- [x] Verify QA name/OID/owner/revision and migration shape; back up QA before additive upgrade; identity-check connection before each statement. Upgrade only 0008 -> 0009 with no data backfill; verify all four fields NULL and business counts unchanged.
- [x] Wire accessible live radius controls into state/list/detail keys. Preserve GPS/manual/saved-address behavior, accuracy warnings, empty/error states and stale-response protection.
- [x] Run rollback-isolated PostgreSQL/API tests on QA only; never reuse legacy fixtures that require empty databases or migrations. Confirm synthetic public point only after approval.
- [x] Run focused frontend tests, responsive check and production build. Exercise fresh loopback QA worker through HTTP without restarting unrelated services.
- [x] Update verification report with actual results, limitations, startup/Chrome steps and remaining blockers; review changed paths and diff.

Ruling: revision metadata in the original provisioning manifest remains historical 0008; runtime preflight now requires 0009 and the explicitly confirmed synthetic public point. Migration and consent each have separate evidence records. No source schema was recopied.

Ruling: use temporary loopback port 8002 to verify a fresh worker, leaving user-owned old 8001 and unrelated original-backed services alone. Owner restarts only QA 8001 for Chrome acceptance. The temporary worker is stopped at completion.

Ruling: update readiness and guarded bootstrap's required revision together through app/db/schema.py, because the new ORM requires 0009. This does not authorize or execute bootstrap or original migration.

Review: fresh-context read-only reviewer reported no substantive defects; added dateline/poles and cross-batch pagination coverage. Final evidence is in docs/LIVE_RADIUS_DISCOVERY_VERIFICATION.md.

Review focus: list/detail request consistency; consent must be literal true/current version; revocation excludes immediately; no public point silently populated from dispatch; original database remains at 0008 and is incompatible with the new ORM until separately approved migration, so do not route this build to it.
