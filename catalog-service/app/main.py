"""
Catalog Service - Menu, Inventory, and Pricing Management

Responsibilities:
- Menu management (items, categories, modifiers)
- Inventory tracking and availability
- Pricing rules and calculations
- Multi-tenant catalog management

This is a read-heavy service designed for aggressive caching.
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from datetime import datetime
from typing import Optional, List
import os

# OpenTelemetry imports - instrumentation from day 1
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
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
    "service.name": "catalog-service",
    "service.version": "0.1.0",
    "deployment.environment": os.getenv("ENV", "local")
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Export to console for now (will add OTLP exporter later)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)


# In-memory data store (will replace with PostgreSQL)
menu_items = {}
inventory = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("=" * 60)
    logger.info("Starting Catalog Service")
    logger.info("=" * 60)

    # Initialize sample data
    _init_sample_data()

    yield

    logger.info("Shutting down Catalog Service")


app = FastAPI(
    title="Catalog Service",
    description="Menu, Inventory, and Pricing Management for Multi-tenant Restaurant Platform",
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
    """Extract tenant ID from header - multi-tenancy pattern"""
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")
    return x_tenant_id


def _init_sample_data():
    """Initialize sample menu and inventory data"""
    global menu_items, inventory

    # Sample tenant: "forkflow-demo"
    tenant_id = "forkflow-demo"

    menu_items[tenant_id] = [
        {
            "id": "burger-001",
            "name": "Classic Burger",
            "description": "Beef patty with lettuce, tomato, onion",
            "category": "burgers",
            "price": 12.99,
            "available": True,
            "tenant_id": tenant_id
        },
        {
            "id": "pizza-001",
            "name": "Margherita Pizza",
            "description": "Fresh mozzarella, basil, tomato sauce",
            "category": "pizza",
            "price": 14.99,
            "available": True,
            "tenant_id": tenant_id
        },
        {
            "id": "salad-001",
            "name": "Caesar Salad",
            "description": "Romaine, parmesan, croutons, caesar dressing",
            "category": "salads",
            "price": 9.99,
            "available": True,
            "tenant_id": tenant_id
        }
    ]

    inventory[tenant_id] = {
        "burger-001": {"quantity": 50, "low_stock_threshold": 10},
        "pizza-001": {"quantity": 30, "low_stock_threshold": 5},
        "salad-001": {"quantity": 25, "low_stock_threshold": 5}
    }

    logger.info(f"Initialized sample data for tenant: {tenant_id}")


@app.get("/health")
def health_check():
    """Health check endpoint for Kubernetes probes"""
    return {
        "status": "healthy",
        "service": "catalog-service",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }


@app.get("/")
def root():
    """Service info"""
    return {
        "service": "catalog-service",
        "version": "0.1.0",
        "description": "Menu, Inventory, and Pricing Management",
        "endpoints": {
            "health": "/health",
            "menu": "/menu",
            "inventory": "/inventory"
        }
    }


@app.get("/menu")
def get_menu(tenant_id: str = Depends(get_tenant_id)):
    """Get menu items for tenant - read-heavy endpoint"""
    with tracer.start_as_current_span("get_menu") as span:
        span.set_attribute("tenant.id", tenant_id)

        if tenant_id not in menu_items:
            logger.warning(f"No menu found for tenant: {tenant_id}")
            raise HTTPException(status_code=404, detail=f"No menu for tenant: {tenant_id}")

        items = menu_items[tenant_id]
        span.set_attribute("menu.items.count", len(items))

        logger.info(f"Retrieved {len(items)} menu items for tenant: {tenant_id}")
        return {
            "tenant_id": tenant_id,
            "items": items,
            "total": len(items)
        }


@app.get("/menu/{item_id}")
def get_menu_item(item_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get specific menu item"""
    with tracer.start_as_current_span("get_menu_item") as span:
        span.set_attribute("tenant.id", tenant_id)
        span.set_attribute("menu.item.id", item_id)

        if tenant_id not in menu_items:
            raise HTTPException(status_code=404, detail=f"No menu for tenant: {tenant_id}")

        item = next((i for i in menu_items[tenant_id] if i["id"] == item_id), None)

        if not item:
            logger.warning(f"Item {item_id} not found for tenant {tenant_id}")
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

        logger.info(f"Retrieved item {item_id} for tenant {tenant_id}")
        return item


@app.get("/inventory")
def get_inventory(tenant_id: str = Depends(get_tenant_id)):
    """Get inventory levels for tenant"""
    with tracer.start_as_current_span("get_inventory") as span:
        span.set_attribute("tenant.id", tenant_id)

        if tenant_id not in inventory:
            logger.warning(f"No inventory found for tenant: {tenant_id}")
            raise HTTPException(status_code=404, detail=f"No inventory for tenant: {tenant_id}")

        inv = inventory[tenant_id]

        # Check for low stock items
        low_stock = [item_id for item_id, data in inv.items()
                     if data["quantity"] <= data["low_stock_threshold"]]

        span.set_attribute("inventory.low_stock.count", len(low_stock))

        logger.info(f"Retrieved inventory for tenant {tenant_id}, {len(low_stock)} items low stock")

        return {
            "tenant_id": tenant_id,
            "inventory": inv,
            "low_stock_items": low_stock
        }


@app.get("/inventory/{item_id}")
def get_item_inventory(item_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get inventory for specific item"""
    with tracer.start_as_current_span("get_item_inventory") as span:
        span.set_attribute("tenant.id", tenant_id)
        span.set_attribute("inventory.item.id", item_id)

        if tenant_id not in inventory or item_id not in inventory[tenant_id]:
            raise HTTPException(status_code=404, detail=f"No inventory for item: {item_id}")

        inv_data = inventory[tenant_id][item_id]
        is_low = inv_data["quantity"] <= inv_data["low_stock_threshold"]

        span.set_attribute("inventory.is_low_stock", is_low)

        return {
            "item_id": item_id,
            "tenant_id": tenant_id,
            **inv_data,
            "is_low_stock": is_low
        }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Catalog Service in development mode")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
