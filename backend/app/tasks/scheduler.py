"""
Scheduler Tasks - Celery tasks for auto-scheduling calls

These tasks run in the background to automatically call customers
with expiring policies.
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

from celery import shared_task
import httpx

logger = logging.getLogger(__name__)

# Backend API URL for making calls
API_BASE_URL = "http://app:8000/api"


@shared_task(bind=True, max_retries=3)
def call_customer_task(self, customer_id: str, reason: str = "expiring_policy") -> Dict[str, Any]:
    """
    Task to call a single customer.
    
    Args:
        customer_id: The customer ID to call
        reason: Reason for the call (expiring_policy, follow_up, manual)
        
    Returns:
        Dict with call result
    """
    try:
        logger.info(f"Initiating call to customer {customer_id} for reason: {reason}")
        
        # Call the API endpoint to initiate the call
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{API_BASE_URL}/calls/initiate/{customer_id}"
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully initiated call to customer {customer_id}")
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "call_id": result.get("id"),
                    "room_name": result.get("room_name")
                }
            else:
                error = response.json().get("detail", "Unknown error")
                logger.warning(f"Failed to call customer {customer_id}: {error}")
                return {
                    "success": False,
                    "customer_id": customer_id,
                    "error": error
                }
                
    except Exception as e:
        logger.error(f"Error calling customer {customer_id}: {str(e)}")
        # Retry on failure
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def call_expiring_policies_task(self, days_before_expiry: int = 30, max_calls: int = 20) -> Dict[str, Any]:
    """
    Daily task to call customers with expiring policies.
    
    This task:
    1. Gets customers with policies expiring within X days
    2. Filters out customers who have been called recently
    3. Initiates calls to eligible customers
    
    Args:
        days_before_expiry: How many days before expiry to start calling
        max_calls: Maximum number of calls to make in one batch
        
    Returns:
        Dict with batch results
    """
    try:
        logger.info(f"Starting expiring policies call batch - days: {days_before_expiry}, max: {max_calls}")
        
        # Get customers to call from the scheduler service
        with httpx.Client(timeout=30.0) as client:
            # Get pending customers
            response = client.get(
                f"{API_BASE_URL}/scheduler/pending-customers",
                params={"days": days_before_expiry, "limit": max_calls}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get pending customers: {response.text}")
                return {"success": False, "error": "Failed to get pending customers"}
            
            pending = response.json()
            customers_to_call = pending.get("customers", [])
            
            if not customers_to_call:
                logger.info("No customers to call today")
                return {
                    "success": True,
                    "total": 0,
                    "called": 0,
                    "message": "No customers to call"
                }
            
            # Initiate calls
            results = []
            called = 0
            
            for customer in customers_to_call:
                customer_id = customer.get("customer_id")
                
                # Queue individual call task
                call_customer_task.delay(customer_id, "expiring_policy")
                called += 1
                results.append({
                    "customer_id": customer_id,
                    "status": "queued"
                })
            
            logger.info(f"Queued {called} calls for expiring policies")
            
            return {
                "success": True,
                "total": len(customers_to_call),
                "called": called,
                "results": results
            }
            
    except Exception as e:
        logger.error(f"Error in expiring policies batch: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task
def cleanup_old_scheduled_calls(days: int = 30) -> Dict[str, Any]:
    """
    Cleanup task to remove old scheduled call records.
    
    Args:
        days: Remove records older than this many days
        
    Returns:
        Dict with cleanup results
    """
    try:
        logger.info(f"Cleaning up scheduled calls older than {days} days")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(
                f"{API_BASE_URL}/scheduler/cleanup",
                params={"days": days}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Cleaned up {result.get('deleted', 0)} old records")
                return {"success": True, **result}
            else:
                return {"success": False, "error": response.text}
                
    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}")
        return {"success": False, "error": str(e)}
