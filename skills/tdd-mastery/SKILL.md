---
name: tdd-mastery
description: "Test-Driven Development Iron Law. Write the test first. Watch it fail. Write minimal code to pass. Use when: (1) writing new code, (2) fixing bugs, (3) wanting to ensure reliability. Triggers on: tdd, test, покрыть тестами, юнит-тест, integration test."
---

# TDD Mastery

> **Philosophy:** If you didn't watch the test fail, you don't know if it tests the right thing.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? **Delete it. Start over.**

## Red-Green-Refactor Cycle

### Phase 1: RED — Write Failing Test

Write one minimal test showing what should happen:

```typescript
test('retries failed operations 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };

  const result = await retryOperation(operation);
  expect(result).toBe('success');
  expect(attempts).toBe(3);
});
```

**Requirements:**
- One behavior per test
- Clear, descriptive name
- Real code (mocks only if unavoidable)

### Phase 2: VERIFY RED — Watch It Fail

**MANDATORY. Never skip.**

```bash
npm test path/to/test.test.ts
# or
pytest tests/path/test.py::test_name -v
```

Confirm:
- Test fails (not errors)
- Failure message is expected
- Fails because feature missing (not typos)

**Test passes?** You're testing existing behavior. Fix test.

### Phase 3: GREEN — Minimal Code

Write **simplest code** to pass the test. Just enough.

```typescript
async function retryOperation<T>(fn: () => Promise<T>): Promise<T> {
  for (let i = 0; i < 3; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === 2) throw e;
    }
  }
  throw new Error('unreachable');
}
```

**Bad:** Adding maxRetries parameter, backoff options, onRetry callback — YAGNI.

### Phase 4: VERIFY GREEN — Watch It Pass

```bash
npm test path/to/test.test.ts
```

Confirm:
- Test passes
- Other tests still pass
- No errors, no warnings

### Phase 5: REFACTOR — Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Don't add behavior.

## Good Test Qualities

| Quality | Good | Bad |
|---------|------|-----|
| **Minimal** | One thing. "and" in name? Split it. | `test('validates email and domain and whitespace')` |
| **Clear** | Name describes behavior | `test('test1')` |
| **Real behavior** | Tests actual code | Tests mock behavior |

## Common Excuses (All Invalid)

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'll add tests later" | Later = never |
| "This code is simple" | Simple bugs still need tests |
