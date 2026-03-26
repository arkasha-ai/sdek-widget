---
name: debug-mastery
description: "Systematic debugging methodology. 4-phase process. No fixes without investigation. Use when: (1) something doesn't work, (2) error in logs, (3) bug report, (4) unexpected behavior. Triggers on: debug, error, bug, не работает, ошибка, fix, починить."
---

# Debug Mastery

> **Philosophy:** Random fixes waste time and create new bugs. Quick patches mask underlying issues.

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## The Four Phases

### Phase 1: Root Cause Investigation

1. **Read Error Messages Carefully**
   - Read stack traces completely
   - Note: line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - Does it happen every time?

3. **Check Recent Changes**
   - Git diff, recent commits
   - New dependencies, config changes
   - Environmental differences

4. **Multi-Component Tracing**
   - For each component boundary:
     - Log what enters
     - Log what exits
     - Verify environment/config propagation

### Phase 2: Form Hypothesis

Based on evidence from Phase 1:
- What assumption failed?
- What boundary condition was violated?
- Why did the original architecture allow this?

**Write the hypothesis before touching code.**

### Phase 3: Implement Fix

- Fix the root cause, not the symptom
- Add regression test so it doesn't break again
- Document WHY the fix works

### Phase 4: Verify

Run the exact scenario that triggered the bug. Confirm:
- Original symptom is gone
- No new failures introduced
- Related functionality still works

## When to Use Especially

- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work

## Don't Skip When

- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (systematic is faster than guess-and-check)
- Manager wants it fixed NOW (systematic is faster)

## Logging for Debugging

Add diagnostic logs before proposing fixes:

```typescript
// For multi-component issues
logger.debug({ component: 'OrderService', input: orderData, userId: orderData.userId });
const result = await orderRepo.create(orderData);
logger.debug({ component: 'OrderService', output: result, orderId: result.id });
```

Run once to gather evidence showing WHERE it breaks.
