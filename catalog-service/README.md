# Catalog Service

Menu, Inventory, and Pricing Management for Multi-tenant Restaurant Platform.

## Responsibilities

- **Menu Management**: Items, categories, modifiers, pricing
- **Inventory Tracking**: Stock levels, availability, low-stock alerts
- **Pricing Rules**: Dynamic pricing, promotions, discounts
- **Multi-tenancy**: Isolated catalogs per tenant (restaurant chain)

## Characteristics

- **Read-heavy**: Designed for aggressive caching
- **Multi-tenant aware**: X-Tenant-ID header required
- **Observable**: OpenTelemetry instrumentation from day 1

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python app/main.py

# Access at http://localhost:8001
# API docs at http://localhost:8001/docs
```

## API Endpoints

### Health & Info
- `GET /health` - Health check
- `GET /` - Service info

### Menu
- `GET /menu` - Get all menu items (requires X-Tenant-ID header)
- `GET /menu/{item_id}` - Get specific menu item

### Inventory
- `GET /inventory` - Get inventory levels (requires X-Tenant-ID header)
- `GET /inventory/{item_id}` - Get inventory for specific item

## Testing

```bash
# Get menu for demo tenant
curl -H "X-Tenant-ID: forkflow-demo" http://localhost:8001/menu

# Get specific item
curl -H "X-Tenant-ID: forkflow-demo" http://localhost:8001/menu/burger-001

# Get inventory
curl -H "X-Tenant-ID: forkflow-demo" http://localhost:8001/inventory
```

## Docker Build

```bash
# Build image
docker build -t catalog-service:latest .

# Run container
docker run -p 8001:8001 catalog-service:latest
```

## Kubernetes Deployment

```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment
kubectl get pods -l app=catalog-service
kubectl get svc catalog-service
```

## Multi-tenancy Pattern

All requests require `X-Tenant-ID` header:

```bash
curl -H "X-Tenant-ID: mcdonalds" http://catalog-service/menu
curl -H "X-Tenant-ID: chipotle" http://catalog-service/menu
```

Each tenant has isolated menu and inventory data.

## OpenTelemetry

Traces are exported to console by default. Configure OTLP exporter:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

## Future Enhancements

- [ ] PostgreSQL database integration
- [ ] Redis caching layer
- [ ] Search/filtering capabilities
- [ ] Menu versioning
- [ ] Bulk operations
- [ ] GraphQL API
