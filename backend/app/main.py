"""
Insurance Voice Agent Backend API

Simple API to manage customers and auto-trigger calls for policy renewals.
Includes background scheduler that automatically calls customers with expiring policies.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.database import create_db_and_tables, engine
from .core.middleware import RequestLoggingMiddleware, RateLimitMiddleware
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
    {
        "name": "Analytics",
        "description": "Call analytics and reporting. Track conversion rates, call outcomes, and performance metrics.",
    },
]


# Track startup time for uptime calculation
startup_time: datetime = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown."""
    global startup_time
    logger.info("Starting Insurance Voice Agent...")
    await create_db_and_tables()
    startup_time = datetime.now()
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
- **Analytics**: Track conversion rates and call outcomes

### Flow:
```
Customer → Policy → Expiring Soon?
                        ↓
              AI Voice Call
                        ↓
         Renewal / Upsell Offer
```
    """,
    version="1.1.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

# Add middleware (order matters - last added is first executed)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content={"error": "Validation Error", "detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred"}
    )


# Routes
app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    """
    Comprehensive health check endpoint.
    
    Returns:
        Service status including database connectivity and uptime.
    """
    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check database connection
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["services"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Calculate uptime
    if startup_time:
        uptime_seconds = (datetime.now() - startup_time).total_seconds()
        health_status["uptime_seconds"] = int(uptime_seconds)
        health_status["uptime_human"] = _format_uptime(uptime_seconds)
    
    return health_status


def _format_uptime(seconds: float) -> str:
    """Format uptime in human readable format."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or not parts:
        parts.append(f"{minutes}m")
    
    return " ".join(parts)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Insurance Voice Agent API",
        "version": "1.1.0",
        "docs": "/docs",
        "health": "/health"
    }

