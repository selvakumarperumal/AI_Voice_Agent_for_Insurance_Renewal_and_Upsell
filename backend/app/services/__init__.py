"""Services Package - Business logic and database operations."""

from .product_service import (
    create_product, get_product, get_product_by_code,
    list_products, update_product, delete_product,
)

from .policy_service import (
    create_policy, get_policy, get_policy_by_number,
    get_customer_policies, get_expiring_policies,
    list_policies, update_policy, cancel_policy,
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

__all__ = [
    # Product
    "create_product", "get_product", "get_product_by_code",
    "list_products", "update_product", "delete_product",
    # Policy
    "create_policy", "get_policy", "get_policy_by_number",
    "get_customer_policies", "get_expiring_policies",
    "list_policies", "update_policy", "cancel_policy",
    # Customer
    "create_customer", "get_customer", "get_customer_by_phone", "get_customer_by_email",
    "list_customers", "update_customer", "delete_customer",
    "search_customers", "get_customers_with_expiring_policies",
    # Call
    "initiate_call", "batch_call_expiring", "get_call", "get_call_by_room",
    "list_calls", "update_status", "update_summary", "get_active",
]
