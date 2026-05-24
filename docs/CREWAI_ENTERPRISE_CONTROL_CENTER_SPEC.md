# CrewAI Enterprise Control Center
## Production Build Specification

Version: 1.0
Target: Enterprise-grade AI Multi-Agent Operating System
Architecture: Full-stack
Frontend: Next.js 15 + React 19 + TypeScript
Backend: FastAPI + CrewAI + Celery
Infra: Docker + Redis + PostgreSQL + PGVector + Ollama

---

# 1. PRODUCT VISION

Build a full enterprise control center for managing CrewAI multi-agent systems visually.

The system should function like:

- VSCode
- Figma Canvas
- n8n Workflow Builder
- Datadog Monitoring
- AI Operations Command Center

Users must be able to:

- Create agents visually
- Connect workflows
- Assign tools
- Configure memory + models
- Run workflows
- Observe internal reasoning
- Pause/resume execution
- Replay failures
- Approve HITL tasks
- Monitor token costs
- Persist reusable workflow templates

---

# 2. MONOREPO STRUCTURE

/project-root
  /apps
    /web
    /api
    /worker
  /packages
    /shared-types
    /ui
    /crew-runtime
  /infra
    docker
    kubernetes
  /docs
  docker-compose.yml

---

# 3. FRONTEND

Framework:
- Next.js App Router
- TypeScript
- TailwindCSS
- Shadcn/UI
- Zustand
- React Flow
- Framer Motion
- Monaco Editor

Folder:

apps/web/src

/app
/components
/store
/lib
/types
/hooks
/services

---

# 4. CORE UI LAYOUT

Must be IDE-style.

Layout:

-------------------------------------------------------
| Left Sidebar | Main Canvas | Right Inspector Panel |
-------------------------------------------------------
| Bottom Observability Terminal / Metrics Dashboard   |
-------------------------------------------------------

Resizable panes required.

Use:
react-resizable-panels

Light theme mandatory.

---

# 5. LEFT SIDEBAR MODULES

Tabs:

## Agents
Draggable templates:
- Research Agent
- Engineer Agent
- QA Agent
- PM Agent
- Analyst Agent

## Tasks
- Sequential Task
- Conditional Task
- Human Approval Task
- Retry Task

## Tools
- Web Search
- SQL
- API Connector
- File Reader
- Python Executor
- Vector Search

## Templates
Saved reusable workflows

---

# 6. VISUAL WORKFLOW CANVAS

Use React Flow.

Node Types:

## Agent Node
Fields:
- avatar
- role
- llm model
- status glow
- memory enabled
- token count

States:
- idle gray
- running blue pulse
- success green
- failed red flash
- waiting-human orange

## Task Node
Fields:
- title
- status
- progress bar
- expected output

## Tool Node
Fields:
- tool icon
- permissions

Edges:
Animated directional flow.

Features:

- drag-drop
- zoom
- minimap
- pan
- auto-layout
- hierarchy mode
- sequential mode
- edge validation
- loop prevention

---

# 7. YAML <-> VISUAL SYNC

Two-way sync required.

Panel:

Monaco editor.

Files:

agents.yaml
tasks.yaml
workflow.yaml

Changes in UI update YAML.

Pasting YAML updates graph.

Parser:
js-yaml

Validation:
zod schemas

---

# 8. RIGHT INSPECTOR PANEL

Dynamic based on selected node.

## Agent Inspector

### Persona
- role
- goal
- backstory markdown editor

### AI Enhancer Button
Prompt:
Expand role using CrewAI best practices.

### Memory Matrix
toggles:
- short term
- long term
- entity memory

Clear DB button

### LLM Routing
Dropdown:

- GPT
- Claude
- Gemini
- Ollama local

Parameters:
- temperature
- max tokens
- iterations
- RPM limit

---

## Task Inspector

Fields:
- description
- expected output
- timeout
- retries
- requires approval
- priority

---

# 9. OBSERVABILITY TERMINAL

