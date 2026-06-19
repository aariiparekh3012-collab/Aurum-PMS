# Transactional Outbox Pattern

This document explains the transactional outbox pattern used to ensure reliable event publishing and eventual consistency across services.

## Problem

When a domain event needs to be published to external systems (message bus, other services), two things must happen atomically:
1. The aggregate state changes in the database
2. The event is published to the message bus

If either fails, we have consistency problems:
- **State changes but event lost** → downstream systems miss important updates
- **Event published but state not saved** → event is received but aggregates has no record

The solution is the **transactional outbox pattern**.

## Solution: Transactional Outbox

```
Domain Event
    ↓
OnboardingApplication.approve()
    ├─ Aggregate state changes ✓
    └─ Domain event recorded in same TX ✓
         ↓
Application.execute()
    ├─ DB transaction commits (aggregate + event in OUTBOX table)
    └─ Outbox relay picks it up asynchronously
         ↓
Outbox Worker (separate process)
    ├─ Read unpublished events
    ├─ Dispatch to in-process handlers (e.g., provision client)
    ├─ Publish to message bus (Redis, RabbitMQ, etc.)
    └─ Mark as published (only after success)
         ↓
Downstream Subscribers
    └─ React to events (portfolio provisioning, compliance dashboard, etc.)
```

### Why This Works

1. **Single DB transaction** — Aggregate changes + event write are atomic (all-or-nothing)
2. **At-least-once delivery** — Event stays in outbox until successfully published
3. **Decoupled publisher & subscriber** — No synchronous coupling to external systems
4. **Graceful degradation** — If message bus is down, events queue in DB and retry

## Implementation

### 1. Database Schema

```sql
CREATE TABLE event_outbox (
    id UUID PRIMARY KEY,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    payload JSONB NOT NULL,
    published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_outbox_unpublished ON event_outbox(published, created_at);
```

### 2. Domain Event Recording

When an aggregate transitions state, it records domain events:

```python
# app/domain/onboarding/entities.py
class OnboardingApplication:
    def approve(self, *, approved_by: str) -> None:
        self._transition(OnboardingStatus.ACTIVE)
        self._events.append(
            events.OnboardingActivated(
                aggregate_id=self.id,
                approved_by=approved_by
            )
        )
```

### 3. Transactional Publishing

Events are written to the outbox in the same transaction as the aggregate:

```python
# app/infrastructure/audit/event_publisher.py
class OutboxEventPublisher(EventPublisher):
    def publish(self, events: list) -> None:
        for event in events:
            self._session.add(
                OutboxModel(
                    aggregate_id=event.aggregate_id,
                    event_type=type(event).__name__,
                    payload=dataclasses.asdict(event),
                    created_at=datetime.now(timezone.utc),
                )
            )
        self._session.flush()  # Part of the SAME transaction
```

### 4. Outbox Relay Worker

A separate process polls the outbox and publishes events:

```bash
# Start the worker
python scripts/process_outbox.py

# Or with custom settings
OUTBOX_BATCH_SIZE=50 OUTBOX_POLL_INTERVAL=2 python scripts/process_outbox.py

# One-shot mode (for cron jobs)
OUTBOX_ONE_SHOT=1 python scripts/process_outbox.py
```

**What the worker does:**

```python
# app/infrastructure/events/outbox_dispatcher.py
class OutboxDispatcher:
    def process_pending(self, *, batch_size: int = 100) -> int:
        # 1. Select unpublished events (with row-level locking)
        events = db.query(OutboxModel)\
            .filter(published==False)\
            .with_for_update(skip_locked=True)\
            .limit(batch_size)
        
        for event in events:
            try:
                # 2. Dispatch to in-process handlers
                if event.event_type == "OnboardingActivated":
                    provision_client(event.aggregate_id)
                
                # 3. Publish to message bus
                message_bus.publish(EventMessage(...))
                
                # 4. Mark as published (only after both succeed)
                event.published = True
                
            except Exception:
                # Leave unpublished for retry
                log_error(...)
        
        db.commit()
        return len(processed)
```

## Message Bus Integration

### No-Op (Local Dev)

By default, events are logged but not published to any external system:

```python
# NoOpMessageBus just logs
message_bus = NoOpMessageBus()
message_bus.publish(event)  # Logs "event_published_noop"
```

### Redis Pub/Sub (Production)

Set `REDIS_URL` to enable Redis publishing:

```bash
REDIS_URL=redis://localhost:6379/0 python scripts/process_outbox.py
```

Events are published to channels named after event type:

```
Event Type          → Redis Channel
OnboardingActivated → onboarding.activated
KycVerified         → kyc.verified
RiskProfiled        → risk.profiled
```

Subscribers can listen:

```python
import redis

r = redis.Redis.from_url("redis://localhost:6379")
pubsub = r.pubsub()
pubsub.subscribe("onboarding.activated")

for message in pubsub.listen():
    if message["type"] == "message":
        event = json.loads(message["data"])
        # Handle event
        handle_onboarding_activated(event)
```

### RabbitMQ (Alternative)

To add RabbitMQ support:

1. Create `app/infrastructure/external/rabbitmq_message_bus.py`
2. Implement `MessageBusPort` interface
3. Update config to detect RabbitMQ URL
4. Deploy RabbitMQ with PMS stack

## Deployment

### Docker Compose

