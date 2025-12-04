# AI Voice Agent for Insurance Renewal and Upsell

A production-ready AI voice agent built with LiveKit Agents for handling insurance policy renewal and upsell conversations over phone calls, with a complete FastAPI backend for managing customers, policies, and call data.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  PostgreSQL  │  │    Redis     │  │   LiveKit Server     │  │
│  │   Database   │  │   (Cache)    │  │   (Voice/WebRTC)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         ▲                 ▲                    ▲                 │
│         │                 │                    │                 │
│  ┌──────┴─────────────────┴────────────────────┴──────────────┐ │
│  │                    FastAPI Backend                          │ │
│  │  • Auth (signup/signin with JWT)                           │ │
│  │  • Customer CRUD                                           │ │
│  │  • Product CRUD                                            │ │
│  │  • Policy CRUD                                             │ │
│  │  • Call Management                                         │ │
│  │  • Outbound Call Initiation                                │ │
│  │  • LiveKit Webhooks                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│         ▲                                      ▲                 │
│         │                                      │                 │
│  ┌──────┴──────────────────────────────────────┴──────────────┐ │
│  │                   LiveKit Voice Agent                       │ │
│  │  • Deepgram STT                                            │ │
│  │  • Google Gemini LLM                                       │ │
│  │  • AWS Polly TTS                                           │ │
│  │  • Twilio SIP (Outbound Calls)                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Features

### Backend API
- **Authentication**: JWT-based auth with signup/signin using Authlib and Argon2
- **Customer Management**: CRUD operations for insurance customers
- **Product Management**: Insurance product catalog management
- **Policy Management**: Customer policy tracking with expiry detection
- **Call Tracking**: Record and manage voice call data
- **Outbound Calls**: Initiate calls to customers via LiveKit SIP
- **Webhooks**: Receive real-time events from LiveKit during calls

### Voice Agent
- **Speech-to-Text**: Deepgram for accurate transcription
- **Language Model**: Google Gemini for intelligent conversation
- **Text-to-Speech**: AWS Polly for natural voice synthesis
- **SIP Integration**: Twilio for outbound phone calls
- **Policy Renewal**: Automated renewal reminders and upsell suggestions

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Twilio account (for SIP/phone calls)
- Deepgram API key
- Google Gemini API key
- AWS credentials (for Polly TTS)

## 🛠️ Setup

### 1. Clone and Configure

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Required Environment Variables

```env
# JWT Authentication
JWT_SECRET_KEY=your-super-secret-key-change-in-production

# LiveKit
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# Twilio SIP
TWILIO_SIP_DOMAIN=your-sip-domain.pstn.twilio.com
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_SIP_USERNAME=your-sip-username
TWILIO_SIP_PASSWORD=your-sip-password

# AI Services
DEEPGRAM_API_KEY=your-deepgram-api-key
GEMINI_API_KEY=your-gemini-api-key
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1
```

### 3. Start Services with Docker

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Seed Database (Optional)

```bash
# Enter backend container
docker-compose exec backend bash

# Run seeding script
python seed_db.py
```

## 📚 API Documentation

Once running, access the API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

#### Authentication
- `POST /api/v1/auth/signup` - Create new user
- `POST /api/v1/auth/signin` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout and revoke tokens
- `GET /api/v1/auth/me` - Get current user info

#### Customers
- `GET /api/v1/customers` - List customers
- `GET /api/v1/customers/{id}` - Get customer by ID
- `POST /api/v1/customers` - Create customer
- `PATCH /api/v1/customers/{id}` - Update customer
- `DELETE /api/v1/customers/{id}` - Delete customer

#### Products
- `GET /api/v1/products` - List products
- `GET /api/v1/products/types` - List product types
- `GET /api/v1/products/{id}` - Get product by ID
- `POST /api/v1/products` - Create product
- `PATCH /api/v1/products/{id}` - Update product
- `DELETE /api/v1/products/{id}` - Delete product

#### Policies
- `GET /api/v1/policies` - List policies
- `GET /api/v1/policies/expiring` - Get expiring policies
- `GET /api/v1/policies/{id}` - Get policy by ID
- `GET /api/v1/policies/customer/{id}/active` - Get customer's active policies
- `POST /api/v1/policies` - Create policy
- `PATCH /api/v1/policies/{id}` - Update policy
- `DELETE /api/v1/policies/{id}` - Cancel policy

#### Calls
- `GET /api/v1/calls` - List calls
- `GET /api/v1/calls/{id}` - Get call by ID
- `GET /api/v1/calls/{id}/messages` - Get call messages
- `POST /api/v1/calls` - Create call record
- `PATCH /api/v1/calls/{id}` - Update call
- `POST /api/v1/calls/{id}/complete` - Complete call with summary

#### Outbound Calls
- `POST /api/v1/outbound/call` - Initiate outbound call
- `POST /api/v1/outbound/call-expiring-customers` - Call customers with expiring policies
- `GET /api/v1/outbound/active-rooms` - List active call rooms
- `POST /api/v1/outbound/end-call/{room}` - End active call

#### Webhooks
- `POST /api/v1/webhooks/livekit` - LiveKit webhook endpoint
- `POST /api/v1/webhooks/livekit/call-summary` - Receive call summary
- `GET /api/v1/webhooks/events` - List webhook events

## 🔧 Development

### Local Development (without Docker)

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv sync

# Run backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run agent (separate terminal)
cd proto
python main.py start
```

### Running Tests

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
pytest
```

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py      # Settings/configuration
│   │   │   ├── database.py    # Database setup
│   │   │   ├── redis.py       # Redis connection
│   │   │   └── security.py    # Auth utilities (argon2, authlib)
│   │   ├── models/
│   │   │   ├── user.py        # User model
│   │   │   ├── customer.py    # Customer model
│   │   │   ├── product.py     # Product model
│   │   │   ├── policy.py      # Policy model
│   │   │   ├── call.py        # Call model
│   │   │   └── webhook.py     # Webhook event model
│   │   ├── routes/
│   │   │   ├── auth.py        # Auth endpoints
│   │   │   ├── customers.py   # Customer endpoints
│   │   │   ├── products.py    # Product endpoints
│   │   │   ├── policies.py    # Policy endpoints
│   │   │   ├── calls.py       # Call endpoints
│   │   │   ├── outbound.py    # Outbound call endpoints
│   │   │   └── webhooks.py    # Webhook endpoints
│   │   ├── services/
│   │   │   └── outbound.py    # Outbound call service
│   │   └── main.py            # FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   └── seed_db.py             # Database seeding
├── proto/
│   ├── main.py                # LiveKit voice agent
│   ├── mock_database.py       # Mock data
│   └── outbound.py            # SIP outbound utilities
├── docker-compose.yml
├── Dockerfile.agent
├── livekit.yaml               # LiveKit server config
├── pyproject.toml
├── .env.example
└── README.md
```

## 🔐 Security Notes

- Change `JWT_SECRET_KEY` in production
- Use strong passwords for database
- Configure CORS_ORIGINS appropriately
- Use HTTPS in production
- Store API keys securely

## 📝 License

MIT License
