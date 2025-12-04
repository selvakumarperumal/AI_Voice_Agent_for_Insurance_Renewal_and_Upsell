"""
Services Package

This package contains all business logic and database operations.
Routes should call these services instead of doing direct DB operations.

Services:
    - product_service: Product catalog CRUD operations
    - policy_service: Policy management and expiry tracking
    - customer_service: Customer CRUD operations
    - call_service: Call initiation and tracking
    - caller: LiveKit SIP calling (low-level)

Architecture:
    Route -> Service -> Database/External APIs
"""

from .product_service import (
    create_product,
    get_product,
    get_product_by_code,
    list_products,
    update_product,
    delete_product,
)

from .policy_service import (
    create_policy,
    get_policy,
    get_policy_by_number,
    get_customer_policies,
    get_expiring_policies,
    list_policies,
    update_policy,
    cancel_policy,
)

from .customer_service import (
    create_customer,
    get_customer,
    get_customer_by_phone,
    get_customer_by_email,
    list_customers,
    update_customer,
    delete_customer,
    search_customers,
    get_customers_with_expiring_policies,
)

from .call_service import (
    initiate_call,
    call_customers_with_expiring_policies,
    get_call,
    get_call_by_room,
    get_customer_calls,
    list_calls,
    update_call_status,
    update_call_summary,
    get_active_calls,
)

__all__ = [
    # Product service
    "create_product",
    "get_product",
    "get_product_by_code",
    "list_products",
    "update_product",
    "delete_product",
    # Policy service
    "create_policy",
    "get_policy",
    "get_policy_by_number",
    "get_customer_policies",
    "get_expiring_policies",
    "list_policies",
    "update_policy",
    "cancel_policy",
    # Customer service
    "create_customer",
    "get_customer",
    "get_customer_by_phone",
    "get_customer_by_email",
    "list_customers",
    "update_customer",
    "delete_customer",
    "search_customers",
    "get_customers_with_expiring_policies",
    # Call service
    "initiate_call",
    "call_customers_with_expiring_policies",
    "get_call",
    "get_call_by_room",
    "get_customer_calls",
    "list_calls",
    "update_call_status",
    "update_call_summary",
    "get_active_calls",
]
