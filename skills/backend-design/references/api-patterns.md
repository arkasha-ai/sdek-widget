# API Patterns

## RESTful Conventions

### Resource Naming
```
GET    /orders          # List
POST   /orders          # Create
GET    /orders/:id      # Read
PATCH  /orders/:id       # Partial update
DELETE /orders/:id      # Delete
```

### Status Codes
| Code | Use |
|------|-----|
| 200 | Success (with body) |
| 201 | Created |
| 204 | Success (no body) |
| 400 | Validation error |
| 401 | Unauthenticated |
| 403 | Unauthorized |
| 404 | Not found |
| 409 | Conflict |
| 422 | Business rule violation |
| 429 | Rate limited |
| 500 | Server error |

## Pagination

### Cursor-Based (Preferred)
```typescript
// Request
GET /orders?cursor=2024-01-01T00:00:00Z&limit=20

// Response
{
  "data": [...],
  "nextCursor": "2024-01-02T00:00:00Z",
  "hasMore": true
}
```

### Offset-Based (Only for Small Tables)
```typescript
GET /orders?offset=0&limit=20
// MAX offset: 10,000
```

## Error Response Format (RFC 7807)

```typescript
// Always include:
interface ProblemDetail {
  type: string;    // URI reference to error type
  title: string;   // Short description
  status: number;  // HTTP status code
  detail: string;  // Human-readable detail
  instance: string; // Request path
}

// Example
{
  "type": "https://api.app.com/errors/validation",
  "title": "Validation Failed",
  "status": 400,
  "detail": "Field 'email' must be a valid email address",
  "instance": "/orders"
}
```

## Idempotency Implementation

```typescript
async function handleRequest(req: Request) {
  const idempotencyKey = req.headers.get('Idempotency-Key');
  
  if (!idempotencyKey) {
    throw new Error('Idempotency-Key header required for this endpoint');
  }
  
  const cacheKey = `idempotency:${idempotencyKey}`;
  const cached = await redis.get(cacheKey);
  
  if (cached) {
    return JSON.parse(cached);
  }
  
  // Execute business logic
  const result = await processOrder(req.body);
  
  // Cache for 24 hours
  await redis.setex(cacheKey, 86400, JSON.stringify(result));
  
  return result;
}
```

## Event-Driven Communication

### Outbox Pattern
```sql
CREATE TABLE outbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  aggregate_type VARCHAR(100),
  aggregate_id UUID,
  event_type VARCHAR(100),
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  processed_at TIMESTAMPTZ NULL
);
```

```typescript
// In same transaction as business operation
await db.transaction(async (trx) => {
  await trx.insert(orders).values(orderData);
  await trx.insert(outbox).values({
    aggregateType: 'Order',
    aggregateId: orderId,
    eventType: 'OrderCreated',
    payload: JSON.stringify({ orderId, userId, total })
  });
});
```
