# CrewAI Enterprise Control Center — Infrastructure & Platform Architecture

> **Document Type**: Principal Infrastructure Architecture Specification  
> **Status**: Pre-Implementation Design  
> **Version**: 1.0  
> **Architecture Source**: [`ARCHITECTURAL_ANALYSIS.md`](ARCHITECTURAL_ANALYSIS.md), [`FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md), [`BACKEND_RUNTIME_ARCHITECTURE.md`](BACKEND_RUNTIME_ARCHITECTURE.md), [`ORCHESTRATION_ARCHITECTURE.md`](ORCHESTRATION_ARCHITECTURE.md)

---

## Table of Contents

1. [Infrastructure Philosophy](#1-infrastructure-philosophy)
2. [Infrastructure Folder Structure](#2-infrastructure-folder-structure)
3. [Docker Architecture & Container Strategy](#3-docker-architecture--container-strategy)
4. [Kubernetes Architecture & Deployment Topology](#4-kubernetes-architecture--deployment-topology)
5. [Redis HA Strategy](#5-redis-ha-strategy)
6. [PostgreSQL HA & PGVector Deployment Strategy](#6-postgresql-ha--pgvector-deployment-strategy)
7. [Ollama Deployment Strategy](#7-ollama-deployment-strategy)
8. [Celery Worker Topology](#8-celery-worker-topology)
9. [Event Streaming Infrastructure](#9-event-streaming-infrastructure)
10. [Observability Stack](#10-observability-stack)
11. [Logging Pipeline](#11-logging-pipeline)
12. [Metrics Pipeline](#12-metrics-pipeline)
13. [Tracing Architecture](#13-tracing-architecture)
14. [Secrets Management](#14-secrets-management)
15. [RBAC Infrastructure](#15-rbac-infrastructure)
16. [CI/CD Pipeline Architecture](#16-cicd-pipeline-architecture)
17. [Backup & Recovery Architecture](#17-backup--recovery-architecture)
18. [Environment Strategy](#18-environment-strategy)
19. [Scaling Strategy](#19-scaling-strategy)
20. [Failover Strategy](#20-failover-strategy)
21. [Infrastructure Security Architecture](#21-infrastructure-security-architecture)
22. [Production Deployment Workflow](#22-production-deployment-workflow)
23. [Network Architecture](#23-network-architecture)
24. [Disaster Recovery Plan](#24-disaster-recovery-plan)

---

## 1. Infrastructure Philosophy

### 1.1 Core Principles

This infrastructure is designed for **enterprise-grade AI workload orchestration**. Every decision is governed by:

| Principle | Implementation |
|-----------|---------------|
| **No single points of failure** | Every critical component has HA configuration with automated failover |
| **Immutable infrastructure** | All changes deployed via CI/CD; no manual server modifications |
| **Infrastructure as Code** | All manifests version-controlled; manual operations produce alerts |
| **Observability by default** | Every service exports metrics, traces, and structured logs |
| **Defense in depth** | Network isolation, secrets management, RBAC at every layer |
| **Horizontal scalability** | All stateless services scale horizontally; stateful services use clustering |

### 1.2 Deployment Models

The infrastructure supports three deployment models:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT MODELS                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Development          Staging                 Production                   │
│  ┌──────────────┐    ┌──────────────┐        ┌──────────────────────┐    │
│  │ Single node   │    │ Multi-node    │        │ Production cluster    │    │
│  │ Docker Compose│    │ K3s / Minikube│        │ EKS / AKS / GKE      │    │
│  │ No HA         │    │ Basic HA     │        │ Full HA + DR         │    │
│  │ Local secrets │    │ Vault dev    │        │ Vault production     │    │
│  │ MinIO (S3)   │    │ MinIO (S3)   │        │ AWS S3 / GCS / Azure │    │
│  └──────────────┘    └──────────────┘        └──────────────────────┘    │
│                                                                           │
│  Cost: $ low          Cost: $$ medium         Cost: $$$ high               │
│  SLA: None            SLA: 99.5%              SLA: 99.95%                  │
│  Recovery: Manual     Recovery: Semi-auto     Recovery: Automated          │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Infrastructure Decision Records

| ID | Decision | Choice | Rationale |
|----|----------|--------|-----------|
| INF-001 | Orchestration | Kubernetes (EKS/AKS/GKE) | Industry standard, managed control plane, broad ecosystem |
| INF-002 | Container runtime | containerd | Default in K8s 1.24+, OCI compliant, secure |
| INF-003 | Ingress controller | ingress-nginx + AWS ALB | Layer 7 routing, SSL termination, WebSocket/SSE support |
| INF-004 | Service mesh | Istio (optional, production only) | mTLS, traffic splitting, observability |
| INF-005 | Secret storage | HashiCorp Vault | Dynamic secrets, audit logging, encryption |
| INF-006 | Image registry | ECR / GCR / Docker Registry + Harbor | Proximity to compute, vulnerability scanning |
| INF-007 | CI/CD | GitHub Actions → ArgoCD | GitOps-driven, declarative, audit trail |
| INF-008 | Observability | OpenTelemetry + Grafana stack | Vendor-neutral, CNCF graduated, unified UI |

---

## 2. Infrastructure Folder Structure

```
infra/
├── README.md                                  # Infrastructure overview and runbooks
│
├── docker/                                    # Docker configurations
│   ├── Dockerfile.web                         # Next.js production build
│   ├── Dockerfile.api                         # FastAPI production build
│   ├── Dockerfile.worker                      # Celery worker production build
│   ├── Dockerfile.worker.beat                 # Celery beat scheduler
│   ├── Dockerfile.nginx                       # nginx reverse proxy
│   ├── docker-compose.yml                     # Development stack
│   ├── docker-compose.override.yml            # Local overrides (gitignored)
│   ├── docker-compose.prod.yml               # Production overrides
│   ├── docker-compose.monitoring.yml         # Monitoring stack add-on
│   ├── docker-compose.seed.yml               # Database seed data
│   └── .dockerignore                          # Shared dockerignore
│
├── k8s/                                       # Kubernetes manifests (production)
│   ├── bases/                                 # Environment-agnostic bases
│   │   ├── kustomization.yaml
│   │   ├── namespaces/
│   │   │   ├── namespace.yaml                 # crewai-system, crewai-app, crewai-obs
│   │   │   └── network-policies.yaml          # Default deny ingress/egress
│   │   ├── api/
│   │   │   ├── deployment.yaml               # FastAPI deployment
│   │   │   ├── service.yaml                  # ClusterIP service
│   │   │   ├── hpa.yaml                      # Horizontal pod autoscaler
│   │   │   ├── pdb.yaml                      # Pod disruption budget
│   │   │   ├── service-account.yaml           # Service account with IAM role
│   │   │   └── configmap.yaml                # API configuration
│   │   ├── web/
│   │   │   ├── deployment.yaml               # Next.js deployment
│   │   │   ├── service.yaml                  # ClusterIP service
│   │   │   ├── hpa.yaml                      # Horizontal pod autoscaler
│   │   │   └── configmap.yaml                # Web configuration
│   │   ├── worker/
│   │   │   ├── deployment-default.yaml       # Default Celery worker
│   │   │   ├── deployment-control.yaml       # Control queue worker
│   │   │   ├── deployment-hitl.yaml          # HITL queue worker
│   │   │   ├── deployment-beat.yaml          # Celery beat scheduler
│   │   │   ├── hpa.yaml                      # Worker autoscaler
│   │   │   └── service-account.yaml           # Worker service account
│   │   ├── redis/
│   │   │   ├── statefulset.yaml              # Redis StatefulSet
│   │   │   ├── service.yaml                  # Headless service
│   │   │   ├── configmap.yaml                # Redis configuration
│   │   │   └── pvc.yaml                      # Persistent volume claim
│   │   ├── postgres/
│   │   │   ├── statefulset.yaml              # PostgreSQL StatefulSet
│   │   │   ├── service.yaml                  # Headless service
│   │   │   ├── configmap.yaml                # PostgreSQL configuration
│   │   │   └── pvc.yaml                      # Persistent volume claim
│   │   ├── ollama/
│   │   │   ├── statefulset.yaml              # Ollama StatefulSet (GPU)
│   │   │   ├── service.yaml                  # ClusterIP service
│   │   │   ├── pvc.yaml                      # Model storage
│   │   │   └── runtime-class.yaml            # GPU runtime class
│   │   ├── ingress/
│   │   │   ├── ingress.yaml                  # ALB/Nginx ingress
│   │   │   ├── tls-certificate.yaml          # cert-manager Certificate
│   │   │   └── middleware.yaml               # Rate limiting, auth
│   │   ├── monitoring/
│   │   │   ├── prometheus/
│   │   │   │   ├── deployment.yaml           # Prometheus server
│   │   │   │   ├── service.yaml
│   │   │   │   ├── configmap.yaml            # Scrape configs
│   │   │   │   ├── pvc.yaml                  # Metrics retention
│   │   │   │   ├── service-monitor-api.yaml  # API scrape target
│   │   │   │   ├── service-monitor-worker.yaml
│   │   │   │   └── service-monitor-redis.yaml
│   │   │   ├── grafana/
│   │   │   │   ├── deployment.yaml           # Grafana
│   │   │   │   ├── service.yaml
│   │   │   │   ├── configmap.yaml            # Datasources, dashboards
│   │   │   │   ├── pvc.yaml                  # Dashboard persistence
│   │   │   │   └── dashboards/
│   │   │   │       ├── api-dashboard.json
│   │   │   │       ├── worker-dashboard.json
│   │   │   │       ├── redis-dashboard.json
│   │   │   │       ├── postgres-dashboard.json
│   │   │   │       ├── celery-dashboard.json
│   │   │   │       └── workflow-dashboard.json
│   │   │   ├── loki/
│   │   │   │   ├── deployment.yaml           # Loki log aggregation
│   │   │   │   ├── service.yaml
│   │   │   │   └── pvc.yaml
│   │   │   ├── tempo/
│   │   │   │   ├── deployment.yaml           # Tempo tracing backend
│   │   │   │   ├── service.yaml
│   │   │   │   └── pvc.yaml
│   │   │   └── alloy/
│   │   │       ├── daemonset.yaml            # OpenTelemetry collector
│   │   │       └── configmap.yaml            # Collector configuration
│   │   ├── logging/
│   │   │   ├── vector/
│   │   │   │   ├── daemonset.yaml            # Vector log agent
│   │   │   │   └── configmap.yaml            # Log pipeline config
│   │   │   └── fluentd/
│   │   │       └── configmap.yaml            # Fluentd config (alternative)
│   │   ├── vault/
│   │   │   ├── deployment.yaml               # HashiCorp Vault
│   │   │   ├── service.yaml
│   │   │   ├── configmap.yaml
│   │   │   └── pvc.yaml
│   │   ├── backup/
│   │   │   ├── cronjob.yaml                  # Scheduled backups
│   │   │   ├── configmap.yaml                # Backup scripts
│   │   │   └── service-account.yaml           # Backup IAM role
│   │   └── jobs/
│   │       ├── db-migration.yaml             # Alembic migration job
│   │       └── db-seed.yaml                  # Database seeding job
│   │
│   ├── overlays/                             # Environment-specific overlays
│   │   ├── dev/
│   │   │   ├── kustomization.yaml
│   │   │   ├── api-patch.yaml                # Lower resources, debug enabled
│   │   │   ├── worker-patch.yaml
│   │   │   ├── ingress-patch.yaml
│   │   │   └── monitoring-patch.yaml         # Dev monitoring config
│   │   ├── staging/
│   │   │   ├── kustomization.yaml
│   │   │   ├── api-patch.yaml
│   │   │   ├── worker-patch.yaml
│   │   │   ├── ingress-patch.yaml
│   │   │   └── replica-counts.yaml
│   │   └── prod/
│   │       ├── kustomization.yaml
│   │       ├── api-patch.yaml
│   │       ├── worker-patch.yaml
│   │       ├── ingress-patch.yaml
│   │       ├── pdb-patches.yaml
│   │       ├── network-policies-patch.yaml
│   │       ├── tolerations-patch.yaml
│   │       └── backup-config.yaml
│   │
│   └── crds/                                 # Custom resource definitions
│       ├── cert-manager.yaml
│       ├── prometheus-operator.yaml
│       └── grafana-operator.yaml
│
├── helm/                                     # Helm charts (alternative to kustomize)
│   └── crewai/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values.dev.yaml
│       ├── values.staging.yaml
│       ├── values.prod.yaml
│       └── templates/
│           ├── _helpers.tpl
│           ├── api-deployment.yaml
│           ├── api-service.yaml
│           ├── api-hpa.yaml
│           ├── web-deployment.yaml
│           ├── web-service.yaml
│           ├── worker-deployment.yaml
│           ├── worker-hpa.yaml
│           ├── redis-statefulset.yaml
│           ├── postgres-statefulset.yaml
│           ├── ollama-statefulset.yaml
│           ├── ingress.yaml
│           ├── configmap.yaml
│           ├── secret-provider.yaml
│           ├── pdb.yaml
│           ├── network-policy.yaml
│           ├── service-account.yaml
│           └── backup-cronjob.yaml
│
├── terraform/                                # Infrastructure provisioning
│   ├── modules/
│   │   ├── eks/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── node-groups.tf
│   │   ├── rds/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── elasticache/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── vault/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── networking/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── s3/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   └── monitoring/
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       └── outputs.tf
│   ├── environments/
│   │   ├── dev/
│   │   │   ├── main.tf
│   │   │   ├── terraform.tfvars
│   │   │   └── backend.tf
│   │   ├── staging/
│   │   │   ├── main.tf
│   │   │   ├── terraform.tfvars
│   │   │   └── backend.tf
│   │   └── prod/
│   │       ├── main.tf
│   │       ├── terraform.tfvars
│   │       ├── backend.tf
│   │       └── remote-state.tf
│   └── outputs.tf
│
├── scripts/                                  # Operational scripts
│   ├── backup.sh
│   ├── restore.sh
│   ├── migrate.sh
│   ├── healthcheck.sh
│   ├── rotate-secrets.sh
│   ├── seed-data.sh
│   ├── ollama-pull-models.sh
│   └── disaster-recovery.sh
│
├── monitoring/                               # Monitoring configurations
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   ├── alert-rules/
│   │   │   ├── api-alerts.yml
│   │   │   ├── worker-alerts.yml
│   │   │   ├── redis-alerts.yml
│   │   │   ├── postgres-alerts.yml
│   │   │   ├── workflow-alerts.yml
│   │   │   ├── ollama-alerts.yml
│   │   │   └── kubernetes-alerts.yml
│   │   └── recording-rules.yml
│   ├── grafana/
│   │   ├── datasources.yml
│   │   ├── dashboards/
│   │   │   ├── api-overview.json
│   │   │   ├── worker-overview.json
│   │   │   ├── redis-overview.json
│   │   │   ├── postgres-overview.json
│   │   │   ├── celery-overview.json
│   │   │   ├── ollama-overview.json
│   │   │   ├── workflow-executions.json
│   │   │   └── kubernetes-cluster.json
│   │   └── alerting/
│   │       ├── notification-policies.yml
│   │       └── contact-points.yml
│   ├── tempo/
│   │   └── tempo.yml
│   └── loki/
│       └── loki.yml
│
├── vault/                                    # Vault configuration
│   ├── policies/
│   │   ├── api-policy.hcl
│   │   ├── worker-policy.hcl
│   │   └── admin-policy.hcl
│   └── secrets/
│       ├── database-creds.tf
│       └── llm-api-keys.tf
│
├── tests/
│   ├── connectivity-test.sh
│   ├── chaos-test.sh
│   └── load-test/
│       ├── k6-script.js
│       └── scenarios/
│
└── docs/
    ├── RUNBOOKS.md
    ├── ARCHITECTURE.md
    ├── DISASTER_RECOVERY.md
    ├── SECURITY.md
    └── ONBOARDING.md
```

---

## 3. Docker Architecture & Container Strategy

### 3.1 Container Images

Each deployable component has a **dedicated Dockerfile** optimized for production:

| Image | Base | Size Target | Build Target |
|-------|------|-------------|--------------|
| `crewai-web` | `node:20-alpine` | < 200MB | Next.js standalone output |
| `crewai-api` | `python:3.12-slim` | < 500MB | FastAPI + dependencies |
| `crewai-worker` | `python:3.12-slim` | < 600MB | Celery + CrewAI + runtime |
| `crewai-worker-beat` | `python:3.12-slim` | < 300MB | Celery beat only |
| `crewai-nginx` | `nginx:alpine` | < 50MB | Reverse proxy config |

### 3.2 Multi-Stage Build Pattern

```dockerfile
# infra/docker/Dockerfile.api
# ============================================================
# STAGE 1: Python dependencies (cached layer)
# ============================================================
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Leverage Docker cache: copy only dependency files first
COPY pyproject.toml requirements.txt ./
COPY packages/shared-types/ packages/shared-types/
COPY packages/crew-runtime/ packages/crew-runtime/

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e packages/shared-types && \
    pip install --no-cache-dir -e packages/crew-runtime

# ============================================================
# STAGE 2: Runtime (minimal image)
# ============================================================
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r crewai && useradd -r -g crewai -d /app -s /sbin/nologin crewai

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /app/packages/ /app/packages/

# Copy application code
COPY apps/api/ apps/api/

# Security: drop privileges
USER crewai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "apps.api.src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3.3 Web Dockerfile (Next.js Standalone)

```dockerfile
# infra/docker/Dockerfile.web
# ============================================================
# STAGE 1: Dependencies
# ============================================================
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY packages/shared-types/ packages/shared-types/
COPY packages/ui/ packages/ui/

RUN corepack enable && pnpm install --frozen-lockfile

# ============================================================
# STAGE 2: Build
# ============================================================
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages ./packages
COPY apps/web/ apps/web/

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN corepack enable && \
    pnpm --filter web build

# ============================================================
# STAGE 3: Production runner
# ============================================================
FROM node:20-alpine AS runner

RUN addgroup --system --gid 1001 crewai && \
    adduser --system --uid 1001 crewai

WORKDIR /app

COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/public ./apps/web/public
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static

USER crewai

EXPOSE 3000

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

CMD ["node", "apps/web/server.js"]
```

### 3.4 Container Strategy Rules

| Rule | Rationale |
|------|-----------|
| **No root user** | All containers run as non-root (`crewai` user) |
| **Read-only root filesystem** | `securityContext.readOnlyRootFilesystem: true` in K8s |
| **No shell in production** | Distroless or `slim` images only |
| **Single responsibility** | One process per container (no supervisord) |
| **Immutable tags** | Git SHA-based image tags; never `:latest` in production |
| **Vulnerability scanning** | All images scanned by Trivy before deployment |
| **Layer caching** | Dependency installation before code copy for CI speed |
| **Health checks** | Every container has liveness + readiness probes |

### 3.5 Image Tagging Strategy

```
{registry}/{repo}/{component}:{git-sha}-{build-number}

Examples:
  123456789012.dkr.ecr.us-east-1.amazonaws.com/crewai/api:a1b2c3d4-5678
  123456789012.dkr.ecr.us-east-1.amazonaws.com/crewai/web:a1b2c3d4-5678
  123456789012.dkr.ecr.us-east-1.amazonaws.com/crewai/worker:a1b2c3d4-5678

Environment aliases (never deployed from, only for reference):
  crewai/api:staging
  crewai/api:prod
```

---

## 4. Kubernetes Architecture & Deployment Topology

### 4.1 Cluster Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KUBERNETES CLUSTER                                    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    CONTROL PLANE (Managed by cloud provider)              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │  API     │  │  Scheduler│  │  CM      │  │  ETCD    │  │  Cloud    │ │
│  │  │  Server  │  │          │  │          │  │          │  │  Control  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    DATA PLANE (Node Groups)                                │ │
│  │                                                                           │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │ │
│  │  │   SYSTEM NODES       │  │   APPLICATION NODES  │  │   GPU NODES      │  │ │
│  │  │   (On-demand)        │  │   (Spot, with PDB)   │  │   (On-demand)   │  │ │
│  │  │                      │  │                      │  │                  │  │ │
│  │  │  taints:             │  │  taints:             │  │  taints:         │  │ │
│  │  │  CriticalAddonsOnly  │  │  role=app            │  │  nvidia.com/gpu  │  │ │
│  │  │                      │  │                      │  │                  │  │ │
│  │  │  - ingress-nginx     │  │  - api pods          │  │  - ollama pods   │  │ │
│  │  │  - cert-manager      │  │  - web pods          │  │                  │  │ │
│  │  │  - prometheus        │  │  - worker pods       │  │  GPU types:      │  │ │
│  │  │  - vault             │  │  - redis             │  │  - A10G (inf)    │  │ │
│  │  │  - cluster-autoscaler│  │  - postgres          │  │  - A100 (train)  │  │ │
│  │  └─────────────────────┘  └─────────────────────┘  └──────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Namespace Isolation

```yaml
# infra/k8s/bases/namespaces/namespace.yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: crewai-system
  labels:
    purpose: system-components
---
apiVersion: v1
kind: Namespace
metadata:
  name: crewai-app
  labels:
    purpose: application-workloads
---
apiVersion: v1
kind: Namespace
metadata:
  name: crewai-obs
  labels:
    purpose: observability-stack
---
apiVersion: v1
kind: Namespace
metadata:
  name: crewai-storage
  labels:
    purpose: data-stores
```

### 4.3 Network Policies

```yaml
# infra/k8s/bases/namespaces/network-policies.yaml
---
# Default deny-all ingress for application namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: crewai-app
spec:
  podSelector: {}
  policyTypes:
    - Ingress
---
# Allow API to be accessed by web and ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-ingress
  namespace: crewai-app
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: api
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              purpose: application-workloads
          podSelector:
            matchLabels:
              app.kubernetes.io/component: web
        - namespaceSelector:
            matchLabels:
              purpose: system-components
          podSelector:
            matchLabels:
              app.kubernetes.io/component: ingress
      ports:
        - port: 8000
---
# Allow worker + api to connect to Redis
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-redis-ingress
  namespace: crewai-app
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: redis
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: worker
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: api
      ports:
        - port: 6379
---
# Allow worker + api to connect to PostgreSQL
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-postgres-ingress
  namespace: crewai-app
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: postgres
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: worker
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: api
      ports:
        - port: 5432
---
# Allow worker to connect to Ollama
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ollama-ingress
  namespace: crewai-app
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: ollama
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: worker
      ports:
        - port: 11434
---
# Restrictive egress for application namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrictive-egress
  namespace: crewai-app
spec:
  podSelector: {}
  egress:
    - to:
        - namespaceSelector: {}
      ports:
        - port: 53
          protocol: UDP
    - to:
        - podSelector: {}
  policyTypes:
    - Egress
```

### 4.4 Service Topology

```
                         ┌─────────────┐
                         │   Internet   │
                         └──────┬──────┘
                                │
                          ┌─────▼─────┐
                          │  Ingress   │
                          │  (ALB/Nginx)│
                          └─────┬─────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
              ┌─────▼─────┐          ┌──────▼──────┐
              │    Web     │          │    API      │
              │  (Next.js) │          │  (FastAPI)  │
              │  :3000     │          │  :8000      │
              └────────────┘          └──────┬──────┘
                                             │
                    ┌────────────────────────┼────────────────────┐
                    │                        │                    │
              ┌─────▼──────┐         ┌───────▼───────┐    ┌──────▼──────┐
              │   Redis     │         │  PostgreSQL    │    │   Worker    │
              │  (Sentinel) │         │  + PGVector    │    │  (Celery)   │
              │  :6379      │         │  :5432         │    │             │
              └────────────┘         └───────────────┘    └──────┬───────┘
                                                                │
                                                          ┌─────▼──────┐
                                                          │   Ollama   │
                                                          │  :11434    │
                                                          └────────────┘
```

### 4.5 Pod Disruption Budgets

```yaml
# infra/k8s/bases/api/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
  namespace: crewai-app
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app.kubernetes.io/component: api
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: worker-pdb
  namespace: crewai-app
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: worker
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: redis-pdb
  namespace: crewai-app
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: redis
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: postgres-pdb
  namespace: crewai-app
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: postgres
```

### 4.6 Horizontal Pod Autoscalers

```yaml
# infra/k8s/bases/api/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: crewai-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
---
# Worker HPA based on Celery queue depth
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: worker-default-hpa
  namespace: crewai-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: worker-default
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Pods
      pods:
        metric:
          name: celery_queue_depth
        target:
          type: AverageValue
          averageValue: 50
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 120
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 600
      policies:
        - type: Pods
          value: 1
          periodSeconds: 300
```

### 4.7 Resource Requests and Limits

| Component | Request CPU | Request Memory | Limit CPU | Limit Memory | Replicas (Prod) |
|-----------|------------|---------------|-----------|-------------|-----------------|
| api | 500m | 512Mi | 2000m | 2Gi | 3-20 |
| web | 200m | 256Mi | 1000m | 1Gi | 2-10 |
| worker-default | 1000m | 2Gi | 4000m | 8Gi | 2-20 |
| worker-control | 500m | 512Mi | 1000m | 1Gi | 2 |
| worker-hitl | 200m | 256Mi | 500m | 512Mi | 2 |
| worker-beat | 100m | 128Mi | 200m | 256Mi | 1 |
| redis | 1000m | 2Gi | 2000m | 4Gi | 3 (sentinel) |
| postgres | 2000m | 4Gi | 4000m | 8Gi | 2 (primary+replica) |
| ollama | 4000m | 16Gi | 8000m | 32Gi | 1 (+ GPU) |

---

## 5. Redis HA Strategy

### 5.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       REDIS HIGH AVAILABILITY                              │
│                                                                           │
│                         ┌─────────────────┐                                │
│                         │   Redis Sentinel  │                               │
│                         │   (3 instances)   │                               │
│                         └──┬──────┬──────┬──┘                               │
│                            │      │      │                                  │
│                   ┌────────┘      │      └────────┐                        │
│                   ▼               ▼               ▼                        │
│            ┌──────────┐   ┌──────────┐   ┌──────────┐                       │
│            │  Redis   │   │  Redis   │   │  Redis   │                       │
│            │ Primary  │──►│ Replica 1│──►│ Replica 2│                       │
│            └──────────┘   └──────────┘   └──────────┘                       │
│                 │              │              │                              │
│                 └──────────────┴──────────────┘                              │
│                              │                                               │
│                      Replication (async)                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Redis Configuration

```conf
# infra/k8s/bases/redis/configmap.conf

# Memory management
maxmemory 4gb
maxmemory-policy allkeys-lru
maxmemory-samples 10

# Persistence
appendonly yes
appendfsync everysec
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Replication
replica-serve-stale-data yes
replica-read-only yes
replica-lazy-flush no
replica-ping-replica-period 10

# Security
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command CONFIG ""
rename-command SHUTDOWN ""
rename-command DEBUG ""

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Connection
timeout 300
tcp-keepalive 60
maxclients 10000
```

### 5.3 Redis Sentinel StatefulSet

```yaml
# infra/k8s/bases/redis/statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: crewai-app
spec:
  serviceName: redis-headless
  replicas: 3
  selector:
    matchLabels:
      app.kubernetes.io/component: redis
  template:
    metadata:
      labels:
        app.kubernetes.io/component: redis
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app.kubernetes.io/component
                      operator: In
                      values:
                        - redis
                topologyKey: topology.kubernetes.io/zone
      containers:
        - name: redis
          image: redis:7-alpine
          command:
            - /bin/sh
            - -c
            - |
              if [[ ${HOSTNAME} == *-0 ]]; then
                redis-server /etc/redis/redis.conf
              else
                redis-server /etc/redis/redis.conf \
                  --replicaof redis-0.redis-headless.crewai-app.svc.cluster.local 6379
              fi
          ports:
            - containerPort: 6379
              name: redis
          volumeMounts:
            - name: config
              mountPath: /etc/redis
            - name: data
              mountPath: /data
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2000m
              memory: 4Gi
          livenessProbe:
            exec:
              command:
                - redis-cli
                - ping
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command:
                - redis-cli
                - ping
            initialDelaySeconds: 5
            periodSeconds: 5
      volumes:
        - name: config
          configMap:
            name: redis-config
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 50Gi
        storageClassName: gp3
```

### 5.4 Redis Failover Flow

```
1. Sentinel detects primary is down (5s quorum timeout)
2. Sentinel leader election (Raft-based among 3 sentinels)
3. New primary promoted from replicas (automatic)
4. Application reconnects via sentinel service discovery
5. Old primary rejoins as replica when recovered
6. Total failover time: ~10-15 seconds
7. Pub/Sub messages during failover window are lost (ephemeral)
```

### 5.5 Redis Database Layout (Production)

| DB Index | Usage | Eviction | Persistence |
|----------|-------|----------|-------------|
| 0 | Celery broker | N/A | No (re-queued on failover) |
| 1 | Celery results | allkeys-lru (24h TTL) | No |
| 2 | Short-term memory | allkeys-lru (1h TTL) | AOF |
| 3 | Event Pub/Sub + Streams | N/A (stream maxlen) | AOF |
| 4 | Rate limiting counters | allkeys-lru (1m TTL) | No |
| 5 | Session store / JWT blacklist | allkeys-lru (24h TTL) | AOF |

---

## 6. PostgreSQL HA & PGVector Deployment Strategy

### 6.1 Architecture (Managed - Preferred)

For production, **managed PostgreSQL (RDS Aurora / Cloud SQL)** is strongly recommended:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL HIGH AVAILABILITY (Managed)                   │
│                                                                           │
│                      ┌──────────────────┐                                  │
│                      │   PgBouncer       │                                  │
│                      │  (Connection Pool)│                                  │
│                      └────────┬─────────┘                                  │
│                               │                                            │
│                ┌──────────────┼──────────────┐                            │
│                ▼              ▼              ▼                            │
│         ┌──────────┐   ┌──────────┐   ┌──────────┐                        │
│         │ Primary  │──►│ Replica 1│──►│ Replica 2│                        │
│         │ (RW)     │   │ (RO)     │   │ (RO)     │                        │
│         │ AZ 1     │   │ AZ 2     │   │ AZ 3     │                        │
│         └──────────┘   └──────────┘   └──────────┘                        │
│              │                                                             │
│         ┌────▼────┐                                                       │
│         │ WAL     │                                                       │
│         │ Archive │   S3 bucket for automated backups                     │
│         └─────────┘                                                       │
│                                                                           │
│  Failover: Automatic within 30-60 seconds (Multi-AZ)                       │
│  Backup: Automated daily snapshots + 30-day retention                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Terraform Configuration (RDS Aurora)

```hcl
# infra/terraform/modules/rds/main.tf

resource "aws_rds_cluster" "postgres" {
  cluster_identifier      = "crewai-postgres-${var.environment}"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "16.3"
  database_name           = "crewai"
  master_username         = "crewai_admin"
  master_password         = random_password.master.result

  backup_retention_period = 30
  preferred_backup_window = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.rds.arn

  enabled_cloudwatch_logs_exports = ["postgresql"]
  deletion_protection     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "crewai-postgres-${var.environment}-final"

  vpc_security_group_ids  = [aws_security_group.rds.id]
  db_subnet_group_name    = aws_db_subnet_group.private.name

  tags = {
    Environment = var.environment
    Application = "crewai"
  }
}

resource "aws_rds_cluster_instance" "primary" {
  identifier         = "crewai-postgres-primary-${var.environment}"
  cluster_identifier = aws_rds_cluster.postgres.id
  instance_class     = var.primary_instance_class
  engine             = aws_rds_cluster.postgres.engine
  engine_version     = aws_rds_cluster.postgres.engine_version
  promotion_tier     = 0
  publicly_accessible = false
}

resource "aws_rds_cluster_instance" "replica" {
  count              = 2
  identifier         = "crewai-postgres-replica-${count.index}-${var.environment}"
  cluster_identifier = aws_rds_cluster.postgres.id
  instance_class     = var.replica_instance_class
  engine             = aws_rds_cluster.postgres.engine
  engine_version     = aws_rds_cluster.postgres.engine_version
  promotion_tier     = 1
  publicly_accessible = false
}
```

### 6.3 PostgreSQL Configuration for PGVector

```conf
# Shared buffer and memory tuning
shared_buffers = '2GB'
effective_cache_size = '6GB'
work_mem = '128MB'
maintenance_work_mem = '512MB'
wal_buffers = '64MB'
random_page_cost = 1.1
effective_io_concurrency = 200

# Connection
max_connections = 200

# PGVector HNSW index tuning (applied per-query)
# SET hnsw.ef_search = 100;
# SET hnsw.ef_construction = 200;
```

### 6.4 PgBouncer Connection Pooling

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
  namespace: crewai-storage
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/component: pgbouncer
  template:
    metadata:
      labels:
        app.kubernetes.io/component: pgbouncer
    spec:
      containers:
        - name: pgbouncer
          image: bitnami/pgbouncer:latest
          ports:
            - containerPort: 6432
              name: pgbouncer
          env:
            - name: POSTGRESQL_HOST
              value: postgres-headless
            - name: POSTGRESQL_PORT
              value: "5432"
            - name: POSTGRESQL_USERNAME
              value: crewai
            - name: POSTGRESQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-creds
                  key: password
            - name: PGBOUNCER_DATABASE
              value: crewai
            - name: PGBOUNCER_MAX_CLIENT_CONN
              value: "500"
            - name: PGBOUNCER_DEFAULT_POOL_SIZE
              value: "50"
            - name: PGBOUNCER_MIN_POOL_SIZE
              value: "10"
            - name: PGBOUNCER_RESERVE_POOL_SIZE
              value: "10"
```

### 6.5 PGVector Index Strategy

| Table | Index Type | Parameters | Use Case |
|-------|-----------|------------|----------|
| `agent_memories.embedding` | HNSW | `m=16, ef_construction=200` | High-recall semantic search |
| `agent_memories.embedding` | IVFFlat | `lists=100` (fallback) | Faster index build for initial load |
| `entity_memories.attributes` | GIN | Default | JSONB structured queries |
| `entity_memories.relations` | GIN | Default | Relationship graph queries |

---

## 7. Ollama Deployment Strategy

### 7.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      OLLAMA DEPLOYMENT ARCHITECTURE                        │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    Ollama StatefulSet (GPU Node)                      │ │
│  │                                                                       │ │
│  │  ┌──────────────┐                                                     │ │
│  │  │  ollama       │  Exposed on cluster-internal service:11434         │ │
│  │  │  (GPU: A10G)  │  Load-balanced across model requests               │ │
│  │  └──────┬───────┘                                                     │ │
│  │         │                                                              │ │
│  │    ┌────▼────┐                                                        │ │
│  │    │  Models │                                                         │ │
│  │    │  Volume │  Pre-pulled models stored on persistent volume          │ │
│  │    │  (200GB)│  Models pulled at deployment time via init container    │ │
│  │    └─────────┘                                                        │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  Pre-pulled at deploy time:                                               │
│  - llama3:8b        (economy tier,  4.7GB)                                │
│  - llama3:70b       (standard tier,  40GB)  [optional, GPU-dependent]     │
│  - mistral          (standard tier,  4.1GB)                                │
│  - nomic-embed-text (embeddings,     274MB)                                │
│                                                                           │
│  Fallback chain:                                                          │
│  ollama/llama3:8b → gpt-4o-mini (cloud) when local capacity exceeded     │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Ollama StatefulSet

```yaml
# infra/k8s/bases/ollama/statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: ollama
  namespace: crewai-app
spec:
  serviceName: ollama-headless
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: ollama
  template:
    metadata:
      labels:
        app.kubernetes.io/component: ollama
    spec:
      runtimeClassName: nvidia
      nodeSelector:
        node-type: gpu
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      initContainers:
        - name: model-puller
          image: ollama/ollama:latest
          command:
            - /bin/sh
            - -c
            - |
              ollama pull llama3:8b &
              ollama pull mistral &
              ollama pull nomic-embed-text &
              wait
          volumeMounts:
            - name: models
              mountPath: /root/.ollama
          resources:
            requests:
              cpu: 2000m
              memory: 8Gi
      containers:
        - name: ollama
          image: ollama/ollama:latest
          ports:
            - containerPort: 11434
              name: ollama
          env:
            - name: OLLAMA_HOST
              value: "0.0.0.0"
            - name: OLLAMA_NUM_PARALLEL
              value: "1"
            - name: OLLAMA_MAX_LOADED_MODELS
              value: "2"
            - name: OLLAMA_KEEP_ALIVE
              value: "5m"
          volumeMounts:
            - name: models
              mountPath: /root/.ollama
          resources:
            requests:
              cpu: 4000m
              memory: 16Gi
              nvidia.com/gpu: 1
            limits:
              cpu: 8000m
              memory: 32Gi
              nvidia.com/gpu: 1
          livenessProbe:
            exec:
              command:
                - ollama
                - list
            initialDelaySeconds: 120
            periodSeconds: 30
          readinessProbe:
            exec:
              command:
                - ollama
                - list
            initialDelaySeconds: 30
            periodSeconds: 10
  volumeClaimTemplates:
    - metadata:
        name: models
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 200Gi
        storageClassName: gp3
```

### 7.3 GPU Node Group Autoscaling

| Metric | Threshold | Window | Action |
|--------|-----------|--------|--------|
| GPU utilization > 80% | Scale up GPU nodes | 5 minutes | Add GPU node to cluster |
| GPU utilization < 30% | Scale down GPU nodes | 30 minutes | Remove GPU node from cluster |
| Ollama queue depth > 5 | Scale up Ollama replicas | 2 minutes | Increase pod count |
| No Ollama pods pending | Scale GPU group to 0 | 60 minutes | Cost optimization |

---

## 8. Celery Worker Topology

### 8.1 Worker Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CELERY WORKER TOPOLOGY                                 │
│                                                                           │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │
│  │   worker-default     │  │   worker-control    │  │   worker-hitl    │  │
│  │   (2-20 replicas)    │  │   (2 replicas)      │  │   (2 replicas)   │  │
│  ├─────────────────────┤  ├─────────────────────┤  ├──────────────────┤  │
│  │                     │  │                     │  │                  │  │
│  │  Queues:            │  │  Queues:            │  │  Queues:         │  │
│  │  - workflow_default │  │  - workflow_control │  │  - hitl          │  │
│  │  - workflow_low     │  │                     │  │                  │  │
│  │  - workflow_high    │  │                     │  │                  │  │
│  │                     │  │                     │  │                  │  │
│  │  Concurrency: 4     │  │  Concurrency: 2     │  │  Concurrency: 2  │  │
│  │  Prefetch: 1        │  │  Prefetch: 1        │  │  Prefetch: 1     │  │
│  │                     │  │                     │  │                  │  │
│  │  CPU: 1000m/RAM:2Gi │  │  CPU: 500m/RAM:512Mi│  │  CPU:200m/RAM:256│  │
│  └──────────┬──────────┘  └──────────┬──────────┘  └────────┬─────────┘  │
│             │                        │                       │            │
│             └───────────┬────────────┴───────────┬──────────┘            │
│                         │                        │                        │
│                   ┌─────▼─────┐            ┌──────▼──────┐               │
│                   │   Redis   │            │  PostgreSQL │               │
│                   │  (Broker) │            │  (Results)  │               │
│                   └───────────┘            └─────────────┘               │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                         Celery Beat                                │    │
│  │  (1 replica, 100m CPU / 128Mi RAM)                                │    │
│  │  Responsible for: periodic task scheduling, heartbeat monitoring   │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Queue Routing Configuration

```python
# apps/worker/src/config.py

CELERY_QUEUES = {
    "workflow_high": {
        "exchange": "workflows",
        "routing_key": "workflow.execute.high",
        "queue_arguments": {"x-max-priority": 10},
    },
    "workflow_default": {
        "exchange": "workflows",
        "routing_key": "workflow.execute.default",
        "queue_arguments": {"x-max-priority": 5},
    },
    "workflow_low": {
        "exchange": "workflows",
        "routing_key": "workflow.execute.low",
        "queue_arguments": {"x-max-priority": 1},
    },
    "workflow_control": {
        "exchange": "workflows.control",
        "routing_key": "workflow.control.#",
        "queue_arguments": {"x-max-priority": 10},
    },
    "hitl": {
        "exchange": "hitl",
        "routing_key": "hitl.decision",
    },
}
```

### 8.3 Task Routing Rules

| Task Type | Queue | Priority | Description |
|-----------|-------|----------|-------------|
| `workflow.execute` (standard) | `workflow_default` | 5 | Standard workflow execution |
| `workflow.execute` (HITL resume) | `workflow_high` | 9 | HITL decisions resume quickly |
| `workflow.execute` (replay) | `workflow_high` | 8 | Replay should not block new executions |
| `workflow.control.pause` | `workflow_control` | 10 | Pause must be delivered ASAP |
| `workflow.control.kill` | `workflow_control` | 10 | Kill must be delivered immediately |
| `hitl.decision` | `hitl` | — | Lightweight, dedicated worker |

### 8.4 Worker Deployment Manifests

```yaml
# infra/k8s/bases/worker/deployment-default.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-default
  namespace: crewai-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/component: worker
      worker-type: default
  template:
    metadata:
      labels:
        app.kubernetes.io/component: worker
        worker-type: default
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      serviceAccountName: worker
      containers:
        - name: worker
          image: {registry}/crewai/worker:{version}
          command:
            - celery
            - -A
            - apps.worker.src.celery_app
            - worker
            - -Q
            - workflow_default,workflow_low,workflow_high
            - --concurrency=4
            - --prefetch-multiplier=1
            - --loglevel=info
            - --max-tasks-per-child=100
          env:
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: redis-creds
                  key: url
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: postgres-creds
                  key: url
          envFrom:
            - secretRef:
                name: llm-api-keys
          resources:
            requests:
              cpu: 1000m
              memory: 2Gi
            limits:
              cpu: 4000m
              memory: 8Gi
          livenessProbe:
            exec:
              command:
                - celery
                - -A
                - apps.worker.src.celery_app
                - inspect
                - ping
            initialDelaySeconds: 60
            periodSeconds: 30
          readinessProbe:
            exec:
              command:
                - celery
                - -A
                - apps.worker.src.celery_app
                - inspect
                - ping
            initialDelaySeconds: 10
            periodSeconds: 10
---
# Worker Control Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-control
  namespace: crewai-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/component: worker
      worker-type: control
  template:
    metadata:
      labels:
        app.kubernetes.io/component: worker
        worker-type: control
    spec:
      serviceAccountName: worker
      containers:
        - name: worker
          image: {registry}/crewai/worker:{version}
          command:
            - celery
            - -A
            - apps.worker.src.celery_app
            - worker
            - -Q
            - workflow_control
            - --concurrency=2
            - --prefetch-multiplier=1
            - --loglevel=info
          env:
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: redis-creds
                  key: url
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: postgres-creds
                  key: url
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
---
# Worker HITL Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-hitl
  namespace: crewai-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/component: worker
      worker-type: hitl
  template:
    metadata:
      labels:
        app.kubernetes.io/component: worker
        worker-type: hitl
    spec:
      serviceAccountName: worker
      containers:
        - name: worker
          image: {registry}/crewai/worker:{version}
          command:
            - celery
            - -A
            - apps.worker.src.celery_app
            - worker
            - -Q
            - hitl
            - --concurrency=2
            - --prefetch-multiplier=1
            - --loglevel=info
          env:
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: redis-creds
                  key: url
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: postgres-creds
                  key: url
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
---
# Celery Beat Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-beat
  namespace: crewai-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: worker
      worker-type: beat
  template:
    metadata:
      labels:
        app.kubernetes.io/component: worker
        worker-type: beat
    spec:
      containers:
        - name: beat
          image: {registry}/crewai/worker:{version}
          command:
            - celery
            - -A
            - apps.worker.src.celery_app
            - beat
            - --loglevel=info
          env:
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: redis-creds
                  key: url
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
```

### 8.5 Celery Monitoring (Flower)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-flower
  namespace: crewai-obs
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: celery-flower
  template:
    metadata:
      labels:
        app.kubernetes.io/component: celery-flower
    spec:
      containers:
        - name: flower
          image: mher/flower:latest
          ports:
            - containerPort: 5555
              name: flower
          env:
            - name: CELERY_BROKER_URL
              valueFrom:
                secretKeyRef:
                  name: redis-creds
                  key: url
            - name: CELERY_RESULT_BACKEND
              valueFrom:
                secretKeyRef:
                  name: redis-creds
                  key: url_database
          args:
            - --port=5555
            - --broker-api=http://redis-service:6379
            - --url-prefix=flower
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
```

---

## 9. Event Streaming Infrastructure

### 9.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      EVENT STREAMING INFRASTRUCTURE                        │
│                                                                           │
│  ┌──────────┐    SSE (HTTP)     ┌──────────────┐    Redis Sub/Stream   ┌──┴──┐
│  │ Frontend │◄──────────────────│   API Server  │◄────────────────────│Worker│
│  │ (Browser)│   Keepalive: 30s  │  SSE Manager  │                     └─────┘
│  └──────────┘                   └──────┬───────┘                           │
│                                        │                                    │
│                                  ┌─────▼─────┐                             │
│                                  │   Redis    │                             │
│                                  │  Stream    │                             │
│                                  │  (Persist) │                             │
│                                  └───────────┘                             │
│                                                                           │
│  Redis Stream vs Pub/Sub Strategy:                                         │
│                                                                           │
│  ┌───────────────────────┐  ┌─────────────────────────────────────────┐  │
│  │     Pub/Sub            │  │     Redis Streams                        │  │
│  │  (Real-time events)    │  │  (Persistent + replay-capable)           │  │
│  ├───────────────────────┤  ├─────────────────────────────────────────┤  │
│  │ - Ephemeral           │  │ - Persistent (maxlen configurable)       │  │
│  │ - No replay           │  │ - Consumer groups for at-least-once      │  │
│  │ - Broadcast to all    │  │ - Replay from last_event_id              │  │
│  │ - No backpressure     │  │ - Backpressure via consumer group ack    │  │
│  │                       │  │                                           │  │
│  │ Use: SSE fan-out,     │  │ Use: Event persistence, replay on        │  │
│  │  real-time UI updates │  │  reconnect, audit log backup             │  │
│  └───────────────────────┘  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Event Channel Layout

```
# Event channels (Redis DB 3)
crew:workflow:{execution_id}:events      # Pub/Sub: Real-time execution events
crew:stream:{execution_id}:events        # Stream: Persistent event log (maxlen 10000)

# Control channels (Redis DB 3)
crew:control:{execution_id}:commands     # Pub/Sub: Pause/resume/kill commands
crew:control:{execution_id}:status       # Pub/Sub: Status acknowledgements

# System channels (Redis DB 3)
crew:system:alerts                       # Pub/Sub: System-wide alerts
crew:system:health                       # Pub/Sub: Health check heartbeat

# Pattern subscriptions
crew:workflow:*:events                   # SSE relay subscribes with PSUBSCRIBE
```

### 9.3 Redis Stream Backpressure Strategy

```python
# apps/worker/src/events/publisher.py

class EventPublisher:
    """
    Dual-mode event publisher:
    - Pub/Sub for real-time SSE fan-out
    - Stream for persistent event log with replay capability
    """

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis
        self._seq = 0

    async def publish(self, event: RuntimeEvent) -> None:
        """Publish a runtime event to both Pub/Sub and Stream."""
        self._seq += 1
        event.sequence = self._seq
        payload = event.model_dump_json()

        # Pub/Sub for real-time streaming to SSE
        channel = f"crew:workflow:{event.execution_id}:events"
        await self._redis.publish(channel, payload)

        # Stream for persistence
        stream = f"crew:stream:{event.execution_id}:events"
        await self._redis.xadd(stream, {"payload": payload}, maxlen=10000)

    async def publish_control(self, execution_id: str, command: str, data: dict) -> None:
        channel = f"crew:control:{execution_id}:commands"
        await self._redis.publish(channel, json.dumps({
            "command": command, "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }))


class EventStreamManager:
    """Manages Redis Stream consumer groups for event replay."""

    async def replay_from(
        self, execution_id: str, last_event_id: str | None,
    ) -> list[RuntimeEvent]:
        stream = f"crew:stream:{execution_id}:events"
        if last_event_id:
            results = await self._redis.xrange(
                stream, min=last_event_id, max="+", count=500
            )
        else:
            results = await self._redis.xrevrange(stream, max="+", count=50)
            results.reverse()
        return [RuntimeEvent.model_validate_json(r[1]["payload"]) for r in results]
```---

## 10. Observability Stack

### 10.1 Stack Architecture

The observability stack follows the **OpenTelemetry** standard for data emission and the **Grafana Ecosystem** for storage, visualization, and alerting.

```
+----------------------------------------------------------+
|                    OBSERVABILITY STACK                     |
+----------------------------------------------------------+
|                                                           |
|  +----------------+  +----------------+  +--------------+ |
|  |    METRICS     |  |     LOGS       |  |    TRACES    | |
|  |                |  |                |  |              | |
|  | OpenTelemetry  |  | Vector/OTel    |  | OpenTelemetry| |
|  | SDK            |  | DaemonSet      |  | SDK          | |
|  |      |         |  |      |         |  |      |       | |
|  |      v         |  |      v         |  |      v       | |
|  | Prometheus     |  | Loki + S3      |  | Tempo + S3  | |
|  | (15d retention)|  | (30d retention)|  | (14d retent) | |
|  +-------+--------+  +-------+--------+  +------+------+ |
|          |                    |                  |        |
|          +---------+----------+---------+--------+        |
|                    |                    |                 |
|                    v                    v                 |
|           +----------------------------------------+     |
|           |              GRAFANA                     |    |
|           |   (Dashboards, Alerting, Explore)        |    |
|           +----------------------------------------+     |
|                    |                                      |
|                    v                                      |
|           +------------------------------+                |
|           |  PagerDuty / Slack           |                |
|           |  (Alert Notification)        |                |
|           +------------------------------+                |
+----------------------------------------------------------+
```

### 10.2 OpenTelemetry Collector Configuration

Receivers: OTLP (gRPC :4317, HTTP :4318)
Processors: batch (5s, 1000 items), memory_limiter (512MB), attributes (environment tags)
Exporters: Prometheus (:8889), Loki (:3100), Tempo (:4317)
Pipelines: traces -> Tempo, metrics -> Prometheus, logs -> Loki

### 10.3 Grafana Datasources

Datasources configured:
- Prometheus: metric storage and querying
- Loki: log aggregation with trace_id derived fields
- Tempo: trace storage with tracesToLogs linking

### 10.4 Prometheus Alert Rules

Alert groups:
- api: HighErrorRate (>5% for 5m), HighLatency (p95>2s for 5m), LowAvailability (<80% for 2m)
- worker: QueueDepthHigh (>500 for 5m), TaskFailureRate (>10% for 10m), NoHeartbeat (2m)
- redis: MemoryHigh (>85% for 5m), ReplicationLag (>1MB for 2m)
- postgres: HighConnections (>150 for 5m), ReplicationLag (>100MB for 5m)
- workflow: ExecutionFailureRate (>15% for 15m), HITLApprovalTimeout (>1h)
- ollama: GPUHighUtilization (>95% for 5m), InferenceLatency (p95>30s for 5m)

### 10.5 Grafana Dashboard Layout

| Dashboard | Key Panels | Refresh |
|-----------|-----------|---------|
| API Overview | Request rate, error rate, p50/p95/p99 latency | 15s |
| Worker Overview | Queue depth, task throughput, failure rate | 15s |
| Redis Overview | Memory, hit rate, ops/sec, replication lag | 15s |
| PostgreSQL | Connections, cache hit ratio, table sizes | 15s |
| Workflow Executions | Success/failure ratio, avg duration, tokens | 30s |
| Kubernetes Cluster | Node health, pod status, resource usage | 30s |

---

## 11. Logging Pipeline

### 11.1 Architecture

All services emit structured JSON logs to stdout. Vector DaemonSet on each K8s node collects, parses, adds metadata, and forwards to Loki. Loki stores logs in S3 with 30-day retention.

### 11.2 Log Format Specification

Every log entry MUST include:
- timestamp (ISO 8601)
- level (debug|info|warn|error|critical)
- logger (module path)
- message (human-readable)
- service (api|worker|web)
- environment (dev|staging|prod)
- correlation_id (for trace linking)
- execution_id / workflow_id (domain context)

### 11.3 Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| DEBUG | Dev only | SQL queries, full payloads |
| INFO | Normal ops | Workflow started, agent thought |
| WARN | Degraded | Tool retry, queue depth high |
| ERROR | Operation failed | Tool timeout, LLM error |
| CRITICAL | System failure | DB connection lost, worker crash |

### 11.4 Log Retention

| Environment | Retention | Storage |
|-------------|-----------|---------|
| Dev | 7 days | PVC |
| Staging | 14 days | PVC + S3 |
| Production | 30 days hot, 90 days cold | S3 via Loki |
| Audit logs (DB) | 1 year | PostgreSQL partitioned |
| Execution logs | 90 days | PostgreSQL partitioned |

---

## 12. Metrics Pipeline

### 12.1 Architecture

Application metrics emitted via OpenTelemetry SDK with Prometheus exporter:
- HTTP: request count, latency, error rate (by method, endpoint, status)
- Workflow: execution count, duration (by workflow_id, status)
- Agent: tool call count (by agent_id, tool_name, status)
- LLM: token count, cost, call duration (by provider, model)
- Memory: query count (by memory_type, status)

Infrastructure metrics collected via Prometheus exporters:
- Node: CPU, memory, disk, network
- GPU: utilization, memory, temperature
- PostgreSQL: query count, cache hit ratio, connections
- Redis: memory, ops/sec, hit rate, replication lag

### 12.2 Key Performance Indicators

| KPI | Target | Alert |
|-----|--------|-------|
| API p95 latency | < 500ms | > 2s for 5m |
| API error rate | < 1% | > 5% for 5m |
| API availability | > 99.9% | < 99.9% |
| Worker failure rate | < 5% | > 10% for 10m |
| Worker queue depth | < 100 | > 500 for 5m |
| Workflow success rate | > 90% | < 85% for 15m |
| Redis memory | < 70% | > 85% for 5m |
| LLM p95 latency | < 10s | > 30s for 5m |
| HITL approval time | < 30 min | > 60 min |
| GPU utilization | < 80% | > 95% for 5m |

---

## 13. Tracing Architecture

### 13.1 Distributed Trace Flow

```
Frontend -> API -> Celery Worker -> CrewRuntime -> Ollama/LLM
   |         |           |               |             |
   +---------+-----------+---------------+-------------+
                       |
                  OpenTelemetry
                  Collector (OTLP)
                       |
                   Tempo (Backend)
                       |
                   Grafana (Explore)
```

### 13.2 Span Hierarchy

Root span: HTTP request or Celery task
- validate_config
- create_execution
- enqueue_task
- build_crew
  - build_agents
  - resolve_llm
  - resolve_tools
- execute_crew
  - agent_N_execution
    - llm_call (tokens, cost, duration)
    - tool_call (input, output, duration)
  - checkpoint_save
- finalize_execution

### 13.3 Trace Sampling Strategy

| Trace Type | Sampling Rate | Rationale |
|------------|---------------|-----------|
| GET requests | 10% | Read-heavy, low-value |
| POST/PUT/DELETE | 100% | Mutations, audit-critical |
| Workflow executions | 100% | Core business value |
| Agent execution steps | 10% | High volume |
| LLM calls | 100% | Cost tracking |
| Errors/exceptions | 100% | Always capture failures |
| Health checks | 0% | No business value |

---

## 14. Secrets Management

### 14.1 Architecture

HashiCorp Vault cluster (3 nodes, etcd backend) stores all secrets:
- Database credentials (dynamic, rotated every 24h)
- Redis credentials (dynamic, rotated every 24h)
- JWT secret (static, rotated quarterly)
- LLM API keys (OpenAI, Anthropic, etc.)

### 14.2 Secret Injection Method

Vault Agent Sidecar pattern:
- Sidecar container in each pod reads secrets from Vault
- Injects secrets as files in the pod (never environment variables)
- Auto-rotates on secret change without pod restart
- Every secret access is audit-logged

### 14.3 Vault Policies

| Policy | Path | Capabilities |
|--------|------|-------------|
| api-policy | secret/data/crewai/api/* | read |
| api-policy | secret/data/crewai/llm/* | read |
| worker-policy | secret/data/crewai/worker/* | read |
| worker-policy | secret/data/crewai/llm/* | read |
| admin-policy | secret/data/crewai/* | read, create, update, delete |

### 14.4 Secret Rotation Schedule

| Secret | Rotation | Method | Downtime |
|--------|----------|--------|----------|
| Database passwords | 24h | Vault dynamic | Zero |
| Redis passwords | 24h | Vault dynamic | Zero |
| JWT secret | Quarterly | Manual + overlap | Zero |
| LLM API keys | As needed | Manual in Vault | Zero |
| TLS certs | 90 days | cert-manager auto | Zero |

---

## 15. RBAC Infrastructure

### 15.1 Role Hierarchy

```
ADMIN     - Full system access (audit logs, user management)
  |
  +-- OPERATOR  - Run/manage workflows, create agents
  |     |
  |     +-- REVIEWER - Approve HITL tasks
  |
  +-- VIEWER    - Read-only access
```

### 15.2 Kubernetes RBAC

Each application component has a dedicated ServiceAccount with minimal permissions:
- API: get/list pods, manage leases (for coordination)
- Worker: get pods, manage leases
- Web: no K8s API access

### 15.3 Application RBAC

Route protection matrix:
| Endpoint | Required Role |
|----------|--------------|
| /health, /ready, /docs | Public |
| /api/v1/auth/* | Public |
| /api/v1/workflows GET | VIEWER |
| /api/v1/workflows POST/PUT | OPERATOR |
| /api/v1/workflows DELETE | ADMIN |
| /api/v1/workflow/run | OPERATOR |
| /api/v1/approvals/* | REVIEWER |
| /api/v1/audit/logs | ADMIN |
| /api/v1/users | ADMIN |

---

## 16. CI/CD Pipeline Architecture

### 16.1 Pipeline Stages

```
Commit -> CI (GitHub Actions) -> CD (ArgoCD) -> Environment

CI Stages:
1. Lint & Type Check (ruff, mypy, eslint, tsc)
2. Unit Tests (pytest, vitest) with services (PostgreSQL, Redis)
3. Docker Build + Vulnerability Scan (Trivy, fail on HIGH+)
4. Push to Registry (ECR/GCR with Git SHA tag)
5. Integration Tests (deploy to ephemeral namespace, run tests, teardown)

CD Stages (ArgoCD GitOps):
6. Deploy to Staging (automatic on main merge)
7. Smoke Tests (health checks, basic assertions)
8. Manual Approval Gate (Slack + GitHub deploy button)
9. Deploy to Production (phased: 10% -> 50% -> 100% canary)
10. Post-deploy Smoke Tests
11. Notify Slack + PagerDuty (low priority)
```

### 16.2 Deployment Rollback

Automatic rollback triggers:
- Health check failures for 5+ minutes
- Error rate spike > 10% for 3+ minutes
- PagerDuty critical alert from deploy

Rollback procedure:
1. argocd app rollback crewai-prod <revision> --prune
2. Verify health: argocd app wait crewai-prod --health
3. Notify Slack: "Production rolled back to revision N"
4. Fix forward, re-deploy

---

## 17. Backup & Recovery Architecture

### 17.1 Backup Schedule

| Data | Method | Frequency | Retention | RPO | RTO |
|------|--------|-----------|-----------|-----|-----|
| PostgreSQL | pg_dump (full) | Daily | 30 days | 24h | 2h |
| PostgreSQL | WAL archive | Continuous | 7 days | 5min | 30min |
| PostgreSQL | RDS snapshot | Daily | 30 days | 24h | 1h |
| Redis RDB | SAVE | Every 6h | 7 days | 6h | 1h |
| Redis AOF | appendfsync everysec | Continuous | 7 days | 1s | 10min |
| Vault | raft snapshot | Daily | 30 days | 24h | 1h |
| Docker images | Registry | Per build | 90 days | N/A | N/A |
| Config | Git | Per commit | Forever | N/A | N/A |

### 17.2 Backup Infrastructure

Kubernetes CronJob runs daily at 3 AM:
- pg_dump with custom format + compression level 9
- Upload to S3 with environment-prefixed path
- S3 lifecycle policy: 30-day retention, then Glacier
- Cross-region replication for DR

### 17.3 Restore Procedure

1. Identify backup timestamp
2. Download from S3
3. Restore PostgreSQL: pg_restore --clean --if-exists
4. Restore Redis: load RDB file
5. Verify data integrity (row counts, checksums)
6. Notify team of restore completion

---

## 18. Environment Strategy

### 18.1 Environment Definitions

| Environment | Purpose | Infrastructure | HA | Data | Deploy Trigger |
|-------------|---------|---------------|----|------|----------------|
| dev | Local dev | Docker Compose | None | Ephemeral | Manual |
| dev-k8s | K8s dev | Single-node K3s | None | Ephemeral | PR auto-deploy |
| staging | Pre-prod | Multi-node K8s | Limited | Anonymized | Main merge |
| prod | Production | Multi-node K8s | Full HA | Real | Manual approval |
| dr | Disaster recovery | Standby K8s (2nd region) | Full HA | Replicated | Manual failover |

### 18.2 Environment Promotion Gates

Development -> Staging:
- All CI checks pass
- Integration tests pass
- ArgoCD auto-deploys on main merge

Staging -> Production:
- Staging healthy for 24h
- Manual approval from lead engineer
- Load test results acceptable
- Security scan reviewed
- Migration runbook reviewed

---

## 19. Scaling Strategy

### 19.1 Horizontal Scaling

| Component | Metric | Threshold | Max Replicas |
|-----------|--------|-----------|-------------|
| API | CPU utilization | > 70% | 20 |
| Worker-default | Queue depth | > 50 | 20 |
| Worker-control | N/A | Fixed | 2 |
| Worker-hitl | Pending HITL count | > 50 | 5 |
| Web | CPU utilization | > 70% | 10 |

### 19.2 Vertical Scaling

| Component | Scale Up | Scale Down |
|-----------|----------|------------|
| PostgreSQL | Instance class upgrade | Instance class downgrade |
| Redis | Memory increase | Memory decrease |
| Ollama | GPU upgrade (A10G -> A100) | GPU downgrade |

### 19.3 Database Scaling

- Read replicas: 2 for read-heavy workloads
- Connection pooling: PgBouncer (500 client -> 50 DB connections)
- PGVector: HNSW index for high-QPS vector search
- Partitioning: execution_logs partitioned by month

---

## 20. Failover Strategy

### 20.1 Component Failover

| Component | Failover Mechanism | RTO | RPO |
|-----------|-------------------|-----|-----|
| API | Kubernetes HPA + PDB | 30s | N/A |
| Worker | Celery acks_late + re-queue | 60s | N/A |
| Redis | Sentinel auto-promote | 15s | 1s (AOF) |
| PostgreSQL | RDS Multi-AZ failover | 60s | < 1s |
| Ollama | No HA (single GPU), retry on failure | 5min | N/A |
| Vault | Raft leader election | 30s | N/A |
| Ingress | Load balancer health checks | 10s | N/A |

### 20.2 Multi-AZ Deployment

- All stateless components spread across 3 availability zones
- Redis: 1 primary + 2 replicas across AZs
- PostgreSQL: Aurora Multi-AZ with 1 writer + 2 readers
- StatefulSets with podAntiAffinity for zone distribution

### 20.3 Graceful Degradation

When dependencies fail:
- Redis down: API returns 503, workers cannot accept new tasks
- PostgreSQL down: API returns 503, in-flight executions fail
- Ollama down: Model router falls back to cloud LLM providers
- Vault down: Cached secrets used for up to 1 hour
- Celery broker down: Tasks remain in queue, no new executions

---

## 21. Infrastructure Security Architecture

### 21.1 Defense in Depth Layers

```
Layer 1: Network
- Private subnets for all workloads
- VPC with no internet gateway for backend services
- Network policies (default deny ingress/egress)
- Security groups limited to necessary ports

Layer 2: Identity
- Kubernetes RBAC with least privilege
- IAM roles for service accounts (IRSA)
- Vault for secrets management
- JWT-based API authentication

Layer 3: Application
- Input validation (Zod/Pydantic schemas)
- Rate limiting (Redis token bucket)
- CORS configuration
- SQL injection prevention (ORM)
- No root containers

Layer 4: Data
- Encryption at rest (RDS/KMS, EBS encryption)
- Encryption in transit (TLS everywhere)
- Secrets never in environment variables
- Audit logging for all state changes

Layer 5: Monitoring
- Prometheus alerting on security events
- Audit log review
- Vulnerability scanning (Trivy)
- Container image scanning
```

### 21.2 Security Controls

| Control | Implementation |
|---------|---------------|
| Network isolation | Private subnets, no public IPs for backend |
| TLS termination | Ingress (ALB) with cert-manager |
| mTLS | Istio (optional, production only) |
| Secrets encryption | Vault with auto-rotation |
| Data encryption at rest | RDS KMS, EBS encryption |
| Container security | Non-root user, read-only root FS |
| Image scanning | Trivy in CI, fail on HIGH+ |
| Audit logging | All API mutations logged |
| Rate limiting | Redis token bucket, 100 req/min/user |

---

## 22. Production Deployment Workflow

### 22.1 Pre-Deployment Checklist

- [ ] CI pipeline passing (lint, test, build, vuln scan)
- [ ] Staging deployment healthy for 24+ hours
- [ ] Load test results within acceptable range
- [ ] Database migration reviewed and tested
- [ ] Rollback plan documented
- [ ] Change request approved

### 22.2 Deployment Steps

```
1. Engineer merges PR to main branch
2. CI pipeline builds and pushes images with Git SHA tag
3. ArgoCD detects new image in registry
4. Phase 1: Deploy to staging (auto-sync)
5. Smoke tests pass in staging
6. Engineer triggers production deploy via GitHub button
7. Phase 2: 10% traffic to new version (15 min observation)
8. Phase 3: 50% traffic to new version (30 min observation)
9. Phase 4: 100% traffic (full rollout)
10. Post-deploy smoke tests run
11. Slack notification sent: "Deploy v1.2.3 complete"
12. Monitor dashboards for 30 minutes post-deploy
```

### 22.3 Database Migration Strategy

- Forward-only migrations (no destructive changes in same release)
- Migrations run as Kubernetes Job before app deployment
- Migration Job uses advisory lock to prevent concurrent runs
- Zero-downtime migration pattern:
  1. Add new columns/tables (non-nullable with default)
  2. Deploy application that uses new schema
  3. Backfill data in background job
  4. Remove old columns in next release

---

## 23. Network Architecture

### 23.1 VPC Architecture

```
Internet -> CloudFront / WAF -> ALB (Public subnet)
                                         |
                    +--------------------+
                    |
                    v
          +-----------------------------+
          |     VPC (10.0.0.0/16)       |
          |                             |
          |  Public subnets: ALB only   |
          |  Private subnets:           |
          |    - EKS control plane      |
          |    - Application pods       |
          |    - Redis                  |
          |    - PostgreSQL             |
          |    - Ollama (GPU)           |
          |  Database subnets: RDS      |
          |  NAT Gateway: LLM API egress|
          +-----------------------------+
```

### 23.2 Security Groups

| Security Group | Inbound | Outbound |
|---------------|---------|----------|
| ALB | 443 (HTTPS from internet) | 80, 443 to EKS |
| EKS API | 443 from ALB | All to private |
| EKS Worker | All from EKS API | 443 to internet (NAT) |
| Redis | 6379 from EKS worker | None |
| PostgreSQL | 5432 from EKS worker | None |
| Ollama | 11434 from EKS worker | 443 to internet |
| Vault | 8200 from EKS control | 2379 etcd peers |

---

## 24. Disaster Recovery Plan

### 24.1 DR Architecture

```
Primary Region (us-east-1)         DR Region (us-west-2)
  EKS Cluster                       EKS Cluster (standby)
  RDS Aurora (Multi-AZ)    ----->   RDS Aurora (cross-region repl)
  ElastiCache Redis                 ElastiCache Redis
  Vault Cluster                     Vault Cluster
  ECR Repository           ----->   ECR Replication
  S3 Backups               ----->   S3 Cross-region repl
```

### 24.2 DR Tiers

| Tier | RTO | RPO | Description |
|------|-----|-----|-------------|
| Tier 1 | < 5 min | < 1 min | Whole-cluster failover (auto) |
| Tier 2 | < 30 min | < 5 min | AZ failure within region |
| Tier 3 | < 2 hours | < 1 hour | Cross-region failover (manual) |
| Tier 4 | < 8 hours | < 24 hours | Full data center loss |

### 24.3 DR Runbook

Tier 3: Cross-region failover procedure:
1. ASSESS: Confirm primary region is unreachable
2. NOTIFY: Declare incident in PagerDuty, notify Slack
3. PROMOTE: Promote DR RDS to primary
4. REPLICATE: Point DR Redis to promote read replica
5. DEPLOY: ArgoCD sync DR overlay (points to DR RDS/Redis)
6. DNS: Update Route53 to point to DR ALB
7. VERIFY: Run smoke tests on DR environment
8. MONITOR: Watch dashboards for 1 hour
9. COMMUNICATE: Status page update, stakeholder notification

Recovery after primary region restored:
1. REPLICATE: Reverse replication direction
2. SYNC: Copy recent data from DR to primary
3. VERIFY: Data integrity checks
4. FAILBACK: Switch DNS back to primary
5. CLEANUP: Restore DR to standby state

### 24.4 DR Testing Schedule

| Test Type | Frequency | Scope |
|-----------|-----------|-------|
| Backup restore test | Monthly | Restore from backup to test environment |
| Component failover | Quarterly | Test each component failover individually |
| Cross-region failover | Bi-annual | Full DR exercise with load test |
| Chaos engineering | Quarterly | Inject failures in staging (network, pod, node) |

---

> **End of Infrastructure & Platform Architecture Specification.**
>
> **Next Steps:**
> 1. Implement Terraform modules for cluster provisioning
> 2. Create Dockerfiles for all components
> 3. Generate Kustomize overlays for each environment
> 4. Configure ArgoCD application and CI/CD pipeline
> 5. Provision monitoring stack (Prometheus, Loki, Tempo, Grafana)
> 6. Configure Vault with secrets and policies
> 7. Implement backup CronJobs and test restore
> 8. Run first DR exercise in staging