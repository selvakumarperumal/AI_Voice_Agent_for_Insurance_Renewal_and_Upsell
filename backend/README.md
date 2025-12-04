# AI Voice Agent for Insurance - Backend API

A FastAPI backend for an AI-powered insurance voice agent system with LiveKit SIP calling integration.

## 🏗️ Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   │
│   ├── core/                   # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py           # Environment settings (pydantic-settings)
│   │   └── database.py         # Async database session management
│   │
│   ├── models/                 # SQLModel database models (one file per entity)
│   │   ├── __init__.py         # Exports all models
│   │   ├── product.py          # Product table
│   │   ├── customer.py         # Customer table
│   │   ├── policy.py           # Policy table
│   │   ├── claim.py            # Claim table
│   │   └── call.py             # Call table
│   │
│   ├── schemas/                # Pydantic schemas for API request/response
│   │   ├── __init__.py         # Exports all schemas
│   │   ├── product.py          # ProductCreate, ProductUpdate, ProductResponse
│   │   ├── customer.py         # CustomerCreate, CustomerUpdate, CustomerResponse
│   │   ├── policy.py           # PolicyCreate, PolicyUpdate, PolicyResponse
│   │   ├── claim.py            # ClaimCreate, ClaimResponse
│   │   └── call.py             # CallSummary, CallResponse
│   │
│   ├── routes/                 # API route handlers (one file per entity)
│   │   ├── __init__.py         # Combines all routers
│   │   ├── products.py         # /products endpoints
│   │   ├── customers.py        # /customers endpoints
│   │   ├── policies.py         # /policies endpoints
│   │   ├── claims.py           # /claims endpoints
│   │   └── calls.py            # /calls endpoints
│   │
│   └── services/               # Business logic layer
│       ├── __init__.py
│       ├── product_service.py  # Product CRUD operations
│       ├── customer_service.py # Customer CRUD operations
│       ├── policy_service.py   # Policy CRUD + renewals
│       ├── claim_service.py    # Claim CRUD operations
│       ├── call_service.py     # Call tracking operations
│       └── caller.py           # LiveKit SIP calling integration
```

## 📊 Database Schema (ER Diagram)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE SCHEMA                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│    PRODUCTS     │         │    CUSTOMERS    │         │      CALLS      │
├─────────────────┤         ├─────────────────┤         ├─────────────────┤
│ id (PK)         │         │ id (PK)         │◄───────┐│ id (PK)         │
│ product_code    │         │ customer_code   │        ││ customer_id(FK) │──┘
│ product_name    │◄──┐     │ name            │        └│ customer_phone  │
│ product_type    │   │     │ email           │         │ customer_name   │
│ base_premium    │   │     │ phone           │         │ room_name       │
│ sum_assured_opt │   │     │ age             │         │ status          │
│ features (JSON) │   │     │ city            │         │ started_at      │
│ eligibility     │   │     │ address         │         │ ended_at        │
│ is_active       │   │     │ last_called     │         │ duration_seconds│
│ created_at      │   │     │ call_count      │         │ outcome         │
│ updated_at      │   │     │ preferred_time  │         │ notes           │
└─────────────────┘   │     │ created_at      │         │ interested_     │
                      │     │ updated_at      │         │   product_id(FK)│──┐
                      │     └─────────────────┘         │ created_at      │  │
                      │              │                  └─────────────────┘  │
                      │              │                           │           │
                      │              ▼                           ▼           │
                      │     ┌─────────────────┐                              │
                      │     │    POLICIES     │                              │
                      │     ├─────────────────┤                              │
                      │     │ id (PK)         │                              │
                      ├─────│ product_id (FK) │                              │
                      │     │ customer_id(FK) │────────────────────────┐     │
                      │     │ policy_number   │                        │     │
                      │     │ premium_amount  │                        │     │
                      │     │ sum_assured     │                        │     │
                      │     │ start_date      │                        │     │
                      │     │ end_date        │                        │     │
                      │     │ status          │                        │     │
                      │     │ renewal_status  │                        │     │
                      │     │ is_auto_renewal │                        │     │
                      │     │ renewal_reminder│                        │     │
                      │     │ created_at      │                        │     │
                      │     │ updated_at      │                        │     │
                      │     └─────────────────┘                        │     │
                      │              │                                 │     │
                      │              ▼                                 │     │
                      │     ┌─────────────────┐                        │     │
                      │     │     CLAIMS      │                        │     │
                      │     ├─────────────────┤                        │     │
                      │     │ id (PK)         │                        │     │
                      │     │ policy_id (FK)  │────────────────────────┘     │
                      │     │ claim_number    │                              │
                      │     │ claim_type      │                              │
                      │     │ claim_amount    │                              │
                      │     │ approved_amount │                              │
                      │     │ claim_date      │                              │
                      │     │ approved_date   │                              │
                      │     │ status          │                              │
                      │     │ description     │                              │
                      │     │ created_at      │                              │
                      └─────│────────────────►│◄─────────────────────────────┘
                            └─────────────────┘
```

