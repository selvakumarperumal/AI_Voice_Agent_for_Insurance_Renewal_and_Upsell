"""
Schemas Package

Exports all request/response schemas for the API.
Schemas are Pydantic models for data validation.
"""
from .product import ProductCreate, ProductUpdate, ProductResponse
from .customer import CustomerCreate, CustomerUpdate, CustomerResponse
from .policy import PolicyCreate, PolicyUpdate, PolicyResponse, PolicyWithProduct
from .customer_policy import (
    CustomerPolicyCreate, CustomerPolicyUpdate, 
    CustomerPolicyResponse, CustomerPolicyWithDetails
)
from .call import CallSummary, CallResponse

__all__ = [
    # Product
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    # Customer
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    # Policy (templates)
    "PolicyCreate",
    "PolicyUpdate",
    "PolicyResponse",
    "PolicyWithProduct",
    # CustomerPolicy (subscriptions)
    "CustomerPolicyCreate",
    "CustomerPolicyUpdate",
    "CustomerPolicyResponse",
    "CustomerPolicyWithDetails",
    # Call
    "CallSummary",
    "CallResponse",
]

