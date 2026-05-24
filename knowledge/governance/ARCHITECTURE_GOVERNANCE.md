# CrewAI Enterprise Control Center — Architecture Governance & Implementation Control Strategy

> **Document Type**: Principal Governance Specification  
> **Status**: Active Enforcement Baseline  
> **Version**: 1.0  
> **Enforcement Authority**: Architecture Governance Board  
> **Source Documents**:  
> - [`ARCHITECTURAL_ANALYSIS.md`](ARCHITECTURAL_ANALYSIS.md)  
> - [`FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md)  
> - [`BACKEND_RUNTIME_ARCHITECTURE.md`](BACKEND_RUNTIME_ARCHITECTURE.md)  
> - [`ORCHESTRATION_ARCHITECTURE.md`](ORCHESTRATION_ARCHITECTURE.md)  
> - [`INFRASTRUCTURE_ARCHITECTURE.md`](INFRASTRUCTURE_ARCHITECTURE.md)  

---

## Table of Contents

1. [Governance Philosophy & Principles](#1-governance-philosophy--principles)
2. [Implementation Governance Model](#2-implementation-governance-model)
3. [Architecture Enforcement Strategy](#3-architecture-enforcement-strategy)
4. [Code Review Standards](#4-code-review-standards)
5. [Module Boundary Enforcement](#5-module-boundary-enforcement)
6. [Event Schema Governance](#6-event-schema-governance)
7. [Frontend Governance Rules](#7-frontend-governance-rules)
8. [Backend Governance Rules](#8-backend-governance-rules)
9. [Orchestration Governance Rules](#9-orchestration-governance-rules)
10. [Infrastructure Governance Rules](#10-infrastructure-governance-rules)
11. [Testing Governance](#11-testing-governance)
12. [Replayability Validation Strategy](#12-replayability-validation-strategy)
13. [Observability Validation Strategy](#13-observability-validation-strategy)
14. [Scalability Validation Strategy](#14-scalability-validation-strategy)
15. [Security Validation Strategy](#15-security-validation-strategy)
16. [CI Architecture Enforcement](#16-ci-architecture-enforcement)
17. [Linting & Type Enforcement](#17-linting--type-enforcement)
18. [ADR Workflow](#18-adr-workflow)
19. [Migration Governance](#19-migration-governance)
20. [Versioning Governance](#20-versioning-governance)
21. [Implementation Phase Control Rules](#21-implementation-phase-control-rules)
22. [AI Implementation Behavior Control](#22-ai-implementation-behavior-control)
23. [Governance Violation Escalation](#23-governance-violation-escalation)

---

## 1. Governance Philosophy & Principles

### 1.1 Core Tenets

This governance model exists to **preserve architecture integrity across the system lifetime**. It is not bureaucratic overhead — it is the mechanism that prevents architectural drift, technical debt accumulation, and scalability collapse.

| Principle | Meaning | Enforcement |
|-----------|---------|-------------|
| **Architecture Before Code** | No implementation begins without validated architecture alignment | Phase gates in CI |
| **Deterministic Execution** | Every system operation must be deterministic and replayable | State machine validation |
| **Observability by Default** | No component is invisible; all runtime behavior emits typed events | Event schema enforcement |
| **Strict Boundary Isolation** | Module boundaries are physical, not conceptual | Import/export lint rules |
| **Fail Closed** | Governance violations block CI, not just warn | Hard gates in pipeline |
| **Long-Term Over Short-Term** | No shortcut is acceptable even if it accelerates delivery | Architecture board veto |

### 1.2 Governance Hierarchy

```
┌──────────────────────────────────────────────────────────────────┐
│                    GOVERNANCE AUTHORITY                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Architecture Governance Board (AGB)                             │
│     - Final authority on all architecture decisions                 │
│     - Approves/rejects ADRs                                         │
│     - Resolves escalated violations                                 │
│                                                                     │
│  2. Automated Enforcement (CI/CD)                                   │
│     - Hard gates: build, lint, type-check, test, boundary-check     │
│     - Soft gates: performance regression, bundle size, complexity   │
│     - Advisory gates: architecture drift detection                  │
│                                                                     │
│  3. Code Review Enforcement                                         │
│     - Every PR requires architecture alignment verification         │
│     - Module boundary compliance check                              │
│     - Event schema compatibility check                              │
│                                                                     │
│  4. Implementation Phase Control                                    │
│     - Phase gates prevent skipping architectural foundations        │
│     - Each phase has explicit entry/exit criteria                   │
│                                                                     │
└──────────────────────────────────────────────────────────────────┘
```

### 1.3 Governance Scope

| Layer | Governance Authority | Enforcement Mechanism |
|-------|---------------------|----------------------|
| Module boundaries | Automated + Review | `eslint-plugin-import`, Python import linters |
| Event schemas | Automated | Zod/Pydantic schema validation in CI |
| State machines | Automated + Review | State transition validator tests |
| API contracts | Automated | OpenAPI schema diff in CI |
| Frontend components | Review + Automated | Bundle size, render count, selector purity |
| Backend services | Review + Automated | Service dependency graph validation |
| Runtime execution | Review + Automated | Checkpoint coverage, replay tests |
| Infrastructure | Review + Automated | Terraform plan validation, k8s conftest |
| Orchestration | Review + Automated | Graph validation, token budget checks |

---

## 2. Implementation Governance Model

### 2.1 Three-Tier Implementation Approval

Every implementation must pass through three governance tiers before merging:

```
TIER 1: AUTOMATED GATES (CI Pipeline)
┌──────────────────────────────────────────────────────────┐
│  Fail-Close Checks:                                       │
│  - TypeScript/Python type checking                        │
│  - ESLint/Ruff linting with governance rules              │
│  - Module boundary enforcement (import rules)             │
│  - Event schema validation                                │
│  - State machine transition validation                    │
│  - Bundle size budget                                     │
│  - Test coverage thresholds                                │
│  - Dependency cycle detection                             │
│                                                           │
│  Warning Checks:                                           │
│  - Performance regression (benchmark diff)                │
│  - Architecture drift detection (module map diff)         │
│  - API schema incompatibility                             │
│  - Duplicate code detection                               │
└──────────────────────────────────────────────────────────┘
                           │
                     All Pass?
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                  YES            NO
                   │              │
                   │        ┌─────┴─────┐
                   │        │  BLOCKED   │
                   │        │ Fix & re-  │
                   │        │ submit     │
                   │        └───────────┘
                   ▼
TIER 2: ARCHITECTURE REVIEW
┌──────────────────────────────────────────────────────────┐
│  Every PR must have:                                      │
│  - Architecture alignment statement                       │
│  - Module boundary compliance declaration                 │
│  - Event schema compatibility declaration                 │
│  - Replayability impact assessment                        │
│  - Observability impact assessment                        │
│                                                           │
│  Reviewers check:                                         │
│  - No architecture layer violations                       │
│  - No tight coupling introduced                           │
│  - No hidden state or side effects                        │
│  - No business logic in UI components                    │
│  - No duplicated logic                                    │
│  - No 'any' types or untyped boundaries                   │
└──────────────────────────────────────────────────────────┘
                           │
                     Approved?
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                  YES            NO
                   │              │
                   │        ┌─────┴─────┐
                   │        │  REJECTED  │
                   │        │ With       │
                   │        │ rationale  │
                   │        └───────────┘
                   ▼
TIER 3: IMPLEMENTATION PHASE GATE
┌──────────────────────────────────────────────────────────┐
│  Validates implementation follows phase roadmap:          │
│  - Phase 0 complete before Phase 1 begins                │
│  - No skipping foundational phases                        │
│  - Cross-phase dependencies respected                    │
│  - Phase exit criteria met before next phase entry        │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Implementation Prohibitions

The following implementations are **strictly prohibited** without explicit AGB exception:

| Prohibition | Rationale | Violation Consequence |
|-------------|-----------|----------------------|
| Direct `apps/web` import from `apps/api` or `apps/worker` | Layer violation; breaks frontend/backend separation | Immediate CI block |
| Business logic in React components | Must be in hooks/services | Review rejection |
| Global state outside Zustand slices | Must be in domain-separated Zustand slices | Review rejection |
| Untyped event emissions | Every event must conform to `RuntimeEvent` envelope | CI block |
| Direct CrewAI calls outside `packages/crew-runtime` | Must go through `CrewRuntime` abstraction | CI block |
| Raw SQLAlchemy queries in service code | Must use repository pattern | Review rejection |
| Missing checkpoint in execution path | Every execution boundary must be checkpointable | Review rejection |
| SSE connections without `SSEClientManager` | Must use centralized SSE management | Review rejection |
| YAML parsing without Zod validation | Must validate before store update | CI block |
| Synchronous event handlers in async context | Must be async with proper error handling | Review rejection |

### 2.3 Implementation Approval Matrix

| Change Type | Automated Gate | Architecture Review | Phase Gate | Authority |
|-------------|---------------|-------------------|------------|-----------|
| Bug fix (no architecture impact) | Required | Not required | Not required | Reviewer |
| New component (existing pattern) | Required | Required | Not required | Reviewer |
| New service/endpoint | Required | Required | Required | AGB |
| New module/package | Required | Required | Required | AGB |
| Architecture change | Required | Required | Required | AGB + All stakeholders |
| Infrastructure change | Required | Required | Required | AGB + DevOps |
| Event schema change | Required | Required | Required | AGB |
| Dependency addition | Required | Required | Not required | Reviewer |

---

## 3. Architecture Enforcement Strategy

### 3.1 Automated Architecture Drift Detection

Architecture drift is detected automatically using **module boundary maps** and **dependency graphs** that are compared against the canonical architecture specification.

```
┌──────────────────────────────────────────────────────────────────┐
│                 ARCHITECTURE DRIFT DETECTION                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Source of Truth: Architecture docs in /docs/                       │
│                                                                     │
│  Detection Mechanism:                                               │
│  1. Extract dependency graph from codebase (import statements)      │
│  2. Compare against canonical module map from architecture docs     │
│  3. Report any deviations:                                          │
│     - Unexplained dependencies (not in canonical map)              │
│     - Missing dependencies (required by canonical but absent)       │
│     - Circular dependencies                                        │
│     - Layer violations (UI importing backend logic, etc.)          │
│  4. Block CI on hard violations, warn on soft violations            │
│                                                                     │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Canonical Dependency Map

The canonical dependency map is defined in [`ARCHITECTURAL_ANALYSIS.md`](ARCHITECTURAL_ANALYSIS.md#33-dependency-rules) and enforced by the CI pipeline:

```
apps/web       → packages/shared-types, packages/ui
apps/api       → packages/shared-types, packages/crew-runtime
apps/worker    → packages/shared-types, packages/crew-runtime
packages/crew-runtime → packages/shared-types
packages/ui    → packages/shared-types
```

**Enforcement script**: [`scripts/enforce-dependencies.sh`](scripts/enforce-dependencies.sh) (run in CI)

```bash
# Pseudocode for dependency enforcement
check_import("apps/web/src/**/*", "apps/api", FORBIDDEN)
check_import("apps/web/src/**/*", "apps/worker", FORBIDDEN)
check_import("apps/api/src/**/*", "apps/web", FORBIDDEN)
check_import("packages/crew-runtime/src/**/*", "apps/*", FORBIDDEN)
check_import("packages/ui/src/**/*", "apps/*", FORBIDDEN)
check_import("packages/ui/src/**/*", "packages/crew-runtime", FORBIDDEN)
```

### 3.3 Layer Violation Classification

| Violation Class | Severity | Example | Action |
|----------------|----------|---------|--------|
| **L1: Direct Layer Break** | CRITICAL | Web importing API models | Immediate CI block, AGB notification |
| **L2: Indirect Layer Break** | HIGH | Service using raw SQL instead of repository | CI block, requires refactor |
| **L3: Boundary Leak** | MEDIUM | UI component importing from another component domain | CI warning, review required |
| **L4: Contract Drift** | MEDIUM | Event schema change without version bump | CI warning, ADR required |
| **L5: Pattern Violation** | LOW | Missing memo on pure component | CI advisory, review suggestion |

### 3.4 Architecture Review Checklist

Every PR requiring architecture review must address:

```
□ Module boundary compliance — no imports cross forbidden boundaries
□ Dependency direction — dependencies flow in the correct direction
□ Layer isolation — business logic is in the correct layer
□ No god objects — components/services are appropriately sized
□ No hidden coupling — no implicit dependencies between modules
□ Event contract compatibility — event schemas are backward compatible
□ State machine validity — state transitions are legal
□ Checkpoint coverage — execution paths are checkpointable
□ Replay safety — changes don't break replayability
□ Observability — new code emits appropriate events/metrics
```

---

## 4. Code Review Standards

### 4.1 Mandatory Review Requirements

Every PR must satisfy the following before review begins:

```
PR REQUIREMENTS:
┌──────────────────────────────────────────────────────────────┐
│  Title: [TYPE] Brief description                              │
│  Types: FEAT | FIX | REFACTOR | TEST | DOCS | INFRA | GOV    │
│                                                               │
│  Body MUST include:                                            │
│  - Architecture alignment: [reference to architecture doc]     │
│  - Module boundary: [which modules affected]                   │
│  - Event impact: [new/modified events] or NONE                │
│  - Replay impact: [how replayability is affected] or NONE     │
│  - Observability: [what observability is added] or NONE       │
│  - Testing: [what tests are included]                          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Review Depth by Change Type

| Change Type | Review Depth | Required Reviewers | Max Review Time |
|-------------|-------------|-------------------|----------------|
| Bug fix (trivial) | Surface | 1 | 24h |
| Bug fix (complex) | Detailed | 1 | 48h |
| Feature (new component) | Detailed | 1 architecture + 1 domain | 72h |
| Feature (new service) | Deep | 1 architecture + 2 domain | 96h |
| Architecture change | Full audit | AGB + all stakeholders | 1 week |
| Infrastructure change | Detailed | 1 architecture + 1 DevOps | 72h |
| Dependency change | Surface | 1 | 24h |

### 4.3 Rejection Criteria

A PR **must be rejected** if any of the following are detected:

```
CRITICAL REJECTIONS (Block Merge):
┌──────────────────────────────────────────────────────────────┐
│  □ Any 'any' type usage without explicit AGB exception       │
│  □ Business logic inside React component                      │
│  □ Direct API call from component (not through service layer) │
│  □ New global state outside Zustand slices                    │
│  □ Missing error handling in async operation                  │
│  □ Circular dependency introduced                             │
│  □ Synchronous blocking call in async context                 │
│  □ Event emission without typed envelope                      │
│  □ Missing checkpoint in execution path                       │
│  □ Direct CrewAI usage outside crew-runtime package           │
│  □ Hardcoded credentials or secrets                            │
│  □ Test coverage below threshold for new code                  │
└──────────────────────────────────────────────────────────────┘

MAJOR REJECTIONS (Require Changes):
┌──────────────────────────────────────────────────────────────┐
│  □ Component > 300 lines (function component + hooks)        │
│  □ Service > 500 lines                                       │
│  □ Hook > 100 lines                                          │
│  □ Missing error boundaries                                   │
│  □ Insufficient test coverage                                 │
│  □ Missing JSDoc/docstrings for public APIs                   │
│  □ Inefficient re-renders (missing memoization)               │
│  □ Tight coupling between modules                             │
│  □ Missing event documentation                                │
└──────────────────────────────────────────────────────────────┘

NOTE REJECTIONS (Advisory):
┌──────────────────────────────────────────────────────────────┐
│  □ Duplicate logic that could be shared                       │
│  □ Overly complex conditional logic                           │
│  □ Missing performance optimization (lazy loading, etc.)     │
│  □ Missing accessibility attributes                           │
│  □ Naming convention violations                               │
└──────────────────────────────────────────────────────────────┘
```

### 4.4 Review Process Flow

```
PR Created
   │
   ▼
Automated Checks (CI) ─── FAIL ──→ Return for fixes
   │ PASS
   ▼
PR Template Complete? ─── NO ──→ Request template completion
   │ YES
   ▼
Assign Reviewers (based on change type)
   │
   ▼
Architecture Review ─── REJECT ──→ Record ADR, return with rationale
   │ PASS
   ▼
Code Review
   │
   ├── CRITICAL issues? ── YES ──→ Block + Escalate to AGB
   │
   ├── MAJOR issues? ── YES ──→ Request changes, re-review
   │
   └── MINOR issues? ── YES ──→ Note, approve with follow-up
   │
   ▼
Approved → Merge (squash with conventional commit)
```

---

## 5. Module Boundary Enforcement

### 5.1 Physical Boundary Rules

Module boundaries are enforced at **three levels**:

```
LEVEL 1: PACKAGE BOUNDARIES (TurboRepo)
┌──────────────────────────────────────────────────────────────┐
│  Enforced by: package.json dependencies + turbo.json pipeline │
│                                                               │
│  Rules:                                                       │
│  - apps/web can only depend on: packages/shared-types, ui    │
│  - apps/api can only depend on: packages/shared-types,       │
│    packages/crew-runtime                                      │
│  - apps/worker can only depend on: packages/shared-types,    │
│    packages/crew-runtime                                      │
│  - packages/crew-runtime can only depend on:                 │
│    packages/shared-types                                      │
│  - packages/ui can only depend on: packages/shared-types     │
│                                                               │
│  Violation: CI pipeline fails with import error               │
└──────────────────────────────────────────────────────────────┘

LEVEL 2: INTERNAL MODULE BOUNDARIES (within each app/package)
┌──────────────────────────────────────────────────────────────┐
│  Enforced by: ESLint import rules + custom lint rules         │
│                                                               │
│  Frontend rules (apps/web):                                   │
│  - services/ → NOT allowed to import from store/              │
│  - store/ → NOT allowed to import from lib/                    │
│  - lib/ → NOT allowed to import from store/                    │
│  - components/ → NOT allowed to import other component domains│
│    directly (must go through hooks)                           │
│  - app/ → allowed to import from all layers                   │
│                                                               │
│  Backend rules (apps/api, apps/worker):                       │
│  - routes/ → imports services/ only                           │
│  - services/ → imports db/repositories/, events/              │
│  - db/repositories/ → imports db/models/ only                 │
│  - db/models/ → NO imports from other layers                  │
│  - events/ → NO imports from routes/ or services/             │
│                                                               │
│  Violation: ESLint error, CI block                            │
└──────────────────────────────────────────────────────────────┘

LEVEL 3: FUNCTIONAL BOUNDARIES (within modules)
┌──────────────────────────────────────────────────────────────┐
│  Enforced by: Code review + architecture review               │
│                                                               │
│  Rules:                                                       │
│  - No god components (>300 lines)                             │
│  - No god services (>500 lines)                               │
│  - Single responsibility per file                              │
│  - Maximum 3 levels of nesting in callbacks                   │
│  - No shared mutable state across module boundaries           │
│  - Cross-module communication via events only                 │
│                                                               │
│  Violation: Review rejection                                  │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Dependency Validation Rules

```
FRONTEND INTERNAL:
  app/ → components/ ✓
  app/ → hooks/ ✓
  app/ → store/ ✓
  app/ → services/ ✓
  app/ → lib/ ✓
  components/ → hooks/ ✓ (preferred)
  components/ → store/ ✓ (selectors only)
  components/ → services/ ✗ (must go through hooks)
  components/ → lib/ ✓ (sync engine, stream)
  hooks/ → store/ ✓
  hooks/ → services/ ✓
  hooks/ → lib/ ✓
  store/ → services/ ✓ (async actions only)
  store/ → lib/ ✗ (sync engine injects, not imports)
  services/ → store/ ✗ (keep API layer pure)
  lib/ → store/ ✗ (never imports store directly)
  
BACKEND INTERNAL (apps/api):
  routes/ → services/ ✓
  routes/ → middleware/ ✓
  routes/ → db/ ✗ (must go through services)
  services/ → db/repositories/ ✓
  services/ → events/ ✓
  services/ → routes/ ✗ (circular)
  db/repositories/ → db/models/ ✓
  db/models/ → any service/ ✗
  events/ → any service/ ✗

WORKER INTERNAL (apps/worker):
  tasks/ → orchestrator/ ✓
  orchestrator/ → runtime/ ✓
  orchestrator/ → checkpoint/ ✓
  orchestrator/ → events/ ✓
  runtime/ → checkpoint/ ✓
  runtime/ → events/ ✓
```

### 5.3 ESLint Import Rule Configuration

```json
// .eslintrc.js (root)
{
  "rules": {
    "import/no-restricted-paths": ["error", {
      "zones": [
        // Frontend forbidden imports
        {
          "target": "apps/web/src/**/*",
          "from": "apps/api/**/*",
          "message": "Frontend must not import from API layer"
        },
        {
          "target": "apps/web/src/**/*",
          "from": "apps/worker/**/*",
          "message": "Frontend must not import from Worker layer"
        },
        {
          "target": "apps/web/src/services/**/*",
          "from": "apps/web/src/store/**/*",
          "message": "Services must not import from Store"
        },
        {
          "target": "apps/web/src/lib/**/*",
          "from": "apps/web/src/store/**/*",
          "message": "Lib must not import from Store directly"
        },
        {
          "target": "apps/web/src/store/**/*",
          "from": "apps/web/src/lib/**/*",
          "message": "Store must not import from Lib directly"
        },
        {
          "target": "apps/web/src/components/**/*",
          "from": "apps/web/src/services/**/*",
          "message": "Components must not import Services directly; use hooks"
        },
        // Backend forbidden imports
        {
          "target": "apps/api/src/**/*",
          "from": "apps/web/**/*",
          "message": "API must not import from Frontend"
        },
        {
          "target": "apps/api/src/db/models/**/*",
          "from": "apps/api/src/services/**/*",
          "message": "Models must not import from Services"
        },
        {
          "target": "apps/api/src/events/**/*",
          "from": "apps/api/src/services/**/*",
          "message": "Events must not import from Services"
        },
        // Runtime forbidden imports
        {
          "target": "packages/crew-runtime/src/**/*",
          "from": "apps/**/*",
          "message": "CrewRuntime must not depend on any app module"
        },
        {
          "target": "packages/crew-runtime/src/**/*",
          "from": "packages/ui/**/*",
          "message": "CrewRuntime must not depend on UI"
        }
      ]
    }]
  }
}
```

### 5.4 Python Import Enforcement

```ini
# setup.cfg (ruff configuration)
[tool.ruff.flake8-tidy-imports]
ban-relative-imports = "all"

[tool.ruff.per-file-ignores]
# API models should not import services
"apps/api/src/db/models/*.py" = ["TID251"]
# Events should not import services
"apps/api/src/events/*.py" = ["TID251"]
# Worker tasks should only import orchestrator
"apps/worker/src/tasks/*.py" = ["TID252"]
```

---

## 6. Event Schema Governance

### 6.1 Event Schema Contract

Every event in the system **must** conform to the canonical [`RuntimeEvent`](packages/shared-types/src/events/base.py:1882) envelope defined in [`packages/shared-types/src/events/`](packages/shared-types/src/events/):

```typescript
// IMMUTABLE CONTRACT — Do not modify without ADR
interface RuntimeEvent<T = unknown> {
  id: string;              // uuid
  type: EventType;         // must be in EventType enum
  timestamp: string;       // ISO 8601
  execution_id: string;
  correlation_id: string;  // must propagate from origin
  source: EventSource;     // 'runtime' | 'worker' | 'api' | 'system'
  step: number;            // monotonic step counter
  sequence: number;        // global event sequence
  data: T;                 // typed per event type
  version: number;         // schema version (forward compatibility)
}
```

### 6.2 Event Type Registration

All event types **must** be registered in the canonical [`EventType`](packages/shared-types/src/events/base.py:1843) enum. No ad-hoc event types.

```typescript
// packages/shared-types/src/events/base.py
// Only location where EventType is defined

class EventType(str, Enum):
    # Workflow lifecycle
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_CHECKPOINT = "WORKFLOW_CHECKPOINT"
    WORKFLOW_PAUSED = "WORKFLOW_PAUSED"
    WORKFLOW_RESUMED = "WORKFLOW_RESUMED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"

    # Agent execution
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_THOUGHT = "AGENT_THOUGHT"
    AGENT_ACTION = "AGENT_ACTION"
    AGENT_OBSERVATION = "AGENT_OBSERVATION"
    TOOL_CALLING = "TOOL_CALLING"
    TOOL_RESULT = "TOOL_RESULT"
    TOOL_ERROR = "TOOL_ERROR"
    AGENT_COMPLETED = "AGENT_COMPLETED"

    # HITL
    HITL_REQUIRED = "HITL_REQUIRED"
    HITL_APPROVED = "HITL_APPROVED"
    HITL_REJECTED = "HITL_REJECTED"
    HITL_REGENERATED = "HITL_REGENERATED"

    # Progress and metrics
    TASK_PROGRESS = "TASK_PROGRESS"
    METRICS_UPDATE = "METRICS_UPDATE"
    ERROR_OCCURRED = "ERROR_OCCURRED"
```

**Rules**:
- New event types require ADR approval
- Event type names must be `UPPER_SNAKE_CASE`
- Event types must be grouped by domain (comments in enum)
- Event types must not be removed — only deprecated (for replay compatibility)

### 6.3 Event Data Schemas

Each event type has a **typed data schema** defined in [`packages/shared-types/src/events/data.py`](packages/shared-types/src/events/data.py):

| Event Type | Data Schema | Required Fields |
|------------|------------|-----------------|
| `AGENT_STARTED` | [`AgentStartedData`](packages/shared-types/src/events/data.py:1909) | `agent_id`, `agent_role`, `task_id` |
| `AGENT_THOUGHT` | [`AgentThoughtData`](packages/shared-types/src/events/data.py:1915) | `agent_id`, `thought` |
| `TOOL_CALLING` | [`ToolCallData`](packages/shared-types/src/events/data.py:1921) | `agent_id`, `tool_name`, `tool_input` |
| `TOOL_RESULT` | [`ToolResultData`](packages/shared-types/src/events/data.py:1927) | `agent_id`, `tool_name`, `tool_output`, `duration_ms` |
| `AGENT_COMPLETED` | [`AgentCompletedData`](packages/shared-types/src/events/data.py:1933) | `agent_id`, `output`, `tokens` |
| `HITL_REQUIRED` | [`HITLRequiredData`](packages/shared-types/src/events/data.py:1938) | `task_id`, `agent_id`, `draft_output` |
| `HITL_DECISION` | [`HITLDecisionData`](packages/shared-types/src/events/data.py:1946) | `approval_id`, `decision` |
| `ERROR_OCCURRED` | [`ErrorData`](packages/shared-types/src/events/data.py:1952) | `error_type`, `error_message` |

**Rules**:
- Data schemas are Pydantic/Zod models with strict typing
- All string fields have explicit max lengths for SSE safety
- Optional fields use `None` union, never `undefined`
- New fields must be optional (backward compatible)
- Field removal requires schema version bump + ADR

### 6.4 Event Schema Validation in CI

```yaml
# .github/workflows/event-schema-check.yml
name: Event Schema Validation
on: [pull_request]

jobs:
  validate-events:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check EventType enum completeness
        run: scripts/check-event-types.sh
        # Verifies all event types in codebase are in canonical enum
        
      - name: Check event data schemas
        run: scripts/check-event-schemas.sh
        # Verifies all data schemas are Pydantic/Zod models
        
      - name: Check backward compatibility
        run: scripts/check-event-compatibility.sh
        # Compares event schemas against previous version
        # Detects breaking changes (field removal, type change)
        
      - name: Check SSE format compliance
        run: scripts/check-sse-format.sh
        # Verifies all events can be serialized to SSE format
```

### 6.5 Event Versioning Strategy

```
Schema Version 1 → Version 2 (additive change only)
  - Can add new optional fields
  - Can add new event types
  - Cannot remove fields
  - Cannot change field types
  - Cannot remove event types

Schema Version 2 → Version 3 (breaking change)
  - Requires ADR approval
  - Requires migration of all consumers
  - Old events remain readable (replay compatibility)
  - New events use new schema version
```

### 6.6 Correlation ID Propagation

Every event **must** carry a `correlation_id` that traces across all service boundaries:

```
Frontend                          API                         Worker
   │                               │                           │
   │── (correlation_id: "abc") ──► │                           │
   │                               │── (correlation_id: "abc")─►│
   │                               │                           │
   │◄── (correlation_id: "abc") ──│◄── (correlation_id: "abc")─│
```

**Enforcement**:
- `RequestIDMiddleware` generates correlation ID if not present
- All events emitted during a request scope must use the same correlation ID
- Correlation ID must be included in logs for traceability
- Missing correlation ID = CI validation failure

---

## 7. Frontend Governance Rules

### 7.1 Component Architecture Rules

```
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND ARCHITECTURE RULES — Violations block merge         │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: NO business logic in components                             │
│      → Must be extracted to hooks/ or services/                 │
│      → Components are pure rendering + event handlers            │
│                                                                 │
│  R2: NO direct API calls from components                         │
│      → Must go through services/ → hooks/ pattern                │
│      → Exception: SSE stream hooks (useWorkflowStream)          │
│                                                                 │
│  R3: NO direct store access in components without selectors      │
│      → Must use memoized selectors from store/selectors/         │
│      → Use shallow comparison to prevent unnecessary renders    │
│                                                                 │
│  R4: NO cross-domain component imports                           │
│      → canvas/ components cannot import terminal/ components     │
│      → Cross-domain communication via store/events only         │
│                                                                 │
│  R5: NO giant components (>300 lines)                            │
│      → Split into smaller components + hooks                     │
│                                                                 │
│  R6: NO 'any' types in frontend code                             │
│      → All types from packages/shared-types or /types/           │
│                                                                 │
│  R7: NO non-memoized callbacks in render                          │
│      → useCallback for event handlers passed to children         │
│      → useMemo for computed values                                │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 Zustand Store Rules

```
┌──────────────────────────────────────────────────────────────┐
│  ZUSTAND STORE GOVERNANCE                                      │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Domain-separated slices only                                │
│      → canvas-slice, execution-slice, terminal-slice, etc.      │
│      → No god stores                                            │
│                                                                 │
│  R2: No slice imports another slice's internals                  │
│      → Cross-slice communication via getState() or subscribe()  │
│      → Never import another slice's type directly               │
│                                                                 │
│  R3: Store actions must be async for API calls                   │
│      → runWorkflow, pauseWorkflow, etc. call services           │
│      → Internal handlers prefixed with _ (private convention)   │
│                                                                 │
│  R4: Selectors must use shallow comparison                       │
│      → Prevents unnecessary re-renders                           │
│      → Selectors in store/selectors/ directory                  │
│                                                                 │
│  R5: Store is canonical source of truth for UI state             │
│      → YAML sync engine writes TO store                         │
│      → Components read FROM store                                │
│      → No dual state (SyncEngine never has its own state copy)  │
│                                                                 │
│  R6: Terminal store has maxEntries limit (10,000)                │
│      → Prevents memory overflow on long-running workflows        │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 React Flow Governance

```
┌──────────────────────────────────────────────────────────────┐
│  REACT FLOW GOVERNANCE                                         │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Node types registered in nodeTypes map only                │
│      → AgentNode, TaskNode, ToolNode are the only node types    │
│                                                                 │
│  R2: Node data typed via WorkflowNodeData union                 │
│      → AgentNodeData | TaskNodeData | ToolNodeData              │
│                                                                 │
│  R3: Canvas events delegated through useCanvasHandlers hook     │
│      → No inline handlers in WorkflowCanvas component           │
│                                                                 │
│  R4: Status updates via dedicated hooks (useAgentStatus)       │
│      → Each node reads only its own status from store           │
│      → Prevents re-rendering all nodes on single status change │
│                                                                 │
│  R5: NodeWrapper provides consistent styling                    │
│      → All nodes use NodeWrapper for drag handle, selection     │
│      → Status-based border colors are centralized               │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 7.4 YAML Sync Engine Governance

```
┌──────────────────────────────────────────────────────────────┐
│  YAML SYNC GOVERNANCE                                          │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Zustand store is canonical source of truth                 │
│      → All UI changes write to store first                      │
│      → YAML editor reflects store state (not vice versa)        │
│                                                                 │
│  R2: YAML → Store path requires Zod validation                  │
│      → Invalid YAML must not update store                       │
│      → Errors displayed in Monaco (not silently ignored)        │
│                                                                 │
│  R3: Version counter prevents sync loops                        │
│      → onUIChange() increments version                          │
│      → onYAMLChange() checks version before updating store      │
│      → Version mismatch triggers conflict resolution            │
│                                                                 │
│  R4: Debounce period is 300ms (store → YAML direction)          │
│      → Prevents excessive YAML regeneration during drag         │
│      → YAML → Store direction is immediate (after validation)  │
│                                                                 │
│  R5: SyncEngine is injected, not imported                        │
│      → SyncEngine receives store reference via constructor      │
│      → SyncEngine does not import store module                  │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 7.5 SSE Client Governance

```
┌──────────────────────────────────────────────────────────────┐
│  SSE CLIENT GOVERNANCE                                          │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All SSE connections managed by SSEClientManager singleton  │
│      → No direct EventSource creation outside SSEClientManager  │
│                                                                 │
│  R2: Reconnection with exponential backoff (max 5 retries)      │
│      → Backoff: 1s, 2s, 4s, 8s, 16s                            │
│      → After max retries, status = 'disconnected'               │
│                                                                 │
│  R3: Last-Event-Id replay on reconnect                           │
│      → Missed events replayed from Redis Stream                 │
│      → No data loss on temporary disconnection                  │
│                                                                 │
│  R4: One connection per workflow view                            │
│      → Multiple handlers can share one connection                │
│      → Connection closed when last handler unsubscribes          │
│                                                                 │
│  R5: Automatic cleanup on component unmount                      │
│      → useWorkflowStream hook handles connect/disconnect         │
│      → No orphaned connections                                   │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 7.6 Frontend Performance Budgets

| Metric | Budget | Enforcement |
|--------|--------|-------------|
| Initial JS bundle | < 300KB gzipped | Webpack/Next.js bundle analyzer |
| Component render time | < 16ms (60fps) | React DevTools Profiler in CI |
| Zustand selector re-renders | < 5 per user action | Custom ESLint rule |
| Virtual list row height | Fixed at 24px | Code review |
| SSE events per second | < 1000 | SSEClientManager throttling |
| Terminal entries in memory | Max 10,000 | Store enforcement |
| Canvas nodes | < 500 | React Flow virtualization |
| Network requests per page load | < 20 | DevTools audit |

---

## 8. Backend Governance Rules

### 8.1 FastAPI Application Rules

```
┌──────────────────────────────────────────────────────────────┐
│  BACKEND ARCHITECTURE RULES — Violations block merge           │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Application factory pattern required                       │
│      → create_app() function, no global app instance            │
│      → Lifespan-managed startup/shutdown                        │
│                                                                 │
│  R2: Dependency injection via Depends()                         │
│      → No global singletons                                     │
│      → No hidden imports in route handlers                      │
│                                                                 │
│  R3: Middleware stack ordered by dependency                     │
│      → RequestID → Auth → RateLimit → Route                     │
│      → No middleware bypass for authenticated routes            │
│                                                                 │
│  R4: Structured error responses                                 │
│      → AppError base class with code, message, status, details  │
│      → Global exception handler catches all unhandled           │
│      → Correlation ID in every error response                   │
│                                                                 │
│  R5: No raw SQLAlchemy in service code                          │
│      → Repository pattern required                              │
│      → Services call repositories, never Session directly      │
│                                                                 │
│  R6: Services are stateless                                     │
│      → All dependencies via constructor injection               │
│      → No class-level mutable state                             │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 8.2 Service Layer Governance

```
┌──────────────────────────────────────────────────────────────┐
│  SERVICE LAYER GOVERNANCE                                       │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: ServiceRegistry is single point of dependency injection    │
│      → All services registered in ServiceRegistry constructor   │
│      → Services accessed via get_services() dependency          │
│                                                                 │
│  R2: Services NEVER call other services directly                │
│      → Cross-service communication via EventEngine only        │
│      → Prevents tight coupling between domains                  │
│                                                                 │
│  R3: Services NEVER import routes                                │
│      → Unidirectional dependency: routes → services             │
│      → No circular dependencies                                 │
│                                                                 │
│  R4: Repositories NEVER access Redis or events                  │
│      → Repositories are pure data access                        │
│      → Events emitted by services after repository operations   │
│                                                                 │
│  R5: Models NEVER contain business logic                         │
│      → SQLAlchemy models are data containers only               │
│      → Business logic in services layer                         │
│                                                                 │
│  R6: Each service has single responsibility                     │
│      → WorkflowService handles workflows only                    │
│      → ExecutionService handles execution only                   │
│      → No service > 500 lines                                   │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 8.3 Database Layer Governance

```
┌──────────────────────────────────────────────────────────────┐
│  DATABASE LAYER GOVERNANCE                                      │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All schema changes via Alembic migrations                 │
│      → No raw ALTER TABLE in production                         │
│      → Migration must be reversible (downgrade)                 │
│                                                                 │
│  R2: Indexes defined for common query patterns                  │
│      → execution_logs: (workflow_id, timestamp), event_type     │
│      → Composite indexes for JOIN-heavy queries                 │
│                                                                 │
│  R3: Partitioning for large tables                              │
│      → execution_logs partitioned by month                      │
│      → agent_memories partitioned by workflow_id                │
│                                                                 │
│  R4: Optimistic locking for state transitions                   │
│      → UPDATE ... WHERE status = :current                       │
│      → Raises ExecutionStateConflictError on race               │
│                                                                 │
│  R5: No raw SQL in service code                                 │
│      → All queries through repository methods                   │
│      → Raw SQL only in migrations                               │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 8.4 Celery & Worker Governance

```
┌──────────────────────────────────────────────────────────────┐
│  CELERY & WORKER GOVERNANCE                                     │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Queue routing must follow the canonical queue map          │
│      → workflow_high, workflow_default, workflow_low            │
│      → workflow_control (pause/resume/kill)                     │
│      → hitl (HITL decisions)                                    │
│                                                                 │
│  R2: Task acknowledgment is at-least-once                       │
│      → acks_late=True                                           │
│      → reject_on_worker_lost=True                                │
│                                                                 │
│  R3: Worker prefetch is 1                                       │
│      → worker_prefetch_multiplier=1                              │
│      → Prevents one worker from hoarding tasks                  │
│                                                                 │
│  R4: Control queue has highest priority                         │
│      → Dedicated workers for control queue                      │
│      → Pause/kill must be delivered ASAP                        │
│                                                                 │
│  R5: All tasks have timeouts                                    │
│      → soft_time_limit: 3600s                                   │
│      → hard_time_limit: 3900s                                   │
│                                                                 │
│  R6: Result expiry is 24 hours                                  │
│      → result_expires: 86400                                    │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 8.5 Execution Orchestrator Governance

```
┌──────────────────────────────────────────────────────────────┐
│  EXECUTION ORCHESTRATOR GOVERNANCE                               │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Every execution must pass through WorkflowStateMachine     │
│      → StateMachine.transition() validates all transitions      │
│      → Illegal transitions raise ExecutionStateConflictError    │
│                                                                 │
│  R2: State transitions must use optimistic locking              │
│      → Concurrent updates detected via UPDATE ... WHERE         │
│      → Race conditions raise ExecutionStateConflictError        │
│                                                                 │
│  R3: Every execution agent boundary must have a checkpoint      │
│      → Pre-agent checkpoint before each agent starts            │
│      → Post-agent checkpoint after each agent completes         │
│      → Pause checkpoint on user-initiated pause                 │
│      → Failure checkpoint on unrecoverable error                │
│                                                                 │
│  R4: Event published for every state transition                 │
│      → WORKFLOW_STARTED, WORKFLOW_PAUSED, etc.                  │
│      → No silent state transitions                              │
│                                                                 │
│  R5: Execution config_snapshot is immutable                     │
│      → Full workflow config captured at execution time          │
│      → Replay uses original snapshot, not current config        │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 9. Orchestration Governance Rules

### 9.1 Orchestration Engine Governance

```
┌──────────────────────────────────────────────────────────────┐
│  ORCHESTRATION ENGINE GOVERNANCE                                │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Orchestration is modeled as a DAG, not a linear chain      │
│      → Topological sort determines execution order              │
│      → Cycles are rejected at graph validation time             │
│                                                                 │
│  R2: Every orchestration node goes through governance layer     │
│      → GovernanceDecision gate before node execution            │
│      → BLOCK, HITL_REQUIRED, or ALLOWED                        │
│                                                                 │
│  R3: Checkpoints pre/post every orchestration node              │
│      → save_pre_node before execution                           │
│      → save_post_node after execution                           │
│      → Enables replay from any node boundary                    │
│                                                                 │
│  R4: Conditional edges must be deterministic                    │
│      → Conditions must be pure functions                        │
│      → No random/state-dependent conditions                     │
│                                                                 │
│  R5: Retry with exponential backoff on node failure             │
│      → maxRetries per node (configurable)                       │
│      → Backoff: 1s, 2s, 4s, 8s                                 │
│      → After max retries, execution status = FAILED             │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 9.2 Planning Engine Governance

```
┌──────────────────────────────────────────────────────────────┐
│  PLANNING ENGINE GOVERNANCE                                      │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All generated graphs must pass Zod validation              │
│      → Schema validation before any graph is accepted           │
│      → Invalid graphs returned with errors, never executed      │
│                                                                 │
│  R2: Token budget must be enforced at planning time             │
│      → estimated_tokens < tokenBudget                           │
│      → Per-agent token limits respected                         │
│      → Budget exceeded → optimizer must reduce                  │
│                                                                 │
│  R3: Planning constraints always applied                        │
│      → maxAgents, maxSteps, allowedModels, etc.                 │
│      → Constraint violations → INFEASIBLE status                │
│                                                                 │
│  R4: Human review gate for autonomous generation                │
│      → AUTO-generated graphs require human approval             │
│      → Templates and manual graphs can skip review              │
│                                                                 │
│  R5: Dynamic replanning is checkpoint-anchored                  │
│      → Replan from specific checkpoint, not from scratch        │
│      → Original plan is preserved for comparison                │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 9.3 Agent Communication Governance

```
┌──────────────────────────────────────────────────────────────┐
│  AGENT COMMUNICATION GOVERNANCE                                  │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All inter-agent communication through orchestration relay  │
│      → Agents do not communicate directly                       │
│      → Every message logged as typed event                      │
│                                                                 │
│  R2: Message types are strictly defined                          │
│      → TASK_OUTPUT | BROADCAST | MERGE_REQUEST | DELEGATE      │
│      → No ad-hoc message types                                  │
│                                                                 │
│  R3: Every message has correlation_id tracing                   │
│      → Links message to originating execution                   │
│      → Enables full communication traceability                  │
│                                                                 │
│  R4: Messages are checkpointed with execution state              │
│      → Message replay on checkpoint restore                     │
│      → No lost messages on pause/resume                         │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 9.4 Dynamic Agent Generation Governance

```
┌──────────────────────────────────────────────────────────────┐
│  DYNAMIC AGENT GENERATION GOVERNANCE                             │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All generated agent configs must pass Zod validation       │
│      → Role, goal, backstory, LLM config, tools all validated   │
│      → Invalid configs raise AgentGenerationError               │
│                                                                 │
│  R2: Auto-fix attempts must re-validate                         │
│      → If validation fails, try auto-fix once                   │
│      → If auto-fix fails, fail completely                       │
│                                                                 │
│  R3: Generated agents registered in catalog with metadata       │
│      → indexed for semantic search                              │
│      → Tracked for usage and success rate                       │
│                                                                 │
│  R4: Agent catalog has semantic search capability               │
│      → Embedding-based matching for agent selection             │
│      → Search threshold: 0.7                                    │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 9.5 Tool Routing Governance

```
┌──────────────────────────────────────────────────────────────┐
│  TOOL ROUTING GOVERNANCE                                         │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All tool calls go through ToolRouter                       │
│      → No direct tool invocation outside ToolRouter             │
│      → Permission check enforced before every call              │
│                                                                 │
│  R2: Fallback chain defined for every tool                      │
│      → Primary tool fails → fallback chain attempted            │
│      → All fallbacks exhausted → ERROR status                   │
│                                                                 │
│  R3: Token tracking on every tool call                           │
│      → Input/output tokens recorded                             │
│      → Duration tracked for performance analysis                │
│                                                                 │
│  R4: Tool call events emitted per invocation                     │
│      → TOOL_CALLING before execution                            │
│      → TOOL_RESULT or TOOL_ERROR after execution                │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 10. Infrastructure Governance Rules

### 10.1 Docker & Container Governance

```
┌──────────────────────────────────────────────────────────────┐
│  CONTAINER GOVERNANCE — Violations block deployment            │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All containers run as non-root user                        │
│      → USER crewai in Dockerfile                                │
│      → No root processes in production                          │
│                                                                 │
│  R2: Images built with multi-stage builds                       │
│      → Build stage → Runtime stage (minimal)                    │
│      → Runtime stage has no build dependencies                  │
│                                                                 │
│  R3: Immutable image tags (never :latest)                       │
│      → Tag format: {git-sha}-{build-number}                     │
│      → Environment aliases for reference only                   │
│                                                                 │
│  R4: Health checks on every container                           │
│      → liveness + readiness probes                              │
│      → Probe endpoints return 200 only when fully ready         │
│                                                                 │
│  R5: Vulnerability scanning before deploy                       │
│      → Trivy scan in CI pipeline                                │
│      → CRITICAL/HIGH vulnerabilities block deployment           │
│                                                                 │
│  R6: Read-only root filesystem in K8s                           │
│      → securityContext.readOnlyRootFilesystem: true             │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 10.2 Kubernetes Governance

```
┌──────────────────────────────────────────────────────────────┐
│  KUBERNETES GOVERNANCE                                           │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All namespaces isolated by network policies                │
│      → Default deny ingress on crewai-app                       │
│      → Explicit allow rules for required communication          │
│      → Egress restricted to DNS + cluster internal              │
│                                                                 │
│  R2: PodDisruptionBudget for all critical services              │
│      → API: minAvailable: 2                                     │
│      → Worker: minAvailable: 1                                  │
│      → Redis: minAvailable: 1                                   │
│      → PostgreSQL: minAvailable: 1                              │
│                                                                 │
│  R3: HorizontalPodAutoscaler for all stateless services         │
│      → API: CPU 70% + Memory 80%                                │
│      → Worker: celery_queue_depth metric                        │
│      → Scale-up fast (60s window), scale-down slow (300s)       │
│                                                                 │
│  R4: Resource requests/limits for all containers                │
│      → Requests ensure scheduling                               │
│      → Limits prevent resource starvation                       │
│                                                                 │
│  R5: Pod anti-affinity for critical components                  │
│      → Redis pods spread across zones                           │
│      → API pods spread across nodes                             │
│                                                                 │
│  R6: Istio service mesh (production only)                       │
│      → mTLS between all services                                │
│      → Traffic splitting for canary deployments                 │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 10.3 Redis Governance

```
┌──────────────────────────────────────────────────────────────┐
│  REDIS GOVERNANCE                                                │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Redis HA via Sentinel (3 instances)                       │
│      → Automatic failover on primary loss                       │
│      → ~10-15s failover window                                  │
│                                                                 │
│  R2: Database isolation across use cases                        │
│      → DB 0: Celery broker                                      │
│      → DB 1: Celery results (24h TTL)                           │
│      → DB 2: Short-term memory (1h TTL)                         │
│      → DB 3: Event Pub/Sub + Streams (maxlen)                   │
│      → DB 4: Rate limiting (1m TTL)                             │
│      → DB 5: Session store (24h TTL)                            │
│                                                                 │
│  R3: Pub/Sub channels follow namespace convention                │
│      → crew:workflow:{id}:events, crew:control:{id}:commands    │
│      → No ad-hoc channel names                                  │
│                                                                 │
│  R4: Event streams have maxlen=10000                             │
│      → Prevents unbounded memory growth                         │
│      → Sufficient for replay on reconnect                       │
│                                                                 │
│  R5: Dangerous commands disabled                                 │
│      → FLUSHALL, FLUSHDB, CONFIG, SHUTDOWN, DEBUG renamed       │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 10.4 PostgreSQL Governance

```
┌──────────────────────────────────────────────────────────────┐
│  POSTGRESQL GOVERNANCE                                           │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Managed RDS Aurora (production) w/ Multi-AZ                │
│      → Automatic failover 30-60s                                │
│      → Read replicas for query offloading                       │
│                                                                 │
│  R2: PgBouncer connection pooling                               │
│      → Max client connections: 500                              │
│      → Default pool size: 50                                    │
│                                                                 │
│  R3: Automated backups with 30-day retention                    │
│      → Daily snapshot window: 03:00-04:00                       │
│      → Point-in-time recovery enabled                           │
│                                                                 │
│  R4: Storage encrypted at rest                                   │
│      → KMS-managed encryption key                               │
│                                                                 │
│  R5: PGVector index strategy documented                          │
│      → HNSW for high-recall semantic search                     │
│      → GIN for JSONB attribute queries                          │
│                                                                 │
│  R6: Connection limits per service                               │
│      → API: max 50 connections                                   │
│      → Worker: max 100 connections                               │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 10.5 Observability Stack Governance

```
┌──────────────────────────────────────────────────────────────┐
│  OBSERVABILITY STACK GOVERNANCE                                  │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All services emit OpenTelemetry metrics, traces, logs      │
│      → OTLP exporter configured in every service                │
│      → Missing observability = deployment block                 │
│                                                                 │
│  R2: Structured JSON logging required                           │
│      → Fields: timestamp, level, logger, message, service       │
│      → Correlation ID in every log entry                        │
│                                                                 │
│  R3: Prometheus metrics for every service endpoint              │
│      → Request count, latency (p50/p95/p99), error rate         │
│      → Labeled by method, endpoint, status                      │
│                                                                 │
│  R4: Grafana dashboards for all components                      │
│      → API, Worker, Redis, PostgreSQL, Workflows                │
│      → Dashboard JSON in version control                        │
│                                                                 │
│  R5: Alert rules defined for all critical metrics               │
│      → PagerDuty/Slack integration                              │
│      → No production deployment without alert configuration     │
│                                                                 │
│  R6: Log retention by environment                                │
│      → Dev: 7 days                                              │
│      → Staging: 14 days                                         │
│      → Production: 30 days hot, 90 days cold                    │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 10.6 CI/CD Governance

```
┌──────────────────────────────────────────────────────────────┐
│  CI/CD GOVERNANCE                                                │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All changes deployed via CI/CD — no manual deploys         │
│      → GitOps with ArgoCD (production)                          │
│      → Direct deploy only for emergency hotfix (with approval)  │
│                                                                 │
│  R2: Pipeline stages required:                                   │
│      → Lint → TypeCheck → Test → Build → Scan → Deploy         │
│      → Each stage gates the next                                │
│                                                                 │
│  R3: Infrastructure changes via Terraform + review               │
│      → Terraform plan must be reviewed                          │
│      → State file in remote backend with locking                │
│                                                                 │
│  R4: Secrets never in code or CI logs                            │
│      → All secrets from Vault or cloud secret manager           │
│      → Secret scanning in CI (trufflehog/gitleaks)              │
│                                                                 │
│  R5: Deployment requires approval (staging + production)         │
│      → Staging: team lead approval                              │
│      → Production: AGB + DevOps approval                        │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 11. Testing Governance

### 11.1 Test Pyramid & Requirements

```
                     ╱╲
                    ╱  ╲
                   ╱ E2E╲
                  ╱ Tests╲         5% of tests
                 ╱────────╲
                ╱          ╲
               ╱Integration ╲      25% of tests
              ╱    Tests     ╲
             ╱────────────────╲
            ╱                  ╲
           ╱   Unit Tests       ╲   70% of tests
          ╱──────────────────────╲
```

### 11.2 Coverage Requirements

| Layer | Statement Coverage | Branch Coverage | Critical Path Coverage |
|-------|-------------------|----------------|----------------------|
| Frontend (hooks/services) | ≥ 80% | ≥ 70% | 100% |
| Frontend (components) | ≥ 70% | ≥ 60% | 100% |
| API (services) | ≥ 90% | ≥ 80% | 100% |
| API (routes) | ≥ 80% | ≥ 70% | 100% |
| Worker (orchestrator) | ≥ 90% | ≥ 85% | 100% |
| Worker (runtime) | ≥ 90% | ≥ 85% | 100% |
| Shared types | 100% | 100% | 100% |
| CrewRuntime | ≥ 95% | ≥ 90% | 100% |
| State machine | 100% | 100% | 100% |
| Event schemas | 100% | 100% | 100% |

### 11.3 Mandatory Test Types

```
EVERY FEATURE REQUIRES:
┌──────────────────────────────────────────────────────────────┐
│  Unit Tests:                                                    │
│  □ Business logic in isolation                                  │
│  □ Edge cases (empty, null, overflow)                           │
│  □ State machine transitions                                    │
│  □ Event schema serialization/deserialization                   │
│  □ Error paths                                                  │
│                                                               │
│  Integration Tests:                                             │
│  □ API endpoint → service → repository (with test DB)           │
│  □ Event publishing → SSE delivery                              │
│  □ Checkpoint save → load → restore                             │
│  □ YAML parse → validate → store                                │
│  □ WebSocket/SSE reconnection                                    │
│                                                               │
│  E2E Tests (Critical paths only):                               │
│  □ Create workflow → Run → Observe events in terminal           │
│  □ Run workflow → Pause → Resume → Complete                     │
│  □ YAML edit → Canvas update → Save → Reload                    │
│  □ HITL: Run → Await approval → Approve → Continue             │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 11.4 Testing Standards

```
┌──────────────────────────────────────────────────────────────┐
│  TESTING STANDARDS — Violations block merge                    │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Tests must be deterministic                                 │
│      → No random/fuzzy values without seed                      │
│      → No dependency on system time (use mocks)                 │
│      → No dependency on external services (use mocks)           │
│                                                                 │
│  R2: Tests must be isolated                                      │
│      → No shared state between tests                            │
│      → Database tests use transaction rollback                  │
│                                                                 │
│  R3: Tests must cover error paths                                │
│      → Every error condition must be tested                     │
│      → Timeout, network failure, validation failure             │
│                                                                 │
│  R4: State machine tests must cover all transitions              │
│      → Every legal transition tested                            │
│      → Every illegal transition tested (expects error)          │
│                                                                 │
│  R5: Event schema tests must verify:                             │
│      → Serialization → deserialization roundtrip                │
│      → Schema version compatibility                             │
│      → Invalid data rejection                                   │
│                                                                 │
│  R6: Replay tests must verify:                                   │
│      → Checkpoint save → load → replay produces same events     │
│      → Event log replay produces identical output               │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 11.5 Test Tooling

| Layer | Unit Tests | Integration Tests | E2E Tests |
|-------|-----------|------------------|-----------|
| Frontend | Vitest + React Testing Library | Vitest + MSW | Playwright |
| API | Pytest | Pytest + test DB | Pytest + httpx |
| Worker | Pytest | Pytest + Celery test worker | Pytest + full stack |
| Shared types | Vitest (TS) / Pytest (Python) | — | — |
| CrewRuntime | Pytest | Pytest + mocked CrewAI | — |

---

## 12. Replayability Validation Strategy

### 12.1 Replayability Requirements

Every execution path in the system must be **replayable** — meaning it can be re-executed from a checkpoint and produce identical (or observably diffable) results.

```
REPLAYABILITY CONTRACT:
┌──────────────────────────────────────────────────────────────┐
│  For any execution E at step N:                                │
│                                                                 │
│  Given: checkpoint C at step N                                  │
│  When:  replay from C with same config                          │
│  Then:  replay produces events E'                                │
│         E' is structurally identical to E[N+1...M]              │
│         (agent outputs may differ due to LLM non-determinism)   │
│                                                                 │
│  Structural identity means:                                      │
│  - Same event types in same order                               │
│  - Same number of events per agent                              │
│  - Same tool calls per agent                                    │
│  - Same step sequence                                           │
│  - Token counts may differ (recorded as variance)               │
└──────────────────────────────────────────────────────────────┘
```

### 12.2 Checkpoint Coverage Requirements

```
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT COVERAGE — Violations block merge                  │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Every agent boundary must be checkpointable                │
│      → Pre-agent checkpoint before agent execution             │
│      → Post-agent checkpoint after agent completion             │
│      → Pause checkpoint on user-initiated pause                │
│                                                                 │
│  R2: Checkpoint must capture:                                   │
│      → Completed agent IDs                                      │
│      → Pending agent IDs                                        │
│      → Completed task IDs                                       │
│      → Shared workflow context                                  │
│      → Memory snapshot (or reference)                           │
│      → Cumulative token usage                                   │
│                                                                 │
│  R3: Checkpoint save must be atomic                              │
│      → All checkpoint data written in single transaction        │
│      → Partial writes must roll back                            │
│                                                                 │
│  R4: Checkpoint load must validate integrity                    │
│      → Checksum verification                                    │
│      → Schema version check                                     │
│      → Execution ID match                                       │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 12.3 Replay Validation in CI

```yaml
# .github/workflows/replay-validation.yml
name: Replay Validation
on: [pull_request]

jobs:
  validate-replay:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check checkpoint coverage
        run: scripts/check-checkpoint-coverage.sh
        # Ensures all agent execution paths have checkpoints
        
      - name: Test checkpoint roundtrip
        run: scripts/test-checkpoint-roundtrip.sh
        # Save → Load → Verify integrity
        
      - name: Test replay determinism
        run: scripts/test-replay-determinism.sh
        # Replay execution and verify event structure matches
```

### 12.4 Replay Diff Validation

```python
# apps/worker/src/orchestrator/replay_engine.py

class ReplayValidator:
    """
    Validates replay output against original execution.
    
    Comparison criteria:
    - Event type sequence (must match exactly)
    - Agent execution order (must match exactly)
    - Tool call sequence (must match exactly)
    - Step count (must match exactly)
    - Token usage (variance tracked, not enforced)
    - Agent output (diff displayed, not enforced)
    """
    
    def validate_replay(
        self,
        original: list[ExecutionEvent],
        replay: list[ExecutionEvent],
    ) -> ReplayValidationResult:
        violations = []
        
        # Check event type sequence
        orig_types = [e.type for e in original]
        replay_types = [e.type for e in replay]
        
        if orig_types != replay_types:
            violations.append(ReplayViolation(
                type="EVENT_SEQUENCE_MISMATCH",
                message="Replay event sequence differs from original",
            ))

        # Check step count
        if len(original) != len(replay):
            violations.append(ReplayViolation(
                type="STEP_COUNT_MISMATCH",
                message=f"Original has {len(original)} events, replay has {len(replay)}",
            ))

        return ReplayValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
        )
