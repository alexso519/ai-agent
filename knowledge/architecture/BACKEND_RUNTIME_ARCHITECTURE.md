# CrewAI Enterprise Control Center — Backend Runtime Architecture

> **Document Type**: Principal Backend Architecture Specification  
> **Status**: Pre-Implementation Design  
> **Version**: 1.0  
> **Architecture Source**: [`ARCHITECTURAL_ANALYSIS.md`](ARCHITECTURAL_ANALYSIS.md), [`FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md)

---

## Table of Contents

1. [FastAPI Application Architecture](#1-fastapi-application-architecture)
2. [Service Boundaries & Domain Separation](#2-service-boundaries--domain-separation)
3. [Runtime Execution Architecture](#3-runtime-execution-architecture)
4. [CrewRuntime Abstraction Design](#4-crewruntime-abstraction-design)
5. [Celery Orchestration Model](#5-celery-orchestration-model)
6. [Redis Event Backbone](#6-redis-event-backbone)
7. [SSE Streaming Pipeline](#7-sse-streaming-pipeline)
8. [Workflow Execution Lifecycle](#8-workflow-execution-lifecycle)
9. [Execution State Machine](#9-execution-state-machine)
10. [Replay & Checkpoint Architecture](#10-replay--checkpoint-architecture)
11. [Event Schema System](#11-event-schema-system)
12. [Persistence Architecture](#12-persistence-architecture)
13. [PostgreSQL Schema Strategy](#13-postgresql-schema-strategy)
14. [Memory Subsystem Architecture](#14-memory-subsystem-architecture)
15. [Audit Logging Architecture](#15-audit-logging-architecture)
16. [Authentication & Authorization Architecture](#16-authentication--authorization-architecture)
17. [Infrastructure Topology](#17-infrastructure-topology)
18. [Backend Folder Structure](#18-backend-folder-structure)
19. [Shared Contract Strategy](#19-shared-contract-strategy)

---

## 1. FastAPI Application Architecture

### 1.1 Application Factory Pattern

The API server uses a **lifespan-managed application factory** that initializes all dependencies in a deterministic order. No global state. No hidden singletons.

[`apps/api/src/main.py`](apps/api/src/main.py)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .middleware.auth import AuthMiddleware
from .middleware.rate_limiter import RateLimitMiddleware
from .middleware.request_id import RequestIDMiddleware
from .events.engine import EventEngine
from .db.session import DatabaseSessionManager
from .services import ServiceRegistry

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Deterministic lifecycle for all backend services."""
    # === STARTUP (ordered by dependency) ===
    # 1. Database connection pool
    db = DatabaseSessionManager()
    await db.connect()
    app.state.db = db

    # 2. Redis connections (broker + pub/sub + cache)
    redis = await RedisEngine.initialize()
    app.state.redis = redis

    # 3. Event engine (Redis Pub/Sub subscriber)
    events = EventEngine(redis)
    await events.start()
    app.state.events = events

    # 4. Service registry
    app.state.services = ServiceRegistry(db, redis, events)

    # 5. Celery app reference (for task inspection)
    app.state.celery = create_celery_app()

    yield

    # === SHUTDOWN (reverse order) ===
    await events.stop()
    await redis.close()
    await db.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CrewAI Control Center API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware stack (outermost first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=env.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)      # Injects X-Request-ID
    app.add_middleware(AuthMiddleware)            # JWT validation
    app.add_middleware(RateLimitMiddleware)       # Token bucket per user

    # Router registration
    from .api.routes import router as api_router
    app.include_router(api_router, prefix="/api/v1")

    # Health endpoints (no auth)
    from .api.health import health_router
    app.include_router(health_router)

    return app
```

### 1.2 Middleware Stack

```
Request
  │
  ▼
┌──────────────────────────────────┐
│ RequestIDMiddleware               │  ← Injects unique X-Request-ID per request
│   - Generates UUID               │     Enables distributed tracing
│   - Adds to request.state        │
└──────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────┐
│ AuthMiddleware                    │  ← Validates JWT, extracts user context
│   - Extracts Bearer token        │     Skips on public routes (/health, /docs)
│   - Decodes JWT → user_id, roles │
│   - Sets request.state.user      │
└──────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────┐
│ RateLimitMiddleware               │  ← Token bucket per user_id
│   - Checks Redis counter         │     100 req/min per user (configurable)
│   - 429 on exhaustion            │
└──────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────┐
│ Route Handler                     │  ← Route processes the request
└──────────────────────────────────┘
  │
  ▼
Response
```

### 1.3 Dependency Injection Pattern

All route handlers use FastAPI's `Depends()` for explicit dependency injection. No global singletons. No hidden imports.

[`apps/api/src/api/dependencies.py`](apps/api/src/api/dependencies.py)

```python
from fastapi import Request, Depends, HTTPException
from ..services import ServiceRegistry
from ..models.user import UserContext

def get_services(request: Request) -> ServiceRegistry:
    """Inject service registry from app state."""
    return request.app.state.services

def get_current_user(request: Request) -> UserContext:
    """Inject authenticated user context from middleware."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def get_db_session(request: Request):
    """Inject database session with automatic rollback on error."""
    db = request.app.state.db
    session = db.session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

### 1.4 Error Handling Strategy

[`apps/api/src/middleware/error_handler.py`](apps/api/src/middleware/error_handler.py)

```python
class AppError(Exception):
    """Base application error with structured payload."""
    def __init__(self, code: str, message: str, status: int = 500, details: dict | None = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}

class WorkflowNotFoundError(AppError):
    def __init__(self, workflow_id: str):
        super().__init__(
            code="WORKFLOW_NOT_FOUND",
            message=f"Workflow {workflow_id} not found",
            status=404,
        )

class ExecutionStateConflictError(AppError):
    def __init__(self, execution_id: str, current: str, expected: str):
        super().__init__(
            code="EXECUTION_STATE_CONFLICT",
            message=f"Execution {execution_id} is in state {current}, expected {expected}",
            status=409,
        )
```

All unhandled exceptions are caught by a global `@app.exception_handler` that logs the error, assigns a correlation ID, and returns a structured error response.

---

## 2. Service Boundaries & Domain Separation

### 2.1 Service Layer Architecture

The API is organized into **domain services** with strict boundaries. Each service is a stateless Python class that accepts dependencies via constructor injection.

[`apps/api/src/services/__init__.py`](apps/api/src/services/__init__.py)

```python
class ServiceRegistry:
    """Registry of all domain services. Single point of dependency injection."""

    def __init__(self, db, redis, events):
        self.workflow = WorkflowService(db, events)
        self.execution = ExecutionService(db, redis, events)
        self.agent = AgentService(db)
        self.task = TaskService(db)
        self.tool = ToolService(db)
        self.approval = ApprovalService(db, events)
        self.metrics = MetricsService(db)
        self.memory = MemoryService(redis, db)
        self.template = TemplateService(db)
        self.auth = AuthService(db, redis)
        self.audit = AuditService(db)
```

### 2.2 Service Responsibility Matrix

| Service | Responsibility | Dependencies | Events Emitted |
|---------|---------------|--------------|----------------|
| [`WorkflowService`](apps/api/src/services/workflow_service.py) | CRUD, YAML config validation, version management | `db` | `WORKFLOW_CREATED`, `WORKFLOW_UPDATED` |
| [`ExecutionService`](apps/api/src/services/execution_service.py) | Run/pause/resume/kill/replay orchestration | `db`, `redis`, `events` | `EXECUTION_ENQUEUED` |
| [`AgentService`](apps/api/src/services/agent_service.py) | Agent CRUD, LLM config, tool binding | `db` | `AGENT_UPDATED` |
| [`TaskService`](apps/api/src/services/task_service.py) | Task CRUD, priority, timeout config | `db` | — |
| [`ToolService`](apps/api/src/services/tool_service.py) | Tool registration, permission management | `db` | — |
| [`ApprovalService`](apps/api/src/services/approval_service.py) | HITL request management, approval/rejection | `db`, `events` | `HITL_DECISION` |
| [`MetricsService`](apps/api/src/services/metrics_service.py) | Token metrics, execution timeline, failure analysis | `db` | — |
| [`MemoryService`](apps/api/src/services/memory_service.py) | Three-tier memory CRUD, snapshot/restore | `redis`, `db` | — |
| [`TemplateService`](apps/api/src/services/template_service.py) | Workflow template CRUD | `db` | — |
| [`AuthService`](apps/api/src/services/auth_service.py) | JWT issue/verify, RBAC enforcement | `db`, `redis` | — |
| [`AuditService`](apps/api/src/services/audit_service.py) | Append-only audit log writes | `db` | — |

### 2.3 Service Dependency Rules

```
┌──────────────────────────────────────────────────────────┐
│                    SERVICE DEPENDENCY FLOW                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Route Layer (api/routes/)                                │
│       │                                                    │
│       ▼                                                   │
│  Service Layer (services/)  ← injects db, redis, events   │
│       │                                                    │
│       ├──→ Repository Layer (db/repositories/)            │
│       │       │                                            │
│       │       └──→ SQLAlchemy Models (db/models/)         │
│       │                                                    │
│       └──→ Event Engine (events/)                         │
│               │                                            │
│               └──→ Redis Pub/Sub                          │
│                                                           │
│  STRICT RULES:                                            │
│  - Services NEVER import routes                           │
│  - Services NEVER call other services directly            │
│  - Cross-service communication via EventEngine ONLY       │
│  - Repositories NEVER access Redis or events              │
│  - Models NEVER contain business logic                    │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Runtime Execution Architecture

### 3.1 End-to-End Execution Flow

```
┌──────────┐     POST /workflow/run      ┌──────────┐
│ Frontend │ ──────────────────────────►  │   API    │
│ (Next.js)│                              │ (FastAPI)│
└──────────┘                              └────┬─────┘
     ▲                                         │
     │                                   1. Validate config
     │                                   2. Create execution record (DB)
     │                                   3. Enqueue Celery task
     │                                   4. Return execution_id
     │                                         │
     │                                         ▼
     │                                  ┌──────────────┐
     │                                  │   Celery      │
     │◄──── SSE Events ─────────────    │   Broker      │
     │                                  │   (Redis)     │
     │                                  └──────┬───────┘
     │                                         │
     │                                         ▼
     │                                  ┌──────────────┐
     │                                  │  Celery       │
     │                                  │  Worker       │
     │                                  │  (run_crew)  │
     │                                  └──────┬───────┘
     │                                         │
     │                                   1. CrewRuntime.construct()
     │                                   2. CrewRuntime.execute()
     │                                   3. CallbackInterceptor captures
     │                                       every step → Redis Pub/Sub
     │                                   4. CheckpointManager saves
     │                                       at each agent boundary
     │                                         │
     │                                         ▼
     │                                  ┌──────────────┐
     │◄──── SSE stream ───────────────  │  Redis       │
     │                                  │  Pub/Sub     │
     │                                  └──────────────┘
```

### 3.2 Runtime Layers (Worker Internal)

```
┌──────────────────────────────────────────────────────────┐
│                    Celery Worker Process                   │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Task Layer (tasks/)                                 │ │
│  │  - run_crew(task_id, execution_id, config)           │ │
│  │  - pause_crew(execution_id)                          │ │
│  │  - resume_crew(execution_id, checkpoint_id)          │ │
│  │  - kill_crew(execution_id)                           │ │
│  │  - replay_crew(execution_id, from_step)              │ │
│  └──────────────────────┬───────────────────────────────┘ │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │  Orchestration Layer (orchestrator/)                  │ │
│  │  - ExecutionOrchestrator: manages lifecycle           │ │
│  │  - EventPublisher: translates runtime events → Redis  │ │
│  │  - CheckpointOrchestrator: save/restore boundaries    │ │
│  │  - HITLController: blocks/resumes on human tasks      │ │
│  └──────────────────────┬───────────────────────────────┘ │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │  Runtime Layer (runtime/)                            │ │
│  │  - CrewRuntime: CrewAI wrapper class                 │ │
│  │  - CrewBuilder: dynamic crew construction            │ │
│  │  - CallbackInterceptor: event capture                │ │
│  │  - ToolRegistry: dynamic tool injection              │ │
│  │  - MemoryBridge: three-tier memory operations        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### 3.3 Worker Task Definitions

[`apps/worker/src/tasks/execution_tasks.py`](apps/worker/src/tasks/execution_tasks.py)

```python
from celery import shared_task
from ..orchestrator.execution_orchestrator import ExecutionOrchestrator

@shared_task(
    bind=True,
    name="workflow.execute",
    queue="workflow_default",
    acks_late=True,           # At-least-once delivery
    reject_on_worker_lost=True,
    task_track_started=True,
)
def run_crew(self, execution_id: str, workflow_config: dict):
    """Execute a crew workflow asynchronously."""
    orchestrator = ExecutionOrchestrator(execution_id)
    return orchestrator.run(workflow_config)


@shared_task(
    bind=True,
    name="workflow.control",
    queue="workflow_control",
    acks_late=True,
)
def control_crew(self, execution_id: str, command: str, payload: dict | None = None):
    """Handle pause, resume, kill, replay commands."""
    orchestrator = ExecutionOrchestrator(execution_id)
    return orchestrator.handle_command(command, payload)
```

---

## 4. CrewRuntime Abstraction Design

### 4.1 Core Interface

[`packages/crew-runtime/src/runtime.py`](packages/crew-runtime/src/runtime.py)

```python
class CrewRuntime:
    """
    Central abstraction wrapping CrewAI execution.

    Responsibilities:
    - Dynamic crew construction from config
    - Managed execution with lifecycle control
    - Event capture via callback interceptor
    - Checkpoint save/restore at agent boundaries
    - Memory bridge operations
    - Graceful pause/resume/kill

    Thread-safety: This class is NOT thread-safe. Each runtime instance
    must be used by exactly one execution at a time.
    """

    def __init__(
        self,
        execution_id: str,
        event_publisher: EventPublisher,
        checkpoint_manager: CheckpointManager,
        memory_bridge: MemoryBridge,
    ):
        self._execution_id = execution_id
        self._events = event_publisher
        self._checkpoints = checkpoint_manager
        self._memory = memory_bridge
        self._crew: Crew | None = None
        self._interceptor: CallbackInterceptor | None = None
        self._state: RuntimeState = RuntimeState.IDLE

    def construct(self, config: WorkflowConfig) -> Crew:
        """
        Phase 1: Build a CrewAI Crew from configuration.

        Steps:
        1. Build agents (with LLM, tools, memory config)
        2. Build tasks (with dependencies, HITL markers)
        3. Inject CallbackInterceptor
        4. Return ready-to-execute Crew
        """
        builder = CrewBuilder(config, self._events, self._memory)
        self._crew = builder.build()
        self._interceptor = builder.interceptor
        self._state = RuntimeState.CONSTRUCTED
        return self._crew

    async def execute(self, context: ExecutionContext) -> AsyncIterator[ExecutionEvent]:
        """
        Phase 2: Execute the constructed Crew.

        Yields typed execution events for the orchestrator to publish.
        Supports pause via asyncio.Event (self._pause_event).
        Supports cancellation via asyncio.Task cancellation.
        """
        self._state = RuntimeState.RUNNING
        self._events.publish(WorkflowStartedEvent(self._execution_id))

        try:
            # Pre-execution checkpoint
            await self._checkpoints.save_pre_execution(self._execution_id, context)

            # Execute through the CrewAI kickoff
            async for event in self._interceptor.watch(self._crew.kickoff_async()):
                if self._pause_event.is_set():
                    await self._checkpoints.save_pause(
                        self._execution_id, event.step
                    )
                    self._state = RuntimeState.PAUSED
                    yield WorkflowPausedEvent(self._execution_id)
                    return

                yield event

            # Post-execution checkpoint
            await self._checkpoints.save_post_execution(self._execution_id)
            self._state = RuntimeState.COMPLETED
            yield WorkflowCompletedEvent(self._execution_id)

        except CrewAIExecutionError as e:
            self._state = RuntimeState.FAILED
            await self._checkpoints.save_failure(self._execution_id, e)
            yield WorkflowFailedEvent(self._execution_id, error=str(e))
        except asyncio.CancelledError:
            self._state = RuntimeState.CANCELLED
            yield WorkflowCancelledEvent(self._execution_id)

    def pause(self) -> None:
        """Signal the runtime to pause at the next safe boundary."""
        self._pause_event.set()

    def resume(self, checkpoint: ExecutionCheckpoint) -> None:
        """
        Phase 3: Resume from a saved checkpoint.

        Restores:
        - Agent execution states
        - Task completion status
        - Shared workflow context
        - Memory snapshots
        """
        self._checkpoints.restore(self._execution_id, checkpoint)
        self._state = RuntimeState.RUNNING
        self._pause_event.clear()

    def kill(self) -> None:
        """Immediately terminate execution."""
        self._state = RuntimeState.CANCELLED
        # CrewAI doesn't natively support cancellation;
        # we cancel the running asyncio task
```

### 4.2 CrewBuilder

[`packages/crew-runtime/src/builder.py`](packages/crew-runtime/src/builder.py)

```python
class CrewBuilder:
    """
    Dynamically constructs CrewAI crews from saved workflow config.

    Key design decisions:
    - Agents are constructed with the LLM config stored in the workflow
    - Tools are resolved from the ToolRegistry by name
    - Tasks are ordered by their dependency graph (topological sort)
    - CallbackInterceptor is injected as the sole CrewAI callback
    - Memory is configured per-agent based on workflow memory settings
    - verbose=False because we handle all observability ourselves
    """

    def __init__(self, config: WorkflowConfig, events: EventPublisher, memory: MemoryBridge):
        self._config = config
        self._events = events
        self._memory = memory
        self.interceptor = CallbackInterceptor(config.execution_id, events)

    def build(self) -> Crew:
        agents = [self._build_agent(a) for a in self._config.agents]
        tasks = self._build_tasks(self._config.tasks, agents)
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=self._config.process_type,  # sequential | hierarchical
            verbose=False,
            callbacks=[self.interceptor],
        )
        return crew

    def _build_agent(self, agent_config: AgentConfig) -> Agent:
        llm = self._resolve_llm(agent_config.llm)
        tools = [self._resolve_tool(t) for t in agent_config.tools]
        memory = self._configure_memory(agent_config.memory) if agent_config.memory else None
        return Agent(
            role=agent_config.role,
            goal=agent_config.goal,
            backstory=agent_config.backstory,
            llm=llm,
            tools=tools,
            memory=memory,
            allow_delegation=agent_config.allow_delegation,
            max_iter=agent_config.max_iterations,
            max_rpm=agent_config.rpm_limit,
        )

    def _resolve_llm(self, llm_config: LLMConfig) -> BaseLLM:
        """Resolve LLM provider from config. Supports OpenAI, Anthropic, Ollama, etc."""
        provider = LLM_PROVIDER_REGISTRY[llm_config.provider]
        return provider(
            model=llm_config.model,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            api_key=self._get_api_key(llm_config.provider),
            base_url=llm_config.base_url,  # For Ollama/local endpoints
        )
