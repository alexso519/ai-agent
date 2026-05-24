# CrewAI Enterprise Control Center

**AI Operating System for Enterprise Workflow Orchestration**

A production-grade, enterprise-scale AI operating system for designing, orchestrating, and monitoring multi-agent AI workflows with human-in-the-loop controls.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   CREWAI ENTERPRISE ECC                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │  Frontend     │  │  API Server  │  │  Worker (Celery) │    │
│  │  (Next.js)   │──│  (FastAPI)   │──│  (CrewRuntime)  │    │
│  └──────────────┘  └──────┬───────┘  └────────┬─────────┘    │
│                           │                    │              │
│                    ┌──────▼───────┐    ┌───────▼─────────┐   │
│                    │  PostgreSQL  │    │  Redis (Pub/Sub) │   │
│                    │  + PGVector  │    │  + Streams      │   │
│                    └──────────────┘    └─────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### System Components

| Component | Technology | Description |
|-----------|-----------|-------------|
| **Web** | Next.js 14 | Frontend with React Flow canvas, YAML editor, terminal |
| **API** | FastAPI | REST API server with SSE streaming |
| **Worker** | Celery + CrewAI | Async workflow execution with CrewRuntime |
| **Shared Types** | TypeScript + Python | Typed contracts, events, schemas, constants |
| **UI Components** | React + Tailwind | Shared UI component library |

### Infrastructure

- **Containers**: Docker with multi-stage builds
- **Orchestration**: Kubernetes (EKS/AKS/GKE) with Kustomize/Helm
- **Database**: PostgreSQL + PGVector for vector search
- **Cache/Queue**: Redis (Celery broker + Pub/Sub + Streams)
- **LLM**: Ollama (local) + OpenAI/Anthropic (cloud)
- **Observability**: OpenTelemetry + Prometheus + Grafana + Loki + Tempo

## Getting Started

### Prerequisites

- **Node.js** >= 20.0.0
- **pnpm** >= 9.0.0
- **Python** >= 3.12
- **Docker** (optional, for containerized development)

### Quick Setup

```bash
# Clone and install
git clone <repo-url>
cd crewai-enterprise-control-center
make setup

# Or manually:
pnpm install
cp .env.example .env
# Edit .env with your configuration

# Start development servers
make dev
```

### Development Commands

```bash
make install       # Install all dependencies
make dev           # Start development servers
make build         # Build all packages and apps
make lint          # Lint all code
make type-check    # Run TypeScript type checking
make test          # Run all tests
make docker-up     # Start Docker development stack
make docker-down   # Stop Docker development stack
make clean         # Clean all build artifacts
```

## Project Structure

```
├── apps/
│   ├── web/                    # Next.js frontend
│   │   └── src/app/            # App Router pages
│   ├── api/                    # FastAPI backend
│   │   └── src/
│   │       ├── api/            # Route handlers
│   │       └── main.py         # Application factory
│   └── worker/                 # Celery worker
│       └── src/
│           ├── celery_app.py   # Celery configuration
│           └── tasks/          # Task definitions
├── packages/
│   ├── shared-types/           # TypeScript + Python shared types
│   │   └── src/
│   │       ├── events/         # Event type definitions
│   │       ├── constants/      # System constants
│   │       └── schemas/        # Zod validation schemas
│   ├── ui/                     # Shared React UI components
│   ├── crew-runtime/           # CrewAI runtime abstraction
│   └── eslint-config/          # Shared ESLint configuration
├── infra/
│   └── docker/                 # Docker configurations
├── .github/workflows/          # CI/CD pipelines
└── docs/                       # Architecture documentation
```

## Architecture Governance

This project follows strict architecture governance as defined in:

- **[ARCHITECTURAL_ANALYSIS.md](docs/ARCHITECTURAL_ANALYSIS.md)** — System analysis and dependency rules
- **[ARCHITECTURE_GOVERNANCE.md](docs/ARCHITECTURE_GOVERNANCE.md)** — Principal governance specification
- **[FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md)** — Frontend architecture
- **[BACKEND_RUNTIME_ARCHITECTURE.md](docs/BACKEND_RUNTIME_ARCHITECTURE.md)** — Backend runtime architecture
- **[ORCHESTRATION_ARCHITECTURE.md](docs/ORCHESTRATION_ARCHITECTURE.md)** — Orchestration architecture
- **[INFRASTRUCTURE_ARCHITECTURE.md](docs/INFRASTRUCTURE_ARCHITECTURE.md)** — Infrastructure architecture

### Key Governance Rules

- **No `any` types** — All TypeScript must be strictly typed
- **Module boundaries** — Dependencies follow the canonical map (enforced by CI)
- **Event schemas** — Every event conforms to `RuntimeEvent` envelope
- **State machines** — All state transitions validated
- **Checkpoints** — Every execution boundary must be checkpointable

## License

Proprietary — All rights reserved.