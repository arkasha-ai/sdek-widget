---
name: git-worktrees
description: "Create isolated git workspaces for feature development. Safety verification, cross-platform support. Use when: (1) working on feature branch, (2) need parallel development, (3) experimental changes. Triggers on: worktree, isolated branch, parallel development, feature branch."
---

# Git Worktrees: Isolated Workspaces

> **Philosophy:** Isolation prevents contamination. Work on features without affecting the main workspace.

## When to Use

**Use before:**
- Starting new feature development
- Making experimental changes
- Working on multiple features in parallel
- Running long processes without blocking

**Skip for:**
- Quick bug fixes on current branch
- Documentation updates
- Configuration changes

## Directory Selection

Priority order:
1. Check `.worktrees/` (preferred, hidden)
2. Check `worktrees/`
3. Check project config for preference
4. Ask user

## Safety Verification

**MUST verify directory is git-ignored before creating worktree:**

```bash
git check-ignore -q .worktrees 2>/dev/null
```

If NOT ignored:
1. Add to `.gitignore`
2. Commit the change
3. Proceed

## Workflow

### Create Worktree

```bash
# Create from new branch
git worktree add .worktrees/feature-name -b feature/name

# Create from existing branch
git worktree add .worktrees/feature-name feature/name
```

### Work in Worktree

```bash
cd .worktrees/feature-name
# Work normally — all git operations are isolated
npm install  # Install deps for this worktree
npm test     # Run tests in isolation
```

### Clean Baseline

Before starting work, run tests in the new worktree to verify clean state:

```bash
cd .worktrees/feature-name
npm test  # Must pass BEFORE any changes
```

### Cleanup

```bash
# When feature is complete
git worktree remove .worktrees/feature-name

# List all worktrees
git worktree list
```

## Rules

- Never create worktrees in tracked directories
- Always verify clean baseline before starting
- One worktree per feature branch
- Clean up after merge/close