```

### 4.3 CallbackInterceptor

[`packages/crew-runtime/src/interceptor.py`](packages/crew-runtime/src/interceptor.py)

```python
class CallbackInterceptor:
    """
    Intercepts all CrewAI execution callbacks and translates them
    to typed system events published via Redis Pub/Sub.

    This is the critical bridge between CrewAI's internal execution
    and the observability pipeline.

    Captured events:
    - agent.start / agent.end
    - task.start / task.end / task.progress
    - tool.start / tool.end / tool.error
    - llm.call / llm.response (token tracking)
    - step.start / step.end
    - error events
    """

    def __init__(self, execution_id: str, publisher: EventPublisher):
        self._execution_id = execution_id
        self._publisher = publisher
        self._step_counter = 0
        self._token_tracker = TokenTracker()

    # CrewAI callback interface methods:

    def on_agent_start(self, agent: Agent, task: Task) -> None:
        self._step_counter += 1
        self._publisher.publish(RuntimeEvent(
            type=EventType.AGENT_STARTED,
            execution_id=self._execution_id,
            step=self._step_counter,
            data=AgentStartedData(
                agent_id=agent.id,
                agent_role=agent.role,
                task_id=task.id,
                task_title=task.description[:100],
            ),
        ))

    def on_agent_action(self, agent: Agent, action: Action) -> None:
        self._publisher.publish(RuntimeEvent(
            type=EventType.AGENT_THOUGHT,
            execution_id=self._execution_id,
            step=self._step_counter,
            data=AgentThoughtData(
                agent_id=agent.id,
                thought=action.thought,
                action=action.tool,
                action_input=action.tool_input,
            ),
        ))

    def on_tool_start(self, agent: Agent, tool: Tool, input_data: dict) -> None:
        self._publisher.publish(RuntimeEvent(
            type=EventType.TOOL_CALLING,
            execution_id=self._execution_id,
            step=self._step_counter,
            data=ToolCallData(
                agent_id=agent.id,
                tool_name=tool.name,
                tool_input=input_data,
                timestamp=datetime.utcnow().isoformat(),
            ),
        ))

    def on_tool_end(self, agent: Agent, tool: Tool, output: Any, duration_ms: int) -> None:
        self._token_tracker.track_tool(tool, output)
        self._publisher.publish(RuntimeEvent(
            type=EventType.TOOL_RESULT,
            execution_id=self._execution_id,
            step=self._step_counter,
            data=ToolResultData(
                agent_id=agent.id,
                tool_name=tool.name,
                tool_output=str(output)[:1000],  # Truncate for SSE
                duration_ms=duration_ms,
            ),
        ))

    def on_agent_end(self, agent: Agent, output: str) -> None:
        self._publisher.publish(RuntimeEvent(
            type=EventType.AGENT_COMPLETED,
            execution_id=self._execution_id,
            step=self._step_counter,
            data=AgentCompletedData(
                agent_id=agent.id,
                output=str(output)[:2000],
                tokens=self._token_tracker.get_agent_totals(agent.id),
            ),
        ))

    def on_error(self, error: Exception, agent: Agent | None = None) -> None:
        self._publisher.publish(RuntimeEvent(
            type=EventType.ERROR_OCCURRED,
            execution_id=self._execution_id,
            step=self._step_counter,
            data=ErrorData(
                agent_id=agent.id if agent else None,
                error_type=type(error).__name__,
                error_message=str(error),
            ),
        ))

    def on_llm_start(self, llm: BaseLLM, prompt: str) -> None:
        self._token_tracker.track_input(llm, prompt)

    def on_llm_end(self, llm: BaseLLM, response: str) -> None:
        self._token_tracker.track_output(llm, response)
```

---

## 5. Celery Orchestration Model

### 5.1 Queue Architecture

The system uses **four Celery queues** with distinct routing and priority:

```python
# apps/worker/src/config.py

CELERY_QUEUES = {
    "workflow_high": {                      # Priority execution
        "exchange": "workflows",
        "routing_key": "workflow.execute.high",
        "queue_arguments": {"x-max-priority": 10},
    },
    "workflow_default": {                   # Standard execution
        "exchange": "workflows",
        "routing_key": "workflow.execute.default",
        "queue_arguments": {"x-max-priority": 5},
    },
    "workflow_low": {                       # Batch/low-priority
        "exchange": "workflows",
        "routing_key": "workflow.execute.low",
        "queue_arguments": {"x-max-priority": 1},
    },
    "workflow_control": {                   # Pause/resume/kill commands
        "exchange": "workflows.control",
        "routing_key": "workflow.control.#",
        "queue_arguments": {"x-max-priority": 10},
    },
    "hitl": {                               # HITL decision responses
        "exchange": "hitl",
        "routing_key": "hitl.decision",
    },
}
```

### 5.2 Task Routing Rules

| Task Type | Queue | Priority | Description |
|-----------|-------|----------|-------------|
| `workflow.execute` | `workflow_default` | 5 | Standard workflow execution |
| `workflow.execute` (HITL resume) | `workflow_high` | 9 | HITL decisions should resume quickly |
| `workflow.execute` (replay) | `workflow_high` | 8 | Replay should not block new executions |
| `workflow.control.pause` | `workflow_control` | 10 | Pause must be delivered ASAP |
| `workflow.control.kill` | `workflow_control` | 10 | Kill must be delivered immediately |
| `hitl.decision` | `hitl` | — | Lightweight, dedicated worker |

### 5.3 Celery Configuration

[`apps/worker/src/celery_app.py`](apps/worker/src/celery_app.py)

```python
from celery import Celery

celery_app = Celery("crewai_worker")

celery_app.config_from_object({
    "broker_url": "redis://redis:6379/0",         # DB 0: Celery broker
    "result_backend": "redis://redis:6379/1",      # DB 1: Celery results

    # Task routing
    "task_queues": list(CELERY_QUEUES.values()),
    "task_routes": {
        "workflow.execute": {
            "queue": "workflow_default",
            "routing_key": "workflow.execute.default",
        },
        "workflow.control.*": {
            "queue": "workflow_control",
            "routing_key": "workflow.control",
        },
        "hitl.decision": {
            "queue": "hitl",
            "routing_key": "hitl.decision",
        },
    },

    # Serialization
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],

    # Reliability
    "task_acks_late": True,                # At-least-once delivery
    "task_reject_on_worker_lost": True,    # Re-queue on worker crash
    "worker_prefetch_multiplier": 1,       # One task at a time per worker
    "task_track_started": True,            # Report RUNNING state

    # Timeouts
    "task_soft_time_limit": 3600,          # 1 hour soft limit
    "task_time_limit": 3900,               # 65 min hard limit

    # Result retention
    "result_expires": 86400,               # 24 hours
})
```

### 5.4 Control Task Pattern

Pause, resume, and kill commands must be handled with **absolute priority**. The control queue has dedicated workers with minimum prefetch.

```python
@shared_task(
    bind=True,
    name="workflow.control.pause",
    queue="workflow_control",
    acks_late=True,
)
def pause_execution(self, execution_id: str):
    """
    Pause a running workflow.

    1. Lookup active Celery task_id for this execution
    2. Revoke the task (SIGTERM)
    3. CrewRuntime.pause() is called via the revocation handler
    4. Checkpoint is saved at the pause boundary
    5. Emit WORKFLOW_PAUSED event
    """
    orchestrator = ExecutionOrchestrator(execution_id)
    orchestrator.pause()


@shared_task(
    bind=True,
    name="workflow.control.resume",
    queue="workflow_control",
    acks_late=True,
)
def resume_execution(self, execution_id: str, checkpoint_id: str):
    """
    Resume a paused workflow from a checkpoint.

    1. Load checkpoint from database
    2. Enqueue new run_crew task with resume flag
    3. CrewRuntime.resume(checkpoint) restores state
    """
    orchestrator = ExecutionOrchestrator(execution_id)
    orchestrator.resume(checkpoint_id)
```

### 5.5 Worker Pool Strategy

```yaml
# docker-compose.yml (worker services)

