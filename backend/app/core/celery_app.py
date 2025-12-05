"""
Celery Application Configuration

Configures Celery for background task processing with Redis as broker.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Redis URL from environment or default
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create Celery app
celery_app = Celery(
    "insurance_scheduler",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.app.tasks.scheduler"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "call-expiring-policies-daily": {
            "task": "backend.app.tasks.scheduler.call_expiring_policies_task",
            # Default: Run every day at 10:00 AM IST
            "schedule": crontab(hour=10, minute=0),
            "args": (),
        },
    },
)

# Optional: Dynamic schedule loading
# The schedule can be updated via API and stored in Redis