```

---

## 13. Observability Validation Strategy

### 13.1 Observability Requirements

Every component in the system must be **fully observable** — meaning its internal state, execution flow, and resource usage are visible through structured events, metrics, and logs.

```
OBSERVABILITY CONTRACT:
┌──────────────────────────────────────────────────────────────┐
│  For any service S in the system:                              │
│                                                                 │
│  REQUIRED:                                                      │
│  □ Health endpoint: /health (liveness), /ready (readiness)     │
│  □ Prometheus metrics: request count, latency, error rate      │
│  □ Structured JSON logs to stdout                               │
│  □ OpenTelemetry traces for all external calls                 │
│  □ Runtime events for all state transitions                    │
│                                                                 │
│  CONDITIONAL:                                                   │
│  □ If S calls LLM: token usage, cost, latency metrics          │
│  □ If S queues tasks: queue depth, task duration metrics       │
│  □ If S stores data: query latency, connection pool metrics    │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 13.2 Observability Validation Checklist

Every PR must pass the following observability validation:

```
□ New endpoints have Prometheus metrics (request count, latency, error rate)
□ New async operations emit typed runtime events
□ New services have health check endpoints
□ New code paths include structured logging
□ New external calls have OpenTelemetry tracing spans
□ New state additions are visible through events/metrics, not just logs
□ Error paths are logged at appropriate severity (WARN vs ERROR)
□ No silent failures — every catch path emits an event or log
```

