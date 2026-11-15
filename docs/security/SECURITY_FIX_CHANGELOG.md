# Security fix changelog

Date: 14 November 2026. Read-only application baseline completed before remediation.
No application authentication architecture, database schema/migration, order/payment
logic or security-sensitive hosting configuration was changed. No commits or pushes.

## SEC-001 — Vite dependency

- Original issue: installed/tracked Vite 8.3.1 matched High tooling advisories.
- Files: `package.json:15`, `pnpm-lock.yaml`; regression coverage in
  `src/utils/securityDependencies.test.js`.
- Change: pin Vite to 8.3.8; regenerate peer snapshots and required Vite transitive
  dependencies. Same Vite major; bundler/native optional dependencies follow the
  vendor patch graph. No application feature refactor.
- Evidence: baseline npm JSON reports High; final tracked-graph pnpm JSON has no
  High/Critical advisories and no Vite finding. Production bundle builds with 8.3.8.
- Regression: installed dependency floor, existing complete frontend suite and
  browser harness; final results in SECURITY_TEST_RESULTS.md.
- Retest: advisory-range presence is resolved (**PASS**). No editor execution or
  file-disclosure exploit was run; disappearance of that exploit is not claimed.

## SEC-002 — undici transitive dependency

- Original issue: jsdom resolved undici 8.11.2, within High advisory ranges.
- Files: `pnpm-workspace.yaml:3`, `pnpm-lock.yaml`, same dependency regression test.
- Change: workspace override to 8.12.2. This remains inside jsdom's existing
  compatible major range and does not add undici to browser application code.
- Evidence: final tracked-graph advisory query no longer reports undici; installed
  dependency check resolves from jsdom's real pnpm location, not an assumed root link.
- Regression: dependency-floor test, frontend suite and build; see final test report.
- Retest: vulnerable dependency resolution removed (**PASS**). No live hostile TLS
  peer, customer data or destructive resource-exhaustion reproduction was used.

## SEC-011 — source-map-js transitive dependency

- Original issue: the pnpm graph exposed source-map-js 1.2.1 via css-tree/jsdom,
  within the High indexed-source-map DoS advisory. The ignored npm lockfile scan
  did not reveal this extra risk.
- Files: `pnpm-workspace.yaml:4`, `pnpm-lock.yaml`, dependency regression test.
- Change: compatible override to 1.2.2 throughout the graph.
- Evidence: intermediate tracked-graph JSON reports High; final JSON reports only
  the two remaining Moderate @vitest/mocker advisories.
- Regression: dependency floor resolves through jsdom/css-tree; frontend/build tests.
- Retest: vulnerable version removed (**PASS**); no event-loop exhaustion test run.

## Scope control and verification history

An initial install refreshed unrelated latest ranges, including jsdom 31. That
temporary refresh was undone before final verification. Original direct dependency
versions are retained except Vite; no dependency major upgrade remains. The final
lock retains required patch transitive changes and new optional vendor dependencies.
pnpm 12 ignores package.json pnpm.overrides, so the final overrides live in its
supported pnpm-workspace.yaml. See [pnpm configuration documentation](https://pnpm.io/settings).

The final `corepack pnpm install --frozen-lockfile --ignore-scripts` completed
successfully: resolution skipped, lock up to date, already up to date. Earlier
offline attempts failed due to store permissions/missing cached registry metadata;
they are retained as failed checks, not successful installs.

Added regression coverage:

- Three dependency-floor tests guard installed Vite/undici/source-map-js versions.
  They supplement fresh advisory scans; they do not detect future CVEs.
- Five isolated backend attacker-input tests cover literal SQL-like text, invalid
  identifiers, trusted-field tampering, secret-free validation and absent uploads.
- Existing full backend baseline: 654 passed; no backend application source changed.

A dependency test initially assumed Node resolution through an unresolved pnpm
symlink. It was corrected to use realpath, and moved to JavaScript to preserve the
existing browser TypeScript configuration without adding Node typings to app code.
All failures and final outcomes are listed in the test report.

## Deferred changes

SEC-003/004/005/006/007/008/009/010/012 remain open or need review; exact statuses
are in SECURITY_FINDINGS.md. The user's automatic fix policy covers confirmed
Critical/High fixes with clear local verification. Medium/Low policy decisions and
auth/schema/order/payment/infrastructure changes were not silently implemented.
In particular no JWT revocation architecture, retention purge, Nginx/HSTS, DB TLS,
SMTP transport policy or account migration was changed.

The two Moderate mocker advisories are not accepted risks. A reviewed Vitest patch
update and regression pass is recommended. Deployment remains **NO-GO** because
critical production evidence is missing, regardless of the three High dependency fixes.