services:
  worker-default:
    image: crewai-worker
    command: celery -A apps.worker.src.celery_app worker
      -Q workflow_default,workflow_low
      --concurrency=4
      --prefetch-multiplier=1
    # 4 concurrent workflow executions

  worker-control:
    image: crewai-worker
    command: celery -A apps.worker.src.celery_app worker
      -Q workflow_control
      --concurrency=2
      --prefetch-multiplier=1
    # Dedicated pool for pause/resume/kill - always available

  worker-hitl:
    image: crewai-worker
    command: celery -A apps.worker.src.celery_app worker
      -Q hitl
      --concurrency=2
      --prefetch-multiplier=1
    # Dedicated pool for HITL decisions
```

---

## 6. Redis Event Backbone

### 6.1 Redis Database Layout

```
┌──────────┬──────────────────────────────────────────────┬───────────┐
│ DB Index │ Usage                                        │ Eviction  │
├──────────┼──────────────────────────────────────────────┼───────────┤
│    0     │ Celery broker (task queue)                   │ N/A       │
│    1     │ Celery result backend                        │ allkeys   │
│          │                                              │ (24h TTL) │
│    2     │ Short-term memory (agent context)            │ allkeys   │
│          │                                              │ (1h TTL)  │
│    3     │ Event Pub/Sub + Streams                      │ N/A       │
│    4     │ Rate limiting counters                       │ allkeys   │
│          │                                              │ (1m TTL)  │
│    5     │ Session store / JWT blacklist                │ allkeys   │
│          │                                              │ (24h TTL) │
└──────────┴──────────────────────────────────────────────┴───────────┘
```

### 6.2 Pub/Sub Channel Namespace

```
# Event channels (DB 3)
crew:workflow:{execution_id}:events     # All runtime events for an execution
crew:workflow:{execution_id}:metrics    # Token/metrics updates (higher frequency)
crew:workflow:{execution_id}:logs       # Aggregated log entries

# Control channels (DB 3)
crew:control:{execution_id}:commands    # Pause/resume/kill commands to worker
crew:control:{execution_id}:status      # Status acknowledgements

# System channels (DB 3)
crew:system:alerts                      # System-wide alerts
crew:system:health                      # Health check heartbeat

# Pattern subscriptions
crew:workflow:*:events                  # SSE relay subscribes with pattern
```

### 6.3 Event Publisher Implementation

[`apps/worker/src/events/publisher.py`](apps/worker/src/events/publisher.py)

```python
import json
import redis.asyncio as aioredis

class EventPublisher:
    """
    Redis Pub/Sub event publisher.

    Every event is:
    1. Published to the execution-specific channel
    2. Optionally appended to a Redis Stream for persistence/replay
    3. Assigned a monotonic sequence ID for ordering
    """

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis
        self._seq = 0

    async def publish(self, event: RuntimeEvent) -> None:
        """Publish a runtime event to Redis Pub/Sub."""
        self._seq += 1
        event.sequence = self._seq

        payload = event.model_dump_json()

        # Pub/Sub for real-time streaming
        channel = f"crew:workflow:{event.execution_id}:events"
        await self._redis.publish(channel, payload)

        # Stream for persistence (consumers can replay from here)
        stream = f"crew:stream:{event.execution_id}:events"
        await self._redis.xadd(stream, {"payload": payload}, maxlen=10000)

    async def publish_control(self, execution_id: str, command: str, data: dict) -> None:
        """Publish a control command to the worker."""
        channel = f"crew:control:{execution_id}:commands"
        await self._redis.publish(channel, json.dumps({
            "command": command,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }))
```

### 6.4 Redis Stream for Event Persistence

Redis Streams provide **at-least-once delivery** and **replay capability**:

```python
class EventStreamManager:
    """
    Manages Redis Stream consumer groups for event replay.

    Each execution writes events to a stream with maxlen=10000.
    When a client reconnects with Last-Event-Id, we replay
    from that point in the stream before switching to Pub/Sub.
    """

    async def replay_from(
        self,
        execution_id: str,
        last_event_id: str | None,
    ) -> list[RuntimeEvent]:
        """Read events from stream starting after last_event_id."""
        stream = f"crew:stream:{execution_id}:events"
        if last_event_id:
            results = await self._redis.xrange(
                stream, min=last_event_id, max="+", count=500
            )
        else:
            results = await self._redis.xrevrange(stream, max="+", count=50)
            results.reverse()

        return [RuntimeEvent.model_validate_json(r[1]["payload"]) for r in results]
```

### 6.5 Redis Connection Management

```python
class RedisEngine:
    """
    Manages Redis connections per database.

    Uses a single connection pool with SELECT for DB access.
    Separate connections for Pub/Sub (which blocks the connection).
    """

    def __init__(self):
        self._pool: aioredis.ConnectionPool | None = None
        self._pubsub: aioredis.Redis | None = None

    @classmethod
    async def initialize(cls) -> "RedisEngine":
        self = cls()
        self._pool = aioredis.ConnectionPool(
            host=env.REDIS_HOST,
            port=env.REDIS_PORT,
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
        # Dedicated connection for Pub/Sub (blocking)
        self._pubsub = aioredis.Redis(
            connection_pool=aioredis.ConnectionPool(
                host=env.REDIS_HOST,
                port=env.REDIS_PORT,
                max_connections=10,
            )
        )
        return self

    def db(self, db_index: int) -> aioredis.Redis:
        """Get a Redis connection for a specific database."""
        return aioredis.Redis(connection_pool=self._pool).select(db_index)

    async def close(self) -> None:
        await self._pool.disconnect()
        await self._pubsub.connection_pool.disconnect()
```

---

## 7. SSE Streaming Pipeline

### 7.1 Architecture Overview

```
┌──────────┐     HTTP SSE     ┌──────────────┐     Redis Sub     ┌──────────┐
│ Frontend │◄───────────────  │    API       │◄────────────────  │  Worker  │
│ (Browser)│   Keepalive 30s  │  SSE Manager │                   │          │
└──────────┘                  └──────┬───────┘                   └──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  EventConsumer       │
                          │  (asyncio Task)      │
                          │                      │
                          │  1. Subscribe to      │
                          │     crew:*:events     │
                          │  2. Buffer & format   │
                          │  3. Write to SSE      │
                          │     queue per client  │
                          └──────────────────────┘
```

### 7.2 SSE Endpoint

[`apps/api/src/api/routes/stream.py`](apps/api/src/api/routes/stream.py)

```python
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from ...services import ServiceRegistry
from ...events.sse_manager import SSEManager

router = APIRouter()

@router.get("/workflow/stream/{execution_id}")
async def stream_workflow_events(
    execution_id: str,
    request: Request,
    last_event_id: str | None = Query(None, alias="lastEventId"),
    services: ServiceRegistry = Depends(get_services),
):
    """
    SSE endpoint for real-time workflow execution events.

    - Replays missed events from Redis Stream on reconnect
    - Subscribes to Redis Pub/Sub for live events
    - Sends keepalive comments every 30 seconds
    - Cleanly disconnects on client close
    """
    sse = SSEManager(services.redis, execution_id)

    return StreamingResponse(
        sse.event_stream(request, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",       # Disable nginx buffering
        },
    )
```

### 7.3 SSEManager Implementation

[`apps/api/src/events/sse_manager.py`](apps/api/src/events/sse_manager.py)

```python
import asyncio
import json
from fastapi import Request

class SSEManager:
    """
    Manages a single SSE connection for a workflow execution.

    Lifecycle:
    1. Client connects → replay events from Redis Stream (if last_event_id)
    2. Subscribe to Redis Pub/Sub channel
    3. Forward events to asyncio.Queue → HTTP response
    4. Keepalive every 30s
    5. On disconnect: unsubscribe, cleanup
    """

    def __init__(self, redis: RedisEngine, execution_id: str):
        self._redis = redis
        self._execution_id = execution_id
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)

    async def event_stream(
        self,
        request: Request,
        last_event_id: str | None,
    ) -> AsyncGenerator[str, None]:
        """Generate SSE event stream."""
        # Phase 1: Replay missed events
        if last_event_id:
            events = await self._replay_events(last_event_id)
            for event in events:
                yield self._format_sse(event)
                if await request.is_disconnected():
                    return

        # Phase 2: Subscribe to live events
        pubsub = self._redis.pubsub()
        channel = f"crew:workflow:{self._execution_id}:events"
        await pubsub.subscribe(channel)

        # Phase 3: Forward events with keepalive
        try:
            listener = asyncio.create_task(self._listen(pubsub))
            keepalive = asyncio.create_task(self._keepalive())

            while not await request.is_disconnected():
                try:
                    message = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                    yield message
                except asyncio.TimeoutError:
                    continue

        finally:
            listener.cancel()
            keepalive.cancel()
            await pubsub.unsubscribe(channel)

    async def _listen(self, pubsub) -> None:
        """Forward Redis Pub/Sub messages to the asyncio queue."""
        async for message in pubsub.listen():
            if message["type"] == "message":
                sse_event = self._format_sse(
                    json.loads(message["data"])
                )
                await self._queue.put(sse_event)

    async def _replay_events(self, last_event_id: str) -> list[dict]:
        """Replay events from Redis Stream since last_event_id."""
        stream = f"crew:stream:{self._execution_id}:events"
        results = await self._redis.db(3).xrange(
            stream, min=last_event_id, max="+", count=500
        )
        return [json.loads(r[1]["payload"]) for r in results]

    def _format_sse(self, event: dict) -> str:
        """Format event as SSE protocol message."""
        lines = [
            f"event: {event['type']}",
            f"id: {event.get('sequence', 0)}",
            f"data: {json.dumps(event)}",
            "",  # Empty line terminates the event
        ]
        return "\n".join(lines)

    async def _keepalive(self) -> None:
        """Send SSE keepalive comment every 30 seconds."""
        while True:
            await asyncio.sleep(30)
            await self._queue.put(": keepalive\n\n")  # Comment line
```

### 7.4 Event Format for SSE

```
event: AGENT_THOUGHT
id: 42
data: {"type":"AGENT_THOUGHT","execution_id":"exec_123","step":7,"data":{"agent_id":"agent_2","thought":"I need to search...","action":"web_search","action_input":{"query":"latest AI research"}},"timestamp":"2026-05-23T10:30:00Z","sequence":42}

event: TOOL_RESULT
id: 43
data: {"type":"TOOL_RESULT","execution_id":"exec_123","step":7,"data":{"agent_id":"agent_2","tool_name":"web_search","tool_output":"Results: ...","duration_ms":1200},"timestamp":"2026-05-23T10:30:01Z","sequence":43}

: keepalive

event: WORKFLOW_COMPLETED
id: 200
data: {"type":"WORKFLOW_COMPLETED","execution_id":"exec_123","step":200,"data":{"status":"SUCCESS","metrics":{"total_tokens":4500,"total_duration_ms":345000,"agent_count":3}},"timestamp":"2026-05-23T10:35:00Z","sequence":200}
```

---

## 8. Workflow Execution Lifecycle

### 8.1 Lifecycle State Transitions

```
                          ┌──────────┐
                          │  DRAFT   │  (Workflow created, not yet runnable)
                          └────┬─────┘
                               │ User clicks "Run"
                               ▼
                          ┌──────────┐
                          │ PENDING  │  (Validated, execution record created)
                          └────┬─────┘
                               │ Enqueued to Celery
                               ▼
                          ┌──────────┐
                     ┌───►│ QUEUED   │  (In Celery queue, waiting for worker)
                     │    └────┬─────┘
                     │         │ Worker picks up task
                     │         ▼
                     │    ┌──────────┐
                     │    │ RUNNING  │  (CrewRuntime executing)
                     │    └────┬─────┘
                     │         ├──────────────────────┐
                     │         │                      │
                     │         ▼                      ▼
                     │    ┌──────────────┐    ┌──────────────┐
                     │    │AWAITING_     │    │              │
                     │    │APPROVAL     │    │   FAILED     │
                     │    └──────┬───────┘    └──────────────┘
                     │           │
                     │      ┌────▼──────┐
                     │      │ SUSPENDED │  (HITL pause or user pause)
                     │      └────┬──────┘
                     │           │ Approved/resumed
                     │           ▼
                     │      ┌──────────┐
                     └──────┤ RUNNING  │  (Resumed from checkpoint)
                            └──────────┘
                               │
                               ▼
                          ┌──────────┐
                          │ SUCCESS  │  (All agents completed)
                          └──────────┘
```

### 8.2 Execution Record Schema

```python
# apps/api/src/db/models/execution.py

