---
name: clean-code
description: "Foundation skill for ALL code output. LLM Firewall, supply chain security, SOLID, no placeholders. Use for: (1) any code generation, (2) code review, (3) refactoring, (4) dependency audit. Triggers on: code, refactor, clean up, review code, SOLID, dependencies."
---

# Clean Code: The Foundation

> **Philosophy:** This skill applies to ALL code. Every piece must pass these gates.

## Iron Laws

1. **NO HALLUCINATED PACKAGES** — Verify before import
2. **NO LAZY PLACEHOLDERS** — Code must be runnable
3. **NO SECURITY SHORTCUTS** — Production-ready defaults
4. **NO OVER-ENGINEERING** — Simplest solution first

## Protocol 1: Supply Chain Security

- **Verify before import** — `npm search` or `pip show` for unfamiliar packages
- **Prefer battle-tested** — lodash, date-fns, zod over obscure alternatives
- **Pin versions** in production — no `^` or `~` for critical deps
- **Never import AI wrapper libraries** without verification
- **Official SDKs only** — openai, anthropic, google-generativeai

## Protocol 2: Security-First Defaults

**Frontend — Forbidden:**
- `dangerouslySetInnerHTML` → use DOMPurify
- `eval()`, `new Function()` → static code only
- Tokens in localStorage → httpOnly cookies

**Backend — Forbidden:**
- `CORS: *` → explicit origin whitelist
- Raw SQL strings → parameterized queries
- `chmod 777` → principle of least privilege
- Hardcoded secrets → env variables + validation

## Protocol 3: No Lazy Placeholders

**Banned:**
```
// TODO: Implement this
// ... logic goes here
function placeholder() { }
throw new Error('Not implemented');
```

Every function must be runnable. Break into smaller complete functions if too complex.

## Protocol 4: Modularity (50/300 Rule)

- Functions > 50 lines → break down
- Files > 300 lines → split into modules

**SOLID Quick Check:**

| Principle | Check |
|-----------|-------|
| **S**ingle Responsibility | Does this do ONE thing? |
| **O**pen/Closed | Can I extend without modifying? |
| **L**iskov Substitution | Can subtypes replace parent? |
| **I**nterface Segregation | Are interfaces minimal? |
| **D**ependency Inversion | Do I depend on abstractions? |

## Protocol 5: YAGNI

- No AbstractFactoryBuilderManager for simple functions
- No 10 layers of abstraction for CRUD
- No "future-proofing" for requirements that don't exist
- **Native First:** `n % 2 !== 0` instead of `npm install is-odd`

## Protocol 6: AI-Era Considerations

When AI writes code:
1. Verify imports exist (AI hallucinates packages)
2. Check types are correct (AI guesses at APIs)
3. Test edge cases (AI misses boundary conditions)
4. Review security (AI takes shortcuts)

## Audit Checklist (Before Commit)

- [ ] No hallucinated imports
- [ ] No TODO/FIXME/placeholder
- [ ] No hardcoded secrets
- [ ] Functions under 50 lines
- [ ] Files under 300 lines
