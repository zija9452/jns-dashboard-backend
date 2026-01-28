---
id: 2
title: clarify-spec-requirements
stage: spec
date: 2026-01-28
surface: agent
model: claude-sonnet-4-5-20250929
feature: regal-pos-backend
branch: 001-regal-pos-backend
user: user
command: /sp.clarify
labels: ["clarification","authentication","pagination","audit-logs"]
links:
  spec: specs/001-regal-pos-backend/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-regal-pos-backend/spec.md
tests:
 - none
---

## Prompt

 /sp.clarify {
  "spec_path": "specs/backend/regal-pos-backend-spec.md",
  "purpose": "Analyze the backend specification for Regal POS clone (FastAPI, SQLModel, Neon, RBAC 'better-auth') and surface ambiguities, missing assumptions, incomplete requirements, and scope conflicts so the team can finalize the API contract and implementation plan.",
  "analyze_for": [
    "Ambiguous terms",
    "Missing assumptions",
    "Incomplete requirements",
    "Scope conflicts",
    "Acceptance-test gaps"
  ],
  "findings": {
    "ambiguous_terms": [
      {"term":"exact parity / same fields","issue":"Which exact Regal POS fields and validation rules? (names, data types, required/optional)"},
      {"term":"better-auth","issue":"High-level behavior provided, but precise token lifetimes, rotation strategy, storage TTL and cookie vs header usage are not rigidly defined."},
      {"term":"cashier tabs (Regal POS cashier tabs)","issue":"Which POS UI actions/fields count as 'cashier tabs' (quick-sell fields, payment methods, cash drawer logic)?"}
    ],
    "missing_assumptions": [
      "Neon connection management strategy (connection pool size, use of pgbouncer or asyncpg parameters) for production",
      "Backup & retention policy for DB and audit logs",
      "Compliance/privacy needs (GDPR/data residency) and PII handling",
      "Rate limiting and brute-force protections for auth endpoints",
      "How 2FA will be delivered (TOTP, SMS, email) and who pays for SMS/email"
    ],
    "incomplete_requirements": [
      "Complete API contract (endpoints, params, response schemas) — intentionally excluded but required next",
      "Exact domain field lists with types & validations (e.g., Product.attributes schema, Invoice.line_item shape, tax calculation rules)",
      "AuditLog schema: which fields are required for full traceability?",
      "Error response standard (error object shape, codes, retryable vs non-retryable)",
      "Backup & migration runbook (how to run alembic in CI/production safely)"
    ],
    "scope_conflicts": [
      "Spec says 'exact parity' with Regal POS but also omits API params from constitution/spec — need either UI field export or screenshots to guarantee parity.",
      "‘Local dev uses docker-compose; production-ready notes for Neon’ — unclear whether production deployment (k8s / managed services) is in scope for implementation or only notes."
    ]
  },
  "recommended_fixes": [
    "Provide canonical Regal POS field list or UI screenshots (admin product form, invoice form, POS screen) to guarantee exact parity.",
    "Add an explicit OpenAPI generation task as the immediate next artifact (openapi.yaml) — include sample requests/responses and auth header examples.",
    "Define token lifecycle policy: default access token = 15 min, refresh token = 30 days, rotation on refresh, revoke on logout (these are suggested defaults; confirm if OK).",
    "Specify persistence policy for refresh JTIs and audit logs (retention period, archive rules).",
    "Specify pagination defaults (limit/offset with default limit=50, max_limit=200) and sorting/filter param format."
  ],
  "suggested_defaults": [
    "Access token expiry = 15 minutes; Refresh token expiry = 30 days; refresh tokens stored with JTI and revoked on logout/rotation.",
    "Password hashing: bcrypt via passlib (current), argon2 optional for higher security.",
    "Pagination: ?limit=50&offset=0, max limit = 200.",
    "Error format: {\"code\": \"string\", \"message\": \"string\", \"details\": {}}",
    "DB pool: use asyncpg defaults + set pool_size env var and recommend pgBouncer for production Neon."
  ],
  "acceptance_test_additions": [
    "Auth flows: login => access + refresh; refresh rotates JTI; old refresh rejected; logout revokes refresh.",
    "Role enforcement: attempt admin-only endpoints with cashier/employee and expect 403.",
    "Invoice lifecycle: create invoice, generate invoice_no, apply payments, create refund, verify stock & audit entries.",
    "Concurrency: simulate two simultaneous stock adjustments for same SKU and verify correct final stock (race conditions handled).",
    "Migration safety: run alembic upgrade in test pipeline and verify no data loss on schema changes in sample DB snapshot."
  ],
  "priority_list_for_resolution": [
    "1. Provide canonical Regal POS field list/screenshots (high priority).",
    "2. Approve token lifecycle & refresh rotation policy (high).",
    "3. Define audit log retention & backup policy (medium).",
    "4. Approve pagination, error schema, and DB pool/connection strategy (medium).",
    "5. Decide on 2FA delivery method (low/medium depending on compliance)."
  ],
  "next_steps": [
    "Attach or point to Regal POS UI field export or representative screenshots so 'exact parity' can be implemented.",
    "Confirm the suggested defaults (token TTLs, pagination, error shape). If you accept them, I will bake them into the OpenAPI and auth code.",
    "Request the OpenAPI (type: 'OpenAPI') if you want me to generate the full contract next — I will include the params, links, example reques
}

## Response snapshot

I've analyzed the specification and conducted a clarification session with 5 key questions that were answered. The specification has been updated with the following clarifications:

1. JWT Token Policy: 15-minute access tokens, 30-day refresh tokens with rotation and revocation on logout
2. Product Entity: Basic fields with standard validation (SKU, name, price, cost, barcode, category, brand, stock quantity)
3. 2FA Implementation: Future biometric authentication (thumb scanning) for employee login, no current 2FA implementation
4. Audit Log Retention: 7-year retention for financial records and critical actions
5. Pagination Settings: Default 50 items per page, maximum 200 items per page

The specification now includes a "Clarifications" section with all decisions documented, and the functional requirements and entities have been updated accordingly. The spec also addresses instant logout functionality and future biometric authentication planning.

## Outcome

- ✅ Impact: Clarified 5 key ambiguities in the specification and updated the document
- 🧪 Tests: none
- 📁 Files: Updated specs/001-regal-pos-backend/spec.md
- 🔁 Next prompts: Proceed to planning phase (/sp.plan)
- 🧠 Reflection: Specification is now more detailed with concrete requirements for authentication, data models, and pagination

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A