class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus), default=ExecutionStatus.PENDING, index=True
    )
    config_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # ^ Full workflow config at time of execution (immutable)

    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    duration_ms: Mapped[int | None]
    error_message: Mapped[str | None]
    error_details: Mapped[dict | None] = mapped_column(JSONB)

    # Checkpoint tracking
    current_step: Mapped[int] = mapped_column(default=0)
    last_checkpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("checkpoints.id"))

    # Token/usage tracking
    total_input_tokens: Mapped[int] = mapped_column(default=0)
    total_output_tokens: Mapped[int] = mapped_column(default=0)
    total_cost: Mapped[Decimal] = mapped_column(Decimal(12, 6), default=0)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="executions")
    checkpoints: Mapped[list["Checkpoint"]] = relationship(back_populates="execution")
    logs: Mapped[list["ExecutionLog"]] = relationship(back_populates="execution")

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
```

### 8.3 Execution Orchestrator

[`apps/worker/src/orchestrator/execution_orchestrator.py`](apps/worker/src/orchestrator/execution_orchestrator.py)

```python
class ExecutionOrchestrator:
    """
    Manages the full lifecycle of a single workflow execution.

    This is the central coordinator that:
    - Constructs the Crew via CrewRuntime
    - Drives execution with checkpoint boundaries
    - Handles pause/resume/kill commands
    - Publishes events to Redis
    - Updates execution status in PostgreSQL
    """

    def __init__(self, execution_id: str):
        self._execution_id = execution_id
        self._db = DatabaseSessionManager()
        self._redis = RedisEngine()
        self._events = EventPublisher(self._redis.db(3))
        self._checkpoints = CheckpointManager(self._db)
        self._memory = MemoryBridge(self._redis.db(2), self._db)
        self._runtime = CrewRuntime(
            execution_id=execution_id,
            event_publisher=self._events,
            checkpoint_manager=self._checkpoints,
            memory_bridge=self._memory,
        )

    async def run(self, workflow_config: dict) -> dict:
        """Execute a workflow from scratch."""
        # 1. Load execution record
        execution = await self._db.get_execution(self._execution_id)

        # 2. Update status to RUNNING
        await self._db.update_execution_status(
            self._execution_id, ExecutionStatus.RUNNING
        )

        # 3. Construct Crew
        crew = self._runtime.construct(workflow_config)

        # 4. Execute with event streaming
        context = ExecutionContext(
            execution_id=self._execution_id,
            workflow_config=workflow_config,
        )

        async for event in self._runtime.execute(context):
            # Publish every event to Redis Pub/Sub
            await self._events.publish(event)

            # Handle specific event types
            if event.type == EventType.AGENT_STARTED:
                await self._db.update_execution_step(
                    self._execution_id, event.step
                )
            elif event.type == EventType.AGENT_COMPLETED:
                await self._checkpoints.save_agent_complete(
                    self._execution_id, event.data
                )
            elif event.type == EventType.WORKFLOW_COMPLETED:
                await self._finalize_success(execution)
            elif event.type == EventType.WORKFLOW_FAILED:
                await self._finalize_failure(execution, event.data)

        return {"status": execution.status.value, "execution_id": self._execution_id}

    async def pause(self) -> None:
        """Pause execution at next safe boundary."""
        self._runtime.pause()
        await self._db.update_execution_status(
            self._execution_id, ExecutionStatus.SUSPENDED
        )

    async def resume(self, checkpoint_id: str) -> None:
        """Resume execution from a checkpoint."""
        checkpoint = await self._checkpoints.load(checkpoint_id)
        self._runtime.resume(checkpoint)
        await self._db.update_execution_status(
            self._execution_id, ExecutionStatus.RUNNING
        )

    async def kill(self) -> None:
        """Immediately terminate execution."""
        self._runtime.kill()
        await self._db.update_execution_status(
            self._execution_id, ExecutionStatus.CANCELLED
        )
```

---

## 9. Execution State Machine

### 9.1 Hierarchical State Machine

The state machine is **hierarchical**: a top-level workflow state machine contains per-agent sub-state machines.

```
                    ┌──────────────────────────────────────┐
                    │         WORKFLOW STATE MACHINE        │
                    └──────────────────────────────────────┘

  PENDING ──► QUEUED ──► RUNNING ──► SUCCESS
                           │
                     ┌─────┼─────┐
                     │     │     │
                     ▼     ▼     ▼
               SUSPENDED FAILED CANCELLED
                     │
                     └──► RUNNING (resume)

  RUNNING state contains per-agent sub-state machines: ──┐
                                                          │
                    ┌──────────────────────────────────────┘
                    │
                    ▼
          ┌──────────────────────────────────────┐
          │      AGENT SUB-STATE MACHINE           │
          └──────────────────────────────────────┘

  IDLE ──► THINKING ──► ACTING ──► TOOL_CALLING ──► OBSERVING ──► COMPLETED
             │            │            │                │
             │            │            │                └──► THINKING (loop, if more steps)
             │            │            │
             │            │            └──► AWAITING_HITL ──► THINKING (approved)
             │            │
             │            └──► FAILED
             │
             └──► FAILED
```

### 9.2 State Machine Enums

[`packages/shared-types/src/constants/states.py`](packages/shared-types/src/constants/states.py)

```python
from enum import Enum

class WorkflowStatus(str, Enum):
    PENDING = "PENDING"                 # Created, not yet started
    QUEUED = "QUEUED"                   # In Celery queue
    RUNNING = "RUNNING"                 # Active execution
    SUSPENDED = "SUSPENDED"             # Paused (has valid checkpoint)
    AWAITING_APPROVAL = "AWAITING_APPROVAL"  # HITL block
    FAILED = "FAILED"                   # Unrecoverable failure
    CANCELLED = "CANCELLED"             # User-cancelled
    SUCCESS = "SUCCESS"                 # Completed successfully

class AgentExecutionStatus(str, Enum):
    IDLE = "IDLE"                       # Waiting to start
    THINKING = "THINKING"               # Internal reasoning
    ACTING = "ACTING"                   # Selected tool/action
    TOOL_CALLING = "TOOL_CALLING"       # Executing external tool
    OBSERVING = "OBSERVING"             # Processing tool result
    AWAITING_HITL = "AWAITING_HITL"     # Paused for human approval
    COMPLETED = "COMPLETED"             # Agent task finished
    FAILED = "FAILED"                   # Agent task failed
```

### 9.3 State Transition Validator

[`apps/worker/src/orchestrator/state_machine.py`](apps/worker/src/orchestrator/state_machine.py)

```python
class WorkflowStateMachine:
    """
    Validates and enforces legal state transitions.

    Every state change must go through this validator.
    Illegal transitions raise ExecutionStateConflictError.
    """

    VALID_TRANSITIONS: dict[WorkflowStatus, set[WorkflowStatus]] = {
        WorkflowStatus.PENDING: {WorkflowStatus.QUEUED, WorkflowStatus.CANCELLED},
        WorkflowStatus.QUEUED: {WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED},
        WorkflowStatus.RUNNING: {
            WorkflowStatus.SUSPENDED,
            WorkflowStatus.AWAITING_APPROVAL,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.SUCCESS,
        },
        WorkflowStatus.SUSPENDED: {
            WorkflowStatus.RUNNING,      # Resume
            WorkflowStatus.CANCELLED,    # Cancel while suspended
        },
        WorkflowStatus.AWAITING_APPROVAL: {
            WorkflowStatus.RUNNING,      # HITL approved
            WorkflowStatus.CANCELLED,    # HITL cancelled
        },
        WorkflowStatus.FAILED: set(),    # Terminal
        WorkflowStatus.CANCELLED: set(), # Terminal
        WorkflowStatus.SUCCESS: set(),   # Terminal
    }

    @classmethod
    def transition(cls, current: WorkflowStatus, target: WorkflowStatus) -> WorkflowStatus:
        """Validate and return the target state. Raises on illegal transition."""
        allowed = cls.VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ExecutionStateConflictError(
                execution_id="",  # Set by caller
                current=current.value,
                expected=" | ".join(s.value for s in allowed),
            )
        return target
```

### 9.4 Thread-Safe State Updates

State transitions in the database use **optimistic locking** to prevent race conditions between concurrent commands:

```python
# apps/api/src/db/repositories/execution_repository.py

async def update_status(
    self,
    execution_id: UUID,
    current_status: WorkflowStatus,
    target_status: WorkflowStatus,
) -> Execution:
    """
    Atomic state transition with optimistic locking.

    Uses PostgreSQL UPDATE ... WHERE status = :current
    Returns None if the row was already modified (race condition).
    """
    result = await self._session.execute(
        update(Execution)
        .where(Execution.id == execution_id)
        .where(Execution.status == current_status)
        .values(
            status=target_status,
            updated_at=func.now(),
        )
        .returning(Execution)
    )
    execution = result.scalar_one_or_none()
    if execution is None:
        raise ExecutionStateConflictError(
            execution_id=str(execution_id),
            current=current_status.value,
            expected="unknown (concurrent modification)",
        )
    return execution
```

---

## 10. Replay & Checkpoint Architecture

### 10.1 Checkpoint Strategy

Checkpoints are saved at **agent-level granularity** — after each agent completes its task execution. This provides the finest practical granularity for resume/replay without excessive overhead.

```
Execution Timeline:

Agent 1 ────► [CHECKPOINT] ────► Agent 2 ────► [CHECKPOINT] ────► Agent 3 ────► [CHECKPOINT]
                 │                     │                            │
                 ▼                     ▼                            ▼
          Saved: Agent 1          Saved: Agent 1+2             Saved: All
          context, tasks          context, tasks               completed
          completed               completed                    tasks
```

### 10.2 Checkpoint Data Model

```python
# apps/api/src/db/models/checkpoint.py

class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("executions.id"), index=True)
    step: Mapped[int] = mapped_column(nullable=False)           # Sequential step number
    status: Mapped[str] = mapped_column(nullable=False)          # RUNNING | SUSPENDED | FAILED

    # Execution state snapshot
    completed_agent_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    pending_agent_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    completed_task_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    pending_task_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Shared context
    shared_context: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Memory state
    memory_snapshot_id: Mapped[str | None]  # Reference to saved memory state

    # Metrics snapshot
    cumulative_tokens: Mapped[dict] = mapped_column(JSONB, default=dict)
    cumulative_cost: Mapped[Decimal] = mapped_column(Decimal(12, 6), default=0)

    # Timing
    duration_ms: Mapped[int | None]          # Duration from execution start to checkpoint
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # Relationships
    execution: Mapped["Execution"] = relationship(back_populates="checkpoints")
```

### 10.3 CheckpointManager

[`apps/worker/src/checkpoint/manager.py`](apps/worker/src/checkpoint/manager.py)

```python
class CheckpointManager:
    """
    Manages checkpoint save/load operations.

    Save strategy:
    - Pre-agent: Save before each agent starts (for replay)
    - Post-agent: Save after each agent completes (for resume)
    - Pause: Save on user-initiated pause
    - Failure: Save on unrecoverable error (for debugging)

    Load strategy:
    - Resume: Load last SUSPENDED checkpoint
    - Replay: Load checkpoint at specific step, replay from there
    - Rollback: Load checkpoint N steps back
    """

    def __init__(self, db: DatabaseSessionManager):
        self._db = db

    async def save_pre_agent(
        self, execution_id: str, agent_id: str, context: ExecutionContext
    ) -> Checkpoint:
        """Save checkpoint before agent execution begins."""
        execution = await self._db.get_execution(execution_id)
        checkpoint = Checkpoint(
            execution_id=execution_id,
            step=execution.current_step + 1,
            status=ExecutionStatus.RUNNING.value,
            completed_agent_ids=list(context.completed_agents),
            pending_agent_ids=list(context.pending_agents),
            completed_task_ids=list(context.completed_tasks),
            pending_task_ids=list(context.pending_tasks),
            shared_context=context.shared_data,
            cumulative_tokens=context.token_tracker.get_snapshot(),
            cumulative_cost=context.token_tracker.get_cost(),
        )
        return await self._db.save_checkpoint(checkpoint)

    async def save_post_agent(
        self, execution_id: str, agent_id: str, result: AgentResult
    ) -> Checkpoint:
        """Save checkpoint after agent completes."""
        execution = await self._db.get_execution(execution_id)
        checkpoint = Checkpoint(
            execution_id=execution_id,
            step=execution.current_step + 1,
            status=ExecutionStatus.RUNNING.value,
            completed_agent_ids=[agent_id],  # Append to existing
            pending_agent_ids=[],
            completed_task_ids=result.completed_task_ids,
            pending_task_ids=result.pending_task_ids,
            shared_context=result.context_updates,
            cumulative_tokens=result.token_snapshot,
            cumulative_cost=result.cost,
        )
        return await self._db.save_checkpoint(checkpoint)

    async def save_pause(self, execution_id: str, step: int) -> Checkpoint:
        """Save checkpoint on user-initiated pause."""
        execution = await self._db.get_execution(execution_id)
        checkpoint = Checkpoint(
            execution_id=execution_id,
            step=step,
            status=ExecutionStatus.SUSPENDED.value,
            completed_agent_ids=execution.completed_agent_ids,
            pending_agent_ids=execution.pending_agent_ids,
            completed_task_ids=execution.completed_task_ids,
            pending_task_ids=execution.pending_task_ids,
            shared_context=execution.shared_context,
            cumulative_tokens=execution.cumulative_tokens,
            cumulative_cost=execution.cumulative_cost,
        )
        saved = await self._db.save_checkpoint(checkpoint)

        # Update execution record with checkpoint reference
        await self._db.update_last_checkpoint(execution_id, saved.id)
        return saved

    async def load_latest(self, execution_id: str) -> Checkpoint | None:
        """Load the most recent checkpoint for an execution."""
        return await self._db.get_latest_checkpoint(execution_id)

    async def load_at_step(self, execution_id: str, step: int) -> Checkpoint | None:
        """Load checkpoint at a specific step (for step-by-step replay)."""
        return await self._db.get_checkpoint_at_step(execution_id, step)
