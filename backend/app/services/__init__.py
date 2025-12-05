"""Services Package - Business logic and database operations."""

from .product_service import (
    create_product, get_product, get_product_by_code,
    list_products, update_product, delete_product,
)

from .policy_service import (
    create_policy, get_policy, get_policy_by_number,
    list_policies, list_policies_with_products, update_policy, delete_policy,
)

from .customer_policy_service import (
    attach_policy_to_customer, get_customer_policies,
    get_expiring_customer_policies, detach_policy_from_customer,
    update_customer_policy,
)

from .customer_service import (
    create_customer, get_customer, get_customer_by_phone, get_customer_by_email,
    list_customers, update_customer, delete_customer,
    search_customers, get_customers_with_expiring_policies,
)

from .call_service import (
    initiate_call, batch_call_expiring, get_call, get_call_by_room,
    list_calls, update_status, update_summary, get_active,
)

from . import scheduler_service

__all__ = [
    # Product
    "create_product", "get_product", "get_product_by_code",
    "list_products", "update_product", "delete_product",
    # Policy (templates)
    "create_policy", "get_policy", "get_policy_by_number",
    "list_policies", "list_policies_with_products", "update_policy", "delete_policy",
    # CustomerPolicy (subscriptions)
    "attach_policy_to_customer", "get_customer_policies",
    "get_expiring_customer_policies", "detach_policy_from_customer",
    "update_customer_policy",
    # Customer
    "create_customer", "get_customer", "get_customer_by_phone", "get_customer_by_email",
    "list_customers", "update_customer", "delete_customer",
    "search_customers", "get_customers_with_expiring_policies",
    # Call
    "initiate_call", "batch_call_expiring", "get_call", "get_call_by_room",
    "list_calls", "update_status", "update_summary", "get_active",
    # Scheduler
    "scheduler_service",
]


