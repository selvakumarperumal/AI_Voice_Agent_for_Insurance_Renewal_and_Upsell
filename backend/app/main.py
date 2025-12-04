"""
Insurance Voice Agent Backend API

Simple API to manage customers and auto-trigger calls for policy renewals.
Includes background scheduler that automatically calls customers with expiring policies.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.database import create_db_and_tables
from .routes import router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# OpenAPI Tags for documentation
tags_metadata = [
    {
        "name": "Products",
        "description": "Insurance product catalog management. Create, update, and manage insurance products offered by the company.",
    },
    {
        "name": "Customers",
        "description": "Customer management operations. Handle customer profiles, contact information, and preferences.",
    },
    {
        "name": "Policies",
        "description": "Policy management and tracking. Create policies, track renewals, and manage policy lifecycle.",
    },
    {
        "name": "Calls",
        "description": "AI voice call management. Initiate outbound calls via LiveKit SIP for renewal reminders and upsell opportunities.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown."""
    logger.info("Starting Insurance Voice Agent...")
    await create_db_and_tables()
    logger.info("Database ready")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Insurance Voice Agent API",
    description="""
## AI-Powered Insurance Voice Agent for Renewal & Upsell

Automated voice agent that calls customers before policy renewal to:
- **Remind** customers about upcoming renewals
- **Explain** policy benefits and coverage details
- **Share** renewal links for easy online renewal
- **Offer** upgrade options and upsell opportunities

### Why This Matters
- Insurance renewal revenue is massive; retention is critical
- Voice automation saves call center costs
- Increases policy renewal rate through proactive outreach

### Features:
- **Product Catalog**: Define insurance products with eligibility rules
- **Customer Database**: Manage customer profiles and contact info
- **Policy Tracking**: Track active policies and expiring renewals
- **AI Voice Calls**: Automated outbound calls via LiveKit SIP

### Flow:
```
Customer → Policy → Expiring Soon?
                        ↓
              AI Voice Call
                        ↓
         Renewal / Upsell Offer
```
    """,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}
