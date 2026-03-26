---
name: brainstorming
description: "Design-first methodology. Explore intent, requirements and design before implementation. Use when: (1) starting new feature, (2) making architectural decisions, (3) need to explore approaches, (4) task takes over 30 min. Triggers on: brainstorm, design, explore, how should we, какой подход, как лучше."
---

# Brainstorming: Design Before Code

> **Philosophy:** Understanding comes before implementation. Never code without a clear design.

## When to Use

**Must use before:**
- Creating new features
- Building new components
- Adding significant functionality
- Any task >30 minutes

**Skip for:**
- Simple bug fixes with obvious solutions
- Documentation updates
- Trivial configuration changes

## The Process

### Phase 1: Understanding

Check current project state:
- Review relevant files and docs
- Check recent commits
- Understand existing patterns

Ask questions **one at a time:**
- Purpose: What problem does this solve?
- Constraints: What limitations exist?
- Success criteria: How do we know it works?
- Edge cases: What could go wrong?

### Phase 2: Explore 2-3 Approaches

Always propose options with trade-offs:

```
**Option A: [Name]**
- Pros: Simple, fast to implement
- Cons: May not scale
- Best for: Quick prototypes

**Option B: [Name]**
- Pros: Scalable, well-tested pattern
- Cons: More complex
- Best for: Production systems

**My recommendation:** Option B because [reasoning]
```

**Lead with your recommended option and explain why.**

### Phase 3: Present Design in Sections

1. Break into sections of 200-300 words
2. Ask after each section: "Does this look right?"
3. Be ready to go back and clarify

Cover:
- Architecture: How components fit together
- Data flow: How information moves
- Error handling: What happens when things fail
- Testing: How we verify it works

### Phase 4: Document

Write design to `docs/plans/YYYY-MM-DD-<topic>-design.md`

## Counter-Architecture Rule

Every recommendation MUST include at least one counter-argument challenging your primary choice. This prevents biased, homogenized designs.

## Hallucination Firewall

Every recommended 3rd-party library MUST be validated (`npm info` or equivalent) before the plan is finalized. AI hallucinates packages.