## 🔗 API Endpoints

### Products `/api/v1/products`
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/products` | Add new insurance product |
| GET | `/products` | List products (filter: type, is_active) |
| GET | `/products/{id}` | Get product by ID |
| PUT | `/products/{id}` | Update product |
| DELETE | `/products/{id}` | Deactivate product |

### Customers `/api/v1/customers`
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/customers` | Add new customer |
| GET | `/customers` | List customers (filter: city) |
| GET | `/customers/{id}` | Get customer by ID |
| PUT | `/customers/{id}` | Update customer |
| DELETE | `/customers/{id}` | Delete customer |

### Policies `/api/v1/policies`
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/policies` | Create new policy |
| GET | `/policies` | List policies (filter: customer, product, status) |
| GET | `/policies/expiring-soon` | Get policies expiring within N days |
| GET | `/policies/{id}` | Get policy by ID |
| GET | `/policies/{id}/details` | Get policy with customer & product details |
| PUT | `/policies/{id}` | Update policy |
| POST | `/policies/{id}/renew` | Renew a policy |

### Claims `/api/v1/claims`
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/claims` | File new claim |
| GET | `/claims` | List claims (filter: policy, status) |
| GET | `/claims/{id}` | Get claim by ID |
| PUT | `/claims/{id}/status` | Update claim status |

### Calls `/api/v1/calls`
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/calls/initiate/{customer_id}` | Initiate AI call to customer |
| GET | `/calls` | List calls (filter: customer, status) |
| GET | `/calls/{id}` | Get call by ID |
| PUT | `/calls/{id}/summary` | Update call summary/outcome |
| PUT | `/calls/{id}/status` | Update call status |
| POST | `/calls/batch` | Batch initiate calls |

## 🛠️ Tech Stack

- **FastAPI** - Async web framework
- **SQLModel** - SQL database ORM (SQLAlchemy + Pydantic)
- **PostgreSQL** - Database (asyncpg driver)
- **LiveKit** - Real-time audio/video rooms
- **LiveKit SIP** - Outbound PSTN calls via Twilio
- **Docker Compose** - Container orchestration

## 🚀 Quick Start

```bash
# Start services
docker compose up -d

# API docs available at:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

## 📁 Code Organization Philosophy

### Separation of Concerns

1. **Routes** (`routes/`) - Handle HTTP requests/responses only
2. **Services** (`services/`) - Business logic and database operations  
3. **Models** (`models/`) - Database table definitions
4. **Schemas** (`schemas/`) - Request/Response validation

### Flow
```
HTTP Request → Route → Service → Database → Service → Route → HTTP Response
```

### Why Separate Files?

- **Maintainability**: Easy to find and modify code
- **Scalability**: Add new features without touching existing code
- **Testability**: Each component can be tested independently
- **Readability**: Clear purpose for each file
