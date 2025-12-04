# Insurance Voice Agent - Architecture

## Overview

An AI-powered voice agent that automatically calls customers to discuss insurance policy renewals and upsell additional products. The system manages insurance products, customer policies, claims, and initiates outbound calls when policies are about to expire.

## System Flow

```mermaid
flowchart TB
    subgraph User["User Actions"]
        A[Manage Products]
        B[Manage Customers]
        C[Manage Policies]
        D[Manage Claims]
        M[Manual Call Trigger]
    end
    
    subgraph Backend["FastAPI Backend"]
        subgraph Routes["Routes Layer"]
            R1["/api/products"]
            R2["/api/customers"]
            R3["/api/policies"]
            R4["/api/claims"]
            R5["/api/call/*"]
            R6["/api/call-summary"]
        end
        
        subgraph Services["Service Layer"]
            S1[product_service]
            S2[customer_service]
            S3[policy_service]
            S4[claim_service]
            S5[call_service]
            S6[caller]
        end
        
        subgraph Database["Database Layer"]
            DB[(PostgreSQL)]
        end
    end
    
    subgraph External["External Services"]
        LK[LiveKit SIP]
        TW[Twilio]
        PH[Customer Phone]
        AI[AI Voice Agent]
    end
    
    %% User flows
    A --> R1
    B --> R2
    C --> R3
    D --> R4
    M --> R5
    
    %% Route to Service
    R1 --> S1
    R2 --> S2
    R3 --> S3
    R4 --> S4
    R5 --> S5
    R6 --> S5
    
    %% Service to Database
    S1 --> DB
    S2 --> DB
    S3 --> DB
    S4 --> DB
    S5 --> DB
    S5 --> S6
    
    %% External integrations
    S6 --> LK
    LK --> TW
    TW --> PH
    AI --> LK
    AI --> R6
```

## Automatic Call Flow

```mermaid
sequenceDiagram
    participant API
    participant CallService
    participant PolicyService
    participant CustomerService
    participant DB as Database
    participant Caller
    participant LiveKit
    participant Phone
    participant Agent as AI Agent
    
    Note over API: POST /call-expiring
    
    API->>CallService: call_customers_with_expiring_policies()
    CallService->>PolicyService: get_expiring_policies()
    PolicyService->>DB: SELECT policies JOIN customers WHERE end_date...
    DB-->>PolicyService: [PolicyWithDetails list]
    PolicyService-->>CallService: policies
    
    loop For each unique customer
        CallService->>CustomerService: get_customer(customer_id)
        CustomerService->>DB: SELECT customer
        DB-->>CustomerService: customer
        CallService->>Caller: make_call(phone, name)
        Caller->>LiveKit: Create SIP participant
        LiveKit->>Phone: Outbound call via Twilio
        Phone-->>LiveKit: Call connected
        Agent->>LiveKit: Join room
        Agent->>Phone: AI conversation
        Phone-->>Agent: Customer responses
        Agent->>API: POST /call-summary
        API->>CallService: update_call_summary()
        CallService->>DB: Update call record
    end
```

## Database Schema

```mermaid
erDiagram
    Product ||--o{ Policy : "has"
    Customer ||--o{ Policy : "has"
    Customer ||--o{ Call : "receives"
    Policy ||--o{ Claim : "has"
    
    Product {
        uuid id PK
        string product_code UK
        string product_name
        string product_type
        int base_premium
        json sum_assured_options
        json features
        json eligibility
        bool is_active
    }
    
    Customer {
        uuid id PK
        string name
        string phone UK
        string email
        int age
        string city
        datetime created_at
    }
    
    Policy {
        uuid id PK
        string policy_number UK
        uuid customer_id FK
        uuid product_id FK
        int premium_amount
        int sum_assured
        date start_date
        date end_date
        string status
    }
    
    Claim {
        uuid id PK
        string claim_number UK
        uuid policy_id FK
        string claim_type
        int claim_amount
        int approved_amount
        date claim_date
        date settlement_date
        string status
    }
    
    Call {
        uuid id PK
        uuid customer_id FK
        string customer_phone
        string customer_name
        string room_name UK
        string status
        datetime started_at
        datetime ended_at
        string outcome
        text notes
    }
```

## Project Structure

```
backend/app/
├── main.py                 # FastAPI app entry point
├── core/
│   ├── config.py          # Environment settings
│   └── database.py        # Database connection
├── models/
│   ├── __init__.py        # Model exports
│   └── models.py          # All database models
├── routes/
│   ├── __init__.py        # Router exports
│   └── api.py             # All API endpoints
└── services/
    ├── __init__.py        # Service exports
    ├── product_service.py # Product CRUD
    ├── customer_service.py# Customer CRUD
    ├── policy_service.py  # Policy management
    ├── claim_service.py   # Claim management
    ├── call_service.py    # Call orchestration
    └── caller.py          # LiveKit SIP integration
```

## Layer Responsibilities

### Routes Layer (`routes/api.py`)
- Handle HTTP requests/responses
- Input validation
- Error response formatting
- **Does NOT** contain business logic or DB operations

### Service Layer (`services/`)
- Business logic
- Database operations
- External API calls
- Can be reused across routes

### Database Layer (`core/database.py`)
- Connection management
- Session handling
- Async operations

## API Endpoints

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/products` | Add new product |
| `GET` | `/api/products` | List products (filter by type/status) |
| `GET` | `/api/products/{id}` | Get single product |
| `PUT` | `/api/products/{id}` | Update product |
| `DELETE` | `/api/products/{id}` | Deactivate product |

### Customers
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/customers` | Add new customer |
| `GET` | `/api/customers` | List customers (filter by city/age) |
| `GET` | `/api/customers/search` | Search by name/email/phone |
| `GET` | `/api/customers/{id}` | Get single customer |
| `GET` | `/api/customers/{id}/policies` | Get customer's policies |
| `GET` | `/api/customers/{id}/calls` | Get customer's call history |
| `PUT` | `/api/customers/{id}` | Update customer |
| `DELETE` | `/api/customers/{id}` | Delete customer |

### Policies
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/policies` | Create new policy |
| `GET` | `/api/policies` | List all policies |
| `GET` | `/api/policies/expiring` | Get expiring policies |
| `GET` | `/api/policies/{id}` | Get single policy |
| `PUT` | `/api/policies/{id}` | Update policy |
| `DELETE` | `/api/policies/{id}` | Cancel policy |

### Claims
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/claims` | Create new claim |
| `GET` | `/api/claims` | List claims (filter by status) |
| `GET` | `/api/claims/{id}` | Get single claim |
| `PUT` | `/api/claims/{id}/status` | Update claim status |
| `GET` | `/api/policies/{id}/claims` | Get policy's claims |

### Calls
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/call/{customer_id}` | Call specific customer |
| `POST` | `/api/call-expiring` | Batch call expiring policies |
| `GET` | `/api/calls` | List call history |
| `GET` | `/api/calls/{id}` | Get single call |
| `GET` | `/api/active-calls` | Get active calls |
| `POST` | `/api/call-summary` | Receive AI agent call results |

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# LiveKit
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
LIVEKIT_URL=wss://your-livekit.livekit.cloud

# Twilio SIP
TWILIO_SIP_DOMAIN=your-domain.pstn.twilio.com
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_SIP_USERNAME=username
TWILIO_SIP_PASSWORD=password
SIP_TRUNK_ID=trunk_id
```