```yaml
version: "3.9"

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: portfolio_db
      POSTGRES_PASSWORD: postgres

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/portfolio_db
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis

  outbox-worker:
    build: ./backend
    command: python scripts/process_outbox.py
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/portfolio_db
      REDIS_URL: redis://redis:6379/0
      OUTBOX_BATCH_SIZE: 50
      OUTBOX_POLL_INTERVAL: 2
    depends_on:
      - db
      - redis
```

Run:

```bash
docker-compose up
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pms-outbox-worker
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pms-outbox-worker
  template:
    metadata:
      labels:
        app: pms-outbox-worker
    spec:
      containers:
      - name: worker
        image: pms:latest
        command: ["python", "scripts/process_outbox.py"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: pms-secrets
              key: database_url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: pms-config
              key: redis_url
        - name: OUTBOX_BATCH_SIZE
          value: "100"
        - name: OUTBOX_POLL_INTERVAL
          value: "5"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command: ["python", "-c", "import sys; exit(0)"]
          initialDelaySeconds: 30
          periodSeconds: 60
```

Deploy:

```bash
kubectl apply -f outbox-worker.yaml
```

## Monitoring

### Metrics to Track

1. **Outbox backlog** — Events published=false
   ```sql
   SELECT COUNT(*) FROM event_outbox WHERE published = FALSE;
   ```

2. **Event age** — Oldest unpublished event
   ```sql
   SELECT MIN(created_at) FROM event_outbox WHERE published = FALSE;
   ```

3. **Processing latency** — Time from created_at to published
   ```sql
   SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) 
   FROM event_outbox WHERE published = TRUE;
   ```

4. **Worker health** — Check worker process is running
   ```bash
   ps aux | grep process_outbox.py
   ```

### Alerts

Set up alerts for:

- **Backlog > threshold** (e.g., > 1000 unpublished events)
  - Indicates worker is slow or down
  - Action: check worker logs, increase batch size / polling frequency

- **Event age > threshold** (e.g., > 5 minutes)
  - Events not being processed in timely manner
  - Action: restart worker, check database performance

- **Worker not running**
  - No events processed in last 5 min (with steady traffic)
  - Action: restart worker process / pod

### Logging

Worker logs structured events:

```json
{
  "timestamp": "2026-06-08T10:30:00Z",
  "level": "INFO",
  "logger": "outbox_worker",
  "message": "event_processed",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "OnboardingActivated",
  "aggregate_id": "app-uuid",
  "duration_ms": 150
}
```

View logs:

```bash
# Local
tail -f backend.log | grep outbox_worker

# Docker
docker logs pms-outbox-worker

# Kubernetes
kubectl logs -f deployment/pms-outbox-worker
```

## Testing

### Unit Tests

```python
def test_outbox_dispatcher_publishes_to_bus():
    mock_bus = Mock(spec=MessageBusPort)
    dispatcher = OutboxDispatcher(session, provision_uc, mock_bus)
    
    # Create event
    app = OnboardingApplication.create(...)
    app.approve(approved_by="officer@example.com")
    session.add(app)
    session.commit()
    
    # Process outbox
    count = dispatcher.process_pending()
    
    assert count == 1
    assert mock_bus.publish.called
```

### Integration Tests

```python
def test_outbox_to_redis_integration():
    """Test event flows from DB outbox to Redis Pub/Sub"""
    redis_bus = RedisMessageBus()
    dispatcher = OutboxDispatcher(session, provision_uc, redis_bus)
    
    # Subscribe to events
    pubsub = redis.pubsub()
    pubsub.subscribe("onboarding.activated")
    
    # Create and approve application
    approve_application(app_id)
    
    # Process outbox
    dispatcher.process_pending()
    
    # Verify event was published to Redis
    message = pubsub.get_message(timeout=1)
    assert message["type"] == "message"
    assert "OnboardingActivated" in message["data"]
```

## Troubleshooting

### Events Not Publishing

**Symptom:** `published=false` events pile up in outbox

**Diagnosis:**
```sql
SELECT COUNT(*) FROM event_outbox WHERE published = FALSE;
SELECT MIN(created_at) FROM event_outbox WHERE published = FALSE;
```

**Check:** Is worker running?
```bash
ps aux | grep process_outbox.py
```

**Check:** Are there errors in worker logs?
```bash
OUTBOX_ONE_SHOT=1 python scripts/process_outbox.py
```

**Fix:**
1. If worker crashed, restart it
2. If message bus is down, bring it up
3. If handler is failing, check application logs

### High Latency

**Symptom:** Events take > 1 minute to publish

**Check:** Worker batch size & polling interval
```bash
# Increase batch size, decrease poll interval
OUTBOX_BATCH_SIZE=200 OUTBOX_POLL_INTERVAL=1 python scripts/process_outbox.py
```

**Check:** Database query performance
```sql
EXPLAIN ANALYZE
SELECT * FROM event_outbox 
WHERE published = FALSE 
ORDER BY created_at ASC LIMIT 100;
```

### Message Bus Errors

**Symptom:** "Redis connection failed" in logs

**Check:** Redis is running
```bash
redis-cli PING  # Should return PONG
```

**Fix:** 
- Restart Redis
- Update `REDIS_URL` in config
- Or remove `REDIS_URL` to fall back to no-op mode

## Further Reading

- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
- [Transactional Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [SEBI Portfolio Manager Record Keeping](https://www.sebi.gov.in/sebi_data/PM_Regulations_2020.pdf)
