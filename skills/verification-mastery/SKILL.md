---
name: verification-mastery
description: "Evidence before claims, always. No completion claims without fresh verification. Use when: (1) claiming a task is done, (2) reporting success, (3) debugging issues, (4) checking if something works. Triggers on: готово, сделано, работает, проверь, done, fixed, complete."
---

# Verification Mastery

> **Philosophy:** Claiming work is complete without verification is dishonesty, not efficiency.

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command **in this message**, you cannot claim it passes.

## The Gate Function

Before claiming any status:
1. **IDENTIFY** — What command proves this claim?
2. **RUN** — Execute the FULL command (fresh, complete)
3. **READ** — Full output, check exit code
4. **VERIFY** — Does output confirm the claim?
5. **ONLY THEN** — Make the claim WITH evidence

Skip any step = lying, not verifying.

## Evidence Requirements

| Claim | Requires | NOT Sufficient |
|-------|----------|----------------|
| "Tests pass" | Test command output: 0 failures | Previous run, "should pass" |
| "Linter clean" | Linter output: 0 errors | Partial check |
| "Build succeeds" | Build command: exit 0 | Logs look good |
| "Bug fixed" | Test original symptom: passes | Code changed |
| "Server runs" | `curl localhost:PORT/health` returns 200 | Process running |
| "Agent completed" | VCS diff shows changes | Agent reports "success" |

## Red Flags — STOP Immediately

If you catch yourself saying:
- "should", "probably", "seems to"
- "Great!", "Perfect!", "Done!" (before verification)
- "Just this once"
- "I'm confident"
- "I'm tired"

**ALL of these require: STOP. Run verification. THEN speak.**

## For AI Agents

When a sub-agent reports "success":
1. Do NOT trust — verify independently
2. Run the actual test/command yourself
3. Show the fresh output as evidence
4. Only then relay the result upstream
