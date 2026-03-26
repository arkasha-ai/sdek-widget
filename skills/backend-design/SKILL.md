---
name: backend-design
description: "Elite backend architecture: Vertical Slice, Zero Trust, Sub-100ms. Use when: (1) designing APIs, (2) choosing database patterns, (3) building services from scratch, (4) debugging performance issues, (5) need to structure a backend project. Triggers on: backend, API, database, service, архитектура бэкенда, спроектировать."
---

# Backend Design System

> **Philosophy:** The Backend is the Fortress. Logic is Law. Latency is the Enemy.
> **Core:** ISOLATE features. TRUST no one. SCALE linearly.

## 1. Vertical Slice Architecture (The Anti-Layer Mandate)

**FORBIDDEN:** "Controllers/Services/Repositories" as primary folders.

**Rule:** Organize by **BUSINESS CAPABILITY**, not technical role.

```
features/create-order/
├── handler.ts    # Controller
├── logic.ts      # Domain
├── schema.ts     # DTO/Validation
└── db.ts         # Data Access

shared/           # Only: Logging, Auth, DB connection
```

**Benefit:** Changing a feature = touching ONE folder. No cross-layer changes.

## 2. The Modular Monolith Mandate

**DO NOT start with microservices.** Start with Modular Monolith.

Rules:
- Modules isolated like internal microservices
- Modules communicate via **Events**, NEVER by importing code directly
- Module A cannot query Module B's tables — ask via API/Event
- **Outbox Pattern:** Write events to `outbox` table in SAME transaction as data change

## 3. Zero Trust Security

1. **Never return raw DB entities** → ResponseDTO
2. **Schema validation (Zod/Pydantic)** BEFORE logic
3. **PASETO v4 > JWT** (Ed25519 if JWT forced)
4. **Anti-Happy-Path:** Document AND test 3 failure scenarios per feature:
   - Race Conditions
   - Data Integrity violations
   - Boundary failures

## 4. Performance: Sub-100ms

| Metric | Target |
|--------|--------|
| P50 | < 100ms |
| P99 | < 500ms |

**UUIDv7 for Primary Keys** — Time-ordered, prevents B-Tree fragmentation.
**N+1 Assassin:** Check every ORM query. Fix: DataLoader or explicit JOIN.

## 5. API Reliability

**RFC 7807 Problem Details** for all errors:
```json
{
  "type": "https://api.app.com/errors/insufficient-funds",
  "title": "Insufficient Funds",
  "status": 403,
  "detail": "Current: 10.00, required: 15.00",
  "instance": "/transactions/12345"
}
```

**Idempotency Keys** for POST/PATCH (money, state): accept `Idempotency-Key` header, cache 24h.

## 6. Database Integrity

- **Hard Constraints > Application checks** (FK, Unique Index, Check Constraints)
- **Cursor Pagination** — never `OFFSET/LIMIT` on large tables
- **Optimistic Locking** — add `version` column, `UPDATE WHERE id=X AND version=Y`
- **Migrations:** Never lock table >1s. Use "Expand and Contract" pattern.

## 7. AI & Vector Readiness

For RAG/semantic search:
- Store embeddings alongside source text
- Use UUIDv7 for correlation
- Consider pgvector for PostgreSQL-based vector search

## References

- **Security detailed protocols:** See `references/security-protocols.md`
- **API patterns:** See `references/api-patterns.md`