Bottom dock panel.

Looks like VSCode terminal.

Real-time streaming:

Tags:

[Planning]
[Thought]
[Action]
[Observation]
[Tool]
[Error]

Colorized.

Supports:

- filtering by agent
- search
- pause scroll
- export logs

Transport:
SSE

---

# 10. METRICS DASHBOARD

Tabs:

## Token Cost
Charts:
- per agent
- per task
- per workflow

## Execution Timeline
Gantt chart

## Failure Heatmap

Libraries:
recharts

---

# 11. EXECUTION CONTROLS

Toolbar buttons:

Run
Pause
Resume
Stop
Retry
Replay
Rollback Snapshot

Execution state machine:

PENDING
RUNNING
SUSPENDED
FAILED
SUCCESS

---

# 12. HUMAN-IN-THE-LOOP

Approval Inbox page.

Cards:
- task
- requesting agent
- draft preview

Detail View:

Left:
AI draft

Right:
Human edit

Bottom:
Instruction box

Buttons:
Approve
Reject
Regenerate
Resume Workflow

---

# 13. BACKEND

Framework:
FastAPI

Structure:

apps/api/src

/api
/services
/models
/schemas
/executors
/events
/db

Endpoints:

POST /workflow/run
POST /workflow/pause
POST /workflow/resume
POST /workflow/kill
GET /workflow/status/{id}
GET /workflow/stream/{id}
POST /workflow/replay/{id}

POST /agents
GET /agents
PUT /agents/{id}

POST /tasks
GET /tasks

---

# 14. CREWAI RUNTIME

Runtime abstraction layer.

Responsibilities:

- construct crews dynamically
- bind agents
- bind tools
- attach memory
- execute tasks
- capture callbacks
- stream events

Integrate CrewAI callbacks for observability.

---

# 15. ASYNC EXECUTION ENGINE

Use:

Celery + Redis

Queue:

workflow_queue

Workers execute:

CrewRunner.run()

Support:

- cancellation
- retries
- checkpoint save
- resumable execution

---

# 16. DATABASE

PostgreSQL + PGVector

Tables:

users
agents
tasks
workflows
executions
snapshots
approvals
logs
memories

ORM:
SQLAlchemy 2

Migrations:
Alembic

---

# 17. MEMORY SUBSYSTEM

Short-term:
Redis

Long-term:
PGVector

Entity Memory:
JSONB

Functions:

store_memory()
query_memory()
clear_memory()

---

# 18. LOCAL LLM SUPPORT

Ollama integration.

Supported:

llama3
mistral
deepseek
codellama

API wrapper:

/llm/route

Model selection per agent.

---

# 19. AUTH

JWT auth

RBAC roles:

Admin
Operator
Reviewer
Viewer

Protected routes required.

---

# 20. DOCKER

Services:

web
api
worker
redis
postgres
pgvector
ollama

Single command:

docker compose up

---

# 21. TESTING

Frontend:
Vitest + RTL

Backend:
Pytest

E2E:
Playwright

Coverage target:
90%

---

# 22. CODING RULES

Strict TypeScript.

No any.

Modular components only.

Reusable hooks.

No duplicated logic.

Enterprise naming conventions.

No placeholder UI.

No mock fake implementations unless explicitly marked.

Production-ready code only.

---

# 23. BUILD ORDER

Phase 1
- project scaffolding
- layout
- auth
- DB

Phase 2
- canvas
- nodes
- inspector
- YAML sync

Phase 3
- CrewAI runtime
- execution engine

Phase 4
- observability terminal

Phase 5
- HITL

Phase 6
- metrics + replay

Phase 7
- production hardening

---

# 24. FINAL DELIVERABLE

Fully operational local enterprise control center where user can:

Create agents visually
Build workflows
Run CrewAI
Observe reasoning live
Pause/approve
Replay failures
Track cost
Persist memory
Deploy locally via Docker

No demo shortcuts allowed.