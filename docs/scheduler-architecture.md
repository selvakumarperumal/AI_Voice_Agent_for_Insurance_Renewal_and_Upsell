# Scheduler Backend Architecture

## What is Celery?

**Celery** is a distributed task queue system that allows you to run tasks in the background, outside of your main application. It's perfect for:
- Scheduled jobs (like calling customers daily)
- Long-running tasks (like sending bulk emails)
- Tasks that shouldn't block your API

---

## The Three Components

### 1. Redis (Message Broker)

```
┌─────────────────────────────────────────────────────────────────┐
│                         REDIS                                    │
│                                                                  │
│   Think of Redis as a "Post Office"                              │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  QUEUE: insurance_scheduler                               │  │
│   │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐             │  │
│   │  │ Task 1 │ │ Task 2 │ │ Task 3 │ │ Task 4 │  ...        │  │
│   │  └────────┘ └────────┘ └────────┘ └────────┘             │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   - Stores tasks in a queue (First In, First Out)               │
│   - Workers pick up tasks from here                              │
│   - Very fast, in-memory storage                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Redis acts as the messenger between Beat and Worker.**

---

### 2. Celery Beat (The Scheduler)

```
┌─────────────────────────────────────────────────────────────────┐
│                      CELERY BEAT                                 │
│                                                                  │
│   Think of Beat as an "Alarm Clock"                              │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  SCHEDULE:                                                │  │
│   │                                                           │  │
│   │  "call-expiring-policies-daily":                          │  │
│   │      - Task: call_expiring_policies_task                  │  │
│   │      - Time: Every day at 10:00 AM                        │  │
│   │                                                           │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   What Beat does:                                                │
│   1. Constantly checks: "Is it time to run any task?"           │
│   2. When it's 10:00 AM → Sends task to Redis queue             │
│   3. Beat does NOT execute tasks, only schedules them           │
│                                                                  │
│   Docker: insurance_celery_beat                                  │
│   Command: celery -A backend.app.core.celery_app beat            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Beat is like a cron job - it triggers tasks at specific times.**

---

### 3. Celery Worker (The Executor)

```
┌─────────────────────────────────────────────────────────────────┐
│                      CELERY WORKER                               │
│                                                                  │
│   Think of Worker as the "Employee"                              │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  WHAT WORKER DOES:                                        │  │
│   │                                                           │  │
│   │  1. Constantly watches Redis queue for new tasks          │  │
│   │  2. Picks up a task from the queue                        │  │
│   │  3. Executes the Python function                          │  │
│   │  4. Reports result back to Redis                          │  │
│   │  5. Goes back to step 1                                   │  │
│   │                                                           │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   In our case, Worker runs:                                      │
│   - call_expiring_policies_task()                                │
│   - call_customer_task()                                         │
│                                                                  │
│   Docker: insurance_celery_worker                                │
│   Command: celery -A backend.app.core.celery_app worker          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Worker does the actual work - calling customers, querying database, etc.**

---

## Complete Flow: What Happens at 10:00 AM

```
TIME: 10:00 AM IST
═══════════════════════════════════════════════════════════════════════════════

STEP 1: Celery Beat checks its schedule
────────────────────────────────────────
    ┌─────────────┐
    │ Celery Beat │ ──▶ "It's 10:00 AM! Time to run call_expiring_policies_task"
    └─────────────┘


STEP 2: Beat sends task to Redis
────────────────────────────────────────
    ┌─────────────┐          ┌─────────┐
    │ Celery Beat │ ────────▶│  Redis  │
    └─────────────┘   task   └─────────┘
                              Queue: [call_expiring_policies_task]


STEP 3: Worker picks up task from Redis
────────────────────────────────────────
    ┌─────────┐          ┌────────────────┐
    │  Redis  │ ────────▶│ Celery Worker  │
    └─────────┘   task   └────────────────┘
    Queue: []            "Got a task! Starting execution..."


STEP 4: Worker calls FastAPI to get pending customers
────────────────────────────────────────
    ┌────────────────┐          ┌─────────┐          ┌────────────┐
    │ Celery Worker  │ ────────▶│ FastAPI │ ────────▶│ PostgreSQL │
    └────────────────┘   HTTP   └─────────┘   SQL    └────────────┘
                         GET /scheduler/pending-customers


STEP 5: Worker initiates call for each customer
────────────────────────────────────────
    ┌────────────────┐          ┌─────────┐          ┌─────────┐
    │ Celery Worker  │ ────────▶│ FastAPI │ ────────▶│ LiveKit │
    └────────────────┘   HTTP   └─────────┘   Call   └─────────┘
                    POST /calls/initiate/customer123
                                                         │
                                                         ▼
                                                  📞 Customer Phone


STEP 6: Results saved to database
────────────────────────────────────────
    ┌─────────┐          ┌────────────┐
    │ FastAPI │ ────────▶│ PostgreSQL │
    └─────────┘   SQL    └────────────┘
                         INSERT INTO calls (...)
                         UPDATE scheduled_calls SET status='completed'


═══════════════════════════════════════════════════════════════════════════════
Done! Worker goes back to watching Redis for more tasks.
```

---

## Code Files

### celery_app.py (Configuration)
```python
# Location: backend/app/core/celery_app.py

celery_app = Celery(
    broker="redis://redis:6379/0",  # Redis connection
    include=["backend.app.tasks.scheduler"]  # Tasks module
)

# Schedule configuration
celery_app.conf.beat_schedule = {
    "call-expiring-policies-daily": {
        "task": "backend.app.tasks.scheduler.call_expiring_policies_task",
        "schedule": crontab(hour=10, minute=0),  # 10:00 AM
    },
}
```

### scheduler.py (Tasks)
```python
# Location: backend/app/tasks/scheduler.py

@shared_task
def call_expiring_policies_task():
    # 1. Get pending customers from API
    # 2. For each customer, queue a call task
    # 3. Return summary

@shared_task
def call_customer_task(customer_id):
    # 1. Call the API to initiate call
    # 2. Return result
```

---

## Docker Compose Configuration

```yaml
# Celery Worker - Executes tasks
celery_worker:
  command: celery -A backend.app.core.celery_app worker --loglevel=info
  depends_on:
    - redis
    - db

# Celery Beat - Schedules tasks  
celery_beat:
  command: celery -A backend.app.core.celery_app beat --loglevel=info
  depends_on:
    - redis
```

---

## Simple Analogy

```
┌────────────────────────────────────────────────────────────────┐
│                    RESTAURANT ANALOGY                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   Celery Beat  = Restaurant Manager                            │
│                  "At 12 PM, prepare lunch orders"              │
│                                                                │
│   Redis        = Order Tickets on the Kitchen Counter          │
│                  Holds orders waiting to be made               │
│                                                                │
│   Celery Worker = Chef                                         │
│                  Picks up orders and cooks them                │
│                                                                │
│   FastAPI      = Kitchen Equipment                             │
│                  The actual tools to do the work               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Why This Architecture?

| Problem | Solution |
|---------|----------|
| API can't wait for 100 calls to complete | Worker runs in background |
| Need to run tasks at specific times | Beat schedules them |
| Need reliable task delivery | Redis queues never lose tasks |
| One worker busy? | Add more workers! |