### 13.3 Metrics Validation in CI

```yaml
# .github/workflows/metrics-validation.yml
name: Metrics Validation
on: [pull_request]

jobs:
  validate-metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check Prometheus metrics registration
        run: scripts/check-metrics-registration.sh
        # Ensures all metrics are registered with proper naming
        
      - name: Check event emissions
        run: scripts/check-event-emissions.sh
        # Ensures all state transitions emit typed events
        
      - name: Check logging coverage
        run: scripts/check-logging-coverage.sh
        # Ensures all error paths have logging
```

### 13.4 Observability Violation Severity

| Violation | Severity | Action |
|-----------|----------|--------|
| Missing health endpoint | HIGH | Block deployment |
| Missing Prometheus metrics | HIGH | Block deployment |
| Missing event emission on state change | MEDIUM | Block merge |
| Missing structured logging | MEDIUM | Block merge |
| Silent catch block | HIGH | Block merge |
| Missing OpenTelemetry span | LOW | Review advisory |

### 13.5 Observability Stack Governance Rules

```
┌──────────────────────────────────────────────────────────────┐
│  OBSERVABILITY GOVERNANCE                                       │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All events must follow the canonical RuntimeEvent envelope │
│      → Type, timestamp, execution_id, correlation_id, source    │
│      → Missing envelope fields = CI validation failure          │
│                                                                 │
│  R2: All metrics must be registered in Prometheus registry       │
│      → Naming convention: crewai_{service}_{metric_name}        │
│      → Labels: service, endpoint, status (for HTTP metrics)     │
│                                                                 │
│  R3: All logs must be structured JSON                            │
│      → Fields: timestamp, level, logger, message, service       │
│      → Correlation_id in every log entry                        │
│      → No free-form text logging (use structured fields)        │
│                                                                 │
│  R4: All external calls must have OpenTelemetry spans            │
│      → LLM calls, database queries, Redis operations            │
│      → Span attributes: service, operation, duration            │
│                                                                 │
│  R5: Execution events must be persisted in execution_logs table  │
│      → INSERT on every runtime event                             │
│      → Partitioned by month for query performance               │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 14. Scalability Validation Strategy

### 14.1 Scalability Requirements

The system must scale horizontally without architectural changes. Scalability validation ensures no component becomes a bottleneck under load.

```
SCALABILITY BOUNDARIES:
┌──────────────────────────────────────────────────────────────┐
│  Component          │ Current Limit │ Scale Strategy           │
├─────────────────────┼───────────────┼─────────────────────────┤
│  API Server         │ 500 concurrent│ Horizontal (HPA)         │
│  SSE Connections    │ 1000 conns    │ WebSocket migration      │
│  Celery Queue       │ 1000 depth    │ Priority queues          │
│  Redis Pub/Sub      │ 10k msg/s     │ Redis Cluster            │
│  PostgreSQL         │ 200 conns     │ PgBouncer + replicas     │
│  PGVector           │ 1M vectors    │ HNSW index + partition   │
│  Token Metrics      │ 1000 writes/s │ Batch write (5s flush)   │
│  Ollama Inference   │ 1 concurrent  │ Multiple GPU replicas    │
└──────────────────────────────────────────────────────────────┘
```

### 14.2 Scalability Validation Rules

```
┌──────────────────────────────────────────────────────────────┐
│  SCALABILITY VALIDATION — Violations block merge                │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: No synchronous blocking calls in async contexts            │
│      → All I/O must be async (HTTP, DB, Redis, LLM)            │
│      → Synchronous calls block the event loop/worker           │
│                                                                 │
│  R2: No thread-unsafe shared state in workers                   │
│      → CrewRuntime is NOT thread-safe (documented)              │
│      → Each runtime instance used by exactly one execution      │
│                                                                 │
│  R3: No connection pool exhaustion                              │
│      → Database connections limited per service                 │
│      → Redis connections pooled with max_connections            │
│                                                                 │
│  R4: No unbounded in-memory data structures                     │
│      → Terminal entries: max 10,000                             │
│      → Event streams: maxlen 10,000                             │
│      → Redis keys: TTL-enforced                                 │
│                                                                 │
│  R5: No serial bottlenecks                                       │
│      → Single Celery queue → priority queues                    │
│      → Single SSE connection → connection multiplexing          │
│      → Single DB writer → read replicas                         │
│                                                                 │
│  R6: Batch writes for high-frequency data                       │
│      → Token metrics: flush every 5s or 100 records             │
│      → Event persistence: async insert (no impact on exec)      │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 14.3 Load Testing Requirements