```

### 10.4 Replay Engine

[`apps/worker/src/orchestrator/replay_engine.py`](apps/worker/src/orchestrator/replay_engine.py)

```python
class ReplayEngine:
    """
    Replays a workflow execution from a specific checkpoint.

    Replay modes:
    1. FULL_REPLAY: Re-run the entire workflow from step 0
    2. STEP_REPLAY: Re-run from a specific checkpoint step
    3. DEBUG_REPLAY: Re-run with original event log for comparison

    Replay creates a NEW execution record linked to the original
    for audit trail and diff comparison.
    """

    async def replay(
        self,
        original_execution_id: str,
        from_step: int = 0,
        mode: ReplayMode = ReplayMode.FULL_REPLAY,
    ) -> str:
        """Execute a replay run. Returns new execution_id."""
        # 1. Load original execution config (immutable snapshot)
        original = await self._db.get_execution(original_execution_id)
        config = original.config_snapshot

        # 2. Create new execution record linked to original
        replay_execution = await self._db.create_replay_execution(
            original_workflow_id=original.workflow_id,
            config_snapshot=config,
            original_execution_id=original_execution_id,
            replay_from_step=from_step,
        )

        # 3. If step > 0, load checkpoint and restore context
        if from_step > 0:
            checkpoint = await self._db.get_checkpoint_at_step(
                original_execution_id, from_step
            )
            if checkpoint:
                config["restore_context"] = {
                    "completed_agents": checkpoint.completed_agent_ids,
                    "completed_tasks": checkpoint.completed_task_ids,
                    "shared_context": checkpoint.shared_context,
                }

        # 4. Enqueue replay execution
        run_crew.delay(
            execution_id=str(replay_execution.id),
            workflow_config=config,
        )

        return str(replay_execution.id)

    async def compare_replay(
        self,
        original_id: str,
        replay_id: str,
    ) -> ReplayDiffReport:
        """
        Compare original execution with replay execution.

        Diffs:
        - Per-agent: output text diff
        - Per-tool: input/output comparison
        - Token usage: variance report
        - Step timing: variance report
        """
        original_events = await self._db.get_execution_events(original_id)
        replay_events = await self._db.get_execution_events(replay_id)

        return self._diff_events(original_events, replay_events)

    def _diff_events(
        self, original: list[ExecutionEvent], replay: list[ExecutionEvent]
    ) -> ReplayDiffReport:
        """Generate a structured diff between two execution event streams."""
        # ... diff logic per agent/task/step
        pass
```

### 10.5 Replay Database Schema

```sql
-- Additional columns on executions table
ALTER TABLE executions ADD COLUMN original_execution_id UUID REFERENCES executions(id);
ALTER TABLE executions ADD COLUMN replay_from_step INT;
ALTER TABLE executions ADD COLUMN replay_mode VARCHAR(20);  -- 'FULL' | 'STEP' | 'DEBUG'

-- Replay diff results
CREATE TABLE replay_diffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_execution_id UUID NOT NULL REFERENCES executions(id),
    replay_execution_id UUID NOT NULL REFERENCES executions(id),
    agent_id UUID,
    step INT,
    diff_type VARCHAR(20) NOT NULL,  -- 'OUTPUT' | 'TOOL_INPUT' | 'TOOL_OUTPUT' | 'TOKENS' | 'TIMING'
    original_value JSONB,
    replay_value JSONB,
    variance JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 11. Event Schema System

### 11.1 Event Envelope

Every event in the system conforms to a strict envelope schema. This ensures forward compatibility, tracing, and replay safety.

[`packages/shared-types/src/events/base.py`](packages/shared-types/src/events/base.py)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4
from enum import Enum

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


class EventSource(str, Enum):
    RUNTIME = "runtime"      # CrewAI execution events
    WORKER = "worker"        # Celery worker operational events
    API = "api"              # API-initiated events
    SYSTEM = "system"        # System health, alerts


class RuntimeEvent(BaseModel):
    """
    Universal event envelope for all system events.

    All events must:
    - Have a unique ID
    - Include correlation_id for tracing across service boundaries
    - Include the source component
    - Be schema-versioned for forward compatibility
    """
    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    execution_id: str
    correlation_id: str
    source: EventSource
    step: int = 0
    sequence: int = 0
    data: dict = Field(default_factory=dict)
    version: int = 1  # Schema version for forward compatibility
```

### 11.2 Typed Event Data Schemas

[`packages/shared-types/src/events/data.py`](packages/shared-types/src/events/data.py)

```python
class AgentStartedData(BaseModel):
    agent_id: str
    agent_role: str
    task_id: str
    task_title: str

class AgentThoughtData(BaseModel):
    agent_id: str
    thought: str
    action: str | None = None
    action_input: dict | None = None

class ToolCallData(BaseModel):
    agent_id: str
    tool_name: str
    tool_input: dict
    timestamp: str

class ToolResultData(BaseModel):
    agent_id: str
    tool_name: str
    tool_output: str
    duration_ms: int

class AgentCompletedData(BaseModel):
    agent_id: str
    output: str
    tokens: dict = Field(default_factory=dict)  # {"input": 150, "output": 300, "total": 450}

class HITLRequiredData(BaseModel):
    task_id: str
    agent_id: str
    agent_role: str
    draft_output: str
    task_description: str
    context: dict = Field(default_factory=dict)

class HITLDecisionData(BaseModel):
    approval_id: str
    decision: str  # "APPROVED" | "REJECTED"
    reason: str | None = None
    edits: str | None = None  # Human-edited output

class ErrorData(BaseModel):
    agent_id: str | None = None
    error_type: str
    error_message: str
    error_details: dict | None = None
```

### 11.3 Event Correlation Strategy

```
Every request from the frontend includes a correlation_id header:

Frontend                          API                         Worker
   │                               │                           │
   │── (correlation_id: "abc") ──► │                           │
   │                               │── (correlation_id: "abc")─►│
   │                               │                           │
   │◄── (correlation_id: "abc") ──│◄── (correlation_id: "abc")─│
```

```python
# Correlation ID propagation in the API

