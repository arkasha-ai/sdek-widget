---
name: optimization-mastery
description: "Cross-domain performance optimization. INP, Partial Hydration, UUIDv7 indexing, AI Token Stewardship. Use when: (1) slow page load, (2) poor Core Web Vitals, (3) database query optimization, (4) reducing LLM token usage, (5) bundle size issues. Triggers on: performance, optimization, slow, latency, INP, bundle size, query optimization."
---

# Optimization Mastery

> **Philosophy:** Efficiency is the highest form of quality. Performance-First is the only law.

## Protocol 1: Frontend Precision (INP and Bundle)

### INP Threshold
- **Core Metric:** Interaction to Next Paint (INP) MUST be < 200ms
- **Action:** Yield to main thread for heavy logic
  ```javascript
  // Use scheduler.yield() or requestIdleCallback
  await scheduler.yield();
  ```

### Hydration Strategies
- **Use:** Partial Hydration or Resumability (Qwik/Astro patterns)
- **Never:** Full Hydration of static content

### Asset Governance
- Images: AVIF/WebP with `srcset` mandatory
- Fonts: Only `wght` variable fonts, subsetted
- JS: Code-split by route, lazy-load below the fold

## Protocol 2: Backend Velocity (Query and Data)

### Identifier Strategy
- **Use UUIDv7** for all primary keys in high-insert tables
- Time-sortable IDs prevent B-tree fragmentation, boost insert speed ~30%

### Query Budget
- **Max Latency:** Sub-100ms for OLTP queries
- Every index MUST be a "Covering Index" for critical read paths
- **N+1 detection:** Check every ORM query, fix with DataLoader or explicit JOIN

### Pagination
- Cursor-based only on large tables (never OFFSET/LIMIT)

## Protocol 3: AI Token Stewardship

### Context Window Management
- **Context Folding:** Summarize history to keep prompts under 4k tokens when possible
- Don't repeat full conversation — summarize, then add only new context

### Credit-Based Execution
- Assign "Token Budget" to complex tool-calling phases
- Track token usage per operation

### Caching
- **Semantic Caching** for repetitive LLM queries
- Cache embeddings alongside source text
- Use prompt fingerprints for deduplication

## Audit Cycle (Before Shipping)

1. Is INP < 200ms?
2. Are primary keys UUIDv7?
3. Is hydration partial/resumable?
4. Is the token budget justified?
5. Are images in modern formats with srcset?
6. Is cursor pagination used on large tables?