```
┌──────────────────────────────────────────────────────────────┐
│  LOAD TESTING — Required before production deployment          │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  Scenarios:                                                     │
│  □ Normal load: 10 concurrent workflow executions              │
│  □ Peak load: 50 concurrent workflow executions                │
│  □ Burst: 100 workflow starts in 1 minute                      │
│  □ SSE stress: 500 concurrent SSE connections                  │
│  □ LLM stress: 1000 token tracking writes/second               │
│                                                                 │
│  Pass criteria:                                                 │
│  □ API p95 latency < 500ms                                     │
│  □ Worker task completion rate = submission rate                │
│  □ SSE event delivery latency < 100ms                           │
│  □ Zero 5xx errors under normal load                           │
│  □ Zero database deadlocks                                      │
│  □ No OOM kills                                                 │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 14.4 Scalability Review Checklist

```
□ Stateless service design — can scale horizontally
□ No in-memory session state (use Redis/DB)
□ Connection limits configured per service
□ Timeouts configured on all external calls
□ Retry with backoff on all external calls
□ Bulkhead pattern for critical resources (DB pool, LLM calls)
□ Circuit breaker for external dependencies (LLM providers)
```

---

## 15. Security Validation Strategy

### 15.1 Security Requirements

Every layer of the system must implement defense-in-depth security. Security validation is **mandatory** before any production deployment.

```
SECURITY LAYERS:
┌──────────────────────────────────────────────────────────────┐
│  LAYER 1: Network                                               │
│  □ Network policies: default deny ingress                      │
│  □ mTLS between services (Istio, production)                   │
│  □ No public exposure of internal services                     │
│  □ WAF/ALB for public endpoints                                │
│                                                               │
│  LAYER 2: Authentication                                        │
│  □ JWT-based auth on all API endpoints                         │
│  □ Public routes: /health, /docs, /redoc only                  │
│  □ Token validation middleware on all protected routes         │
│  □ Rate limiting per user (100 req/min)                        │
│                                                               │
│  LAYER 3: Authorization                                         │
│  □ RBAC for workflow operations                                │
│  □ Tool permission checks per agent                            │
│  □ HITL approval required for sensitive operations             │
│                                                               │
│  LAYER 4: Secrets                                               │
│  □ No secrets in code, config files, or CI logs                │
│  □ All secrets from Vault or cloud secret manager              │
│  □ LLM API keys encrypted at rest                              │
│                                                               │
│  LAYER 5: Data                                                  │
│  □ Database storage encrypted at rest (KMS)                    │
│  □ TLS for all external communication                          │
│  □ PII/credentials never logged                                │
│                                                               │
│  LAYER 6: Supply Chain                                          │
│  □ All container images scanned for vulnerabilities            │
│  □ Dependencies scanned for known vulnerabilities              │
│  □ SBOM generated per build                                    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 15.2 Security Validation Rules