class RequestIDMiddleware:
    """Ensures every request has a correlation_id for tracing."""

    async def __call__(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = f"corr_{uuid4().hex[:16]}"

        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

---

## 12. Persistence Architecture

### 12.1 Repository Pattern

Data access is isolated behind **repository interfaces**. No raw SQLAlchemy queries in service code.

[`apps/api/src/db/repositories/base.py`](apps/api/src/db/repositories/base.py)

```python
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession

class BaseRepository(ABC):
    """Abstract base repository with common CRUD operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, id: UUID) -> Base | None:
        return await self._session.get(self.model_class, id)

    async def list(self, filters: dict | None = None, limit: int = 100, offset: int = 0) -> list[Base]:
        query = select(self.model_class)
        if filters:
            for key, value in filters.items():
                query = query.where(getattr(self.model_class, key) == value)
        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def save(self, instance: Base) -> Base:
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def delete(self, instance: Base) -> None:
        await self._session.delete(instance)
```

### 12.2 Repository Implementations

[`apps/api/src/db/repositories/execution_repository.py`](apps/api/src/db/repositories/execution_repository.py)

```python
class ExecutionRepository(BaseRepository):
    model_class = Execution

    async def get_with_checkpoints(self, execution_id: UUID) -> Execution | None:
        """Get execution with eagerly loaded checkpoints."""
        query = (
            select(Execution)
            .options(selectinload(Execution.checkpoints))
            .where(Execution.id == execution_id)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def transfer_ownership(
        self, execution_id: UUID, from_status: str, to_status: str
    ) -> Execution | None:
        """Atomic state transition with optimistic lock."""
        result = await self._session.execute(
            update(Execution)
            .where(Execution.id == execution_id)
            .where(Execution.status == from_status)
            .values(status=to_status, updated_at=func.now())
            .returning(Execution)
        )
        return result.scalar_one_or_none()

    async def update_metrics(
        self,
        execution_id: UUID,
        input_tokens: int,
        output_tokens: int,
        cost: Decimal,
    ) -> None:
        """Accumulate token/cost metrics."""
        await self._session.execute(
            update(Execution)
            .where(Execution.id == execution_id)
            .values(
                total_input_tokens=Execution.total_input_tokens + input_tokens,
                total_output_tokens=Execution.total_output_tokens + output_tokens,
                total_cost=Execution.total_cost + cost,
            )
        )
```

[`apps/api/src/db/repositories/checkpoint_repository.py`](apps/api/src/db/repositories/checkpoint_repository.py)

```python
class CheckpointRepository(BaseRepository):
    model_class = Checkpoint

    async def get_latest_by_execution(self, execution_id: UUID) -> Checkpoint | None:
        query = (
            select(Checkpoint)
            .where(Checkpoint.execution_id == execution_id)
            .order_by(Checkpoint.step.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_step(self, execution_id: UUID, step: int) -> Checkpoint | None:
        query = (
            select(Checkpoint)
            .where(Checkpoint.execution_id == execution_id)
            .where(Checkpoint.step == step)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
```

### 12.3 Session Management

```python
class DatabaseSessionManager:
    """
    Manages async SQLAlchemy sessions with automatic commit/rollback.

    Uses asyncpg for PostgreSQL connectivity.
    Connection pooling with configurable pool size.
    """

    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self):
        self._engine = create_async_engine(
            env.DATABASE_URL,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,       # Verify connections before use
            pool_recycle=3600,         # Recycle connections after 1 hour
            echo=env.DEBUG_SQL,       # SQL logging in debug mode
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    def session(self) -> AsyncSession:
        """Get a new session from the pool."""
        return self._session_factory()

    async def disconnect(self):
        if self._engine:
            await self._engine.dispose()
```

---

## 13. PostgreSQL Schema Strategy

### 13.1 Core Tables

```sql
-- apps/api/src/db/migrations/versions/001_initial_schema.py

-- ============================================================
-- WORKFLOWS
-- ============================================================
CREATE TABLE workflows (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    config          JSONB NOT NULL DEFAULT '{}',    -- Full workflow YAML/config
    version         INT NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'DRAFT',  -- DRAFT | ACTIVE | ARCHIVED
    project_id      UUID,                                -- Future: multi-tenancy
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    INDEX idx_workflows_project (project_id),
    INDEX idx_workflows_created_by (created_by),
    INDEX idx_workflows_status (status)
);

-- ============================================================
-- WORKFLOW VERSIONS (immutable history)
-- ============================================================
CREATE TABLE workflow_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    version         INT NOT NULL,
    config          JSONB NOT NULL,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(workflow_id, version),
    INDEX idx_wf_versions_workflow (workflow_id)
);

-- ============================================================
-- EXECUTIONS
-- ============================================================
CREATE TABLE executions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id         UUID NOT NULL REFERENCES workflows(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    config_snapshot     JSONB NOT NULL,            -- Immutable config copy
    current_step        INT NOT NULL DEFAULT 0,
    last_checkpoint_id  UUID,

    -- Original execution link (for replays)
    original_execution_id UUID REFERENCES executions(id),
    replay_from_step    INT,
    replay_mode         VARCHAR(20),

    -- Timing
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    duration_ms         INT,

    -- Error
    error_message       TEXT,
    error_details       JSONB,

    -- Token tracking
    total_input_tokens  INT NOT NULL DEFAULT 0,
    total_output_tokens INT NOT NULL DEFAULT 0,
    total_cost          DECIMAL(12,6) NOT NULL DEFAULT 0,

    -- Audit
    triggered_by        UUID REFERENCES users(id),
    correlation_id      UUID,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    INDEX idx_executions_workflow (workflow_id),
    INDEX idx_executions_status (status),
    INDEX idx_executions_original (original_execution_id),
    INDEX idx_executions_created (created_at DESC)
);

-- ============================================================
-- CHECKPOINTS
-- ============================================================
CREATE TABLE checkpoints (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id        UUID NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    step                INT NOT NULL,
    status              VARCHAR(20) NOT NULL,

    completed_agent_ids JSONB NOT NULL DEFAULT '[]',
    pending_agent_ids   JSONB NOT NULL DEFAULT '[]',
    completed_task_ids  JSONB NOT NULL DEFAULT '[]',
    pending_task_ids    JSONB NOT NULL DEFAULT '[]',

    shared_context      JSONB NOT NULL DEFAULT '{}',
    memory_snapshot_id  VARCHAR(255),
    cumulative_tokens   JSONB NOT NULL DEFAULT '{}',
    cumulative_cost     DECIMAL(12,6) NOT NULL DEFAULT 0,
    duration_ms         INT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    INDEX idx_checkpoints_execution (execution_id),
    INDEX idx_checkpoints_exec_step (execution_id, step)
);

-- ============================================================
-- EXECUTION LOGS (append-only event store)
-- ============================================================
CREATE TABLE execution_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id     UUID NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    event_type      VARCHAR(50) NOT NULL,
    correlation_id  UUID NOT NULL,
    source          VARCHAR(20) NOT NULL,
    step            INT NOT NULL DEFAULT 0,
    sequence        INT NOT NULL DEFAULT 0,

    agent_id        VARCHAR(255),
    task_id         VARCHAR(255),
    payload         JSONB NOT NULL,
    level           VARCHAR(10) NOT NULL DEFAULT 'INFO',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Monthly partitions
CREATE TABLE execution_logs_2026_05 PARTITION OF execution_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE execution_logs_2026_06 PARTITION OF execution_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- Log indexes
CREATE INDEX idx_logs_execution_time ON execution_logs (execution_id, created_at DESC);
CREATE INDEX idx_logs_event_type ON execution_logs (event_type);
CREATE INDEX idx_logs_correlation ON execution_logs (correlation_id);
CREATE INDEX idx_logs_level ON execution_logs (level);

-- ============================================================
-- AGENTS (CRUD)
-- ============================================================
CREATE TABLE agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     UUID REFERENCES workflows(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    role            TEXT NOT NULL,
    goal            TEXT NOT NULL,
    backstory       TEXT,

    -- LLM configuration
    llm_provider    VARCHAR(50) NOT NULL DEFAULT 'openai',
    llm_model       VARCHAR(100) NOT NULL DEFAULT 'gpt-4',
    temperature     REAL DEFAULT 0.7,
    max_tokens      INT DEFAULT 4096,
    max_iterations  INT DEFAULT 15,
    rpm_limit       INT DEFAULT 10,

    -- Memory
    short_term_memory  BOOLEAN DEFAULT TRUE,
    long_term_memory   BOOLEAN DEFAULT FALSE,
    entity_memory      BOOLEAN DEFAULT FALSE,

    -- Tool assignments
    tool_ids        JSONB NOT NULL DEFAULT '[]',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    INDEX idx_agents_workflow (workflow_id)
);

-- ============================================================
-- APPROVALS (HITL)
-- ============================================================
CREATE TABLE approvals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id    UUID NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    task_id         VARCHAR(255) NOT NULL,
    agent_id        VARCHAR(255) NOT NULL,
    workflow_id     UUID REFERENCES workflows(id),

    draft_output    TEXT NOT NULL,
    edited_output   TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING | APPROVED | REJECTED
    reason          TEXT,
    reviewed_by     UUID REFERENCES users(id),
    reviewed_at     TIMESTAMPTZ,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    INDEX idx_approvals_execution (execution_id),
    INDEX idx_approvals_status (status),
    INDEX idx_approvals_reviewer (reviewed_by)
);
```

### 13.2 Token Metrics Table

```sql
-- ============================================================
-- TOKEN METRICS (write-optimized for high-frequency inserts)
-- ============================================================
CREATE TABLE token_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id    UUID NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    agent_id        VARCHAR(255),
    task_id         VARCHAR(255),
    step            INT NOT NULL DEFAULT 0,

    provider        VARCHAR(50) NOT NULL,       -- openai, anthropic, ollama
    model           VARCHAR(100) NOT NULL,
    input_tokens    INT NOT NULL DEFAULT 0,
    output_tokens   INT NOT NULL DEFAULT 0,
    total_tokens    INT NOT NULL DEFAULT 0,
    estimated_cost  DECIMAL(10,6) NOT NULL DEFAULT 0,
    duration_ms     INT NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    INDEX idx_token_metrics_execution (execution_id, created_at DESC),
    INDEX idx_token_metrics_agent (execution_id, agent_id)
);
```

### 13.3 Audit Logs Table

```sql
-- ============================================================
-- AUDIT LOGS (immutable, append-only)
-- ============================================================
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    action          VARCHAR(100) NOT NULL,       -- workflow.run, agent.update, etc.
    resource_type   VARCHAR(50) NOT NULL,        -- workflow, agent, execution, etc.
    resource_id     UUID,
    before_state    JSONB,
    after_state     JSONB,
    ip_address      INET,
    user_agent      TEXT,
    correlation_id  UUID,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    INDEX idx_audit_user (user_id, created_at DESC),
    INDEX idx_audit_action (action, created_at DESC),
    INDEX idx_audit_resource (resource_type, resource_id),
    INDEX idx_audit_correlation (correlation_id)
);
```

### 13.4 Memory Tables

```sql
-- ============================================================
-- LONG-TERM MEMORY (PGVector)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE agent_memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    agent_id        VARCHAR(255) NOT NULL,
    memory_type     VARCHAR(20) NOT NULL DEFAULT 'long_term',  -- long_term | entity

    embedding       vector(1536),          -- OpenAI embedding dimension
    content         TEXT NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ,

    INDEX idx_memories_workflow_agent (workflow_id, agent_id),
    INDEX idx_memories_embedding (embedding) USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200),
    INDEX idx_memories_metadata (metadata) USING gin
);

-- ============================================================
-- ENTITY MEMORY (structured facts)
-- ============================================================
CREATE TABLE entity_memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    agent_id        VARCHAR(255) NOT NULL,
    entity_name     VARCHAR(255) NOT NULL,

    attributes      JSONB NOT NULL DEFAULT '{}',
    relations       JSONB NOT NULL DEFAULT '[]',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(workflow_id, agent_id, entity_name),
    INDEX idx_entity_memories_workflow_agent (workflow_id, agent_id),
    INDEX idx_entity_attributes (attributes) USING gin,
    INDEX idx_entity_relations (relations) USING gin
);
```

### 13.5 Migration Strategy

```python
# apps/api/src/db/migrations/env.py

from alembic import context
from sqlalchemy import engine_from_config

def run_migrations_online():
    """Run migrations with locking to prevent concurrent migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Acquire advisory lock for migration (prevent concurrent runs)
        connection.execute(text("SELECT pg_advisory_xact_lock(42)"))
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,     # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )
        with context.begin_transaction():
            context.run_migrations()
```

---

## 14. Memory Subsystem Architecture

### 14.1 Three-Tier Memory Model

```
┌────────────────────────────────────────────────────────────┐
│                    MemoryBridge                              │
│  (Unified interface — routes to correct backend by type)    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐   ┌────────────────┐   ┌───────────┐ │
│   │  Short-Term      │   │  Long-Term     │   │  Entity   │ │
│   │  (Redis DB 2)    │   │  (PGVector)    │   │  (JSONB)  │ │
│   │                  │   │                │   │           │ │
│   │  TTL: 3600s      │   │  Semantic      │   │  Structured│ │
│   │  Session context │   │  Search        │   │  Facts    │ │
│   │  Key-value       │   │  Embeddings    │   │  Relations │ │
│   │                  │   │  Cosine sim    │   │  GIN idx  │ │
│   └─────────────────┘   └────────────────┘   └───────────┘ │
│                                                             │
│  Namespace: crew:{workflow_id}:agent:{agent_id}:memory:{key}│
└────────────────────────────────────────────────────────────┘
```

### 14.2 MemoryBridge Implementation

[`apps/worker/src/runtime/memory/bridge.py`](apps/worker/src/runtime/memory/bridge.py)

```python
class MemoryBridge:
    """
    Unified memory interface for agent memory operations.

    Routes operations to the correct backend based on memory_type:
    - SHORT_TERM → Redis (with TTL)
    - LONG_TERM → PGVector (with embedding)
    - ENTITY → PostgreSQL JSONB (structured facts)

    All operations include workflow isolation via namespacing.
    """

    def __init__(self, redis_db, db_session):
        self._redis = redis_db
        self._db = db_session

    async def store(
        self,
        workflow_id: str,
        agent_id: str,
        memory_type: MemoryType,
        key: str,
        value: Any,
        metadata: dict | None = None,
    ) -> None:
        if memory_type == MemoryType.SHORT_TERM:
            await self._store_short_term(workflow_id, agent_id, key, value)
        elif memory_type == MemoryType.LONG_TERM:
            await self._store_long_term(workflow_id, agent_id, key, value, metadata)
        elif memory_type == MemoryType.ENTITY:
            await self._store_entity(workflow_id, agent_id, key, value)

    async def query(
        self,
        workflow_id: str,
        agent_id: str,
        memory_type: MemoryType,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[MemoryItem]:
        if memory_type == MemoryType.SHORT_TERM:
            return await self._query_short_term(workflow_id, agent_id, query)
        elif memory_type == MemoryType.LONG_TERM:
            return await self._query_long_term(workflow_id, agent_id, query, limit, threshold)
        elif memory_type == MemoryType.ENTITY:
            return await self._query_entity(workflow_id, agent_id, query, limit)

    async def snapshot(self, workflow_id: str) -> MemorySnapshot:
        """Capture full memory state for checkpointing."""
        return MemorySnapshot(
            workflow_id=workflow_id,
            short_term=await self._snapshot_short_term(workflow_id),
            long_term=await self._snapshot_long_term(workflow_id),
            entity=await self._snapshot_entity(workflow_id),
            timestamp=datetime.utcnow().isoformat(),
        )

    async def restore(self, workflow_id: str, snapshot: MemorySnapshot) -> None:
        """Restore memory state from a checkpoint snapshot."""
        await self._restore_short_term(workflow_id, snapshot.short_term)
        await self._restore_long_term(workflow_id, snapshot.long_term)
        await self._restore_entity(workflow_id, snapshot.entity)

    async def clear(
        self,
        workflow_id: str,
        agent_id: str | None = None,
        memory_type: MemoryType | None = None,
    ) -> None:
        """Clear memory for a workflow, optionally filtered by agent and type."""
        # Redis keys to delete
        pattern = f"crew:{workflow_id}:agent:{agent_id or '*'}:memory:*"
        if memory_type:
            pattern = f"crew:{workflow_id}:agent:{agent_id or '*'}:memory:{memory_type.value}:*"

        # ... clear operations for each backend

    # ---- Private backend implementations ----

    async def _store_short_term(self, workflow_id: str, agent_id: str, key: str, value: Any) -> None:
        redis_key = f"crew:{workflow_id}:agent:{agent_id}:memory:short_term:{key}"
        await self._redis.setex(redis_key, 3600, json.dumps(value))

    async def _store_long_term(
        self, workflow_id: str, agent_id: str, content: str, metadata: dict | None
    ) -> None:
        from pgvector.sqlalchemy import Vector

        # Generate embedding (call out to embedding service)
        embedding = await self._generate_embedding(content)

        memory = AgentMemory(
            workflow_id=workflow_id,
            agent_id=agent_id,
            memory_type="long_term",
            embedding=embedding,
            content=content,
            metadata=metadata or {},
        )
        self._db.add(memory)
        await self._db.flush()

    async def _query_long_term(
        self, workflow_id: str, agent_id: str, query: str, limit: int, threshold: float
    ) -> list[MemoryItem]:
        query_embedding = await self._generate_embedding(query)

        result = await self._db.execute(
            select(AgentMemory)
            .where(AgentMemory.workflow_id == workflow_id)
            .where(AgentMemory.agent_id == agent_id)
            .order_by(AgentMemory.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        memories = result.scalars().all()

        return [
            MemoryItem(
                content=m.content,
                metadata=m.metadata,
                score=1 - m.embedding.cosine_distance(query_embedding),
            )
            for m in memories
            if 1 - m.embedding.cosine_distance(query_embedding) >= threshold
        ]

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding via configured provider (OpenAI, Ollama, etc.)."""
        # ... call embedding API
        pass
```

### 14.3 Memory Namespace Isolation

```
Redis Key Structure (Short-Term):
  crew:{workflow_id}:agent:{agent_id}:memory:short_term:{conversation_key}

PGVector Row (Long-Term):
  workflow_id, agent_id, embedding, content, metadata

JSONB Row (Entity):
  workflow_id, agent_id, entity_name, attributes {}, relations []

This ensures:
- Full workflow isolation (no cross-workflow memory leaks)
- Agent-specific scoping within a workflow
- Bulk cleanup: DELETE FROM agent_memories WHERE workflow_id = X
- Replay isolation: replay executions get fresh memory namespaces
```

---

## 15. Audit Logging Architecture

### 15.1 Audit Log Model

All audit logs are **append-only**. No updates, no deletes. This provides an immutable trail for compliance and debugging.

[`apps/api/src/services/audit_service.py`](apps/api/src/services/audit_service.py)

```python
class AuditService:
    """
    Append-only audit logging service.

    All state-changing operations must call this service.
    Schema: { who, did what, to which resource, before/after state, when, from where }
    """

    def __init__(self, db):
        self._db = db

    async def log(
        self,
        user_id: UUID,
        action: str,           # workflow.run, agent.update, execution.pause, etc.
        resource_type: str,    # workflow, agent, execution, approval, etc.
        resource_id: UUID | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Write an immutable audit log entry."""
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )
        self._db.add(log_entry)
        # No flush needed — caller's transaction handles commit
```

### 15.2 Audit-Aware Service Decorator

```python
from functools import wraps
from ..services.audit_service import AuditService

def audit_log(
    action: str,
    resource_type: str,
    resource_id_arg: str | None = None,    # Name of arg containing resource ID
    before_state_arg: str | None = None,   # Name of arg containing before state
):
    """Decorator that automatically logs auditable actions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Capture before state if requested
            before = None
            if before_state_arg:
                resource_id = kwargs.get(resource_id_arg)
                before = await self._get_resource_state(resource_type, resource_id)

            # Execute the operation
            result = await func(self, *args, **kwargs)

            # Log the audit entry
            audit: AuditService = self._audit
            await audit.log(
                user_id=self._current_user.id,
                action=action,
                resource_type=resource_type,
                resource_id=kwargs.get(resource_id_arg) if resource_id_arg else result.id,
                before_state=before,
                after_state=await self._get_resource_state(resource_type, result.id),
                correlation_id=self._correlation_id,
            )
            return result
        return wrapper
    return decorator
```

### 15.3 Audit Events (Explicit)

For critical operations, audit events are also published to Redis so the frontend can show real-time audit notifications:

```python
# In ExecutionService.run()
await self._audit.log(
    user_id=user.id,
    action="workflow.run",
    resource_type="execution",
    resource_id=execution.id,
    before_state=None,
    after_state={"status": "PENDING", "config": config_summary},
    correlation_id=correlation_id,
)

# Also publish audit event for real-time display
await self._events.publish(RuntimeEvent(
    type=EventType.AUDIT_EVENT,  # Not in original spec, added for audit
    execution_id=str(execution.id),
    correlation_id=correlation_id,
    source=EventSource.API,
    data={
        "action": "workflow.run",
        "user_id": str(user.id),
        "resource_type": "execution",
    },
))
```

### 15.4 Audit Query API

```python
@router.get("/audit/logs")
async def get_audit_logs(
    user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: UUID | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    services: ServiceRegistry = Depends(get_services),
    current_user: UserContext = Depends(get_current_user),
):
    """Query audit logs with filters. Requires ADMIN role."""
    if "ADMIN" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    filters = {}
    if user_id: filters["user_id"] = user_id
    if action: filters["action"] = action
    if resource_type: filters["resource_type"] = resource_type
    if resource_id: filters["resource_id"] = resource_id

    return await services.audit.query(filters, from_date, to_date, limit, offset)
```

---

## 16. Authentication & Authorization Architecture

### 16.1 JWT Strategy

[`apps/api/src/services/auth_service.py`](apps/api/src/services/auth_service.py)

```python
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

class AuthService:
    """
    JWT-based authentication service.

    Access tokens: Short-lived (15 minutes)
    Refresh tokens: Long-lived (7 days), stored in Redis for revocation
    Password hashing: bcrypt via passlib
    """

    def __init__(self, db, redis):
        self._db = db
        self._redis = redis
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._algorithm = "HS256"
        self._secret = env.JWT_SECRET
        self._access_ttl = timedelta(minutes=15)
        self._refresh_ttl = timedelta(days=7)

    async def authenticate(self, email: str, password: str) -> AuthTokens | None:
        """Authenticate user credentials. Returns token pair on success."""
        user = await self._db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if not user or not self._pwd_context.verify(password, user.password_hash):
            return None

        return await self._create_tokens(user)

    async def refresh_access_token(self, refresh_token: str) -> AuthTokens:
        """Exchange a valid refresh token for a new token pair."""
        try:
            payload = jwt.decode(
                refresh_token, self._secret, algorithms=[self._algorithm]
            )
            if payload["type"] != "refresh":
                raise InvalidTokenError("Invalid token type")
        except jwt.PyJWTError:
            raise InvalidTokenError("Invalid or expired refresh token")

        # Check if token has been revoked
        if await self._redis.get(f"revoked_token:{payload['jti']}"):
            raise InvalidTokenError("Token has been revoked")

        user = await self._db.get(User, payload["sub"])
        return await self._create_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh token (add to Redis blacklist)."""
        try:
            payload = jwt.decode(
                refresh_token, self._secret, algorithms=[self._algorithm]
            )
            # Blacklist until token expiry
            exp = payload["exp"] - datetime.utcnow().timestamp()
            if exp > 0:
                await self._redis.setex(
                    f"revoked_token:{payload['jti']}", int(exp), "revoked"
                )
        except jwt.PyJWTError:
            pass  # Already invalid, noop

    async def _create_tokens(self, user: User) -> AuthTokens:
        now = datetime.utcnow()
        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "roles": user.roles,
            "type": "access",
            "iat": now,
            "exp": now + self._access_ttl,
            "jti": uuid4().hex,
        }
        refresh_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "iat": now,
            "exp": now + self._refresh_ttl,
            "jti": uuid4().hex,
        }
        return AuthTokens(
            access_token=jwt.encode(access_payload, self._secret, algorithm=self._algorithm),
            refresh_token=jwt.encode(refresh_payload, self._secret, algorithm=self._algorithm),
            expires_in=int(self._access_ttl.total_seconds()),
        )
```

### 16.2 RBAC Model

```python
# packages/shared-types/src/constants/roles.py

class UserRole(str, Enum):
    ADMIN = "ADMIN"           # Full system access
    OPERATOR = "OPERATOR"     # Can run/manage workflows
    REVIEWER = "REVIEWER"     # Can approve HITL tasks
    VIEWER = "VIEWER"         # Read-only access

# apps/api/src/middleware/auth.py

class AuthMiddleware:
    """Validates JWT on every request (except public routes)."""

    PUBLIC_PATHS = {
        "/health",
        "/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
    }

    async def __call__(self, request: Request, call_next):
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"code": "MISSING_AUTH", "message": "Authorization header required"},
            )

        token = auth_header[7:]
        try:
            payload = jwt.decode(token, env.JWT_SECRET, algorithms=["HS256"])
            request.state.user = UserContext(
                id=payload["sub"],
                email=payload["email"],
                roles=payload["roles"],
            )
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"code": "TOKEN_EXPIRED", "message": "Access token expired"},
            )
        except jwt.PyJWTError:
            return JSONResponse(
                status_code=401,
                content={"code": "INVALID_TOKEN", "message": "Invalid access token"},
            )

        return await call_next(request)


# apps/api/src/middleware/rbac.py

def require_role(role: UserRole):
    """Dependency that enforces a minimum role level."""
    async def checker(user: UserContext = Depends(get_current_user)):
        if role not in user.roles and UserRole.ADMIN not in user.roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {role.value}",
            )
        return user
    return checker
```

### 16.3 Route Protection Matrix

```python
# apps/api/src/api/routes/workflows.py

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])

@router.get("/")
async def list_workflows(
    services: ServiceRegistry = Depends(get_services),
    user: UserContext = Depends(require_role(UserRole.VIEWER)),
):
    return await services.workflow.list(user.id)

@router.post("/run")
async def run_workflow(
    body: RunWorkflowRequest,
    services: ServiceRegistry = Depends(get_services),
    user: UserContext = Depends(require_role(UserRole.OPERATOR)),
):
    return await services.execution.run(workflow_id=body.workflow_id, user_id=user.id)

@router.post("/pause")
async def pause_workflow(
    body: PauseWorkflowRequest,
    services: ServiceRegistry = Depends(get_services),
    user: UserContext = Depends(require_role(UserRole.OPERATOR)),
):
    return await services.execution.pause(body.execution_id)

@router.get("/audit")
async def get_audit_logs(
    services: ServiceRegistry = Depends(get_services),
    user: UserContext = Depends(require_role(UserRole.ADMIN)),
):
    """Audit log access restricted to ADMIN only."""
    return await services.audit.query(...)
```

---

## 17. Infrastructure Topology

### 17.1 Docker Compose Architecture

```yaml
# docker-compose.yml

version: "3.9"

services:
  # ──────────────────────────────────────────
  # Reverse Proxy
  # ──────────────────────────────────────────
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./infra/docker/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - web
      - api
    networks:
      - frontend

  # ──────────────────────────────────────────
  # Frontend
  # ──────────────────────────────────────────
  web:
    build:
      context: .
      dockerfile: infra/docker/web.Dockerfile
    expose:
      - "3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000/api/v1
    depends_on:
      - api
    networks:
      - frontend
      - backend

  # ──────────────────────────────────────────
  # API Server (FastAPI)
  # ──────────────────────────────────────────
  api:
    build:
      context: .
      dockerfile: infra/docker/api.Dockerfile
    expose:
      - "8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://crewai:crewai@postgres:5432/crewai
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
      - CORS_ORIGINS=http://localhost:3000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./apps/api/src:/app/apps/api/src
    command: uvicorn apps.api.src.main:app --host 0.0.0.0 --port 8000 --reload --workers 2
    networks:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ──────────────────────────────────────────
  # Celery Workers
  # ──────────────────────────────────────────
  worker-default:
    build:
      context: .
      dockerfile: infra/docker/worker.Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://crewai:crewai@postgres:5432/crewai
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    command: celery -A apps.worker.src.celery_app worker -Q workflow_default,workflow_low --concurrency=4 --prefetch-multiplier=1 --loglevel=info
    volumes:
      - ./apps/worker/src:/app/apps/worker/src
    restart: unless-stopped
    networks:
      - backend

  worker-control:
    build:
      context: .
      dockerfile: infra/docker/worker.Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://crewai:crewai@postgres:5432/crewai
      - REDIS_URL=redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    command: celery -A apps.worker.src.celery_app worker -Q workflow_control --concurrency=2 --prefetch-multiplier=1 --loglevel=info
    volumes:
      - ./apps/worker/src:/app/apps/worker/src
    restart: unless-stopped
    networks:
      - backend

  worker-hitl:
    build:
      context: .
      dockerfile: infra/docker/worker.Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://crewai:crewai@postgres:5432/crewai
      - REDIS_URL=redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    command: celery -A apps.worker.src.celery_app worker -Q hitl --concurrency=2 --prefetch-multiplier=1 --loglevel=info
    volumes:
      - ./apps/worker/src:/app/apps/worker/src
    restart: unless-stopped
    networks:
      - backend

  # ──────────────────────────────────────────
  # Celery Beat (scheduler)
  # ──────────────────────────────────────────
  worker-beat:
    build:
      context: .
      dockerfile: infra/docker/worker.Dockerfile
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      redis:
        condition: service_started
    command: celery -A apps.worker.src.celery_app beat --loglevel=info
    networks:
      - backend

  # ──────────────────────────────────────────
  # Redis (broker + pub/sub + short-term memory)
  # ──────────────────────────────────────────
  redis:
    image: redis:7-alpine
    expose:
      - "6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  # ──────────────────────────────────────────
  # PostgreSQL + PGVector
  # ──────────────────────────────────────────
  postgres:
    image: pgvector/pgvector:pg16
    expose:
      - "5432"
    environment:
      - POSTGRES_USER=crewai
      - POSTGRES_PASSWORD=crewai
      - POSTGRES_DB=crewai
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U crewai"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  # ──────────────────────────────────────────
  # Ollama (local LLM inference)
  # ──────────────────────────────────────────
  ollama:
    image: ollama/ollama:latest
    expose:
      - "11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - backend

volumes:
  redis_data:
  postgres_data:
  ollama_data:

networks:
  frontend:
  backend:
    internal: true  # Backend services not exposed externally
```

### 17.2 Service Dependencies

```
             ┌──────────┐
             │  nginx   │  (port 80 — reverse proxy)
             └────┬─────┘
                  │
          ┌───────┴───────┐
          │               │
     ┌────▼────┐    ┌─────▼─────┐
     │   web   │    │    api    │  (port 8000 — FastAPI)
     │ (3000)  │    └─────┬─────┘
     └─────────┘          │
                          │
              ┌───────────┼───────────┐
              │           │           │
         ┌────▼────┐ ┌───▼───┐ ┌────▼────┐
         │  redis  │ │postgre│ │ worker  │
         │ (6379)  │ │(5432) │ │ pool    │
         └─────────┘ └───────┘ └─────────┘
                                     │
                               ┌─────┴─────┐
                               │   ollama  │
                               │  (11434)  │
                               └───────────┘
```

### 17.3 Horizontal Scaling Strategy

| Component | Scale Mechanism | Triggers | Notes |
|-----------|----------------|----------|-------|
| **API** | Behind nginx load balancer, add containers | CPU > 70%, connections > 500 | Stateless — no session affinity needed |
| **worker-default** | Add containers with same queue config | Queue depth > 100 | Prefetch=1 ensures fair distribution |
| **worker-control** | 2 dedicated containers max | — | Low volume, control commands only |
| **worker-hitl** | Add containers | Pending HITL count > 50 | Lightweight, fast operations |
| **Redis** | Vertical (more memory) or Cluster mode | Memory > 80% | Pub/Sub doesn't scale horizontally in cluster mode |
| **PostgreSQL** | Connection pooling (pgbouncer) + read replicas | Connections > 100, query latency > 200ms | PGVector on read replicas |

### 17.4 Redis Failover Strategy

```
In production (non-Docker):
- Redis Sentinel for HA with automatic failover
- 3 Sentinel nodes, 1 primary, 2 replicas
- Pub/Sub channels survive failover (ephemeral)

In Docker (development):
- Single Redis node with AOF persistence
- Restart policy: unless-stopped
- Health check ensures readiness
```

---

## 18. Backend Folder Structure

```
project-root/
├── apps/
│   ├── api/                                    # FastAPI Server
│   │   └── src/
│   │       ├── main.py                         # App factory + lifespan
│   │       ├── config.py                       # Environment variables + settings
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── dependencies.py             # FastAPI dependency injection
│   │       │   ├── health.py                   # /health, /ready, /metrics endpoints
│   │       │   └── routes/
│   │       │       ├── __init__.py              # Router aggregation
│   │       │       ├── auth.py                 # POST /auth/login, /auth/refresh, /auth/logout
│   │       │       ├── workflows.py            # CRUD /workflows
│   │       │       ├── agents.py               # CRUD /agents
│   │       │       ├── tasks.py                # CRUD /tasks
│   │       │       ├── execution.py            # POST /workflow/run, /pause, /resume, /kill, /replay
│   │       │       ├── stream.py               # GET /workflow/stream/{id} (SSE)
│   │       │       ├── approvals.py            # HITL endpoints
│   │       │       ├── templates.py            # Workflow template CRUD
│   │       │       ├── metrics.py              # GET /metrics/{workflow_id}/...
│   │       │       ├── memory.py               # Memory CRUD + clearance
│   │       │       ├── audit.py                # GET /audit/logs (ADMIN only)
│   │       │       └── users.py                # User management (ADMIN only)
│   │       ├── services/
│   │       │   ├── __init__.py                 # ServiceRegistry
│   │       │   ├── auth_service.py             # JWT issue/verify, RBAC
│   │       │   ├── workflow_service.py         # Workflow CRUD + versioning
│   │       │   ├── execution_service.py        # Execution orchestration
│   │       │   ├── agent_service.py            # Agent CRUD
│   │       │   ├── task_service.py             # Task CRUD
│   │       │   ├── tool_service.py             # Tool registration
│   │       │   ├── approval_service.py         # HITL management
│   │       │   ├── metrics_service.py          # Token/timing/failure aggregation
│   │       │   ├── memory_service.py           # Three-tier memory operations
│   │       │   ├── template_service.py         # Template CRUD
│   │       │   ├── audit_service.py            # Append-only audit logging
│   │       │   └── user_service.py             # User CRUD
│   │       ├── events/
│   │       │   ├── __init__.py
│   │       │   ├── engine.py                   # EventEngine: Redis subscriber lifecycle
│   │       │   ├── consumer.py                 # Event consumer: Pub/Sub → service handlers
│   │       │   ├── sse_manager.py              # SSE connection lifecycle per client
│   │       │   └── handlers/
│   │       │       ├── __init__.py
│   │       │       ├── workflow_events.py      # Workflow lifecycle event handlers
│   │       │       ├── agent_events.py         # Agent execution event handlers
│   │       │       ├── hitl_events.py          # HITL event handlers
│   │       │       ├── metrics_events.py       # Metrics event handlers
│   │       │       └── audit_events.py         # Audit event handlers
│   │       ├── middleware/
│   │       │   ├── __init__.py
│   │       │   ├── auth.py                     # JWT validation middleware
│   │       │   ├── rbac.py                     # Role-based access control
│   │       │   ├── rate_limiter.py             # Token bucket rate limiting + circuit breaker
│   │       │   ├── request_id.py              # X-Request-ID / correlation ID
│   │       │   └── error_handler.py            # Global exception handler
│   │       ├── models/                         # Pydantic domain models (API contracts)
│   │       │   ├── __init__.py
│   │       │   ├── user.py                     # UserContext, AuthTokens, LoginRequest
│   │       │   ├── workflow.py                 # WorkflowConfig, WorkflowSummary
│   │       │   ├── execution.py                # RunRequest, ExecutionStatus, PauseRequest
│   │       │   ├── agent.py                    # AgentConfig, AgentSummary
│   │       │   ├── task.py                     # TaskConfig, TaskSummary
│   │       │   ├── approval.py                 # ApprovalRequest, ApproveRequest, RejectRequest
│   │       │   ├── metrics.py                  # TokenMetrics, ExecutionTimeline, FailureMetric
│   │       │   ├── memory.py                   # MemoryItem, MemorySnapshot, MemoryQuery
│   │       │   ├── template.py                 # TemplateSummary, TemplateDetail
│   │       │   └── audit.py                    # AuditLogEntry, AuditQuery
│   │       └── db/
│   │           ├── __init__.py
│   │           ├── session.py                  # DatabaseSessionManager (async engine + sessions)
│   │           ├── models/                     # SQLAlchemy ORM models
│   │           │   ├── __init__.py
│   │           │   ├── base.py                 # DeclarativeBase + common mixins
│   │           │   ├── user.py                 # User ORM model
│   │           │   ├── workflow.py             # Workflow ORM model
│   │           │   ├── execution.py            # Execution ORM model
│   │           │   ├── checkpoint.py           # Checkpoint ORM model
│   │           │   ├── agent.py                # Agent ORM model
│   │           │   ├── approval.py             # Approval ORM model
│   │           │   ├── log.py                  # ExecutionLog ORM model
│   │           │   ├── metrics.py              # TokenMetrics ORM model
│   │           │   ├── memory.py               # AgentMemory, EntityMemory ORM models
│   │           │   ├── audit.py                # AuditLog ORM model
│   │           │   └── template.py             # WorkflowTemplate ORM model
│   │           ├── repositories/              # Data access layer
│   │           │   ├── __init__.py
│   │           │   ├── base.py                 # BaseRepository (abstract CRUD)
│   │           │   ├── workflow_repository.py
│   │           │   ├── execution_repository.py
│   │           │   ├── checkpoint_repository.py
│   │           │   ├── agent_repository.py
│   │           │   ├── approval_repository.py
│   │           │   ├── log_repository.py
│   │           │   ├── metrics_repository.py
│   │           │   ├── memory_repository.py
│   │           │   ├── audit_repository.py
│   │           │   └── user_repository.py
│   │           └── migrations/                 # Alembic migrations
│   │               ├── env.py
│   │               ├── alembic.ini
│   │               └── versions/
│   │                   ├── 001_initial_schema.py
│   │                   ├── 002_add_checkpoints.py
│   │                   ├── 003_add_pgvector.py
│   │                   └── ...
│   │
│   └── worker/                                 # Celery Worker
│       └── src/
│           ├── __init__.py
│           ├── celery_app.py                   # Celery application instance
│           ├── config.py                       # Worker configuration
│           ├── tasks/
│           │   ├── __init__.py
│           │   ├── execution_tasks.py          # run_crew, control_crew
│           │   └── hitl_tasks.py               # process_hitl_decision
│           ├── orchestrator/
│           │   ├── __init__.py
│           │   ├── execution_orchestrator.py   # Lifecycle coordinator
│           │   ├── state_machine.py            # State transition validation
│           │   └── replay_engine.py            # Replay orchestration
│           ├── runtime/
│           │   ├── __init__.py
│           │   ├── crew_builder.py             # Dynamic CrewAI crew construction
│           │   ├── crew_builder.py
│           │   ├── tool_registry.py            # Tool resolution/injection
│           │   └── memory/
│           │       ├── __init__.py
│           │       └── bridge.py               # MemoryBridge implementation
│           ├── checkpoint/
│           │   ├── __init__.py
│           │   └── manager.py                  # CheckpointManager
│           └── events/
│               ├── __init__.py
│               └── publisher.py               # EventPublisher (Redis Pub/Sub + Streams)

├── packages/
│   ├── shared-types/                           # Shared contracts
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── types/                          # Domain types
│   │       │   ├── __init__.py
│   │       │   ├── workflow.py                 # WorkflowConfig, AgentConfig, TaskConfig
│   │       │   ├── execution.py                # ExecutionStatus, ExecutionContext
│   │       │   └── common.py                   # UUID, Timestamp, PaginatedResponse
│   │       ├── events/                         # Event schemas
│   │       │   ├── __init__.py
│   │       │   ├── base.py                     # RuntimeEvent envelope
│   │       │   └── data.py                     # Typed event data payloads
│   │       ├── schemas/                        # Zod-compatible Pydantic validation
│   │       │   ├── __init__.py
│   │       │   ├── workflow_schema.py           # Workflow config validation
│   │       │   ├── agent_schema.py
│   │       │   └── execution_schema.py
│   │       └── constants/
│   │           ├── __init__.py
│   │           ├── states.py                   # WorkflowStatus, AgentExecutionStatus enums
│   │           ├── events.py                   # EventType, EventSource enums
│   │           └── roles.py                    # UserRole enum
│   │
│   └── crew-runtime/                           # CrewAI runtime abstraction
│       └── src/
│           ├── __init__.py
│           ├── runtime.py                      # CrewRuntime class
│           ├── builder.py                      # CrewBuilder
│           ├── interceptor.py                  # CallbackInterceptor
│           ├── tool_registry.py                # ToolRegistry
│           ├── token_tracker.py                # TokenTracker
│           └── memory/
│               ├── __init__.py
│               └── bridge.py                   # MemoryBridge interface

├── infra/
│   ├── docker/
│   │   ├── api.Dockerfile
│   │   ├── worker.Dockerfile
│   │   ├── web.Dockerfile
│   │   └── nginx.conf
│   ├── kubernetes/                             # Future: K8s manifests
│   │   ├── api-deployment.yaml
│   │   ├── worker-deployment.yaml
│   │   └── ...
│   └── scripts/
│       ├── backup.sh                           # pg_dump + Redis RDB + S3 sync
│       ├── restore.sh                          # Restore from backup
│       └── migrate.sh                          # Alembic migration runner

├── docker-compose.yml
├── docker-compose.prod.yml                     # Production overrides (secrets, replicas)
├── pyproject.toml                              # Root Python project config
├── requirements.txt                            # Production dependencies
└── Makefile                                    # Dev commands
```

---

## 19. Shared Contract Strategy

### 19.1 Contract Layers

```
┌────────────────────────────────────────────────────────────┐
│                    CONTRACT HIERARCHY                        │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: Enums & Constants (shared-types/constants/)        │
│  ├── WorkflowStatus, AgentExecutionStatus                   │
│  ├── EventType, EventSource                                 │
│  ├── UserRole, MemoryType                                   │
│  └── Shared across ALL services                             │
│                                                             │
│  Layer 2: Event Schemas (shared-types/events/)              │
│  ├── RuntimeEvent envelope                                  │
│  ├── Typed event data payloads                              │
│  └── Used by: API, Worker, Frontend (via SSE)              │
│                                                             │
│  Layer 3: Domain Types (shared-types/types/)                │
│  ├── WorkflowConfig, AgentConfig, TaskConfig                │
│  ├── ExecutionContext, CheckpointData                       │
│  └── Used by: API ↔ Worker ↔ Runtime                       │
│                                                             │
│  Layer 4: Validation Schemas (shared-types/schemas/)        │
│  ├── Pydantic models for API request/response validation    │
│  ├── Mirror schemas in Zod for frontend validation          │
│  └── Single source of truth for all data shapes             │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### 19.2 Type Generation Strategy

Types are defined **once** in the Python `shared-types` package. Frontend TypeScript types are generated from these Python definitions:

```python
# packages/shared-types/src/events/base.py

class RuntimeEvent(BaseModel):
    """This class is the canonical definition of the event envelope.
    
    When this changes, the TypeScript equivalent must be regenerated.
    Script: scripts/generate_types.sh
    """
    id: str
    type: EventType
    timestamp: str
    execution_id: str
    correlation_id: str
    source: EventSource
    step: int
    sequence: int
    data: dict
    version: int
```

```typescript
// Generated: packages/shared-types/src/events/base.ts
// Auto-generated from Python shared-types. DO NOT EDIT MANUALLY.

export interface RuntimeEvent<T = unknown> {
  id: string;
  type: EventType;
  timestamp: string;
  executionId: string;
  correlationId: string;
  source: EventSource;
  step: number;
  sequence: number;
  data: T;
  version: number;
}
```

### 19.3 Validation Consistency

Both Python (Pydantic) and TypeScript (Zod) schemas must validate **identical shapes**:

```python
# packages/shared-types/src/schemas/workflow_schema.py

class WorkflowConfigSchema(BaseModel):
    """Canonical workflow config validation. Mirrored in Zod for frontend."""
    model_config = ConfigDict(extra="forbid")  # No extra fields

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    agents: list[AgentConfigSchema] = Field(..., min_length=1, max_length=50)
    tasks: list[TaskConfigSchema] = Field(..., min_length=1, max_length=200)
    process_type: Literal["sequential", "hierarchical"] = "sequential"
    version: int = Field(default=1, ge=1)
```

```typescript
// packages/shared-types/src/schemas/workflow-schema.ts
// Must be manually kept in sync with Python version above

export const WorkflowConfigSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().max(2000).optional(),
  agents: z.array(AgentConfigSchema).min(1).max(50),
  tasks: z.array(TaskConfigSchema).min(1).max(200),
  process_type: z.enum(['sequential', 'hierarchical']).default('sequential'),
  version: z.number().int().min(1).default(1),
}).strict();  // No extra fields
```

### 19.4 Dependency Graph

```
                    ┌───────────────────────────┐
                    │  packages/shared-types     │
                    │  (constants, events,       │
                    │   types, schemas)          │
                    └──────────┬────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  apps/api        │  │  apps/worker     │  │  apps/web        │
