# Business-owner decisions required before release

12 November 2026. **B. NOT READY — BLOCKERS REMAIN.** Do not replace any missing fact with an invented example. `src/config/business.ts` centralises empty identity/grievance fields and the existing repository support number. Every policy exposes its draft status. Providing a fact does not by itself close a legal or operational requirement.

| Required input/decision | Why / evidence needed | Release gate |
| --- | --- | --- |
| Actual operator legal entity and legal form; registered/principal office; applicable registration/GST disclosures | Validate documents and required UI/marketplace disclosures with counsel; brand is not identity | Beta and public |
| Named grievance officer, designation and genuine monitored contact details | Approve grievance, consumer complaint and privacy/IP escalation process; acknowledge/track/redress with staffed ownership; do not designate support phone by inference | Beta and public |
| Confirm ownership and monitoring of existing `+91 80800 98882` WhatsApp destination | Source provenance only, no verification that it belongs to operator; confirm support data handling and access | Beta and public |
| Age eligibility | No adult-only decision or age/parental-consent system exists. Decide safe admission and treatment of any existing minor data with counsel. Do not collect DOB/IDs just for this audit | Beta and public |
| Purpose/processing grounds and notices | Confirm lawful processing grounds, meaningful notices/languages, optional sharing and withdrawal consequences; decide final policy adoption/effective date and versioned terms/consent evidence where needed | Beta and public |
| Retention schedule per data category | Cover accounts, unused/used addresses, orders, RFQs/quotes, property visits/reports, reviews, notifications/outbox, audit and quota scopes, access logs, backups and third-party copies; lawful holds and end-of-beta cleanup | Beta and public |
| Correction/export/deletion/withdrawal procedure | Current account profile is read-only; no erasure/export endpoint. Define verified request handling, authorised operators, non-disclosure checks, processor deletion and backup expiry; do not promise unsupported SLA | Beta and public |
| Hosting/database/logging/CDN/backups/SMTP vendors and locations | Contracts, processors/subprocessors, transfers, encryption/TLS, role access, recovery/breach response, real cookie/network inspection. No AWS or production inspection performed | Beta and public |
| Static image rights | Six Unsplash image IDs lack recorded creator/source-page/license/release evidence. Provide records or approved replacements. No assumed licence | Beta if externally visible; public |
| Seller/provider disclosures and responsibility | Validate required seller identity/contact, cancellation/returns/fees, invoices/taxes, prohibited listings, professional obligations and moderation/escalation | Beta and public |
| Food admission | Live schemas omit a food category; sample food is not orderable. Do not advertise live food commerce without an approved food-safety/allergen/licensing process | Before food functionality |
| Real Estate obligations | Owner/agent authority, applicable RERA/ad disclosures, due diligence, complaints, visit safety/address sharing, expiry and retention | Before sale listings admitted |
| Creative agreements | Quote scope, delivery, revisions, cancellation/disputes, ownership/licensing of final work, portfolio and client/subject permissions; no payment/escrow/cancellation endpoint | Before provider admission |
| Consumer remedies | Return/cancellation/refund/direct-payment rules and escalation. Current state cancellations are not money transfers; a workflow limit must not waive statutory rights | Beta and public |
| Terms adoption, limitation language and law/forum | Counsel review; no arbitrary jurisdiction/address/liability clauses or inferred acceptance | Beta and public |
| External image/link policy and security operations | Assess arbitrary image hosts, insecure HTTP legacy links, malicious URLs, signed URL expiry, source/IP exposure and takedown handling; remove/replace only with approved scope | Beta and public |
| Accessibility and moderation operations | Screen-reader/manual keyboard verification, accessible image-description product decision, complaint alternatives to WhatsApp and supported notice languages | Beta review; public gate |
| Deployment evidence and release approval | Owner checks SPA rewrites for public legal paths, HTTPS/security headers, frontend API origin, allowlist/abuse controls, worker scheduling and controlled test population | Beta and public |

No self-service legal decision is implied by these drafts. Missing facts stop adoption/release; unaffected source fixes and verification can be reviewed independently. No schema migration, production inspection, AWS operation, deployment, commit or push is part of this work.