```
┌──────────────────────────────────────────────────────────────┐
│  SECURITY VALIDATION — Violations block deployment              │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: No hardcoded secrets in codebase                           │
│      → Secret scanning in CI (trufflehog/gitleaks)             │
│      → Block commit if secret detected                         │
│                                                                 │
│  R2: All API endpoints (except public) require JWT auth         │
│      → AuthMiddleware validates JWT on every request            │
│      → Missing auth middleware = deployment block               │
│                                                                 │
│  R3: All user inputs validated with Zod/Pydantic                │
│      → No raw request body parsing                              │
│      → Validation errors return 422 with details                │
│                                                                 │
│  R4: SQL injection prevention                                   │
│      → Parameterized queries only (no string concatenation)    │
│      → Repository pattern prevents raw SQL                     │
│                                                                 │
│  R5: No sensitive data in logs                                  │
│      → Credentials, tokens, PII masked/omitted                 │
│      → LLM inputs/outputs truncated in logs                    │
│                                                                 │
│  R6: Rate limiting on all API endpoints                         │
│      → Token bucket per user (configurable)                    │
│      → 429 response on exhaustion                              │
│                                                                 │
│  R7: LLM provider circuit breaker                               │
│      → After N consecutive failures, circuit opens             │
│      → Half-open after cooldown, close on success              │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 15.3 Security Review Checklist

```
□ Authentication: JWT validated on all protected endpoints
□ Authorization: RBAC enforced for all operations
□ Input validation: Zod/Pydantic schemas on all inputs
□ Output encoding: No raw JSON serialization of untrusted data
□ Secrets: No secrets in code, env vars from Vault/secrets manager
□ CSRF: SameSite cookies, CSRF tokens for state-changing operations
□ Rate limiting: Configured per endpoint/user
□ Dependencies: No known CVEs in dependencies (SCA scan)
□ Containers: No root user, read-only root filesystem
□ Network: Network policies restrict pod-to-pod communication
```

### 15.4 Security CI Pipeline

```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on: [pull_request, push]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Secret scanning
        uses: trufflesecurity/trufflehog@v3
      
      - name: SAST scan
        uses: github/codeql-action/analyze@v3
      
      - name: Dependency scan
        run: |
          pip freeze | safety check --stdin
          npm audit --audit-level=high
      
      - name: Container scan
        run: trivy image crewai-api:latest --severity CRITICAL,HIGH
