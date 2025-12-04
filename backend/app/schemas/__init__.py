"""
Schemas Package

Exports all request/response schemas for the API.
Schemas are Pydantic models for data validation.
"""
from .product import ProductCreate, ProductUpdate, ProductResponse
from .customer import CustomerCreate, CustomerUpdate, CustomerResponse
from .policy import PolicyCreate, PolicyUpdate, PolicyResponse, PolicyWithDetails
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
    # Policy
    "PolicyCreate",
    "PolicyUpdate",
    "PolicyResponse",
    "PolicyWithDetails",
    # Call
    "CallSummary",
    "CallResponse",
]
