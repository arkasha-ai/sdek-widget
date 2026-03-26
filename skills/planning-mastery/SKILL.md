---
name: planning-mastery
description: "Concise implementation plans using RFC-Lite format. STRICTLY under 300 lines. Use when: (1) planning a feature, (2) breaking down a task, (3) creating implementation roadmap. Triggers on: plan, roadmap, decompose, декомпозиция, разбить на задачи."
---

# RFC-Lite Planning Protocol

> **The 300-Line Limit:** If your plan exceeds 300 lines, **YOU HAVE FAILED.**
> Code belongs in files, not plans. No pseudo-code. No entire file contents.

## Core Philosophy

Understanding comes before implementation. A well-designed solution is half-implemented.

## Mandatory Template

```markdown
# [Task/Feature Name] - Implementation Plan

## 1. Objective
[1-2 sentences strictly defining the goal.]

## 2. Tech Strategy
- **Pattern:** [e.g. Composition vs Inheritance]
- **State:** [e.g. Global Store vs Local Hook]
- **Constraints:** [e.g. "No external libs"]

## 3. File Changes
| Action | File Path | Brief Purpose |
|:-------|:----------|:--------------|
| [NEW]  | `src/components/X.tsx` | Visual shell |
| [MOD]  | `src/App.tsx` | Routing integration |

## 4. Execution Sequence
1. **Scaffold:** Create component files with types (No logic yet).
2. **Logic:** Implement hook with TDD.
3. **Visuals:** Apply styles.
4. **Connect:** Wire up to parent.

## 5. Verification
- [ ] Tests pass
- [ ] No console errors
- [ ] Blast radius checked
```

## Zero Tolerance Rules

1. **NO CODE BLOCKS** in the plan
2. **NO EXPLANATIONS** — don't teach why React is good
3. **NO CONVERSATION** — don't talk to the user in the plan
4. **STAY HIGH LEVEL** — "Implement Auth" > "Write function login() { ... }"

## Blast Radius Mapping

Before defining file changes:
- Identify which existing features or tests might break
- If change requires modifying >5 files for one feature → pause, propose architectural abstraction instead