```

---

## 16. CI Architecture Enforcement

### 16.1 CI Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  CI PIPELINE — Every PR must pass all stages                   │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  STAGE 1: LINT (2 min)                                          │
│  ├── ESLint / Ruff — governance rules enforced                 │
│  ├── Prettier — code formatting check                          │
│  └── Import order — consistent module organization            │
│                                                                 │
│  STAGE 2: TYPE CHECK (3 min)                                    │
│  ├── TypeScript — strict mode, no any                           │
│  ├── mypy / Pyright — strict Python types                      │
│  └── Pydantic/Zod — schema validation                         │
│                                                                 │
│  STAGE 3: TEST (10 min)                                         │
│  ├── Unit tests — coverage thresholds                          │
│  ├── Integration tests — API + DB + Redis                      │
│  └── State machine tests — all transitions                     │
│                                                                 │
│  STAGE 4: BUILD (5 min)                                         │
│  ├── Next.js build — standalone output                         │
│  ├── Docker build — multi-stage                                │
│  └── Bundle analysis — size budget check                       │
│                                                                 │
│  STAGE 5: ARCHITECTURE (3 min)                                  │
│  ├── Module boundary check — import rules                      │
│  ├── Event schema check — backward compatibility              │
│  ├── Dependency graph validation — no cycles                  │
│  └── Architecture drift detection — compare to canonical      │
│                                                                 │
│  STAGE 6: SECURITY (5 min)                                      │
│  ├── Secret scanning                                           │
│  ├── Dependency vulnerability scan                             │
│  └── SAST scan                                                  │
│                                                                 │
│  STAGE 7: DEPLOY (conditional)                                  │
│  ├── Build and push images (on merge to main)                  │
│  ├── Update staging environment (on merge to main)             │
│  └── Production deployment (on release tag)                    │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 16.2 CI Gate Configuration

```yaml
# .github/workflows/ci.yml
name: CI Pipeline
on: [pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pnpm lint
      - run: pnpm format:check
      # HARD GATE: Lint errors block merge
  
  typecheck:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - run: pnpm typecheck
      # HARD GATE: Type errors block merge
  
  test:
    runs-on: ubuntu-latest
    needs: typecheck
    steps:
      - uses: actions/checkout@v4
      - run: pnpm test -- --coverage
      - run: scripts/check-coverage.sh
      # HARD GATE: Test failures + coverage below threshold block merge
  
  architecture:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - run: scripts/enforce-dependencies.sh
      - run: scripts/check-event-schemas.sh
      - run: scripts/check-dependency-cycles.sh
      - run: scripts/detect-architecture-drift.sh
      # HARD GATE: Architecture violations block merge
  
  security:
    runs-on: ubuntu-latest
    needs: architecture
    steps:
      - uses: actions/checkout@v4
      - run: scripts/secret-scan.sh
      - run: scripts/dependency-scan.sh
      # HARD GATE: Security violations block merge
```

### 16.3 CI Pass/Fail Criteria

| Stage | Hard Gate | Soft Gate | Block Duration |
|-------|-----------|-----------|----------------|
| Lint | Errors | Warnings | Until fixed |
| Type check | Errors | — | Until fixed |
| Unit tests | Failures + coverage < threshold | Coverage trend decline | Until fixed |
| Integration tests | Failures | Performance regression | Until fixed |
| Build | Build failure | Bundle size > 110% | Until fixed |
| Architecture | L1/L2 violations | L3/L4 violations | Until fixed |
| Security | CRITICAL/HIGH CVE | MEDIUM CVE | Until fixed |
| Event schema | Breaking change | Additive change | Until ADR approved |

### 16.4 CI Times & SLAs

| Stage | Target Time | Max Time | SLA |
|-------|-------------|----------|-----|
| Lint | 2 min | 5 min | 95% |
| Type check | 3 min | 8 min | 95% |
| Test | 10 min | 20 min | 90% |
| Build | 5 min | 15 min | 90% |
| Architecture | 3 min | 8 min | 95% |
| Security | 5 min | 10 min | 95% |
| **Total** | **28 min** | **66 min** | **90%** |

---

## 17. Linting & Type Enforcement

### 17.1 Linting Configuration

The following linting tools are configured with **governance rules** — violations are errors, not warnings:

#### TypeScript/JavaScript (Frontend)

```json
// .eslintrc.js — Governance-specific rules
{
  "rules": {
    // Strict type enforcement
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/strict-boolean-expressions": "error",
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    
    // Module boundary enforcement
    "import/no-restricted-paths": ["error", {
      "zones": [
        { "target": "src/services", "from": "src/store", "message": "Services must not import Store" },
        { "target": "src/components", "from": "src/services", "message": "Components must not import Services directly" }
      ]
    }],
    "import/no-cycle": "error",
    "import/no-relative-parent-imports": "error",
    
    // React governance
    "react/no-array-index-key": "error",
    "react/jsx-no-bind": ["error", { "allowArrowFunctions": true }],
    "react-hooks/exhaustive-deps": "error",
    
    // Complexity limits
    "max-lines": ["error", { "max": 300, "skipBlankLines": true, "skipComments": true }],
    "max-depth": ["error", 4],
    "max-nested-callbacks": ["error", 3],
    "max-params": ["error", 4],
    "complexity": ["error", 15],
    
    // Naming conventions
    "@typescript-eslint/naming-convention": [
      "error",
      { "selector": "interface", "format": ["PascalCase"], "prefix": ["I"] },
      { "selector": "typeAlias", "format": ["PascalCase"] },
      { "selector": "enum", "format": ["PascalCase"] },
      { "selector": "variable", "format": ["camelCase", "UPPER_CASE"] }
    ]
  }
}
```

#### Python (Backend)

```ini
# setup.cfg — Governance-specific ruff rules
[tool.ruff]
select = [
    "E", "W", "F", "I", "N", "D", "UP", "YTT",
    "ANN", "ASYNC", "B", "BLE", "COM", "C4",
    "DTZ", "EM", "FLY", "ISC", "ICN", "G",
    "LOG", "PTH", "PERF", "PLE", "PLR", "PLW",
    "PT", "PIE", "Q", "RSE", "RET", "RUFF",
    "SIM", "SLF", "SLOT", "T10", "T20", "TID",
    "TRY", "UP", "W", "YTT"
]
ignore = []

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]

[tool.ruff.pydocstyle]
convention = "google"

[tool.ruff.flake8-tidy-imports]
ban-relative-imports = "all"

[tool.ruff.mccabe]
max-complexity = 15

[tool.ruff.pycodestyle]
max-line-length = 100
```

### 17.2 Type Enforcement Rules

```
┌──────────────────────────────────────────────────────────────┐
│  TYPE ENFORCEMENT — Strict mode required in all packages      │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  TypeScript (Frontend + Shared Types):                          │
│  □ strict: true                                                │
│  □ noImplicitAny: true                                         │
│  □ strictNullChecks: true                                      │
│  □ noUncheckedIndexedAccess: true                              │
│  □ exactOptionalPropertyTypes: true                            │
│  □ No 'any' type — use 'unknown' if type is truly unknown     │
│  □ All function return types explicitly annotated              │
│  □ All API responses typed via shared-types package            │
│                                                                 │
│  Python (Backend + Runtime):                                    │
│  □ Type hints on all function signatures                        │
│  □ mypy strict mode                                             │
│  □ Pydantic models for all data structures                      │
│  □ No Dict[str, Any] — use typed models                        │
│  □ No bare try/except — catch specific exceptions              │
│  □ Optional[str] over str | None for backward compatibility    │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 17.3 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        types_or: [javascript, typescript, css, markdown, yaml]
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  
  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: pnpm typecheck
        language: node
        types: [python]
      
      - id: eslint
        name: eslint
        entry: pnpm lint
        language: node
        types_or: [javascript, typescript, tsx]
```

---

## 18. ADR Workflow

### 18.1 When ADRs Are Required

Architecture Decision Records (ADRs) are required for:

```
REQUIRED ADR:
┌──────────────────────────────────────────────────────────────┐
│  □ Adding a new package/dependency                             │
│  □ Changing module boundaries                                  │
│  □ Adding/modifying event schemas                              │
│  □ Changing state machine transitions                          │
│  □ Adding/modifying API contracts                              │
│  □ Changing infrastructure topology                            │
│  □ Adding new LLM provider integration                         │
│  □ Changing deployment model                                   │
│  □ Adding new service/component                                │
│  □ Changing security model                                     │
│  □ Any change that affects replayability                       │
│  □ Any change that affects scalability                         │
│                                                               │
│  NOT REQUIRED:                                                  │
│  □ Bug fixes (no architecture impact)                          │
│  □ Adding tests                                                │
│  □ Documentation updates                                       │
│  □ Refactoring (preserving same contract)                      │
│  □ UI component changes (no logic changes)                    │
└──────────────────────────────────────────────────────────────┘
```

### 18.2 ADR Template

```markdown
# ADR-{NNN}: {Title}

> **Status**: {Proposed | Accepted | Deprecated | Superseded}
> **Date**: {YYYY-MM-DD}
> **Author**: {Name}
> **Superceded by**: ADR-{NNN} (if applicable)

## Context

