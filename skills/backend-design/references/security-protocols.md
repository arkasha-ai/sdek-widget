# Security Protocols

## Token Strategy

### PASETO v4 (Preferred)
```
PASETO v4.public.xxxxxx...  # Ed25519 signed
```
- Stateless, non-extensible
- No algorithm confusion attacks

### JWT (If forced)
- Algorithm: RS256 or ES256 (asymmetric)
- NEVER HS256 (symmetric, key confusion attacks)
- Claims: `iss`, `aud`, `exp`, `iat`, `jti`
- Rotation: publish new public key

## Input Validation

### Schema-First
```typescript
import { z } from 'zod';

const CreateOrderSchema = z.object({
  userId: z.string().uuid(),
  items: z.array(z.object({
    productId: z.string().uuid(),
    quantity: z.number().int().positive().max(100)
  })).min(1).max(50)
});

// Validate BEFORE any logic
const data = CreateOrderSchema.parse(body);
```

### SQL Injection Prevention
- NEVER concatenate user input into SQL
- Use parameterized queries exclusively
- Whitelist validation for dynamic sort columns

## Rate Limiting

| Endpoint Type | Limit |
|---------------|-------|
| Auth | 5/min per IP |
| API | 100/min per user |
| Public | 1000/min per IP |

## Secrets Management

- NEVER commit secrets to VCS
- Use environment variables with validation (zod schema)
- Rotate secrets: 90-day cycle for API keys
- Audit log for secret access

## CORS Policy

```typescript
const corsOptions = {
  origin: process.env.ALLOWED_ORIGINS?.split(',') || [],
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization', 'Idempotency-Key'],
  credentials: true,
  maxAge: 86400
};
```
