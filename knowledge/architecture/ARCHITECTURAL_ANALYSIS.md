# CrewAI Enterprise Control Center — Architectural Analysis

> **Document Type**: Principal Architecture Review  
> **Status**: Pre-Implementation Analysis  
> **Version**: 1.0  
> **Spec Reference**: [`CREWAI_ENTERPRISE_CONTROL_CENTER_SPEC.md`](CREWAI_ENTERPRISE_CONTROL_CENTER_SPEC.md)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architectural Risks & Mitigations](#2-architectural-risks--mitigations)
3. [Domain Architecture & Module Boundaries](#3-domain-architecture--module-boundaries)
4. [Event-Driven Architecture](#4-event-driven-architecture)
5. [Execution Lifecycle & State Machines](#5-execution-lifecycle--state-machines)
6. [Multi-Agent Orchestration Architecture](#6-multi-agent-orchestration-architecture)
7. [Observability Architecture](#7-observability-architecture)
8. [Memory Architecture](#8-memory-architecture)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Infrastructure Architecture](#10-infrastructure-architecture)
11. [Data Flow Diagrams](#11-data-flow-diagrams)
12. [Missing Enterprise Systems](#12-missing-enterprise-systems)
13. [Implementation Roadmap](#13-implementation-roadmap)
14. [Scaling Considerations](#14-scaling-considerations)

---

## 1. Executive Summary

The CrewAI Enterprise Control Center spec describes a **full-stack AI Multi-Agent Operating System** that visually manages CrewAI agent workflows. The architectural ambition is correct — an IDE-style control plane with real-time observability, execution control, and human-in-the-loop capabilities.

However, the specification as written contains **critical architectural gaps** in five areas:

1. **Execution state machine** — The 5-state model (`PENDING → RUNNING → SUSPENDED → FAILED → SUCCESS`) is insufficient for the real complexity of multi-agent execution, checkpointing, partial failures, and resumable workflows.
2. **Event architecture** — No event bus or pub/sub layer is defined. SSE is mentioned for the terminal, but the system needs an internal event backbone for decoupled communication between the frontend, API, Celery workers, and CrewAI runtime.
3. **CrewAI runtime abstraction** — Dynamic crew construction, callback interception, checkpoint injection, and execution replay require a **runtime wrapper layer** that the spec acknowledges but does not fully account for in complexity.
4. **YAML↔UI bidirectional sync** — Two-way sync without a canonical source-of-truth strategy will produce race conditions and data corruption.
5. **Observability architecture** — Distributed tracing across `Frontend → API → Celery → CrewAI → LLM` is not addressed. The spec focuses on UI but not on the data pipeline that feeds it.

The following analysis defines the **correct architecture** to address these gaps before implementation begins.

---

## 2. Architectural Risks & Mitigations

### Risk 1: Under-Specified Execution State Machine
| Aspect | Detail |
|--------|--------|
| **Problem** | The spec defines 5 states. Real CrewAI execution involves: agent thinking → tool selection → tool execution → observation → task completion → agent handoff. Each phase can fail, require HITL, or hit rate limits. |
| **Impact** | Without richer states, the UI cannot accurately reflect execution progress; pause/resume/replay becomes unreliable. |
| **Mitigation** | Implement a **hierarchical state machine** with top-level workflow states and nested per-agent/per-task sub-states. See [Section 5](#5-execution-lifecycle--state-machines). |

### Risk 2: Missing Event Backbone
| Aspect | Detail |
|--------|--------|
| **Problem** | SSE is only mentioned for the terminal. The API, Celery workers, and runtime need a shared event transport for decoupled communication. Without it, every feature (HITL, metrics, logs, status updates) requires tight point-to-point coupling. |
| **Impact** | Adding new observability consumers requires modifying producers. Horizontal scaling becomes impossible. |
| **Mitigation** | Introduce **Redis Pub/Sub** as the internal event bus. See [Section 4](#4-event-driven-architecture). |

### Risk 3: CrewAI Runtime Integration Complexity
| Aspect | Detail |
|--------|--------|
| **Problem** | CrewAI v0.x does not natively support: dynamic crew construction from JSON, fine-grained execution events, checkpoint/resume, or execution replay at the agent/task level. |
| **Impact** | The runtime abstraction layer will require significant wrapping and monkey-patching of CrewAI internals. |
| **Mitigation** | Build a [`CrewRuntime`](packages/crew-runtime/src/runtime.ts) abstraction that wraps CrewAI with: callback interceptor, checkpoint manager, event emitter, and lifecycle controller. See [Section 6](#6-multi-agent-orchestration-architecture). |

### Risk 4: YAML↔UI Sync Without Canonical Source of Truth
| Aspect | Detail |
|--------|--------|
| **Problem** | Bidirectional sync without a canonical source of truth causes: sync loops (UI change → YAML update → UI re-render → YAML change), race conditions on concurrent edits, and data loss when validation fails on one side. |
| **Impact** | Users lose work; workflow representation becomes inconsistent. |
| **Mitigation** | Adopt a **three-phase sync model** with the **Zustand store as canonical source of truth**. See [`apps/web/src/lib/sync/sync-engine.ts`](#). |

### Risk 5: SSE Scaling Ceiling
| Aspect | Detail |
|--------|--------|
| **Problem** | SSE is single-direction, single-connection. With multiple concurrent workflows and observability consumers per user, the API becomes connection-bound. |
| **Impact** | Beyond ~500 concurrent connections, the API server degrades. No horizontal scaling without sticky sessions. |
| **Mitigation** | Use **Redis Pub/Sub as a message relay**: workers publish events → API subscribes → SSE fan-out per user session. See [Section 4](#4-event-driven-architecture). |

---

## 3. Domain Architecture & Module Boundaries

### 3.1 Domain Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BOUNDED CONTEXTS                             │
├──────────────┬──────────────┬──────────────┬───────────────────────┤
│  WORKFLOW    │  AGENT       │  EXECUTION   │  OBSERVABILITY        │
│  DESIGN      │  MANAGEMENT  │  RUNTIME     │                       │
├──────────────┼──────────────┼──────────────┼───────────────────────┤
│ - Canvas     │ - CRUD       │ - Scheduler  │ - Streaming           │
│ - Nodes      │ - Memory     │ - State Mgr  │ - Metrics             │
│ - Edges      │ - LLM Config │ - Checkpoint │ - Logs                │
│ - YAML Sync  │ - Tools      │ - HITL       │ - Tracing             │
│ - Templates  │ - Persona    │ - Replay     │ - Alerting            │
└──────────────┴──────────────┴──────────────┴───────────────────────┘
         │              │              │               │
         └──────────────┴──────────────┴───────────────┘
                            │
                  ┌─────────▼──────────┐
                  │  SHARED KERNEL     │
                  │  (Types, Events,   │
                  │   Validation, IDs) │
                  └────────────────────┘
```

### 3.2 Module Responsibilities

#### [`apps/web/`](apps/web/src/) — Frontend
| Module | Responsibility |
|--------|---------------|
| [`/store`](apps/web/src/store/) | Zustand stores: canvas state, execution state, UI state, notification state |
| [`/components/canvas`](apps/web/src/components/canvas/) | React Flow nodes, edges, custom controls, minimap |
| [`/components/inspector`](apps/web/src/components/inspector/) | Dynamic right panel — agent/task/tool inspector forms |
| [`/components/terminal`](apps/web/src/components/terminal/) | SSE-connected observability terminal with filtering/search |
| [`/components/metrics`](apps/web/src/components/metrics/) | Recharts dashboards: token cost, Gantt, failure heatmap |
| [`/components/layout`](apps/web/src/components/layout/) | Resizable pane shell, sidebar, toolbar |
| [`/lib/sync`](apps/web/src/lib/sync/) | YAML↔Store bidirectional sync engine |
| [`/lib/stream`](apps/web/src/lib/stream/) | SSE client manager with reconnection, backpressure |
| [`/services`](apps/web/src/services/) | API client layer with typed endpoints |

#### [`apps/api/`](apps/api/src/) — Backend API
| Module | Responsibility |
|--------|---------------|
| [`/api/routes`](apps/api/src/api/routes/) | REST endpoints: workflows, agents, tasks, executions, approvals |
| [`/api/ws`](apps/api/src/api/ws/) | SSE endpoint manager per user session |
| [`/services`](apps/api/src/services/) | Business logic: workflow orchestration, agent CRUD, HITL routing |
| [`/executors`](apps/api/src/executors/) | Celery task definitions: `run_crew`, `pause_crew`, `resume_crew` |
| [`/events`](apps/api/src/events/) | Event publisher (Redis Pub/Sub), event consumer (SSE relay) |
| [`/db`](apps/api/src/db/) | SQLAlchemy models, migrations, repositories |
| [`/models`](apps/api/src/models/) | Pydantic domain models |
| [`/schemas`](apps/api/src/schemas/) | Zod schemas for validation (shared via package) |

#### [`apps/worker/`](apps/worker/src/) — Celery Worker
| Module | Responsibility |
|--------|---------------|
| [`/tasks`](apps/worker/src/tasks/) | Celery task definitions: execution orchestration |
| [`/runtime`](apps/worker/src/runtime/) | CrewAI runtime bridge — wraps CrewAI execution |
| [`/checkpoint`](apps/worker/src/checkpoint/) | Execution checkpoint manager (save/restore) |
| [`/events`](apps/worker/src/events/) | Event publisher — emits execution events to Redis Pub/Sub |

#### [`packages/crew-runtime/`](packages/crew-runtime/src/) — Shared Runtime Library
| Module | Responsibility |
|--------|---------------|
| [`/runtime`](packages/crew-runtime/src/runtime.ts) | `CrewRuntime` class — dynamic crew construction, execution, lifecycle |
| [`/callbacks`](packages/crew-runtime/src/callbacks/) | `CrewCallbackInterceptor` — intercepts all CrewAI step callbacks |
| [`/checkpoint`](packages/crew-runtime/src/checkpoint/) | `CheckpointManager` — save/restore execution state |
| [`/memory`](packages/crew-runtime/src/memory/) | `MemoryBridge` — routes memory operations to Redis/PGVector |
| [`/events`](packages/crew-runtime/src/events/) | Runtime event types and emitters |

#### [`packages/shared-types/`](packages/shared-types/src/) — Shared Contracts
| Module | Responsibility |
|--------|---------------|
| [`/types`](packages/shared-types/src/types/) | Domain type definitions |
| [`/events`](packages/shared-types/src/events/) | Event type definitions (runtime events, system events) |
| [`/schemas`](packages/shared-types/src/schemas/) | Zod validation schemas |
| [`/constants`](packages/shared-types/src/constants/) | Shared constants, enums, state machine definitions |

#### [`packages/ui/`](packages/ui/src/) — Shared UI Components
| Module | Responsibility |
|--------|---------------|
| Agent cards, tool badges, status indicators, form controls, chart primitives |

### 3.3 Dependency Rules

```
apps/web       → packages/shared-types, packages/ui
apps/api       → packages/shared-types, packages/crew-runtime
apps/worker    → packages/shared-types, packages/crew-runtime
packages/crew-runtime → packages/shared-types
packages/ui    → packages/shared-types
```

**Strict rules:**
- No `apps/web` imports from `apps/api` or `apps/worker`
- No `apps/api` imports from `apps/web`
- All inter-app contracts go through [`packages/shared-types`](packages/shared-types/src/)
- [`packages/crew-runtime`](packages/crew-runtime/src/) has zero HTTP/framework dependencies — pure execution logic

---

## 4. Event-Driven Architecture

### 4.1 Event Taxonomy

The system defines **three event layers**:

| Layer | Transport | Producer | Consumer | Purpose |
|-------|-----------|----------|----------|---------|
| **Runtime Events** | Python `asyncio.Queue` | CrewAI callbacks | CrewRuntime → Event Translator | Raw execution observations |
| **System Events** | Redis Pub/Sub | Worker, API | API → SSE, Worker, services | Decoupled internal communication |
| **Client Events** | SSE (HTTP long-lived) | API | Frontend | Real-time UI updates |

### 4.2 Event Flow Architecture

```
┌──────────┐    SSE Connection     ┌──────────┐
│  Browser │◄──────────────────────│   API    │
│  (Web)   │                       │  Server  │
└──────────┘                       └────┬─────┘
                                        │
                                   Redis │ Pub/Sub
                                        │
                              ┌─────────▼──────────┐
                              │   Redis Pub/Sub     │
                              │  (Event Backbone)   │
                              └──┬──────────┬───────┘
                                 │          │
                      ┌──────────▼──┐  ┌────▼──────────┐
                      │  Celery     │  │  API Internal  │
                      │  Worker     │  │  Subscribers   │
                      └──────┬──────┘  └───────────────┘
                             │
                    ┌────────▼────────┐
                    │  CrewRuntime    │
                    │  (via callback  │
                    │   interceptor)  │
                    └─────────────────┘
```

### 4.3 Event Catalog

```typescript
// packages/shared-types/src/events/runtime-events.ts

// Workflow Lifecycle
WORKFLOW_STARTED      // { workflowId, timestamp }
WORKFLOW_CHECKPOINT   // { workflowId, step, snapshotId }
WORKFLOW_PAUSED       // { workflowId, reason }
WORKFLOW_RESUMED      // { workflowId, fromSnapshot }
WORKFLOW_COMPLETED    // { workflowId, status, metrics }
WORKFLOW_FAILED       // { workflowId, error, step }

// Agent Execution
AGENT_THOUGHT         // { workflowId, agentId, thought }
AGENT_ACTION          // { workflowId, agentId, action, tool }
AGENT_OBSERVATION     // { workflowId, agentId, observation }
AGENT_TOOL_CALL       // { workflowId, agentId, tool, input, output, duration }
AGENT_TOOL_ERROR      // { workflowId, agentId, tool, error }
AGENT_COMPLETED       // { workflowId, agentId, output, tokens }

// HITL
HITL_REQUIRED         // { workflowId, taskId, agentId, draft }
HITL_APPROVED         // { workflowId, taskId, approvedBy }
HITL_REJECTED         // { workflowId, taskId, reason }

// System
TASK_PROGRESS         // { workflowId, taskId, progress }
METRICS_UPDATE        // { workflowId, tokenCost, duration }
ERROR_OCCURRED        // { workflowId, severity, message }
```

### 4.4 Event Schema & Validation

Every event MUST conform to a strict envelope:

```typescript
interface RuntimeEvent<T = unknown> {
  id: string;           // uuid
  type: EventType;
  timestamp: string;    // ISO 8601
  workflowId: string;
  correlationId: string; // trace across frontend → api → worker → runtime
  source: EventSource;   // 'runtime' | 'worker' | 'api' | 'system'
  data: T;
  version: number;       // schema version for forward compatibility
}
```

### 4.5 SSE Connection Lifecycle

```
Client connects  →  GET /api/workflow/stream/{workflowId}
                       │
                  ┌────▼────┐
                  │  API    │
                  │  creates│
                  │  Redis  │
                  │  sub    │
                  └────┬────┘
                       │
                  Subscribe to:
                  crew:workflow:{workflowId}:*
                       │
                  ┌────▼────┐
                  │  Events │
                  │  stream │
                  │  to SSE │
                  └─────────┘
```

**Key properties:**
- One SSE connection per workflow view
- Reconnection with `Last-Event-Id` for replay safety
- `correlationId` enables frontend to deduplicate events
- API subscribes/unsubscribes Redis channels per connection lifecycle

---

## 5. Execution Lifecycle & State Machines

### 5.1 Hierarchical State Machine

The spec's flat 5-state model is replaced with a **hierarchical state machine**:

```
                    ┌──────────────────────────────────┐
                    │        WORKFLOW STATE            │
                    │  (Top-Level Finite State Machine)│
                    └──────────────────────────────────┘

  PENDING ──► RUNNING ──► SUSPENDED ──► RUNNING ──► SUCCESS
                │            │            │
                ▼            ▼            ▼
              FAILED     CANCELLED     FAILED

    RUNNING ── contains ──► AGENT SUB-STATE MACHINE
    SUSPENDED ── contains ──► CHECKPOINT SNAPSHOT
```

### 5.2 Workflow State Machine

```typescript
type WorkflowStatus =
  | 'PENDING'           // Created, not yet started
  | 'QUEUED'            // In Celery queue
  | 'RUNNING'           // Active execution
  | 'SUSPENDED'         // Paused (has valid checkpoint)
  | 'AWAITING_APPROVAL' // HITL block
  | 'FAILED'            // Unrecoverable failure
  | 'CANCELLED'         // User-cancelled
  | 'SUCCESS';          // Completed successfully
```

### 5.3 Agent Sub-State Machine (within RUNNING)

Each agent within a running workflow has a sub-state machine:

```typescript
type AgentExecutionStatus =
  | 'IDLE'              // Waiting to start
  | 'THINKING'          # [Thought] internal reasoning
  | 'ACTING'            # [Action] selected tool/action
  | 'TOOL_CALLING'      # [Tool] executing external tool
  | 'OBSERVING'         # [Observation] processing tool result
  | 'AWAITING_HITL'     # [Waiting-human] paused for approval
  | 'COMPLETED'         # Agent task finished
  | 'FAILED';           # Agent task failed
```

### 5.4 Checkpoint Lifecycle

Checkpoints enable pause/resume/replay:

```
Execution Step ──► Pre-Agent Checkpoint
                      │
                      ▼
                 Agent Execute
                      │
                      ▼
                 Post-Agent Checkpoint
                      │
             ┌────────┴────────┐
             ▼                  ▼
        Next Agent         SUSPENDED
                             │
                        Restore from
                        last checkpoint
                             │
                             ▼
                        RUNNING
```

**Checkpoint data:**
```typescript
interface ExecutionCheckpoint {
  id: string;
  workflowId: string;
  step: number;                    // sequential step counter
  agentStates: Map<string, AgentState>; // current agent progress
  completedTasks: string[];        // finished task IDs
  pendingTasks: string[];          // unstarted task IDs
  context: Record<string, unknown>; // shared workflow context
  memorySnapshots: MemorySnapshot;  // current memory state
  timestamp: string;
}
```

### 5.5 Replay Lifecycle

```
User clicks Replay ──► Fetch execution history
                            │
                      ┌─────▼─────┐
                      │  Replay   │
                      │  Engine   │
                      └─────┬─────┘
                            │
                      Re-execute from step N
                      with original event log
                      for replay fidelity
                            │
                      ┌─────▼─────┐
                      │  Compare  │
                      │  outputs  │
                      └─────┬─────┘
                            │
                      Show diff in terminal
```

---

## 6. Multi-Agent Orchestration Architecture

### 6.1 Runtime Abstraction Layer

The [`CrewRuntime`](packages/crew-runtime/src/runtime.ts) is the central abstraction that wraps CrewAI execution:

```
┌──────────────────────────────────────────────────┐
│                  CrewRuntime                       │
├──────────────────────────────────────────────────┤
│ + construct(config: CrewConfig): Crew             │
│ + execute(crew: Crew, context: Context): AsyncGen │
│ + pause(workflowId: string): Checkpoint            │
│ + resume(workflowId: string, cp: Checkpoint): void │
│ + kill(workflowId: string): void                   │
├──────────────────────────────────────────────────┤
│ Internal components:                               │
│ - CrewBuilder        (dynamic crew construction)   │
│ - ToolRegistry       (tool binding/injection)      │
│ - MemoryAttacher     (memory bus configuration)    │
│ - CallbackInterceptor (event capture)              │
│ - CheckpointManager  (state persistence)           │
│ - EventEmitter       (Redis Pub/Sub publishing)    │
└──────────────────────────────────────────────────┘
```

### 6.2 Dynamic Crew Construction

```python
# apps/worker/src/runtime/crew_builder.py

class CrewBuilder:
    """
    Constructs CrewAI crews dynamically from workflow config.
    
    - Binds agents with their LLM config, tools, memory
    - Creates task chain from workflow graph
    - Injects callback interceptor
    - Returns ready-to-execute Crew instance
    """
    
    def build(self, config: WorkflowConfig) -> Crew:
        agents = [self._build_agent(a) for a in config.agents]
        tasks = self._build_tasks(config.tasks, agents)
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=config.process_type,  # sequential / hierarchical
            verbose=False,  # we handle observability ourselves
            callbacks=[CallbackInterceptor(config.workflow_id)],
        )
        return crew
```

### 6.3 Callback Interceptor

```python
# packages/crew-runtime/src/callbacks/interceptor.py

class CallbackInterceptor:
    """
    Intercepts all CrewAI execution callbacks and translates
    them to typed system events published via Redis Pub/Sub.
    
    Captures:
    - agent.start / agent.end
    - task.start / task.end
    - tool.use / tool.result
    - llm.call / llm.response (token tracking)
    - error events
    """
    
    def on_agent_start(self, agent, task):
        self.emit(AgentStartedEvent(...))
    
    def on_agent_action(self, agent, action):
        self.emit(AgentThinkingEvent(...) or AgentActionEvent(...))
    
    def on_tool_use(self, agent, tool, input, output):
        self.emit(ToolCalledEvent(...))
        self._track_tokens(agent, output)
    
    def on_agent_end(self, agent, output):
        self.emit(AgentCompletedEvent(...))
        self.checkpoint_manager.save(agent, output)
```

### 6.4 HITL Integration Flow

```
                    ┌──────────┐
                    │  Agent   │
                    │  reaches │
                    │  HITL    │
                    │  task    │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │  Emit    │
                    │  HITL    │
                    │  Event   │
                    └────┬─────┘
                         │
              ┌──────────▼──────────┐
              │  Worker Suspends    │
              │  + Checkpoints      │
              │  + Updates Status   │
              │  to AWAITING_APPROVAL│
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  API → SSE Update   │
              │  Frontend Shows     │
              │  Approval Inbox     │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  User Approves/     │
              │  Edits/Rejects      │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  API Publishes      │
              │  HITL_DECISION      │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  Worker Consumes    │
              │  Restores Checkpoint│
              │  Resumes Agent      │
              │  with human input   │
              └──────────┬──────────┘
                         │
                    ┌────▼─────┐
                    │  Agent   │
                    │  Continues│
                    └──────────┘
```

---

## 7. Observability Architecture

### 7.1 Data Pipeline

```
Runtime (CrewAI) ──► CallbackInterceptor
                            │
                    Event Translator
                    (CrewAI → Typed Event)
                            │
                    ┌───────▼───────┐
                    │  Redis Pub/Sub│
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
          ┌───▼───┐   ┌────▼────┐   ┌───▼───┐
          │  SSE  │   │ Metrics │   │  Log  │
          │  Fan- │   │ Store   │   │ Store │
          │  Out  │   │(Postgres)│   │(Postgres)│
          └───┬───┘   └────┬────┘   └───┬───┘
              │             │             │
          ┌───▼───┐   ┌────▼────┐   ┌───▼───┐
          │Terminal│   │ DB      │   │ Query │
          │ UI     │   │ Queries │   │ API   │
          └───────┘   └─────────┘   └───────┘
```

### 7.2 Log Storage Schema

```sql
-- apps/api/src/db/migrations/versions/001_create_logs.py

CREATE TABLE execution_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     UUID NOT NULL REFERENCES workflows(id),
    correlation_id  UUID NOT NULL,  -- trace ID
    event_type      VARCHAR(50) NOT NULL,  -- AGENT_THOUGHT, TOOL_CALL, etc.
    agent_id        UUID REFERENCES agents(id),
    task_id         UUID REFERENCES tasks(id),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload         JSONB NOT NULL,  -- event-specific data
    level           VARCHAR(10) NOT NULL DEFAULT 'INFO',  -- INFO, WARN, ERROR
    
    -- indexes for common query patterns
    INDEX idx_logs_workflow_time (workflow_id, timestamp),
    INDEX idx_logs_event_type (event_type),
    INDEX idx_logs_agent (agent_id),
    INDEX idx_logs_correlation (correlation_id)
);

-- Partition by month for performance at scale
PARTITION BY RANGE (timestamp);
```

### 7.3 Metrics Pipeline

Metrics are **computed at write time** (not query time) for dashboard performance:

```python
# apps/worker/src/events/metrics_processor.py

class MetricsProcessor:
    """
    Consumes runtime events and maintains aggregated metrics.
    
    Updates:
    - TokenUsage: per-agent, per-task, per-workflow running totals
    - StepDuration: execution timing for Gantt chart
    - FailureCount: per-agent, per-task error tracking
    - CostProjection: running cost estimate
    """
    
    TABLE token_metrics (
        workflow_id UUID,
        agent_id UUID,
        task_id UUID,
        step INT,
        input_tokens INT,
        output_tokens INT,
        total_tokens INT,
        estimated_cost DECIMAL(10,6),
        duration_ms INT,
        timestamp TIMESTAMPTZ
    );
```

### 7.4 SSE Event Stream

Each SSE event follows a strict format for client-side parsing:

```
event: AGENT_THOUGHT
id: evt_abc123
data: {"workflowId":"wf_1","agentId":"agent_2","thought":"I need to search the database...","timestamp":"2026-05-23T10:30:00Z","correlationId":"corr_456"}

event: AGENT_TOOL_CALL
id: evt_abc124
data: {"workflowId":"wf_1","agentId":"agent_2","tool":"sql_query","input":"SELECT * FROM users","output":"[results...]","duration":1200,"timestamp":"2026-05-23T10:30:01Z"}
```

---

## 8. Memory Architecture

### 8.1 Three-Tier Memory System

```
┌──────────────────────────────────────────────────┐
│                  MemoryBridge                      │
│  (Unified interface for all memory operations)    │
├──────────────────────────────────────────────────┤
│                                                    │
│   ┌──────────────┐   ┌────────────┐   ┌────────┐ │
│   │ Short-Term   │   │ Long-Term  │   │ Entity │ │
│   │ (Redis)      │   │ (PGVector) │   │ (JSONB)│ │
│   │              │   │            │   │        │ │
│   │ TTL: 1 hour  │   │ Persistent │   │Persist.│ │
│   │ Session-only │   │ Semantic   │   │Structured│ │
│   │ Key-value    │   │ Embeddings │   │Relations│ │
│   └──────────────┘   └────────────┘   └────────┘ │
│                                                    │
└──────────────────────────────────────────────────┘
```

### 8.2 Memory Operations Interface

```python
# packages/crew-runtime/src/memory/memory_bridge.py

class MemoryBridge:
    """
    Unified memory interface with routing logic.
    """
    
    async def store(
        self,
        workflow_id: str,
        agent_id: str,
        memory_type: MemoryType,  # SHORT_TERM | LONG_TERM | ENTITY
        key: str,
        value: Any,
        metadata: dict = None
    ) -> None
    
    async def query(
        self,
        workflow_id: str,
        agent_id: str,
        memory_type: MemoryType,
        query: str,
        limit: int = 10,
        threshold: float = 0.7
    ) -> list[MemoryItem]
    
    async def clear(
        self,
        workflow_id: str,
        agent_id: str = None,
        memory_type: MemoryType = None
    ) -> None
    
    async def snapshot(
        self,
        workflow_id: str
    ) -> MemorySnapshot
    
    async def restore(
        self,
        workflow_id: str,
        snapshot: MemorySnapshot
    ) -> None
```

### 8.3 Storage Backends

#### Short-Term (Redis)
```python
# Namespace: crew:{workflow_id}:agent:{agent_id}:short_term
# TTL: 3600 seconds
# Data: JSON-serialized conversation context
```

#### Long-Term (PGVector)
```python
# Table: agent_memories
# Columns: id, workflow_id, agent_id, embedding vector(1536), 
#          content TEXT, metadata JSONB, created_at
# Index: IVFFlat or HNSW on embedding
# Query: cosine similarity search
```

#### Entity Memory (JSONB)
```python
# Table: entity_memories
# Columns: id, workflow_id, agent_id, entity_name, 
#          attributes JSONB, relations JSONB, created_at, updated_at
# Index: GIN on attributes, GIN on relations
```

### 8.4 Memory Namespacing

All memory operations MUST include workflow isolation:

```
crew:{workflow_id}:agent:{agent_id}:memory:{type}:{key}
```

This ensures:
- Memory isolation between workflows
- Bulk cleanup per workflow
- Agent-specific memory scoping

---

## 9. Frontend Architecture

### 9.1 Component Tree

```
<App>
  <ResizablePanelGroup>
    <LeftSidebar>
      <SidebarTabs>  <!-- Agents | Tasks | Tools | Templates -->
        <AgentPalette />     <!-- Draggable agent templates -->
        <TaskPalette />      <!-- Draggable task templates -->
        <ToolPalette />      <!-- Draggable tool templates -->
        <TemplateLibrary />  <!-- Saved workflow templates -->
      </SidebarTabs>
    </LeftSidebar>
    
    <MainArea>
      <ExecutionToolbar />   <!-- Run/Pause/Resume/Stop/Retry/Replay -->
      <WorkflowCanvas>       <!-- React Flow -->
        <AgentNode />
        <TaskNode />
        <ToolNode />
        <CustomEdge />
        <MiniMap />
        <Controls />
      </WorkflowCanvas>
      <YAMLEditor />         <!-- Monaco Editor, collapsible -->
    </MainArea>
    
    <RightInspector>         <!-- Dynamic based on selection -->
      <AgentInspector />
      <TaskInspector />
      <ToolInspector />
    </RightInspector>
  </ResizablePanelGroup>
  
  <BottomPanel>
    <ObservabilityTerminal />  <!-- SSE-connected log viewer -->
    <MetricsDashboard>         <!-- Recharts tabs -->
      <TokenCostChart />
      <GanttTimeline />
      <FailureHeatmap />
    </MetricsDashboard>
  </BottomPanel>
  
  <HITLDialog />              <!-- Modal overlay for approvals -->
</App>
```

### 9.2 Zustand Store Architecture

The stores are **domain-separated** to prevent god stores:

```typescript
// apps/web/src/store/

// Canvas Store — workflow graph state
interface CanvasStore {
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  viewport: Viewport;
  
  // Actions
  addNode: (type: NodeType, position: XYPosition) => void;
  removeNode: (id: string) => void;
  connectNodes: (source: string, target: string) => void;
  updateNodeConfig: (id: string, config: Partial<NodeConfig>) => void;
  applyLayout: (mode: 'hierarchy' | 'sequential') => void;
}

// Execution Store — workflow runtime state
interface ExecutionStore {
  workflowStatus: WorkflowStatus;
  agentStates: Map<string, AgentExecutionStatus>;
  progress: number;  // 0-100
  activeExecutionId: string | null;
  
  // Actions
  runWorkflow: () => Promise<void>;
  pauseWorkflow: () => Promise<void>;
  resumeWorkflow: () => Promise<void>;
  stopWorkflow: () => Promise<void>;
}

// Terminal Store — observability stream
interface TerminalStore {
  entries: LogEntry[];
  filter: { agentId?: string; level?: string };
  isPaused: boolean;
  
  // Actions
  appendEntry: (entry: LogEntry) => void;
  setFilter: (filter: TerminalFilter) => void;
  clear: () => void;
  exportLogs: () => string;
}

// HITL Store — approval management
interface HITLStore {
  pendingApprovals: ApprovalRequest[];
  activeApproval: ApprovalRequest | null;
  
  // Actions
  approve: (id: string, edits?: string) => Promise<void>;
  reject: (id: string, reason: string) => Promise<void>;
  regenerate: (id: string) => Promise<void>;
}
```

### 9.3 YAML↔Store Sync Engine

The sync engine uses a **three-phase model** with the Zustand store as canonical source of truth:

```
Phase 1: UI Change → Store
  User interacts with canvas/inspector
  → Store updates (canonical state)
  → Sync Engine schedules debounced YAML write

Phase 2: YAML Paste → Store
  User pastes YAML in Monaco editor
  → Zod validation
  → On success: Store replaces graph state
  → Canvas re-renders from store
  → On failure: Show validation errors in editor

Phase 3: Conflict Resolution
  If both UI and YAML change simultaneously:
  → Last-write-wins with version counter
  → Version mismatch triggers notification
  → User chooses which version to keep
```

```typescript
// apps/web/src/lib/sync/sync-engine.ts

class SyncEngine {
  private store: ZustandStore;
  private version: number = 0;
  private debounceTimer: NodeJS.Timeout | null = null;
  
  // Called by store subscribers
  onUIChange(change: GraphChange): void {
    this.version++;
    this.scheduleYAMLSync();
  }
  
  // Called by Monaco editor
  onYAMLChange(yaml: string): ValidationResult {
    const parsed = this.validate(yaml);
    if (!parsed.success) return parsed;
    
    // Check version conflict
    if (parsed.version > this.version) {
      this.version = parsed.version;
      this.store.replaceGraph(parsed.graph);
    }
    return { success: true };
  }
  
  private scheduleYAMLSync(): void {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      const yaml = this.storeToYAML();
      this.updateEditor(yaml);
    }, 300);  // 300ms debounce
  }
}
```

### 9.4 SSE Client Manager

```typescript
// apps/web/src/lib/stream/sse-client.ts

class SSEClient {
  private connections: Map<string, EventSource> = new Map();
  private reconnectAttempts: Map<string, number> = new Map();
  private maxRetries = 5;
  private backoff = [1000, 2000, 4000, 8000, 16000];  // exponential
  
  connect(workflowId: string, handlers: EventHandlers): void {
    const url = `/api/workflow/stream/${workflowId}`;
    const source = new EventSource(url);
    
    source.addEventListener('message', (event) => {
      const parsed = JSON.parse(event.data);
      handlers.onEvent(parsed);
      this.updateLastEventId(workflowId, event.lastEventId);
    });
    
    source.onerror = () => {
      this.reconnect(workflowId, handlers);
    };
    
    this.connections.set(workflowId, source);
  }
  
  private reconnect(workflowId: string, handlers: EventHandlers): void {
    const attempts = this.reconnectAttempts.get(workflowId) ?? 0;
    if (attempts >= this.maxRetries) return;
    
    const delay = this.backoff[attempts];
    setTimeout(() => {
      this.connect(workflowId, handlers);
    }, delay);
    
    this.reconnectAttempts.set(workflowId, attempts + 1);
  }
  
  disconnect(workflowId: string): void {
    this.connections.get(workflowId)?.close();
    this.connections.delete(workflowId);
    this.reconnectAttempts.delete(workflowId);
  }
}
```

---

## 10. Infrastructure Architecture

### 10.1 Docker Compose Topology

```yaml
# docker-compose.yml

services:
  web:         # Next.js (port 3000)
  api:         # FastAPI (port 8000)
  worker:      # Celery worker
  redis:       # Redis (pub/sub + Celery broker + short-term memory)
  postgres:    # PostgreSQL (primary DB + PGVector)
  ollama:      # Local LLM inference
```

### 10.2 Service Dependencies

```
web → api
api → postgres, redis
worker → redis, postgres, ollama
```

### 10.3 Celery Configuration

```python
# apps/worker/src/config.py

CELERY_CONFIG = {
    'broker_url': 'redis://redis:6379/0',      # Celery broker
    'result_backend': 'redis://redis:6379/1',   # Celery results
    'task_queues': {
        'workflow_queue': {                     # Primary execution queue
            'exchange': 'workflows',
            'routing_key': 'workflow.execute',
        },
        'hitl_queue': {                         # HITL response queue
            'exchange': 'hitl',
            'routing_key': 'hitl.decision',
        },
    },
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'task_track_started': True,
    'task_acks_late': True,                     # At-least-once delivery
    'worker_prefetch_multiplier': 1,            # One task at a time per worker
    'result_expires': 86400,                    # Results TTL: 24h
}
```

### 10.4 Redis Namespace Plan

```redis
# Redis Namespace Layout
# 
# DB 0: Celery broker
# DB 1: Celery results
# DB 2: Short-term memory
# DB 3: Event pub/sub
# DB 4: Rate limiting
# DB 5: Session store

# Events (DB 3)
PUB/SUB channels:
  crew:workflow:{workflow_id}:events    # Workflow-specific events
  crew:system:alerts                     # System-wide alerts
  crew:system:health                     # Health check events

# Rate limiting (DB 4)
  ratelimit:{provider}:{agent_id}       # LLM provider rate limits
  ratelimit:api:{user_id}               # API rate limits
```

### 10.5 Scaling Strategy

| Component | Scale Strategy | Trigger |
|-----------|---------------|---------|
| API Server | Horizontal (load balancer) | CPU > 70% |
| Celery Worker | Horizontal (multiple containers) | Queue depth > 100 |
| Redis | Vertical (memory) or Cluster mode | Memory > 80% |
| PostgreSQL | Connection pooling + read replicas | Connections > 100 |
| PGVector | Index optimization (HNSW) | Query latency > 500ms |

---

## 11. Data Flow Diagrams

### 11.1 Run Workflow

```
User: Clicks "Run" in toolbar
  │
  ▼
Frontend: ExecutionStore.runWorkflow()
  │ POST /workflow/run
  ▼
API: workflow_service.run(config)
  │ 1. Validate workflow config (Zod)
  │ 2. Create execution record (DB)
  │ 3. Enqueue Celery task
  │ 4. Return execution ID
  ▼
Worker: run_crew.delay(execution_id, config)
  │
  ▼
Worker: CrewRuntime.execute()
  │ 1. CrewBuilder constructs Crew dynamically
  │ 2. Crew.kickoff() starts execution
  │ 3. CallbackInterceptor captures every event
  │    → Publishes to Redis Pub/Sub
  ▼
Redist: PUBLISH crew:workflow:{id}:events
  │
  ▼
API: Event consumer receives → SSE push
  │
  ▼
Frontend: SSEClient receives events
  │ 1. TerminalStore.appendEntry() → Terminal renders
  │ 2. ExecutionStore updates status/progress
  │ 3. Canvas nodes update status glow
```

### 11.2 Pause/Resume Workflow

```
User: Clicks "Pause"
  │ POST /workflow/pause
  ▼
API: 1. Update execution status → SUSPENDED
     2. Publish PAUSE command to Redis
  ▼
Worker: 1. Receives PAUSE command
        2. CheckpointManager.save() → DB
        3. Crew.kill() terminates current step
        4. Publishes WORKFLOW_PAUSED event
  ▼
Frontend: Status = SUSPENDED, checkpoint available

User: Clicks "Resume"
  │ POST /workflow/resume
  ▼
API: 1. Load checkpoint from DB
     2. Enqueue resume task
  ▼
Worker: 1. CrewRuntime.resume(checkpoint)
        2. Restores agent/task/context state
        3. Continues execution from checkpoint
```

### 11.3 YAML Sync

```
User edits YAML in Monaco
  │
  ▼
SyncEngine.onYAMLChange(yaml)
  │ 1. Parse YAML → JSON
  │ 2. Validate with Zod schema
  │ 3. Check version conflict
  │ 4. On success:
  │    a. Store.replaceGraph(parsed.graph)
  │    b. Canvas re-renders
  │    c. version++
  │ 5. On failure:
  │    a. Highlight errors in Monaco
  │    b. NO store change

User drags node on canvas
  │
  ▼
Store.addNode(type, position)
  │ version++
  │
  ▼
SyncEngine.scheduleYAMLSync()
  │ 300ms debounce
  ▼
SyncEngine.storeToYAML()
  │ 1. Serialize store.graph → YAML
  │ 2. Update Monaco editor content
```

---

## 12. Missing Enterprise Systems

The following systems are **not specified** in the spec but are **required** for production readiness:

### 12.1 Secret Management
```typescript
// infra/secrets/
// 
// Required secrets:
// - LLM_API_KEYS (OpenAI, Anthropic, Google)
// - DATABASE_URL
// - REDIS_URL
// - JWT_SECRET
// - ENCRYPTION_KEY
//
// Must NOT be in docker-compose.yml
// Use: Docker secrets, .env.secret (gitignored), or HashiCorp Vault
```

### 12.2 Audit Logging
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,    -- workflow.run, agent.update, etc.
    resource_type VARCHAR(50),
    resource_id UUID,
    before_state JSONB,
    after_state JSONB,
    ip_address INET,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 12.3 Rate Limiting & Circuit Breaking
```python
# apps/api/src/middleware/rate_limiter.py

class LLMCircuitBreaker:
    """
    Tracks LLM provider failures.
    After N consecutive failures in window T:
    → Open circuit (block requests)
    → Half-open after cooldown
    → Close on successful probe
    """
    
    states: { CLOSED, HALF_OPEN, OPEN }
    failure_threshold: 5
    cooldown_seconds: 60
```

### 12.4 Workflow Versioning
```sql
ALTER TABLE workflows ADD COLUMN version INT DEFAULT 1;
CREATE TABLE workflow_versions (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    version INT NOT NULL,
    config JSONB NOT NULL,         -- full workflow config at that version
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workflow_id, version)
);
```

### 12.5 Multi-Tenancy (Future)
```sql
ALTER TABLE workflows ADD COLUMN project_id UUID;
ALTER TABLE agents ADD COLUMN project_id UUID;

CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    created_at TIMESTAMPTZ
);
```

### 12.6 Health Check Endpoints
```
GET /health         → Simple liveness
GET /ready          → Readiness (DB, Redis, Celery worker)
GET /metrics        → Prometheus metrics endpoint
GET /health/llm     → LLM provider connectivity
```

### 12.7 Backup & Restore
```bash
# infra/scripts/backup.sh
# - pg_dump for PostgreSQL
# - Redis RDB snapshot
# - Workflow version archive
# - S3/GCS sync for offsite
```

---

## 13. Implementation Roadmap

The spec's 7-phase build order is **insufficiently defensive**. The correct order must account for architectural foundations first.

```
Phase 0: Architectural Foundation (Week 1)
├── Monorepo scaffold (TurboRepo)
├── packages/shared-types (events, schemas, constants)
├── packages/ui foundation (Button, Card, Layout primitives)
├── Docker Compose skeleton (all services, no business logic)
└── CI/CD pipeline (lint, type-check, test)

Phase 1: Data & Auth Layer (Week 2)
├── PostgreSQL schema + Alembic migrations
├── SQLAlchemy models + repositories
├── JWT auth + RBAC middleware
├── Redis connection management
├── API health endpoints
└── Secret management

Phase 2: Core Frontend Shell (Week 3)
├── IDE layout (resizable panels)
├── Left sidebar with tabs
├── React Flow canvas (empty graph)
├── Right inspector panel (dynamic routing)
├── Bottom panel shell (tabs: terminal/metrics)
├── Zustand store foundation (canvas, UI state)
└── ExecutionToolbar (buttons only, no logic)

Phase 3: YAML ↔ Canvas Sync (Week 4)
├── Zod schemas for all workflow configs
├── YAML parser/generator (js-yaml)
├── SyncEngine (three-phase sync model)
├── Monaco editor integration
├── Canvas → YAML serialization
├── YAML → Canvas deserialization
└── Drag-drop palette → canvas

Phase 4: Inspector Forms (Week 5)
├── AgentInspector (persona, memory, LLM, tools)
├── TaskInspector (description, timeout, retries, HITL)
├── ToolInspector (config, permissions)
├── AI Enhancer button
└── Form validation + state persistence

Phase 5: CrewAI Runtime (Weeks 6-7)
├── packages/crew-runtime:
│   ├── CrewBuilder (dynamic construction)
│   ├── CallbackInterceptor (event capture)
│   ├── EventEmitter (Redis publish)
│   ├── CheckpointManager (save/restore)
│   ├── MemoryBridge (three-tier memory)
│   └── ToolRegistry (dynamic binding)
├── CrewRuntime integration tests
└── Memory subsystem implementation

Phase 6: Async Execution Engine (Week 8)
├── Celery configuration + task definitions
├── run_crew task
├── pause/resume/kill task handlers
├── Redis event → API relay
├── SSE endpoint + connection management
└── Execution state machine integration

Phase 7: Observability (Week 9)
├── SSE client manager (frontend)
├── ObservabilityTerminal component
│   ├── Real-time streaming
│   ├── Color-coded tags
│   ├── Filter by agent
│   ├── Search
│   ├── Pause scroll
│   └── Export logs
├── execution_logs table + ingestion
├── Metrics pipeline (compute at write time)
└── Token tracking integration

Phase 8: Execution Controls (Week 10)
├── Run/Pause/Resume/Stop/Retry wiring
├── Checkpoint save/restore (end-to-end)
├── Replay engine
│   ├── Original event log replay
│   ├── Side-by-side diff (original vs replay)
│   └── Replay checkpointing
├── Rollback snapshot
└── Execution history page

Phase 9: Human-in-the-Loop (Week 11)
├── HITL Celery queue
├── Approval inbox page
├── Approval detail view (draft vs edit)
├── Approve/reject/regenerate API
├── HITL resume workflow flow
└── HITL store + components

Phase 10: Metrics Dashboard (Week 12)
├── Token cost charts (per agent/task/workflow)
├── Execution timeline (Gantt chart)
├── Failure heatmap
├── Metrics aggregation queries
└── Dashboard page

Phase 11: Production Hardening (Week 13)
├── Audit logging
├── Rate limiting + circuit breaker
├── Error boundaries (React)
├── Retry logic (all layers)
├── Load testing
├── Performance optimization
│   ├── React Flow virtualization
│   ├── PGVector index tuning
│   └── Redis memory monitoring
├── Backup/restore scripts
└── Documentation

Phase 12: Polish & E2E Testing (Week 14)
├── Playwright E2E tests
├── Pytest integration tests
├── Vitest + RTL unit tests
├── Accessibility audit
├── Edge case hardening
└── Final QA pass
```

---

## 14. Scaling Considerations

### 14.1 Current Bottleneck: Single Celery Queue

**Problem**: All workflows go through `workflow_queue`. If one workflow has 10 agents with long LLM calls, it blocks others.

**Mitigation**: Implement **priority queues** and **per-workflow worker pools**:
```python
QUEUES = {
    'workflow_high': {'routing_key': 'workflow.priority.high'},
    'workflow_default': {'routing_key': 'workflow.priority.default'},
    'workflow_low': {'routing_key': 'workflow.priority.low'},
    'hitl': {'routing_key': 'hitl.decision'},
}
```

### 14.2 Future Bottleneck: SSE Connection Count

**Problem**: Each SSE connection holds a Redis subscriber and a long-lived HTTP connection.

**Mitigation**: At scale > 1000 concurrent connections:
- Replace SSE with **WebSocket** (bidirectional, lower overhead)
- Use **Redis Streams** (consumer groups) instead of Pub/Sub for event persistence
- Implement **connection multiplexing** (one connection per user, not per workflow)

### 14.3 Future Bottleneck: PGVector Performance

**Problem**: Long-term memory queries on large datasets (>1M vectors) will degrade.

**Mitigation**:
- Use **HNSW index** (not IVFFlat) for high-recall, high-QPS scenarios
- **Partition** memory table by workflow_id or date
- Implement **memory pruning** (remove low-relevance memories based on access frequency)
- Consider **separate vector database** (Qdrant, Pinecone) at scale

### 14.4 Future Bottleneck: Token Cost Tracking

**Problem**: Every LLM call must be intercepted and token usage recorded. At high throughput, this becomes a write bottleneck.

**Mitigation**:
- **Batch write** token metrics (flush every 5 seconds or 100 records)
- Use **Redis counter** for real-time token display (eventual consistency to DB)
- **Async insert** into token_metrics table (no impact on execution path)

---

## Appendix A: File Structure (Finalized)

```
/project-root
├── apps/
│   ├── web/
│   │   └── src/
│   │       ├── app/                    # Next.js App Router pages
│   │       ├── components/
│   │       │   ├── canvas/             # React Flow nodes, edges, controls
│   │       │   ├── inspector/          # Agent/Task/Tool inspectors
│   │       │   ├── terminal/           # Observability terminal
│   │       │   ├── metrics/            # Dashboard charts
│   │       │   ├── layout/             # Resizable panels, sidebar
│   │       │   ├── hitl/               # Approval components
│   │       │   └── shared/             # Reusable UI primitives
│   │       ├── store/                  # Zustand stores
│   │       ├── lib/
│   │       │   ├── sync/              # YAML↔Store sync engine
│   │       │   └── stream/            # SSE client manager
│   │       ├── services/               # API client layer
│   │       ├── hooks/                  # Custom hooks
│   │       └── types/                  # Frontend-specific types
│   │
│   ├── api/
│   │   └── src/
│   │       ├── api/
│   │       │   ├── routes/             # REST endpoints
│   │       │   └── ws/                 # SSE endpoint
│   │       ├── services/               # Business logic
│   │       ├── executors/              # Celery task definitions
│   │       ├── events/                 # Event publisher/consumer
│   │       ├── middleware/             # Auth, rate limiting
│   │       ├── db/
│   │       │   ├── models/             # SQLAlchemy models
│   │       │   ├── repositories/       # Data access layer
│   │       │   └── migrations/         # Alembic migrations
│   │       ├── models/                 # Pydantic domain models
│   │       └── schemas/                # Zod validation schemas
│   │
│   └── worker/
│       └── src/
│           ├── tasks/                  # Celery task handlers
│           ├── runtime/                # CrewAI runtime wrapper
│           ├── checkpoint/             # Checkpoint manager
│           └── events/                 # Event publisher
│
├── packages/
│   ├── shared-types/
│   │   └── src/
│   │       ├── types/                  # Domain types
│   │       ├── events/                 # Event type definitions
│   │       ├── schemas/               # Zod schemas
│   │       └── constants/              # Enums, state machines
│   │
│   ├── ui/
│   │   └── src/                        # Shared UI components
│   │
│   └── crew-runtime/
│       └── src/
│           ├── runtime.ts              # CrewRuntime class
│           ├── callbacks/              # Callback interceptor
│           ├── checkpoint/             # Checkpoint manager
│           ├── memory/                 # Memory bridge
│           └── events/                 # Runtime event emitters
│
├── infra/
│   ├── docker/                         # Docker configs
│   │   ├── web.Dockerfile
│   │   ├── api.Dockerfile
│   │   └── worker.Dockerfile
│   └── kubernetes/                     # Future k8s manifests
│
├── docs/                               # Architecture docs
├── docker-compose.yml
├── package.json                        # Root workspace
├── turbo.json                          # Turborepo config
└── tsconfig.base.json                  # Shared TS config
```

---

## Appendix B: State Machine Reference

### Workflow Top-Level
```
PENDING → QUEUED → RUNNING → SUCCESS
                      │
                      ├──→ SUSPENDED → RUNNING
                      │
                      ├──→ AWAITING_APPROVAL → RUNNING
                      │
                      └──→ FAILED
```

### Agent Sub-Level (within RUNNING)
```
IDLE → THINKING → ACTING → TOOL_CALLING → OBSERVING → COMPLETED
                      │          │              │
                      │          │              └──→ THINKING (loop)
                      │          │
                      │          └──→ AWAITING_HITL → THINKING
                      │
                      └──→ FAILED
```

---

*End of Architectural Analysis.*