{What is the issue that we're seeing that is motivating this decision?}

## Decision

{What is the change that we're proposing?}

## Consequences

{What becomes easier or more difficult?}

### Positive

- {Positive consequence 1}
- {Positive consequence 2}

### Negative

- {Negative consequence 1}
- {Negative consequence 2}

## Compliance

{How will this decision be enforced?}

## References

- [Architecture Document Reference](link)
- [Related ADR](link)
```

### 18.3 ADR Workflow

```
┌──────────────────────────────────────────────────────────────┐
│  ADR WORKFLOW                                                  │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  STEP 1: DRAFT                                                  │
│  Author creates ADR in docs/adr/ADR-{NNN}-{title}.md           │
│  Submit as PR with architecture label                           │
│                                                                 │
│  STEP 2: REVIEW                                                 │
│  AGB reviews within 5 business days                             │
│  Stakeholders provide feedback                                  │
│  Review criteria:                                                │
│  - Architecture alignment                                       │
│  - Impact on existing systems                                   │
│  - Replayability impact                                         │
│  - Scalability impact                                           │
│  - Security implications                                        │
│                                                                 │
│  STEP 3: DECISION                                               │
│  ACCEPTED: Merge PR, update architecture docs                   │
│  REJECTED: Close PR with rationale, seek alternative            │
│  DEFERRED: Postpone until further information available         │
│                                                                 │
│  STEP 4: ENFORCEMENT                                            │
│  Update CI rules to enforce the decision                       │
│  Update architecture documentation                              │
│  Communicate to all team members                                │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 18.4 ADR Index

All ADRs are stored in [`docs/adr/`](docs/adr/) with a central index:

```markdown
# Architecture Decision Records Index

| ADR | Title | Status | Date | Author |
|-----|-------|--------|------|--------|
| 001 | Event-driven architecture backbone | Accepted | 2026-05-01 | AGB |
| 002 | Hierarchical state machine model | Accepted | 2026-05-05 | AGB |
| 003 | Redis Stream for event persistence | Proposed | 2026-05-10 | — |
```

---

## 19. Migration Governance

### 19.1 Database Migration Rules

```
┌──────────────────────────────────────────────────────────────┐
│  DATABASE MIGRATION GOVERNANCE                                  │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: All schema changes via Alembic migrations                 │
│      → No raw ALTER TABLE in production                         │
│      → Migration files must be reviewed                        │
│                                                                 │
│  R2: Every migration must be reversible                         │
│      → upgrade() AND downgrade() functions                     │
│      → Downgrade must restore exact previous state             │
│                                                                 │
│  R3: Migrations must be backward compatible                     │
│      → Can add columns (nullable or with default)              │
│      → Can add tables                                           │
│      → Cannot remove columns/tables (deprecate only)           │
│      → Cannot change column types (add new column instead)     │
│                                                                 │
│  R4: Migration naming convention                                │
│      → {version}_{description}.py                               │
│      → Example: 002_add_execution_checkpoint.py                │
│                                                                 │
│  R5: Data migrations separate from schema migrations            │
│      → Schema migration: changes table structure               │
│      → Data migration: transforms existing data                │
│      → Data migrations have additional rollback checks         │
│                                                                 │
│  R6: CI validates migration order                               │
│      → alembic check runs in CI                                 │
│      → Detects conflicting migrations                           │
│      → Detects missing downgrade paths                         │
│                                                                 │
│  R7: Production migrations are zero-downtime                    │
│      → Add columns as nullable, then backfill                   │
│      → Table locking operations scheduled during maintenance   │
│      → Long-running migrations use batch processing           │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 19.2 Event Schema Migration

```
┌──────────────────────────────────────────────────────────────┐
│  EVENT SCHEMA MIGRATION GOVERNANCE                              │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Event schema version is in the event envelope              │
│      → version field in RuntimeEvent                           │
│      → Consumers check version before processing               │
│                                                                 │
│  R2: Additive changes only (no breaking changes)                │
│      → New optional fields allowed                              │
│      → New event types allowed                                  │
│      → Field removal = schema version bump + ADR               │
│                                                                 │
│  R3: Old events remain readable forever                         │
│      → execution_logs table stores raw event payload           │
│      → Replay uses original event format                       │
│                                                                 │
│  R4: Event consumer compatibility                               │
│      → Consumers must handle unknown fields gracefully         │
│      → Consumers must handle unknown event types gracefully    │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 19.3 Configuration Migration

```
┌──────────────────────────────────────────────────────────────┐
│  CONFIGURATION MIGRATION GOVERNANCE                              │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Workflow config snapshots are immutable                    │
│      → config_snapshot at execution time is frozen             │
│      → Schema changes do not affect existing executions        │
│                                                                 │
│  R2: YAML schema versioned                                      │
│      → Version field in YAML frontmatter                        │
│      → Schema upgrade migrates YAML on load                    │
│                                                                 │
│  R3: Infrastructure config via Terraform                        │
│      → Terraform plan must be reviewed                         │
│      → State file in remote backend with locking               │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 20. Versioning Governance

### 20.1 Versioning Strategy

| Artifact | Versioning Scheme | Location | Update Frequency |
|----------|------------------|----------|-----------------|
| System | SemVer (MAJOR.MINOR.PATCH) | Root package.json | Per release |
| API | SemVer (MAJOR.MINOR.PATCH) | apps/api/pyproject.toml | Per API change |
| Shared types | SemVer (MAJOR.MINOR.PATCH) | packages/shared-types/package.json | Per contract change |
| Event schema | Integer (V1, V2, V3) | RuntimeEvent.version field | Per schema change |
| Workflow YAML | Integer (file version) | YAML frontmatter | Per config change |
| Database | Alembic revision hash | apps/api/src/db/versions/ | Per migration |
| Docker images | Git SHA + build number | Image tag | Per build |
| Kubernetes manifests | Git SHA | Kustomize/Helm | Per infra change |

### 20.2 Semantic Versioning Rules

```
┌──────────────────────────────────────────────────────────────┐
│  SEMANTIC VERSIONING GOVERNANCE                                 │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  MAJOR (1.x.x → 2.x.x):                                        │
│  □ Breaking API contract changes                                │
│  □ Breaking event schema changes (field removal)               │
│  □ Database schema changes requiring migration                 │
│  □ State machine topology changes                              │
│                                                                 │
│  MINOR (x.1.x → x.2.x):                                        │
│  □ Additive API changes (new endpoints)                        │
│  □ New event types                                              │
│  □ New optional event fields                                    │
│  □ New workflow features                                        │
│                                                                 │
│  PATCH (x.x.1 → x.x.2):                                        │
│  □ Bug fixes                                                    │
│  □ Performance improvements                                     │
│  □ Documentation updates                                        │
│  □ Non-breaking dependency updates                              │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 20.3 API Versioning

```
┌──────────────────────────────────────────────────────────────┐
│  API VERSIONING GOVERNANCE                                       │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: API version in URL path (/api/v1/, /api/v2/)              │
│      → Header-based versioning considered for future           │
│                                                                 │
│  R2: Old API versions supported for minimum 2 releases          │
│      → Deprecation announced at least 1 release in advance     │
│      → Sunset header on deprecated endpoints                   │
│                                                                 │
│  R3: API changelog required for every version                   │
│      → CHANGELOG.md in apps/api/                               │
│      → Breaking changes highlighted                            │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 20.4 Event Schema Versioning

```
┌──────────────────────────────────────────────────────────────┐
│  EVENT SCHEMA VERSIONING GOVERNANCE                              │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Event version in envelope (current: v1)                    │
│      → version field in every RuntimeEvent                      │
│      → Consumers check version before processing               │
│                                                                 │
│  R2: New version = new data schema type                         │
│      → AgentStartedDataV1, AgentStartedDataV2                   │
│      → Old version maintained for replay compatibility          │
│                                                                 │
│  R3: Event type names never removed                              │
│      → DEPRECATED_ prefix when event is no longer emitted      │
│      → Consumers may stop processing deprecated events         │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 21. Implementation Phase Control Rules

### 21.1 Phase Architecture

Implementation follows the **14-phase roadmap** defined in [`ARCHITECTURAL_ANALYSIS.md`](ARCHITECTURAL_ANALYSIS.md#13-implementation-roadmap). Phase gates prevent skipping architectural foundations.

```
PHASE DEPENDENCY MAP:
┌──────────────────────────────────────────────────────────────┐
│  Phase 0: Foundation ──► Phase 1: Data Layer                   │
│     (required by all)       (required by 2,3,5,7,10)          │
│          │                         │                           │
│          ▼                         ▼                           │
│  Phase 2: Frontend Shell ──► Phase 3: YAML Sync                │
│     (required by 4,7,8,10)       (required by 4,7,8)           │
│          │                         │                           │
│          ▼                         ▼                           │
│  Phase 4: Inspector ──► Phase 5: CrewRuntime                   │
│     (UI only)               (required by 6,8,9,10)            │
│                                   │                            │
│                                   ▼                            │
│  Phase 6: Async Engine ──► Phase 7: Observability              │
│     (required by 8,9,10)        (UI + backend)                │
│          │                         │                           │
│          ▼                         ▼                           │
│  Phase 8: Execution Ctrl ──► Phase 9: HITL                     │
│     (requires 5,6,7)            (requires 5,6,7,8)            │
│          │                         │                           │
│          ▼                         ▼                           │
│  Phase 10: Metrics ──► Phase 11: Hardening                     │
│     (requires 5,6,7)            (requires all above)          │
│                                   │                            │
│                                   ▼                            │
│  Phase 12: Polish + E2E                                        │
│     (requires all above)                                       │
└──────────────────────────────────────────────────────────────┘
```

### 21.2 Phase Entry/Exit Criteria

Each phase has strict entry and exit criteria. **No phase may begin before its entry criteria are met. No phase is complete until its exit criteria are satisfied.**

```
PHASE 0: ARCHITECTURAL FOUNDATION
────────────────────────────────────
Entry Criteria:  None (starting point)
Exit Criteria:
  □ Monorepo scaffold (TurboRepo) with build working
  □ packages/shared-types with all event types and schemas
  □ packages/ui foundation (Button, Card, Layout primitives)
  □ Docker Compose skeleton (all services, no business logic)
  □ CI/CD pipeline passing (lint, type-check, test)
  □ All architecture documents finalized and reviewed

PHASE 1: DATA & AUTH LAYER
────────────────────────────────────
Entry Criteria:  Phase 0 complete
Exit Criteria:
  □ PostgreSQL schema with all tables migrated
  □ SQLAlchemy models + repositories implemented
  □ JWT auth + RBAC middleware working
  □ Redis connection management tested
  □ API health endpoints responding
  □ Secret management configured
  □ All database operations covered by integration tests

PHASE 2: CORE FRONTEND SHELL
────────────────────────────────────
Entry Criteria:  Phase 0 complete
Exit Criteria:
  □ IDE layout (resizable panels) rendering
  □ Left sidebar with tabs functional
  □ React Flow canvas rendering (empty graph)
  □ Right inspector panel routing dynamically
  □ Bottom panel shell with tabs
  □ Zustand store foundation (canvas, UI state)
  □ ExecutionToolbar buttons rendered

PHASE 3: YAML ↔ CANVAS SYNC
────────────────────────────────────
Entry Criteria:  Phase 1, Phase 2 complete
Exit Criteria:
  □ Zod schemas for all workflow configs passing
  □ YAML parser/generator (js-yaml) working
  □ SyncEngine with three-phase sync model passing tests
  □ Monaco editor integration working
  □ Canvas → YAML serialization round-trip passing
  □ YAML → Canvas deserialization round-trip passing
  □ Drag-drop palette → canvas working

PHASE 4: INSPECTOR FORMS
────────────────────────────────────
Entry Criteria:  Phase 2, Phase 3 complete
Exit Criteria:
  □ AgentInspector with all form fields functional
  □ TaskInspector with all form fields functional
  □ ToolInspector with all form fields functional
  □ AI Enhancer button working
  □ Form validation + state persistence passing tests

PHASE 5: CREWRUNTIME
────────────────────────────────────
Entry Criteria:  Phase 1 complete
Exit Criteria:
  □ CrewBuilder constructing crews dynamically
  □ CallbackInterceptor capturing all execution events
  □ EventEmitter publishing to Redis
  □ CheckpointManager save/restore working
  □ MemoryBridge with three-tier memory working
  □ ToolRegistry with dynamic binding working
  □ Full integration tests passing

PHASE 6: ASYNC EXECUTION ENGINE
────────────────────────────────────
Entry Criteria:  Phase 5 complete
Exit Criteria:
  □ Celery configuration with all queues working
  □ run_crew task executing successfully
  □ pause/resume/kill task handlers working
  □ Redis event → API relay working
  □ SSE endpoint + connection management working
  □ Execution state machine integration passing all tests

PHASE 7: OBSERVABILITY
────────────────────────────────────
Entry Criteria:  Phase 6 complete
Exit Criteria:
  □ SSE client manager (frontend) working
  □ ObservabilityTerminal with real-time streaming
  □ Color-coded tags, filtering, search, pause, export all working
  □ execution_logs table ingesting events
  □ Metrics pipeline computing at write time
  □ Token tracking integrated

PHASE 8: EXECUTION CONTROLS
────────────────────────────────────
Entry Criteria:  Phase 5, Phase 6, Phase 7 complete
Exit Criteria:
  □ Run/Pause/Resume/Stop/Retry all wired end-to-end
  □ Checkpoint save/restore working end-to-end
  □ Replay engine working (full + step replay)
  □ Replay diff comparison working
  □ Execution history page rendering

PHASE 9: HUMAN-IN-THE-LOOP
────────────────────────────────────
Entry Criteria:  Phase 5, Phase 6, Phase 7, Phase 8 complete
Exit Criteria:
  □ HITL Celery queue working
  □ Approval inbox page rendering
  □ Approval detail view (draft vs edit) working
  □ Approve/reject/regenerate API working
  □ HITL resume workflow flow working end-to-end
  □ HITL store + components rendering

PHASE 10: METRICS DASHBOARD
────────────────────────────────────
Entry Criteria:  Phase 5, Phase 6, Phase 7 complete
Exit Criteria:
  □ Token cost charts (per agent/task/workflow) rendering
  □ Execution timeline (Gantt chart) rendering
  □ Failure heatmap rendering
  □ Metrics aggregation queries optimized
  □ Dashboard page rendering with real data

PHASE 11: PRODUCTION HARDENING
────────────────────────────────────
Entry Criteria:  All phases 0-10 complete
Exit Criteria:
  □ Audit logging implemented and tested
  □ Rate limiting + circuit breaker working
  □ Error boundaries (React) implemented
  □ Retry logic (all layers) tested
  □ Load testing passing criteria
  □ Performance optimization verified
  □ Backup/restore scripts working
  □ Documentation complete

PHASE 12: POLISH & E2E TESTING
────────────────────────────────────
Entry Criteria:  Phase 11 complete
Exit Criteria:
  □ Playwright E2E tests passing
  □ Pytest integration tests passing
  □ Vitest + RTL unit tests passing
  □ Accessibility audit passing
  □ Edge case hardening verified
  □ Final QA pass approved
```

### 21.3 Phase Gate Enforcement

```
┌──────────────────────────────────────────────────────────────┐
│  PHASE GATE ENFORCEMENT — Violations block PR                  │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: CI validates phase dependency                              │
│      → Script checks which phase files belong to               │
│      → Validates prerequisite phases are complete              │
│      → PRs that skip phases are blocked                        │
│                                                                 │
│  R2: Phase exit criteria must be documented                     │
│      → Exit criteria checklist in phase document               │
│      → Signed off by AGB before next phase begins              │
│                                                                 │
│  R3: Phase violation consequences                               │
│      → Code merged out of phase order = revert                 │
│      → Dependency on incomplete phase = defer                  │
│      → Repeated violations = AGB escalation                    │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 21.4 Phase Marker Convention

Each file in the codebase should be tagged with its implementation phase:

```typescript
// @phase: 0 - Architectural Foundation
// packages/shared-types/src/events/base.py

// @phase: 2 - Core Frontend Shell
// apps/web/src/components/layout/resizable-panel-group.tsx

// @phase: 5 - CrewRuntime
// packages/crew-runtime/src/runtime.py
```

Phase markers enable automated validation:

```bash
# scripts/check-phase-dependencies.sh
# Validates that Phase N files don't depend on Phase N+2 files
check_phase_dependency("phase:0", "phase:2", FORBIDDEN)
check_phase_dependency("phase:5", "phase:3", FORBIDDEN)
```

---

## 22. AI Implementation Behavior Control

### 22.1 AI Implementation Boundaries

AI coding agents (such as this system) operate under **strict behavioral constraints** when implementing code for this codebase.

```
┌──────────────────────────────────────────────────────────────┐
│  AI IMPLEMENTATION BEHAVIOR CONTROL RULES                       │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  R1: Architecture documents are SOURCE OF TRUTH                 │
│      → AI must read architecture docs before implementing      │
│      → AI must reference the specific doc/section it follows   │
│      → AI must NOT deviate from documented architecture        │
│                                                                 │
│  R2: AI must implement ALL defined types                        │
│      → No placeholder types                                     │
│      → No 'any' types                                           │
│      → All types from packages/shared-types                     │
│                                                                 │
│  R3: AI must implement ALL defined interfaces                   │
│      → No stub implementations                                  │
│      → No TODO/FIXME placeholders                              │
│      → Every abstract method must have concrete implementation │
│                                                                 │
│  R4: AI must follow module boundaries                           │
│      → No cross-boundary imports                                │
│      → No business logic in UI components                      │
│      → No inter-app communication outside shared-types         │
│                                                                 │
│  R5: AI must implement error handling                           │
│      → All error paths must be handled                          │
│      → All async operations must have try/catch                │
│      => All external calls must have timeout                   │
│                                                                 │
│  R6: AI must not duplicate code                                 │
│      → Check existing implementations before creating new      │
│      → Extract shared logic into reusable modules              │
│      → Use shared-types package for common contracts           │
│                                                                 │
│  R7: AI must maintain observability                             │
│      → Every new feature must emit typed events                │
│      → Every new endpoint must have metrics                    │
│      → Every new code path must have structured logging        │
│                                                                 │
│  R8: AI must not create architectural shortcuts                 │
│      → No bypassing abstraction layers                         │
│      → No synchronous wrappers around async APIs               │
│      → No hiding state in global variables                     │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 22.2 AI Pre-Implementation Checklist

Before an AI coding agent begins implementation, it must verify:

```
□ Architecture documents reviewed for the relevant domain
□ All interfaces/types defined in docs are understood
□ Module boundaries and dependency rules confirmed
□ Event types and schemas identified
□ State machine transitions identified
□ Checkpoint requirements understood
□ Existing similar implementations reviewed (no duplication)
```

### 22.3 AI Implementation Review Focus

During review of AI-generated code, focus on:

```
□ Architecture compliance — does it follow the documented architecture?
□ Type correctness — no 'any' types, all types from shared-types?
□ Module boundaries — no forbidden imports?
□ Error handling — all error paths covered?
□ Observability — events, metrics, logs present?
□ Checkpoint coverage — execution paths checkpointable?
□ Event compliance — events follow RuntimeEvent envelope?
□ Code quality — no duplication, no giant files, no god components?
```

### 22.4 AI Prohibited Patterns

```
STRICTLY PROHIBITED FOR AI IMPLEMENTATION:
┌──────────────────────────────────────────────────────────────┐
│  □ Creating new files outside the architectural folder        │
│    structure                                                   │
│  □ Adding dependencies not in the architecture plan           │
│  □ Creating global/static mutable state                       │
│  □ Bypassing the Zustand store for UI state management        │
│  □ Direct CrewAI API calls outside packages/crew-runtime      │
│  □ Creating event types not in the EventType enum             │
│  □ Skipping checkpoint implementation in execution paths      │
│  □ Mixing frontend and backend logic                          │
│  □ Using 'any' type under any circumstance                    │
│  □ Creating untyped event emissions                           │
│  □ Modifying architecture documents without ADR               │
│  □ Adding business logic to UI components                     │
│  □ Creating circular dependencies                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 23. Governance Violation Escalation

### 23.1 Violation Classification

```
┌──────────────────────────────────────────────────────────────┐
│  GOVERNANCE VIOLATION CLASSIFICATION                            │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  LEVEL 1: CRITICAL (Immediate escalation)                       │
│  ───────────────────────────────────────────                    │
│  □ Security breach (credential leak, auth bypass)              │
│  □ Data loss (deleted data, corrupted checkpoint)              │
│  □ Production outage (deployment of broken code)               │
│  □ Architecture bypass (layer violation in production)         │
│  Action: Immediate AGB meeting, rollback, incident report      │
│                                                                 │
│  LEVEL 2: HIGH (Block merge)                                    │
│  ─────────────────────────────────                              │
│  □ Module boundary violation                                     │
│  □ Missing event schema                                         │
│  □ Missing checkpoint                                            │
│  □ Missing type safety ('any' types)                            │
│  □ Missing error handling                                       │
│  □ Synchronous blocking in async context                        │
│  Action: Block CI, require fix, re-review                       │
│                                                                 │
│  LEVEL 3: MEDIUM (Require changes)                              │
│  ─────────────────────────────────                               │
│  □ Component > 300 lines                                        │
│  □ Service > 500 lines                                          │
│  □ Missing observability (events, metrics)                      │
│  □ Inefficient re-renders                                       │
│  □ Insufficient test coverage                                   │
│  Action: Block merge, require changes, re-review                 │
│                                                                 │
│  LEVEL 4: LOW (Advisory)                                        │
│  ─────────────────────────                                       │
│  □ Code style deviations                                        │
│  □ Naming convention violations                                 │
│  □ Missing documentation                                        │
│  □ Duplicate code (minor)                                       │
│  Action: Note in review, address in follow-up PR                │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 23.2 Escalation Flow

```
Violation Detected (automated or manual)
   │
   ▼
Classify Violation
   │
   ├── LEVEL 1 (CRITICAL)
   │      │
   │      ▼
   │  1. Immediate rollback of affected code
   │  2. Notify AGB + all stakeholders
   │  3. Root cause analysis within 24h
   │  4. Incident report within 48h
   │  5. Preventive measures implemented within 1 week
   │  6. AGB review of fix before re-deploy
   │
   ├── LEVEL 2 (HIGH)
   │      │
   │      ▼
   │  1. Block CI pipeline
   │  2. Notify PR author + reviewer
   │  3. Fix required before merge
   │  4. Re-review after fix
   │  5. AGB notified of pattern (if recurring)
   │
   ├── LEVEL 3 (MEDIUM)
   │      │
   │      ▼
   │  1. Block merge
   │  2. Request changes from author
   │  3. Re-review after changes
   │
   └── LEVEL 4 (LOW)
          │
          ▼
      1. Note in PR review
      2. Author addresses in same or follow-up PR
      3. Tracked for pattern analysis
```

### 23.3 Recurring Violation Consequences

```
┌──────────────────────────────────────────────────────────────┐
│  RECURRING VIOLATION ESCALATION                                 │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  Same author, same violation type, >3 occurrences:              │
│  □ Mandatory architecture training                              │
│  □ All PRs require AGB review (temporary)                      │
│  □ Automated lint rules added to prevent recurrence            │
│                                                                 │
│  Same team, same violation type, >5 occurrences:                │
│  □ Team-wide architecture review session                       │
│  □ Additional CI gates added                                   │
│  □ Architecture documentation updated for clarity              │
│                                                                 │
│  System-wide pattern violation:                                 │
│  □ AGB issues architecture guidance                            │
│  □ Automated detection tooling added                           │
│  □ Architecture documentation revised                          │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 23.4 Governance Audit

```
┌──────────────────────────────────────────────────────────────┐
│  GOVERNANCE AUDIT — Quarterly review by AGB                    │
├──────────────────────────────────────────────────────────────┤
│                                                                 │
│  Audit Scope:                                                   │
│  □ Architecture drift since last audit                          │
│  □ Violation trends (types, frequency, authors)                │
│  □ ADR adoption rate                                           │
│  □ CI gate effectiveness (false positives, missed violations)  │
│  □ Test coverage trends                                        │
│  □ Performance trends                                          │
│  □ Security posture                                            │
│                                                                 │
│  Audit Output:                                                  │
│  □ Governance effectiveness report                              │
│  □ Recommended rule changes                                    │
│  □ Training requirements                                        │
│  □ Tooling improvements                                         │
│                                                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Appendix A: Governance Quick Reference

### A.1 Pre-Commit Checklist

```
Before every commit, verify:
□ No forbidden imports (check import rules)
□ No 'any' types
□ No synchronous blocking in async code
□ Typed event emissions
□ Error handling on all async operations
□ No secrets hardcoded
□ Tests pass + coverage threshold met
□ Lint passes
□ Type check passes
```

### A.2 Pre-Merge Checklist

```
Before every merge, verify:
□ CI pipeline green (all stages)
□ Architecture review completed (if required)
□ ADR approved (if required)
□ Phase gate criteria met
□ Event schema backward compatible
□ No L1/L2 violations
□ Test coverage thresholds met
□ Security scan passed
```

### A.3 Pre-Deploy Checklist

```
Before every production deployment, verify:
□ Load testing passed
□ Security scan passed
□ Migration tested (if applicable)
□ Rollback plan documented
□ Monitoring dashboards updated
□ Alert rules configured
□ Runbook updated (if new operations)
□ AGB approval obtained (if architecture change)
```

---

## Appendix B: Governance Automation Scripts

### B.1 Architecture Enforcement Scripts

```
scripts/
├── enforce-dependencies.sh       # Module boundary check
├── check-event-types.sh          # Event type enum completeness
├── check-event-schemas.sh        # Event schema validation
├── check-event-compatibility.sh  # Backward compatibility check
├── check-dependency-cycles.sh    # Circular dependency detection
├── detect-architecture-drift.sh  # Compare to canonical architecture
├── check-phase-dependencies.sh   # Phase gate compliance
├── check-checkpoint-coverage.sh  # Checkpoint coverage check
├── check-metrics-registration.sh # Prometheus metrics check
├── check-logging-coverage.sh     # Logging coverage check
├── check-coverage.sh             # Test coverage thresholds
├── secret-scan.sh                # Secret detection
├── dependency-scan.sh            # Vulnerability scanning
└── check-coverage.sh             # Code coverage validation
```

---

## Appendix C: Governance Documents Index

| Document | Location | Purpose |
|----------|----------|---------|
| Architecture Governance | [`docs/ARCHITECTURE_GOVERNANCE.md`](ARCHITECTURE_GOVERNANCE.md) | This document — governance rules |
| Architectural Analysis | [`docs/ARCHITECTURAL_ANALYSIS.md`](ARCHITECTURAL_ANALYSIS.md) | Principal architecture review |
| Frontend Architecture | [`docs/FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md) | Frontend specification |
| Backend Runtime | [`docs/BACKEND_RUNTIME_ARCHITECTURE.md`](BACKEND_RUNTIME_ARCHITECTURE.md) | Backend specification |
| Orchestration | [`docs/ORCHESTRATION_ARCHITECTURE.md`](ORCHESTRATION_ARCHITECTURE.md) | AI orchestration specification |
| Infrastructure | [`docs/INFRASTRUCTURE_ARCHITECTURE.md`](INFRASTRUCTURE_ARCHITECTURE.md) | Infrastructure specification |
| ADR Index | [`docs/adr/README.md`](adr/README.md) | Architecture decision records |
| Spec Reference | [`CREWAI_ENTERPRISE_CONTROL_CENTER_SPEC.md`](CREWAI_ENTERPRISE_CONTROL_CENTER_SPEC.md) | Original specification |

---

*End of Architecture Governance & Implementation Control Strategy.*