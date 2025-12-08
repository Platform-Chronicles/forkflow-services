# ForkFlow Services

Microservices for the ForkFlow restaurant tech platform.

## Overview

This repository contains the microservices that power ForkFlow, demonstrating the evolution from monolith to microservices architecture with proper observability, security, and deployment practices.

## Project Context

**Part of:** [Platform Chronicles](https://github.com/Platform-Chronicles)
**Narrative:** Chapters 2-5
**Demonstrates:** Modern microservices architecture, API design, service communication patterns

## Repository Structure

```
forkflow-services/
├── menu-service/                   # Go - Menu management
│   ├── cmd/
│   ├── internal/
│   ├── api/
│   ├── Dockerfile
│   └── README.md
├── order-service/                  # Python/FastAPI - Order processing
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── kitchen-display/                # Node.js - Real-time kitchen display
│   ├── src/
│   ├── tests/
│   ├── package.json
│   ├── Dockerfile
│   └── README.md
├── inventory-service/              # Python - Batch inventory reconciliation
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
└── shared/
    ├── proto/                      # gRPC protocol definitions
    └── docs/                       # Shared API documentation
```

## Services

### Menu Service (Go)
**Purpose:** Manage restaurant menu items, pricing, and availability

**Tech Stack:**
- Go 1.21+
- gRPC for service-to-service communication
- REST API for external clients
- PostgreSQL for data storage
- Redis for caching

**Features:**
- High-performance reads with caching
- Real-time menu updates
- Multi-language support
- Bulk operations for menu imports

### Order Service (Python/FastAPI)
**Purpose:** Process customer orders and manage order lifecycle

**Tech Stack:**
- Python 3.11+
- FastAPI for REST API
- PostgreSQL with SQLAlchemy
- Redis for session management
- Event publishing for order updates

**Features:**
- Order validation and processing
- Transaction management
- Event-driven architecture
- Integration with payment systems

### Kitchen Display Service (Node.js)
**Purpose:** Real-time kitchen order display system

**Tech Stack:**
- Node.js 18+
- Express.js
- WebSocket for real-time updates
- Redis for pub/sub
- React frontend

**Features:**
- Real-time order updates
- Order status management
- Kitchen workflow optimization
- Multiple display support

### Inventory Service (Python)
**Purpose:** Batch inventory reconciliation and tracking

**Tech Stack:**
- Python 3.11+
- CronJob-based execution
- PostgreSQL for storage
- Event-driven for notifications

**Features:**
- Automated inventory reconciliation
- Low stock alerts
- Usage analytics
- Supplier integration

## Prerequisites

Each service has its own prerequisites. See individual service READMEs.

**Common requirements:**
- Docker and Docker Compose
- Kubernetes cluster (for deployment)
- PostgreSQL 15+
- Redis 7+

## Quick Start

### Run All Services Locally

```bash
# Start infrastructure
docker-compose up -d postgres redis

# Menu Service
cd menu-service
go run cmd/server/main.go

# Order Service
cd order-service
pip install -r requirements.txt
uvicorn app.main:app --reload

# Kitchen Display
cd kitchen-display
npm install
npm run dev
```

### Run with Docker Compose

```bash
docker-compose up --build
```

## API Documentation

- **Menu Service:** http://localhost:8080/docs
- **Order Service:** http://localhost:8001/docs
- **Kitchen Display:** http://localhost:3000

## Service Communication

```
                ┌─────────────────┐
                │   API Gateway   │
                └────────┬────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼─────┐
    │  Menu   │    │  Order  │    │ Kitchen  │
    │ Service │◄───┤ Service │───►│ Display  │
    └────┬────┘    └────┬────┘    └──────────┘
         │              │
         │         ┌────▼────────┐
         └────────►│ Inventory   │
                   │  Service    │
                   └─────────────┘
```

## Technologies

- **Go** - High-performance services
- **Python/FastAPI** - Business logic services
- **Node.js** - Real-time services
- **gRPC** - Service-to-service communication
- **REST** - External API
- **PostgreSQL** - Data persistence
- **Redis** - Caching and pub/sub

## Observability

All services are instrumented with:
- **OpenTelemetry** - Distributed tracing
- **Prometheus metrics** - Service metrics
- **Structured logging** - JSON logs to Loki

See [forkflow-observability](https://github.com/Platform-Chronicles/forkflow-observability) for monitoring setup.

## Security

All services implement:
- Authentication and authorization
- Input validation
- Rate limiting
- Secrets from Vault (not environment variables)

See [forkflow-security](https://github.com/Platform-Chronicles/forkflow-security) for security configurations.

## Deployment

Services are deployed via GitOps:
- Kubernetes manifests in [forkflow-gitops](https://github.com/Platform-Chronicles/forkflow-gitops)
- ArgoCD for continuous deployment
- Health checks and readiness probes
- Resource limits and quotas

## Testing

```bash
# Run all tests
./scripts/test-all.sh

# Run specific service tests
cd menu-service && go test ./...
cd order-service && pytest
cd kitchen-display && npm test
```

## Related Repositories

- [forkflow-monolith](https://github.com/Platform-Chronicles/forkflow-monolith) - Original monolith
- [forkflow-gitops](https://github.com/Platform-Chronicles/forkflow-gitops) - Deployment configs
- [forkflow-observability](https://github.com/Platform-Chronicles/forkflow-observability) - Monitoring
- [forkflow-tests](https://github.com/Platform-Chronicles/forkflow-tests) - Integration tests

## Development

### Adding a New Service

1. Copy service template from [forkflow-portal](https://github.com/Platform-Chronicles/forkflow-portal)
2. Implement service logic
3. Add Dockerfile and Kubernetes manifests
4. Update GitOps repository
5. Register in service catalog

### Code Standards

- **Go:** Follow standard Go conventions, use golangci-lint
- **Python:** Follow PEP 8, use black formatter, type hints
- **Node.js:** ESLint configuration, Prettier formatting
- **All:** Unit tests required, integration tests recommended

## License

MIT
