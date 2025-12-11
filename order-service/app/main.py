"""
Order Service - Order Lifecycle Management

Responsibilities:
- Order creation and validation
- Order status management (pending → confirmed → preparing → ready → completed)
- Integration with catalog-service for menu validation
- Multi-tenant order tracking

This service demonstrates distributed system challenges:
- Service-to-service communication
- Distributed transactions
- Error handling across services
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from datetime import datetime
import logging
import sys
import os
import uuid
import httpx

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# OpenTelemetry setup
resource = Resource(attributes={
    "service.name": "order-service",
    "service.version": "0.1.0",
    "deployment.environment": os.getenv("ENV", "local")
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Export to console for now
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

# Instrument httpx for tracing service-to-service calls
HTTPXClientInstrumentor().instrument()

# Configuration
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://catalog-service")


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    item_id: str
    quantity: int
    price: float


class CreateOrderRequest(BaseModel):
    items: List[OrderItem]
    customer_name: str
    table_number: Optional[int] = None
    notes: Optional[str] = None


class Order(BaseModel):
    id: str
    tenant_id: str
    customer_name: str
    table_number: Optional[int]
    items: List[OrderItem]
    total: float
    status: OrderStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


# In-memory storage (will replace with PostgreSQL)
orders = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("=" * 60)
    logger.info("Starting Order Service")
    logger.info(f"Catalog Service URL: {CATALOG_SERVICE_URL}")
    logger.info("=" * 60)
    yield
    logger.info("Shutting down Order Service")


app = FastAPI(
    title="Order Service",
    description="Order Lifecycle Management for Multi-tenant Restaurant Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Extract tenant ID from header"""
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")
    return x_tenant_id


async def validate_menu_items(tenant_id: str, items: List[OrderItem]) -> bool:
    """
    Call catalog-service to validate menu items exist and are available.

    This is where distributed system complexity starts!
    - Network call can fail
    - Catalog service might be down
    - Need to handle timeouts
    - Want to trace this across services
    """
    with tracer.start_as_current_span("validate_menu_items") as span:
        span.set_attribute("tenant.id", tenant_id)
        span.set_attribute("items.count", len(items))

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                for item in items:
                    span.add_event(f"Validating item: {item.item_id}")

                    # Call catalog-service to check item exists
                    response = await client.get(
                        f"{CATALOG_SERVICE_URL}/menu/{item.item_id}",
                        headers={"X-Tenant-ID": tenant_id}
                    )

                    if response.status_code == 404:
                        span.set_attribute("validation.failed", True)
                        span.set_attribute("validation.reason", f"Item {item.item_id} not found")
                        logger.warning(f"Item {item.item_id} not found in catalog")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Item {item.item_id} not found in menu"
                        )

                    response.raise_for_status()

                    menu_item = response.json()
                    if not menu_item.get("available"):
                        span.set_attribute("validation.failed", True)
                        span.set_attribute("validation.reason", f"Item {item.item_id} unavailable")
                        logger.warning(f"Item {item.item_id} is not available")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Item {item.item_id} is not available"
                        )

                span.set_attribute("validation.success", True)
                logger.info(f"All {len(items)} items validated successfully")
                return True

        except httpx.TimeoutException:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "timeout")
            logger.error("Catalog service timeout")
            raise HTTPException(
                status_code=503,
                detail="Catalog service unavailable (timeout)"
            )
        except httpx.RequestError as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "network")
            logger.error(f"Catalog service error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Catalog service unavailable: {str(e)}"
            )


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "order-service",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }


@app.get("/")
def root():
    """Service info"""
    return {
        "service": "order-service",
        "version": "0.1.0",
        "description": "Order Lifecycle Management",
        "endpoints": {
            "health": "/health",
            "orders": "/orders",
            "create_order": "POST /orders"
        }
    }


@app.post("/orders", status_code=201)
async def create_order(
    request: CreateOrderRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Order:
    """Create a new order - validates items with catalog-service"""
    with tracer.start_as_current_span("create_order") as span:
        span.set_attribute("tenant.id", tenant_id)
        span.set_attribute("customer.name", request.customer_name)
        span.set_attribute("items.count", len(request.items))

        logger.info(f"Creating order for {request.customer_name}, {len(request.items)} items")

        # Validate items with catalog-service (distributed call!)
        await validate_menu_items(tenant_id, request.items)

        # Calculate total
        total = sum(item.price * item.quantity for item in request.items)

        # Create order
        order_id = str(uuid.uuid4())
        now = datetime.now()

        order = Order(
            id=order_id,
            tenant_id=tenant_id,
            customer_name=request.customer_name,
            table_number=request.table_number,
            items=request.items,
            total=total,
            status=OrderStatus.PENDING,
            notes=request.notes,
            created_at=now,
            updated_at=now
        )

        # Store order
        if tenant_id not in orders:
            orders[tenant_id] = {}
        orders[tenant_id][order_id] = order

        span.set_attribute("order.id", order_id)
        span.set_attribute("order.total", total)

        logger.info(f"Order {order_id} created successfully, total: ${total:.2f}")

        return order


@app.get("/orders")
def get_orders(tenant_id: str = Depends(get_tenant_id)) -> List[Order]:
    """Get all orders for tenant"""
    with tracer.start_as_current_span("get_orders") as span:
        span.set_attribute("tenant.id", tenant_id)

        if tenant_id not in orders:
            return []

        tenant_orders = list(orders[tenant_id].values())
        span.set_attribute("orders.count", len(tenant_orders))

        logger.info(f"Retrieved {len(tenant_orders)} orders for tenant {tenant_id}")
        return tenant_orders


@app.get("/orders/{order_id}")
def get_order(order_id: str, tenant_id: str = Depends(get_tenant_id)) -> Order:
    """Get specific order"""
    with tracer.start_as_current_span("get_order") as span:
        span.set_attribute("tenant.id", tenant_id)
        span.set_attribute("order.id", order_id)

        if tenant_id not in orders or order_id not in orders[tenant_id]:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        return orders[tenant_id][order_id]


@app.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: str,
    status: OrderStatus,
    tenant_id: str = Depends(get_tenant_id)
) -> Order:
    """Update order status"""
    with tracer.start_as_current_span("update_order_status") as span:
        span.set_attribute("tenant.id", tenant_id)
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.new_status", status.value)

        if tenant_id not in orders or order_id not in orders[tenant_id]:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        order = orders[tenant_id][order_id]
        old_status = order.status
        order.status = status
        order.updated_at = datetime.now()

        logger.info(f"Order {order_id} status updated: {old_status} → {status}")

        return order


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Order Service in development mode")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