│  (FastAPI)       │  │  (Celery)        │  │  (Next.js)       │
│                  │  │                  │  │                  │
│  Imports:        │  │  Imports:        │  │  Imports:        │
│  - shared-types  │  │  - shared-types  │  │  - shared-types  │
│  - crew-runtime  │  │  - crew-runtime  │  │                  │
└─────────────────┘  └──────────────────┘  └──────────────────┘
         │                    │
         └────────────────────┘
                    │
                    ▼
          ┌──────────────────┐
          │ packages/crew-   │
          │ runtime          │
          │                  │
          │ Imports:         │
          │ - shared-types   │
          │ (ONLY)           │
          │                  │
          │ ZERO HTTP deps   │
          │ ZERO framework   │
          │ Pure execution   │
          └──────────────────┘
```

### 19.5 Strict Import Rules

```
RULE: No app imports another app's internals.

✅ ALLOWED:
  apps/api → packages/shared-types
  apps/api → packages/crew-runtime
  apps/worker → packages/shared-types
  apps/worker → packages/crew-runtime
  apps/web → packages/shared-types
  packages/crew-runtime → packages/shared-types

❌ FORBIDDEN:
  apps/web → apps/api (never)
  apps/web → apps/worker (never)
  apps/web → packages/crew-runtime (never)
  apps/api → apps/web (never)
  packages/crew-runtime → apps/api (framework dependency)
  packages/crew-runtime → apps/worker (framework dependency)
```

### 19.6 Versioning Strategy

| Contract | Versioning | Frequency | Breaking Change Protocol |
|----------|-----------|-----------|-------------------------|
| **Event schema** | Major version in `RuntimeEvent.version` | Rare | New event types are additive; breaking changes add new envelope version |
| **API routes** | URL prefix `/api/v1/` | Rare | New endpoints added before old ones deprecated |
| **Domain types** | Patch version in `shared-types` package | Per feature | Type generation script updated with new fields |
| **Database schema** | Alembic migration sequence | Per feature | Backward-compatible migrations only; no destructive changes in same release |

---

> *End of Backend Runtime Architecture Specification.*

> **Next Step**: Phase 0 implementation — monorepo scaffold, Docker Compose skeleton, shared-types package, and database migration foundation.
