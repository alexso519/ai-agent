# CrewAI Enterprise Control Center — AI Orchestration Architecture

> **Document Type**: Principal AI Orchestration Architecture Specification  
> **Status**: Pre-Implementation Design  
> **Version**: 1.0  
> **Architecture Source**: [`ARCHITECTURAL_ANALYSIS.md`](ARCHITECTURAL_ANALYSIS.md), [`FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md), [`BACKEND_RUNTIME_ARCHITECTURE.md`](BACKEND_RUNTIME_ARCHITECTURE.md)

---

## Table of Contents

1. [Orchestration Engine Architecture](#1-orchestration-engine-architecture)
2. [Planning Engine Architecture](#2-planning-engine-architecture)
3. [Autonomous Workflow Generation Pipeline](#3-autonomous-workflow-generation-pipeline)
4. [Natural-Language-to-Workflow Pipeline](#4-natural-language-to-workflow-pipeline)
5. [Dynamic Agent Generation System](#5-dynamic-agent-generation-system)
6. [Task Decomposition Engine](#6-task-decomposition-engine)
7. [Tool Routing Architecture](#7-tool-routing-architecture)
8. [Memory Orchestration Architecture](#8-memory-orchestration-architecture)
9. [Execution Planning Lifecycle](#9-execution-planning-lifecycle)
10. [Agent Communication Model](#10-agent-communication-model)
11. [Runtime Adaptation Architecture](#11-runtime-adaptation-architecture)
12. [Replay-Aware Orchestration](#12-replay-aware-orchestration)
13. [Human-in-the-Loop Orchestration Flow](#13-human-in-the-loop-orchestration-flow)
14. [Approval Insertion Strategy](#14-approval-insertion-strategy)
15. [Token Optimization Strategy](#15-token-optimization-strategy)
16. [Model Routing Architecture](#16-model-routing-architecture)
17. [Ollama Integration Strategy](#17-ollama-integration-strategy)
18. [Prompt Template Architecture](#18-prompt-template-architecture)
19. [Orchestration Event Taxonomy](#19-orchestration-event-taxonomy)
20. [Orchestration Debugging Strategy](#20-orchestration-debugging-strategy)

---

## 1. Orchestration Engine Architecture

### 1.1 Core Principle

The orchestration engine is the **central nervous system** of the AI operating system. It is **not** a monolithic controller but a **layered orchestration graph** where each layer has distinct responsibilities, observability hooks, and recovery mechanisms.

### 1.2 Orchestration Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION ENGINE (Top-Level)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────┐ │
│  │  STRATEGIC LAYER  │  │  TACTICAL LAYER   │  │  OPERATIONAL LAYER    │ │
│  │  (What to do)     │  │  (How to do it)   │  │  (Do it)              │ │
│  ├───────────────────┤  ├───────────────────┤  ├───────────────────────┤ │
│  │ - Goal analysis   │  │ - Agent selection │  │ - Crew construction   │ │
│  │ - Workflow design │  │ - Task assignment │  │ - Task execution      │ │
│  │ - Planner agents  │  │ - Tool routing    │  │ - Tool invocation     │ │
│  │ - Decomposition   │  │ - Memory attach   │  │ - Observation capture  │ │
│  │ - Strategy eval   │  │ - Model routing   │  │ - Event emission      │ │
│  └───────────────────┘  └───────────────────┘  └───────────────────────┘ │
│                                                                           │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────┐ │
│  │  OBSERVABILITY    │  │  RECOVERY         │  │  GOVERNANCE           │ │
│  │  LAYER            │  │  LAYER            │  │  LAYER                │ │
│  ├───────────────────┤  ├───────────────────┤  ├───────────────────────┤ │
│  │ - Event capture   │  │ - Checkpoint      │  │ - Permission check    │ │
│  │ - Metrics stream  │  │ - Retry logic     │  │ - Audit logging       │ │
│  │ - Trace prop.     │  │ - Fallback paths  │  │ - HITL insertion      │ │
│  │ - Log aggregation │  │ - Degradation     │  │ - Compliance          │ │
│  └───────────────────┘  └───────────────────┘  └───────────────────────┘ │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Orchestration Graph Model

Orchestration is modeled as a **directed acyclic graph (DAG)** of orchestration nodes, not a linear chain:

```typescript
// packages/shared-types/src/types/orchestration.ts

interface OrchestrationGraph {
  id: string;
  workflowId: string;
  nodes: OrchestrationNode[];
  edges: OrchestrationEdge[];
  metadata: {
    version: number;
    createdAt: string;
    strategy: 'manual' | 'autonomous' | 'nlp-generated';
    tokenBudget: number;
    maxSteps: number;
  };
}

interface OrchestrationNode {
  id: string;
  type: OrchestrationNodeType;
  // STRATEGIC types:
  // | 'GOAL_DEFINITION' | 'DECOMPOSITION' | 'AGENT_SELECTION'
  // | 'WORKFLOW_DESIGN' | 'STRATEGY_EVALUATION'
  // TACTICAL types:
  // | 'TASK_ASSIGNMENT' | 'TOOL_ROUTING' | 'MEMORY_ATTACH'
  // | 'MODEL_SELECTION' | 'PROMPT_COMPOSITION'
  // OPERATIONAL types:
  // | 'CREW_CONSTRUCTION' | 'TASK_EXECUTION' | 'TOOL_INVOCATION'
  // | 'OBSERVATION_CAPTURE' | 'OUTPUT_PRODUCTION'

  config: Record<string, unknown>;
  status: OrchestrationNodeStatus;
  // 'PENDING' | 'PLANNING' | 'READY' | 'EXECUTING'
  // | 'COMPLETED' | 'FAILED' | 'SKIPPED' | 'ROLLED_BACK'

  tokenBudget?: number;
  maxRetries: number;
  retryCount: number;
  timeoutMs: number;
  checkpointRequired: boolean;
  hitlRequired: boolean;
}

interface OrchestrationEdge {
  sourceId: string;
  targetId: string;
  condition?: string; // Optional conditional routing expression
  dataFlow?: string[]; // What data passes between nodes
}
```

### 1.4 Orchestration Engine Core

The core engine is an **event-driven state machine** that walks the orchestration graph:

```python
# apps/worker/src/orchestrator/engine.py

class OrchestrationEngine:
    """
    The central orchestration engine that walks the orchestration graph.
    
    Design:
    - Event-driven: reacts to node completion events
    - State-persisted: full state is checkpointable
    - Observable: every transition emits typed events
    - Recoverable: any node can be retried from its checkpoint
    - Governed: every node passes through the governance layer before execution
    """
    
    def __init__(
        self,
        execution_id: str,
        graph: OrchestrationGraph,
        event_publisher: EventPublisher,
        checkpoint_manager: CheckpointManager,
        governance: GovernanceLayer,
    ):
        self._execution_id = execution_id
        self._graph = graph
        self._events = event_publisher
        self._checkpoints = checkpoint_manager
        self._governance = governance
        self._node_states: dict[str, OrchestrationNodeStatus] = {}
        self._context: ExecutionContext = ExecutionContext()
    
    async def execute(self) -> ExecutionResult:
        """
        Walk the orchestration graph in topological order.
        
        For each node:
        1. Check governance (permissions, HITL, token budget)
        2. Dispatch to appropriate handler based on node type
        3. Capture output and update context
        4. Emit completion event
        5. Save checkpoint
        6. Select next node based on edges and conditions
        """
        sorted_nodes = self._topological_sort()
        
        for node in sorted_nodes:
            # Governance gate
            decision = await self._governance.evaluate(node, self._context)
            if decision == GovernanceDecision.BLOCK:
                await self._handle_blocked(node)
                continue
            elif decision == GovernanceDecision.HITL_REQUIRED:
                await self._insert_hitl(node)
                return ExecutionResult(status='AWAITING_APPROVAL')
            
            # Execute node with checkpoint
            checkpoint = await self._checkpoints.save_pre_node(node, self._context)
            
            try:
                result = await self._dispatch_node(node)
                self._context.merge(result)
                self._node_states[node.id] = 'COMPLETED'
                await self._events.publish(NodeCompletedEvent(...))
                await self._checkpoints.save_post_node(node, self._context)
            except Exception as e:
                await self._handle_node_failure(node, e)
                if node.retry_count < node.maxRetries:
                    await self._retry_node(node)
                else:
                    return ExecutionResult(status='FAILED', error=str(e))
        
        return ExecutionResult(status='SUCCESS')
```

### 1.5 Orchestration Engine Key Properties

| Property | Implementation | Rationale |
|----------|---------------|-----------|
| **Deterministic** | Topological sort of DAG | Same graph → same execution order |
| **Observable** | Every node emits start/complete/fail events | Full execution traceability |
| **Checkpointable** | Pre/post node checkpoints | Resume from any node boundary |
| **Governed** | Governance layer gates every node | Security, compliance, HITL |
| **Adaptable** | Conditional edges enable dynamic paths | Runtime adaptation without replanning |
| **Recoverable** | Per-node retry with exponential backoff | Graceful degradation |

---

## 2. Planning Engine Architecture

### 2.1 Planning Engine Role

The planning engine is the **strategic brain** that converts user intent into an executable orchestration graph. It operates **before** execution begins and can be re-invoked during execution for dynamic replanning.

### 2.2 Planning Architecture

```
                      ┌──────────────────────────┐
                      │     USER INTENT           │
                      │  (NL goal, template,      │
                      │   or manual graph)        │
                      └───────────┬──────────────┘
                                  │
                                  ▼
              ┌──────────────────────────────────────┐
              │          PLANNING ENGINE               │
              ├──────────────────────────────────────┤
              │                                       │
              │  ┌────────────┐  ┌────────────────┐  │
              │  │ INTENT     │  │ CONSTRAINT     │  │
              │  │ ANALYZER   │──│ CHECKER        │  │
              │  └──────┬─────┘  └───────┬────────┘  │
              │         │                │            │
              │         ▼                ▼            │
              │  ┌─────────────────────────────────┐  │
              │  │      GRAPH GENERATOR              │  │
              │  │  (LLM-assisted graph construction)│  │
              │  └──────────────┬──────────────────┘  │
              │                 │                      │
              │                 ▼                      │
              │  ┌─────────────────────────────────┐  │
              │  │      GRAPH VALIDATOR              │  │
              │  │  (Zod schema + custom rules)      │  │
              │  └──────────────┬──────────────────┘  │
              │                 │                      │
              │                 ▼                      │
              │  ┌─────────────────────────────────┐  │
              │  │      OPTIMIZER                    │  │
              │  │  (token budget, parallelization,  │  │
              │  │   agent merging, tool pruning)    │  │
              │  └──────────────┬──────────────────┘  │
              │                 │                      │
              └─────────────────┼──────────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │  ORCHESTRATION GRAPH │
                    │  (ready for engine)  │
                    └──────────────────────┘
```

### 2.3 Planning Engine Interface

```python
# apps/worker/src/planner/engine.py

class PlanningEngine:
    """
    Strategic planning engine that converts intent to orchestration graphs.
    
    Modes:
    1. MANUAL: User-defined graph (validation only)
    2. AUTO: LLM generates graph from goal description
    3. HYBRID: LLM generates → user edits → validated
    4. TEMPLATE: Load from saved template → customize
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        validator: GraphValidator,
        optimizer: GraphOptimizer,
        agent_catalog: AgentCatalog,
        tool_registry: ToolRegistry,
    ):
        self._llm = llm_provider
        self._validator = validator
        self._optimizer = optimizer
        self._agent_catalog = agent_catalog
        self._tool_registry = tool_registry
    
    async def plan(
        self,
        intent: PlanningIntent,
        constraints: PlanningConstraints,
    ) -> PlanningResult:
        """
        Convert intent to a validated, optimized orchestration graph.
        
        Steps:
        1. Analyze intent (extract goals, entities, constraints)
        2. Check constraints (token budget, max agents, available tools)
        3. Generate candidate graph(s)
        4. Validate graph (schema, connectivity, loop-free, resource limits)
        5. Optimize graph (parallelization, token efficiency)
        6. Return result with metadata
        """
        # Phase 1: Intent analysis
        analysis = await self._analyze_intent(intent)
        
        # Phase 2: Constraint checking
        constraint_result = await self._check_constraints(analysis, constraints)
        if not constraint_result.is_feasible:
            return PlanningResult(
                status='INFEASIBLE',
                reasons=constraint_result.reasons,
                suggestions=constraint_result.suggestions,
            )
        
        # Phase 3: Graph generation
        graph = await self._generate_graph(analysis, constraint_result)
        
        # Phase 4: Validation
        validation = self._validator.validate(graph)
        if not validation.is_valid:
            return PlanningResult(
                status='INVALID',
                graph=graph,
                errors=validation.errors,
            )
        
        # Phase 5: Optimization
        optimized = self._optimizer.optimize(graph, constraints)
        
        return PlanningResult(
            status='READY',
            graph=optimized,
            metadata=PlanningMetadata(
                estimated_tokens=optimized.estimated_tokens,
                estimated_duration=optimized.estimated_duration,
                agent_count=len(optimized.agent_nodes),
                task_count=len(optimized.task_nodes),
                parallel_branches=optimized.parallel_count,
            ),
        )
    
    async def replan(
        self,
        current_graph: OrchestrationGraph,
        execution_context: ExecutionContext,
        failure_info: FailureInfo | None = None,
    ) -> OrchestrationGraph:
        """
        Dynamic replanning during execution.
        
        Triggered by:
        - Agent failure (reassign or replace agent)
        - Tool failure (route to alternative tool)
        - Context change (new information changes the plan)
        - Token budget exceeded (simplify remaining tasks)
        """
        # Analyze what went wrong
        # Generate modified graph from current state
        # Validate and optimize
        # Return new graph for remaining execution
        pass
```

### 2.4 Planning Constraints Model

```typescript
// packages/shared-types/src/types/planning.ts

interface PlanningConstraints {
  maxAgents: number;              // Maximum concurrent agents
  maxSteps: number;               // Maximum execution steps
  tokenBudget: number;            // Total token budget
  maxTokensPerAgent: number;      // Per-agent token limit
  allowedModels: string[];        // Allowed LLM models
  allowedTools: string[];         // Allowed tools
  maxParallelBranches: number;    // Maximum parallel execution paths
  timeoutMs: number;              // Total execution timeout
  requiredApprovals: string[];    // Steps requiring HITL
  preferredModel: string;         // Default model if not specified
}

interface PlanningIntent {
  type: 'goal' | 'template' | 'manual' | 'nlp';
  goal?: string;                  // Natural language goal (for AUTO mode)
  templateId?: string;            // Saved template ID (for TEMPLATE mode)
  graph?: OrchestrationGraph;     // Pre-defined graph (for MANUAL mode)
  nlpInput?: string;              // Raw natural language (for NLP mode)
}
```

### 2.5 Planner Agent System

The planning engine uses **specialized planner agents** for different planning phases:

```python
class IntentAnalyzerAgent:
    """LLM-powered agent that analyzes user intent."""
    
    async def analyze(self, intent: PlanningIntent) -> IntentAnalysis:
        """
        Extract from intent:
        - Primary goal
        - Sub-goals
        - Required domain knowledge
        - Entities involved
        - Success criteria
        - Risk factors
        """
        prompt = self._build_analysis_prompt(intent)
        response = await self._llm.generate(prompt)
        return IntentAnalysis.parse(response)

class GraphDesignerAgent:
    """LLM-powered agent that designs the orchestration graph."""
    
    async def design(
        self,
        analysis: IntentAnalysis,
        constraints: PlanningConstraints,
        agent_catalog: AgentCatalog,
        tool_registry: ToolRegistry,
    ) -> OrchestrationGraph:
        """
        Design a graph by:
        1. Selecting appropriate agents from catalog
        2. Decomposing goal into tasks
        3. Assigning tools to tasks
        4. Ordering tasks (sequential or parallel)
        5. Inserting HITL points
        6. Defining data flow between tasks
        """
        prompt = self._build_design_prompt(analysis, constraints, agent_catalog, tool_registry)
        response = await self._llm.generate(prompt)
        return OrchestrationGraph.parse(response)
```

---

## 3. Autonomous Workflow Generation Pipeline

### 3.1 Pipeline Architecture

The autonomous workflow generation pipeline enables the system to **self-create workflows** without human intervention, given a high-level goal.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   GOAL       │───►│  INTENT     │───►│  DOMAIN     │───►│  AGENT       │
│   INPUT      │    │  ANALYSIS   │    │  MAPPING    │    │  SELECTION   │
│              │    │              │    │              │    │              │
│ "Analyze    │    │ Extract:     │    │ Map to:      │    │ Select from  │
│  customer   │    │ - Goal       │    │ - Industry   │    │ catalog:     │
│  churn and  │    │ - Context    │    │ - Domain     │    │ - Analyst    │
│  generate   │    │ - Entities   │    │ - Skills     │    │ - Engineer   │
│  report"    │    │ - Constraints │    │ - Tools       │    │ - Writer     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                   │
                                                                   ▼
              ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
              │  WORKFLOW    │◄───│  TASK        │◄───│  TOOL        │
              │  GENERATION  │    │  DECOMP      │    │  ASSIGNMENT  │
              │              │    │  OSITION     │    │              │
              │ Full graph   │    │ Break goal   │    │ Match tools  │
              │ with nodes,  │    │ into subtasks│    │ to tasks     │
              │ edges, config│    │ with deps    │    │ per agent    │
              └──────┬───────┘    └──────────────┘    └──────────────┘
                     │
                     ▼
              ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
              │  VALIDATION  │───►│  OPTIMIZATION│───►│  HUMAN       │
              │              │    │              │    │  REVIEW      │
              │ Schema check │    │ Token budget │    │ (Optional)   │
              │ Loop detect  │    │ Parallelize  │    │              │
              │ Resource chk │    │ Merge agents │    │              │
              └──────────────┘    └──────────────┘    └──────────────┘
```

### 3.2 Autonomous Generation Algorithm

```python
class AutonomousWorkflowGenerator:
    """
    Generates complete workflows autonomously from high-level goals.
    
    Uses a multi-step LLM pipeline with intermediate validation
    at each phase to prevent error propagation.
    """
    
    async def generate(
        self,
        goal: str,
        context: WorkflowContext,
    ) -> AutonomousGenerationResult:
        """
        Full autonomous pipeline:
        1. Analyze goal → structured intent
        2. Map to domain → relevant agents, tools, patterns
        3. Select agents → optimal agent configuration
        4. Assign tools → per-agent tool sets
        5. Decompose tasks → task dependency graph
        6. Generate graph → complete orchestration graph
        7. Validate → schema + business rules
        8. Optimize → token efficiency, parallelism
        """
        # Phase 1-2: Analysis
        intent = await self._intent_analyzer.analyze(PlanningIntent(goal=goal, type='goal'))
        domain_map = await self._domain_mapper.map(intent, context)
        
        # Phase 3: Agent selection
        agents = await self._agent_selector.select(
            requirements=domain_map.required_capabilities,
            constraints=context.constraints,
            catalog=self._agent_catalog,
        )
        if not agents:
            # Dynamic agent creation fallback
            agents = await self._dynamic_agent_generator.create(
                domain_map.required_capabilities
            )
        
        # Phase 4: Tool assignment
        for agent in agents:
            agent.tools = await self._tool_assigner.assign(
                agent.role,
                domain_map.required_tools,
                self._tool_registry,
            )
        
        # Phase 5: Task decomposition
        tasks = await self._task_decomposer.decompose(
            goal=intent.primary_goal,
            sub_goals=intent.sub_goals,
            agents=agents,
            domain=domain_map,
        )
        
        # Phase 6: Graph generation
        graph = await self._graph_generator.build(
            agents=agents,
            tasks=tasks,
            domain_map=domain_map,
        )
        
        # Phase 7: Validation
        validation = self._validator.validate(graph)
        if not validation.is_valid:
            # Auto-repair common issues
            graph = await self._auto_repair(graph, validation.errors)
            validation = self._validator.validate(graph)
            if not validation.is_valid:
                return AutonomousGenerationResult(
                    status='FAILED',
                    graph=graph,
                    errors=validation.errors,
                )
        
        # Phase 8: Optimization
        optimized = self._optimizer.optimize(graph, context.constraints)
        
        return AutonomousGenerationResult(
            status='SUCCESS',
            graph=optimized,
            metadata=GenerationMetadata(
                confidence=0.85,
                estimated_tokens=optimized.estimated_tokens,
                agent_count=len(agents),
                task_count=len(tasks),
            ),
        )
```

### 3.3 Domain Mapping System

```python
class DomainMapper:
    """
    Maps natural language goals to domain-specific knowledge.
    
    Maintains:
    - Domain ontologies (tech, finance, healthcare, etc.)
    - Agent archetypes per domain
    - Common tool chains per domain
    - Best-practice workflow patterns
    """
    
    DOMAIN_PATTERNS = {
        'data_analysis': {
            'agents': ['analyst', 'visualizer', 'reporter'],
            'tools': ['sql', 'python_executor', 'file_reader'],
            'pattern': 'sequential_with_parallel_subtasks',
        },
        'research': {
            'agents': ['researcher', 'analyst', 'writer'],
            'tools': ['web_search', 'vector_search', 'file_reader'],
            'pattern': 'parallel_research_then_sequential_synthesis',
        },
        'software_dev': {
            'agents': ['architect', 'engineer', 'qa'],
            'tools': ['python_executor', 'api_connector', 'file_reader'],
            'pattern': 'sequential_with_review_gates',
        },
    }
    
    async def map(
        self,
        intent: IntentAnalysis,
        context: WorkflowContext,
    ) -> DomainMap:
        """Map analyzed intent to domain configuration."""
        domain = await self._detect_domain(intent.goal)
        pattern = self.DOMAIN_PATTERNS.get(domain, self.DOMAIN_PATTERNS['data_analysis'])
        
        return DomainMap(
            domain=domain,
            execution_pattern=pattern,
            required_capabilities=pattern['agents'],
            required_tools=pattern['tools'],
            suggested_agents=self._rank_agents(pattern['agents'], context),
        )
```

---

## 4. Natural-Language-to-Workflow Pipeline

### 4.1 Pipeline Overview

This pipeline converts **raw natural language** (a sentence, paragraph, or conversation) into a fully configured orchestration graph.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      NLP-TO-WORKFLOW PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  "I need to analyze customer feedback from our database,                 │
│   find common complaints, and generate a report with charts"             │
│                                                                           │
│  ┌──────────────┐                                                         │
│  │  NLP PARSER  │──► Intent Classification                               │
│  │  (LLM-based) │──► Entity Extraction (database, feedback, report)      │
│  └──────┬───────┘──► Relationship Extraction                             │
│         │                                                                 │
│         ▼                                                                 │
│  ┌──────────────┐                                                         │
│  │  INTENT      │──► Primary: data_analysis + reporting                  │
│  │  CLASSIFIER  │──► Sub-actions: query, analyze, generate, visualize   │
│  └──────┬───────┘                                                         │
│         │                                                                 │
│         ▼                                                                 │
│  ┌──────────────┐                                                         │
│  │  ENTITY      │──► database → "customer_feedback"                      │
│  │  EXTRACTOR   │──► output → "report with charts"                       │
│  └──────┬───────┘──► constraints → implicit                              │
│         │                                                                 │
│         ▼                                                                 │
│  ┌──────────────────┐                                                     │
│  │  WORKFLOW        │──► Agent: Data Analyst (SQL + Python)              │
│  │  GENERATOR       │──► Agent: Report Writer (file + generate)          │
│  │  (to autonomous  │──► Task: query DB → analyze → visualize → write    │
│  │   pipeline)      │──► Graph: sequential with parallel sub-analysis    │
│  └──────────────────┘                                                     │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 NLP Parser Architecture

```python
class NLPToWorkflowParser:
    """
    Converts natural language to structured workflow intent.
    
    Uses a multi-stage LLM prompting approach:
    1. Raw NL → Structured JSON (intent + entities + constraints)
    2. Structured JSON → Validated PlanningIntent
    3. PlanningIntent → Autonomous workflow generation pipeline
    """
    
    async def parse(self, nl_input: str) -> ParsedWorkflowIntent:
        """
        Parse natural language into structured workflow intent.
        
        Returns:
        - Primary goal
        - Sub-goals / steps
        - Entities (data sources, outputs, tools)
        - Constraints (implicit from language)
        - Confidence score
        - Alternatives (if ambiguous)
        """
        # Stage 1: NL → Structured extraction
        extraction = await self._llm.extract_structured(
            system_prompt=self._EXTRACTION_PROMPT,
            user_input=nl_input,
            output_schema=StructuredExtraction,
        )
        
        # Stage 2: Resolve ambiguity
        if extraction.confidence < self._AMBIGUITY_THRESHOLD:
            disambiguation = await self._disambiguate(nl_input, extraction)
            extraction = disambiguation
        
        # Stage 3: Map to capabilities
        capabilities = await self._capability_mapper.map(extraction)
        
        return ParsedWorkflowIntent(
            goal=extraction.primary_goal,
            sub_goals=extraction.sub_goals,
            entities=extraction.entities,
            constraints=self._infer_constraints(extraction),
            suggested_agents=capabilities.suggested_agents,
            suggested_tools=capabilities.suggested_tools,
            confidence=extraction.confidence,
            alternatives=extraction.alternatives,
        )
    
    _EXTRACTION_PROMPT = """
    You are a workflow intent extractor. Given a natural language description
    of a task, extract the following structured information:
    
    1. Primary goal (one sentence)
    2. Sub-goals / steps (ordered list)
    3. Entities mentioned:
       - Data sources (databases, files, APIs)
       - Outputs (reports, files, dashboards)
       - Tools (search, code, analysis)
    4. Implicit constraints:
       - Deadlines or timeframes
       - Quality requirements
       - Specific methodologies
    5. Ambiguities or unclear aspects
    
    Return your analysis as valid JSON matching the specified schema.
    Be specific and actionable. If the input is vague, note the ambiguity
    and provide the most likely interpretation.
    """
```

### 4.3 Capability Mapping

```python
class CapabilityMapper:
    """
    Maps extracted NL intent to system capabilities.
    
    Maintains a semantic index of:
    - Agent capabilities (role descriptions, skills)
    - Tool capabilities (what each tool does)
    - Task patterns (common workflow structures)
    """
    
    async def map(self, extraction: StructuredExtraction) -> CapabilityMap:
        """
        Map extracted intent to available agents and tools.
        
        Uses embedding-based semantic search to match
        natural language descriptions to agent/tool capabilities.
        """
        # Embed the goal and sub-goals
        goal_embedding = await self._embedder.embed(extraction.primary_goal)
        
        # Semantic search for matching agents
        agent_matches = await self._agent_index.search(
            embedding=goal_embedding,
            top_k=3,
            threshold=0.7,
        )
        
        # Semantic search for matching tools
        tool_matches = await self._tool_index.search(
            embedding=goal_embedding,
            top_k=5,
            threshold=0.6,
        )
        
        return CapabilityMap(
            suggested_agents=[
                AgentSuggestion(
                    agent_id=match.id,
                    role=match.role,
                    confidence=match.score,
                    reason=match.explanation,
                )
                for match in agent_matches
            ],
            suggested_tools=[
                ToolSuggestion(
                    tool_name=match.name,
                    confidence=match.score,
                    reason=match.explanation,
                )
                for match in tool_matches
            ],
        )
```

---

## 5. Dynamic Agent Generation System

### 5.1 System Architecture

The dynamic agent generation system creates **new agent configurations on-the-fly** when the agent catalog doesn't contain a suitable agent for a required capability.

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AGENT GENERATION SYSTEM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Trigger: Required capability not found in agent catalog              │
│           OR user requests a custom agent via NL                      │
│                                                                       │
│  ┌────────────┐    ┌────────────┐    ┌────────────────────────────┐  │
│  │ CAPABILITY │───►│ PERSONA    │───►│ LLM CONFIGURATION          │  │
│  │ ANALYZER   │    │ GENERATOR  │    │ GENERATOR                  │  │
│  │            │    │            │    │                            │  │
│  │ Input:     │    │ Generates: │    │ Generates:                 │  │
│  │ Required   │    │ - role     │    │ - model recommendation     │  │
│  │ skills     │    │ - goal     │    │ - temperature              │  │
│  │ Domain     │    │ - backstory│    │ - max_tokens              │  │
│  │ Context    │    │ - persona  │    │ - max_iterations          │  │
│  └────────────┘    └──────┬─────┘    └────────────┬───────────────┘  │
│                           │                        │                  │
│                           ▼                        ▼                  │
│              ┌──────────────────────────────────────────────┐        │
│              │           TOOL ASSIGNMENT                      │        │
│              │           GENERATOR                            │        │
│              ├──────────────────────────────────────────────┤        │
│              │  Selects tools based on role + domain:         │        │
│              │  - Required tools (must-have)                  │        │
│              │  - Optional tools (nice-to-have)               │        │
│              │  - Tool permissions (scoped to task)           │        │
│              └──────────────────────┬───────────────────────┘        │
│                                     │                                │
│                                     ▼                                │
│              ┌──────────────────────────────────────────────┐        │
│              │           MEMORY CONFIGURATION                  │        │
│              │           GENERATOR                            │        │
│              ├──────────────────────────────────────────────┤        │
│              │  Determines memory requirements:               │        │
│              │  - Short-term (conversation context)          │        │
│              │  - Long-term (knowledge retention)            │        │
│              │  - Entity (structured facts)                  │        │
│              └──────────────────────┬───────────────────────┘        │
│                                     │                                │
│                                     ▼                                │
│              ┌──────────────────────────────────────────────┐        │
│              │           AGENT CONFIG ASSEMBLER                │        │
│              ├──────────────────────────────────────────────┤        │
│              │  Assembles complete AgentConfig from:          │        │
│              │  - Generated persona                          │        │
│              │  - LLM configuration                          │        │
│              │  - Tool assignments                           │        │
│              │  - Memory configuration                       │        │
│              │  - Validation (Zod schema)                    │        │
│              └──────────────────────┬───────────────────────┘        │
│                                     │                                │
│                                     ▼                                │
│              ┌──────────────────────────────────────────────┐        │
│              │           CATALOG REGISTRAR                     │        │
│              ├──────────────────────────────────────────────┤        │
│              │  - Save to agent catalog for reuse            │        │
│              │  - Index by capability for future matching    │        │
│              │  - Emit AGENT_CREATED event                   │        │
│              └──────────────────────────────────────────────┘        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Agent Generator Implementation

```python
class DynamicAgentGenerator:
    """
    Creates agent configurations on-the-fly from capability requirements.
    
    Uses LLM to generate role-appropriate agent configurations
    and validates them against system constraints before creation.
    """
    
    def __init__(
        self,
        llm: LLMProvider,
        tool_registry: ToolRegistry,
        validator: AgentConfigValidator,
        catalog: AgentCatalog,
    ):
        self._llm = llm
        self._tool_registry = tool_registry
        self._validator = validator
        self._catalog = catalog
    
    async def create_from_requirement(
        self,
        requirement: CapabilityRequirement,
        constraints: PlanningConstraints,
    ) -> AgentConfig:
        """
        Create a new agent configuration from a capability requirement.
        
        The LLM generates an optimal agent persona based on:
        - Required capabilities (skills, knowledge areas)
        - Domain context (industry, task type)
        - Constraint context (budget, model availability)
        """
        # Generate persona
        persona = await self._generate_persona(requirement)
        
        # Recommend LLM
        llm_config = await self._recommend_llm(requirement, constraints)
        
        # Assign tools
        tools = await self._assign_tools(requirement, persona)
        
        # Configure memory
        memory_config = self._configure_memory(requirement)
        
        # Assemble
        config = AgentConfig(
            role=persona.role,
            goal=persona.goal,
            backstory=persona.backstory,
            llm=llm_config,
            tools=tools,
            memory=memory_config,
            allow_delegation=True,
            max_iterations=constraints.maxSteps or 15,
            rpm_limit=constraints.rpmLimit or 10,
        )
        
        # Validate
        validation = self._validator.validate(config)
        if not validation.is_valid:
            # Auto-fix common issues
            config = await self._auto_fix(config, validation.errors)
            validation = self._validator.validate(config)
            if not validation.is_valid:
                raise AgentGenerationError(validation.errors)
        
        # Register in catalog
        await self._catalog.register(config, requirement)
        
        return config
    
    async def _generate_persona(
        self,
        requirement: CapabilityRequirement,
    ) -> AgentPersona:
        """Generate role, goal, and backstory using LLM."""
        prompt = f"""
        You are an expert AI agent designer. Create an agent persona for:
        
        Required capabilities: {requirement.skills}
        Domain: {requirement.domain}
        Context: {requirement.context}
        
        Generate a JSON object with:
        1. "role": A professional role title (e.g., "Senior Data Analyst")
        2. "goal": A clear, measurable goal for this agent
        3. "backstory": 2-3 sentence backstory explaining expertise
        
        The agent should be specialized, professional, and production-ready.
        """
        
        response = await self._llm.generate(prompt)
        return AgentPersona.parse(response)
    
    async def _recommend_llm(
        self,
        requirement: CapabilityRequirement,
        constraints: PlanningConstraints,
    ) -> LLMConfig:
        """Recommend optimal LLM configuration."""
        # If constraints specify a model, use it
        if constraints.preferredModel and constraints.allowedModels:
            return LLMConfig(
                provider=self._detect_provider(constraints.preferredModel),
                model=constraints.preferredModel,
                temperature=0.7,
                max_tokens=4096,
            )
        
        # Otherwise, use LLM to recommend
        prompt = f"""
        Recommend optimal LLM configuration for an agent with:
        Role: {requirement.domain} specialist
        Tasks: {requirement.context}
        
        Consider:
        - For analytical tasks: lower temperature (0.1-0.3)
        - For creative tasks: higher temperature (0.7-0.9)
        - For code generation: specialized code models
        
        Return: {{"provider": "...", "model": "...", "temperature": 0.X, "max_tokens": X}}
        """
        
        response = await self._llm.generate(prompt)
        return LLMConfig.parse(response)
```

### 5.3 Agent Catalog

```python
class AgentCatalog:
    """
    Registry of available agent configurations.
    
    Supports:
    - CRUD for agent templates
    - Semantic search by capability
    - Versioning for agent config changes
    - Usage tracking (popularity, success rate)
    """
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[AgentMatch]:
        """Semantic search for agents by capability description."""
        query_embedding = await self._embedder.embed(query)
        
        results = await self._vector_index.search(
            query_embedding,
            top_k=top_k,
            threshold=threshold,
        )
        
        return [
            AgentMatch(
                agent_id=r.id,
                role=r.metadata['role'],
                similarity=r.score,
                usage_count=r.metadata.get('usage_count', 0),
                success_rate=r.metadata.get('success_rate', 0.0),
            )
            for r in results
        ]
    
    async def register(
        self,
        config: AgentConfig,
        requirement: CapabilityRequirement,
    ) -> str:
        """Register a dynamically generated agent in the catalog."""
        agent_id = str(uuid4())
        
        # Store full config
        await self._db.execute(
            insert(AgentTemplate).values(
                id=agent_id,
                role=config.role,
                goal=config.goal,
                backstory=config.backstory,
                llm_config=config.llm.model_dump(),
                tool_ids=config.tools,
                memory_config=config.memory.model_dump(),
                capability_tags=requirement.skills,
                domain=requirement.domain,
                is_dynamic=True,
            )
        )
        
        # Index for semantic search
        embedding = await self._embedder.embed(config.goal + " " + config.backstory)
        await self._vector_index.insert(
            id=agent_id,
            embedding=embedding,
            metadata={
                'role': config.role,
                'domain': requirement.domain,
                'capabilities': requirement.skills,
                'usage_count': 0,
                'success_rate': 0.0,
            },
        )
        
        return agent_id
```

---

## 6. Task Decomposition Engine

### 6.1 Decomposition Architecture

The task decomposition engine breaks complex goals into **executable task graphs** with dependency tracking, parallelization opportunities, and resource allocation.

```
                    ┌──────────────────────┐
                    │   COMPLEX GOAL        │
                    │  "Analyze customer    │
                    │   churn and generate  │
                    │   report"             │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌──────────────────────────────────┐
              │     DECOMPOSITION ENGINE            │
              ├──────────────────────────────────┤
              │                                    │
              │  1. GOAL DECOMPOSITION              │
              │     ┌──────────────────────┐       │
              │     │ Level 0: "Analyze    │       │
              │     │           churn"     │       │
              │     ├──────────────────────┤       │
              │     │ Level 1: ├─ Query data      │
              │     │          ├─ Analyze patterns│
              │     │          ├─ Visualize       │
              │     │          └─ Write report    │
              │     └──────────────────────┘       │
              │                                    │
              │  2. DEPENDENCY ANALYSIS             │
              │     Data Query ──┐                  │
              │                  ├──► Analysis      │
              │     Visualize ──┘                  │
              │                        └──► Report │
              │                                    │
              │  3. PARALLELIZATION                 │
              │     Query (parallel by region)      │
              │     ├──► NA Analysis                │
              │     ├──► EU Analysis   ──► Merge    │
              │     └──► APAC Analysis              │
              │                                    │
              │  4. RESOURCE ALLOCATION             │
              │     Agent: Analyst (query + analyze)│
              │     Agent: Writer (visualize + rpt) │
              │     Tools: SQL, Python, File Writer │
              │                                    │
              └──────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   TASK DEPENDENCY     │
                    │   GRAPH (DAG)         │
                    │                      │
                    │  T1 ──► T2 ──► T4    │
                    │         │            │
                    │         └──► T3 ────┘
                    └──────────────────────┘
```

### 6.2 Decomposition Algorithm

```python
class TaskDecompositionEngine:
    """
    Decomposes complex goals into executable task DAGs.
    
    Uses hierarchical decomposition with LLM guidance:
    1. Level 0: Goal → high-level phases
    2. Level 1: Phases → concrete tasks
    3. Level 2: Tasks → atomic steps (with tool calls)
    
    Each level validates feasibility before proceeding deeper.
    """
    
    async def decompose(
        self,
        goal: str,
        sub_goals: list[str],
        agents: list[AgentConfig],
        constraints: PlanningConstraints,
    ) -> TaskDecomposition:
        """
        Decompose a goal into an executable task graph.
        
        Returns:
        - Tasks with descriptions, expected outputs
        - Dependency edges between tasks
        - Agent assignments per task
        - Tool assignments per task
        - Parallelization opportunities
        - HITL requirements
        """
        # Phase 1: Coarse decomposition (goal → phases)
        phases = await self._coarse_decompose(goal, sub_goals)
        
        # Phase 2: Fine decomposition (phases → tasks)
        all_tasks = []
        for phase in phases:
            tasks = await self._fine_decompose(phase, agents, constraints)
            all_tasks.extend(tasks)
        
        # Phase 3: Dependency analysis
        deps = await self._analyze_dependencies(all_tasks)
        
        # Phase 4: Parallelization
        parallel_groups = self._identify_parallel_groups(all_tasks, deps)
        
        # Phase 5: Agent assignment
        assignments = await self._assign_agents(all_tasks, agents)
        
        return TaskDecomposition(
            tasks=all_tasks,
            dependencies=deps,
            parallel_groups=parallel_groups,
            agent_assignments=assignments,
            metadata=DecompositionMetadata(
                total_tasks=len(all_tasks),
                max_depth=self._calculate_depth(deps),
                parallelization_factor=len(parallel_groups) / max(len(all_tasks), 1),
            ),
        )
    
    async def _coarse_decompose(self, goal: str, sub_goals: list[str]) -> list[Phase]:
        """Break goal into high-level phases (3-7 phases)."""
        prompt = f"""
        Decompose this goal into 3-7 high-level phases:
        
        Goal: {goal}
        Sub-goals: {sub_goals}
        
        Each phase should be:
        - Self-contained (produce a useful intermediate output)
        - Sequentially ordered (where dependencies exist)
        - Assignable to a single agent type
        
        Return JSON array: [{{"id": "phase_1", "name": "...", "description": "...",
                              "expected_output": "...", "agent_type": "..."}}]
        """
        response = await self._llm.generate(prompt)
        return [Phase.parse(p) for p in json.loads(response)]
    
    async def _fine_decompose(
        self,
        phase: Phase,
        agents: list[AgentConfig],
        constraints: PlanningConstraints,
    ) -> list[Task]:
        """Break a phase into concrete, executable tasks."""
        prompt = f"""
        Break this phase into concrete, executable tasks:
        
        Phase: {phase.name}
        Description: {phase.description}
        Expected output: {phase.expected_output}
        Available agents: {[a.role for a in agents]}
        
        Each task must:
        - Be atomic (single operation)
        - Have a clear tool or action
        - Specify expected output format
        - Include estimated complexity (low/medium/high)
        
        Return JSON array of task objects.
        """
        response = await self._llm.generate(prompt)
        return [Task.parse(t) for t in json.loads(response)]
```

### 6.3 Dependency Analysis

```python
class DependencyAnalyzer:
    """
    Analyzes task dependencies to produce a valid DAG.
    
    Rules:
    - Input/output matching: if Task B needs Task A's output, A → B
    - Sequential: all tasks within a phase are sequential by default
    - Parallel: independent tasks can run in parallel
    - No circular dependencies: validated via topological sort
    """
    
    def analyze(self, tasks: list[Task]) -> DependencyGraph:
        """
        Build dependency graph using:
        1. Explicit dependencies (task declares depends_on)
        2. Implicit dependencies (output/input matching)
        3. Resource constraints (same tool can't run in parallel)
        """
        deps: dict[str, set[str]] = {}
        
        # Build task output registry
        outputs: dict[str, set[str]] = {}
        for task in tasks:
            outputs[task.id] = set(task.outputs or [])
        
        # Detect implicit dependencies
        for task in tasks:
            for input_req in (task.inputs or []):
                for other_id, other_outputs in outputs.items():
                    if other_id != task.id and input_req in other_outputs:
                        if task.id not in deps:
                            deps[task.id] = set()
                        deps[task.id].add(other_id)
            
            # Add explicit dependencies
            if task.depends_on:
                if task.id not in deps:
                    deps[task.id] = set()
                deps[task.id].update(task.depends_on)
        
        # Validate (detect cycles)
        if self._has_cycles(deps, tasks):
            raise CircularDependencyError("Task graph contains cycles")
        
        return DependencyGraph(dependencies=deps, tasks=tasks)
```

---

## 7. Tool Routing Architecture

### 7.1 Tool Routing Model

The tool routing architecture determines **which tool gets called by which agent, with what permissions, and with what fallback strategy**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       TOOL ROUTING ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────┐                                                         │
│  │  Agent      │──► Tool Call Request: {tool_name, input, context}       │
│  │  Requests   │                                                         │
│  │  Tool Use   │                                                         │
│  └──────┬──────┘                                                         │
│         │                                                                 │
│         ▼                                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    TOOL ROUTER                                    │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │                                                                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │   │
│  │  │PERMISSION│  │ CAPABILITY│  │  LOAD    │  │  FALLBACK        │ │   │
│  │  │ CHECK    │──│ MATCH    │──│ BALANCER │──│  RESOLVER        │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │   │
│  │       │             │              │                │            │   │
│  │       ▼             ▼              ▼                ▼            │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │              TOOL EXECUTION GATE                          │   │   │
│  │  ├──────────────────────────────────────────────────────────┤   │   │
│  │  │  Routes to:                                               │   │   │
│  │  │  - Local tool (Python executor, file reader)              │   │   │
│  │  │  - Remote tool (web search, API connector)                │   │   │
│  │  │  - LLM-based tool (code generation, summarization)       │   │   │
│  │  │  - Delegated tool (hand off to another agent)            │   │   │
│  │  └──────────────────────────┬───────────────────────────────┘   │   │
│  │                             │                                    │   │
│  └─────────────────────────────┼────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    TOOL EXECUTION                                  │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  Execute → Capture output → Track tokens → Emit event → Return   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Tool Router Implementation

```python
# packages/crew-runtime/src/tools/router.py

class ToolRouter:
    """
    Routes tool calls from agents to the appropriate execution engine.
    
    Responsibilities:
    - Permission verification (is agent allowed to use this tool?)
    - Capability matching (does the tool support the requested operation?)
    - Load balancing (distribute across tool instances if available)
    - Fallback resolution (if primary tool fails, try alternative)
    - Token tracking (record token usage for each tool call)
    - Event emission (publish tool call/result events)
    """
    
    def __init__(
        self,
        registry: ToolRegistry,
        permission_manager: PermissionManager,
        event_publisher: EventPublisher,
        token_tracker: TokenTracker,
    ):
        self._registry = registry
        self._permissions = permission_manager
        self._events = event_publisher
        self._token_tracker = token_tracker
    
    async def route(
        self,
        agent_id: str,
        tool_name: str,
        input_data: dict,
        context: ExecutionContext,
    ) -> ToolResult:
        """
        Route a tool call to the appropriate execution path.
        
        1. Resolve tool from registry
        2. Check permissions
        3. Execute with timeout
        4. Handle errors with fallback
        5. Track tokens and emit events
        6. Return result
        """
        # Resolve tool
        tool = await self._registry.resolve(tool_name)
        if not tool:
            return await self._try_fallback(agent_id, tool_name, input_data, context)
        
        # Permission check
        if not await self._permissions.check(agent_id, tool_name, tool.required_permissions):
            return ToolResult(
                status='ERROR',
                error=f"Agent {agent_id} lacks permission for {tool_name}",
            )
        
        # Emit tool_call event
        await self._events.publish(ToolCallEvent(
            agent_id=agent_id,
            tool_name=tool_name,
            tool_input=input_data,
        ))
        
        # Execute with timeout
        try:
            start = time.monotonic()
            output = await asyncio.wait_for(
                tool.execute(input_data),
                timeout=tool.timeout_ms / 1000,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            
            # Track tokens
            self._token_tracker.track_tool(agent_id, tool_name, output, duration_ms)
            
            # Emit tool_result event
            await self._events.publish(ToolResultEvent(
                agent_id=agent_id,
                tool_name=tool_name,
                tool_output=str(output)[:1000],
                duration_ms=duration_ms,
            ))
            
            return ToolResult(status='SUCCESS', output=output, duration_ms=duration_ms)
            
        except asyncio.TimeoutError:
            # Try fallback
            return await self._try_fallback(agent_id, tool_name, input_data, context)
        except Exception as e:
            # Emit error event
            await self._events.publish(ToolErrorEvent(
                agent_id=agent_id,
                tool_name=tool_name,
                error=str(e),
            ))
            return ToolResult(status='ERROR', error=str(e))
    
    async def _try_fallback(
        self,
        agent_id: str,
        tool_name: str,
        input_data: dict,
        context: ExecutionContext,
    ) -> ToolResult:
        """
        Attempt fallback tool when primary fails.
        
        Fallback chain is defined in tool registry:
        - web_search → vector_search (cached results)
        - python_executor → api_connector (if available)
        - sql → file_reader (if CSV export exists)
        """
        fallback_chain = self._registry.get_fallback_chain(tool_name)
        
        for fallback_tool in fallback_chain:
            # Check if fallback is available and permitted
            if await self._permissions.check(agent_id, fallback_tool.name, fallback_tool.required_permissions):
                try:
                    result = await fallback_tool.execute(input_data)
                    return ToolResult(
                        status='SUCCESS',
                        output=result,
                        fallback_from=tool_name,
                        duration_ms=0,
                    )
                except Exception:
                    continue
        
        return ToolResult(
            status='ERROR',
            error=f"All fallbacks exhausted for {tool_name}",
            fallback_from=tool_name,
        )
```

### 7.3 Tool Registry

```python
class ToolRegistry:
    """
    Central registry of all available tools.
    
    Supports:
    - Tool registration with metadata
    - Tool capability discovery
    - Fallback chain configuration
    - Permission templates
    - Tool versioning
    """
    
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._fallback_chains: dict[str, list[str]] = {}
        self._capability_index: dict[str, list[str]] = {}  # capability → tool_names
    
    def register(self, definition: ToolDefinition) -> None:
        """Register a tool with the system."""
        self._tools[definition.name] = definition
        
        # Index by capability
        for capability in definition.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            self._capability_index[capability].append(definition.name)
    
    def configure_fallback(
        self,
        primary_tool: str,
        fallback_chain: list[str],
    ) -> None:
        """Configure fallback chain for a tool."""
        self._fallback_chains[primary_tool] = fallback_chain
    
    async def resolve(self, name: str) -> ToolDefinition | None:
        """Resolve a tool by name."""
        return self._tools.get(name)
    
    def get_fallback_chain(self, tool_name: str) -> list[ToolDefinition]:
        """Get fallback chain for a tool."""
        chain = self._fallback_chains.get(tool_name, [])
        return [self._tools[name] for name in chain if name in self._tools]
    
    def find_by_capability(self, capability: str) -> list[ToolDefinition]:
        """Find tools by capability."""
        return [
            self._tools[name]
            for name in self._capability_index.get(capability, [])
            if name in self._tools
        ]
    
    async def discover_capabilities(self, agent_role: str) -> list[ToolSuggestion]:
        """
        Discover recommended tools for an agent role.
        Based on role-capability mappings and usage statistics.
        """
        # Semantic match agent role to tool capabilities
        role_embedding = await self._embedder.embed(agent_role)
        
        results = []
        for tool in self._tools.values():
            tool_embedding = await self._embedder.embed(tool.description)
            similarity = cosine_similarity(role_embedding, tool_embedding)
            
            if similarity > 0.6:
                results.append(ToolSuggestion(
                    tool_name=tool.name,
                    confidence=similarity,
                    reason=f"Tool capability matches agent role requirements",
                ))
        
        return sorted(results, key=lambda r: r.confidence, reverse=True)
```

---

## 8. Memory Orchestration Architecture

### 8.1 Orchestrated Memory Model

Memory orchestration coordinates **which memory is available to which agent, at which phase, and how memory flows between agents**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MEMORY ORCHESTRATION                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   MEMORY ORCHESTRATOR                             │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │                                                                   │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │   │
│  │  │ MEMORY SCOPE     │  │ MEMORY FLOW      │  │ MEMORY        │  │   │
│  │  │ CONTROLLER       │  │ CONTROLLER       │  │ PRUNER        │  │   │
│  │  ├──────────────────┤  ├──────────────────┤  ├────────────────┤  │   │
│  │  │ Per-agent scope  │  │ Agent-to-agent   │  │ TTL management │  │   │
│  │  │ Per-task scope   │  │ Workflow-level   │  │ Relevance       │  │   │
│  │  │ Workflow-global  │  │ Checkpoint-safe  │  │ Budget control │  │   │
│  │  │ Agent isolation  │  │ Replay-isolated  │  │ Size limits    │  │   │
│  │  └──────────────────┘  └──────────────────┘  └────────────────┘  │   │
│  │                                                                   │   │
│  │  ┌──────────────────────────────────────────────────────────┐    │   │
│  │  │              MEMORY BRIDGE (unified interface)              │    │   │
│  │  ├──────────────────────────────────────────────────────────┤    │   │
│  │  │  store() | query() | clear() | snapshot() | restore()    │    │   │
│  │  └────────────┬──────────────────────┬─────────────────────┘    │   │
│  │               │                      │                           │   │
│  └───────────────┼──────────────────────┼───────────────────────────┘   │
│                  │                      │                               │
│                  ▼                      ▼                               │
│  ┌──────────────────┐    ┌──────────────────────────┐                   │
│  │  SHORT-TERM      │    │  LONG-TERM + ENTITY       │                   │
│  │  (Redis DB 2)    │    │  (PostgreSQL + PGVector)   │                   │
│  │  TTL: 3600s      │    │  Persistent                │                   │
│  └──────────────────┘    └──────────────────────────┘                   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Memory Scope Controller

```python
class MemoryScopeController:
    """
    Controls which memory is accessible to which agent at what time.
    
    Scope hierarchy:
    - WORKFLOW: All agents in the workflow can read/write
    - AGENT: Only the specific agent can access
    - TASK: Only available during specific task execution
    - ISOLATED: Copy-on-write for replay isolation
    """
    
    def __init__(self, memory_bridge: MemoryBridge):
        self._bridge = memory_bridge
    
    async def store(
        self,
        workflow_id: str,
        agent_id: str,
        scope: MemoryScope,
        key: str,
        value: Any,
        metadata: dict | None = None,
    ) -> None:
        """Store memory with scope control."""
        scoped_key = self._scope_key(scope, workflow_id, agent_id, key)
        
        if scope == MemoryScope.WORKFLOW:
            # All agents read, writing agent stamps ownership
            await self._bridge.store(
                workflow_id=workflow_id,
                agent_id=agent_id,
                memory_type=MemoryType.SHORT_TERM,
                key=f"workflow_global:{key}",
                value=value,
                metadata={"scope": "workflow", "owner": agent_id, **(metadata or {})},
            )
        elif scope == MemoryScope.AGENT:
            await self._bridge.store(
                workflow_id=workflow_id,
                agent_id=agent_id,
                memory_type=MemoryType.SHORT_TERM,
                key=key,
                value=value,
                metadata={"scope": "agent", **(metadata or {})},
            )
    
    async def query(
        self,
        workflow_id: str,
        agent_id: str,
        scope: MemoryScope,
        query: str,
        limit: int = 10,
    ) -> list[MemoryItem]:
        """Query memory with scope filtering."""
        if scope == MemoryScope.WORKFLOW:
            # Query across all agents in workflow
            return await self._bridge.query(
                workflow_id=workflow_id,
                agent_id="*",  # All agents
                memory_type=MemoryType.SHORT_TERM,
                query=query,
                limit=limit,
            )
        else:
            return await self._bridge.query(
                workflow_id=workflow_id,
                agent_id=agent_id,
                memory_type=MemoryType.SHORT_TERM,
                query=query,
                limit=limit,
            )
    
    def _scope_key(
        self,
        scope: MemoryScope,
        workflow_id: str,
        agent_id: str,
        key: str,
    ) -> str:
        """Generate scoped key for memory storage."""
        if scope == MemoryScope.WORKFLOW:
            return f"crew:{workflow_id}:shared:{key}"
        elif scope == MemoryScope.AGENT:
            return f"crew:{workflow_id}:agent:{agent_id}:memory:{key}"
        return f"crew:{workflow_id}:{key}"
```

### 8.3 Memory Flow Controller

```python
class MemoryFlowController:
    """
    Controls how memory flows between agents in a workflow.
    
    Flow patterns:
    - SEQUENTIAL: Agent A's output becomes Agent B's context
    - BROADCAST: Agent A's output is shared with all subsequent agents
    - ISOLATED: Each agent starts with a clean context
    - MERGE: Multiple agent outputs are merged into shared context
    """
    
    async def transfer(
        self,
        from_agent: str,
        to_agent: str,
        workflow_id: str,
        flow_pattern: MemoryFlowPattern,
        context: ExecutionContext,
    ) -> None:
        """Transfer memory between agents according to flow pattern."""
        
        if flow_pattern == MemoryFlowPattern.SEQUENTIAL:
            # Pass only relevant context
            summary = await self._summarize_agent_output(from_agent, workflow_id)
            await self._bridge.store(
                workflow_id=workflow_id,
                agent_id=to_agent,
                memory_type=MemoryType.SHORT_TERM,
                key=f"from:{from_agent}:summary",
                value=summary,
            )
        
        elif flow_pattern == MemoryFlowPattern.BROADCAST:
            # Share full context
            snapshot = await self._bridge.snapshot(workflow_id)
            await self._bridge.store(
                workflow_id=workflow_id,
                agent_id=to_agent,
                memory_type=MemoryType.SHORT_TERM,
                key="shared_context",
                value=snapshot,
            )
```

### 8.4 Memory Pruner

```python
class MemoryPruner:
    """
    Manages memory growth to prevent unbounded consumption.
    
    Strategies:
    - TTL-based: Remove entries older than TTL
    - Relevance-based: Remove lowest-scored entries when budget exceeded
    - Summarization: Replace multiple entries with a summary
    - Deduplication: Remove semantically similar entries
    """
    
    async def prune(
        self,
        workflow_id: str,
        agent_id: str | None = None,
        strategy: PruneStrategy = PruneStrategy.TTL,
    ) -> int:
        """Prune memory and return count of removed entries."""
        if strategy == PruneStrategy.TTL:
            return await self._prune_by_ttl(workflow_id, agent_id)
        elif strategy == PruneStrategy.RELEVANCE:
            return await self._prune_by_relevance(workflow_id, agent_id)
        elif strategy == PruneStrategy.SUMMARIZE:
            return await self._summarize_and_prune(workflow_id, agent_id)
    
    async def _summarize_and_prune(
        self,
        workflow_id: str,
        agent_id: str | None,
    ) -> int:
        """
        Replace multiple old entries with a single summary.
        
        When an agent has > N memory entries in short-term:
        1. Take oldest 50% of entries
        2. Use LLM to generate a summary
        3. Store summary as single entry
        4. Delete the original entries
        """
        # ... summarization logic
        pass
```

---

## 9. Execution Planning Lifecycle

### 9.1 Full Lifecycle

The execution planning lifecycle spans from **initial intent through planning, execution, completion, and post-execution analysis**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXECUTION PLANNING LIFECYCLE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  PHASE 0: INTENT                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Input: User goal, NL description, or template                     │   │
│  │ Goal: Capture what the user wants to accomplish                   │   │
│  │ Output: PlanningIntent (structured)                               │   │
│  │ Owner: Frontend + Intent Analyzer Agent                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  PHASE 1: PLAN                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Input: PlanningIntent + PlanningConstraints                       │   │
│  │ Steps: Analyze → Decompose → Design Graph → Validate → Optimize   │   │
│  │ Output: OrchestrationGraph (validated + optimized)                │   │
│  │ Owner: PlanningEngine + Planner Agents                            │   │
│  │ Gate: Human review (optional, configurable)                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  PHASE 2: APPROVE                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Input: OrchestrationGraph                                         │   │
│  │ Action: User reviews and approves the generated plan              │   │
│  │ Skip: If auto-approve is configured for trusted workflows         │   │
│  │ Output: Approved orchestration graph (versioned + locked)         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  PHASE 3: EXECUTE                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Input: Approved OrchestrationGraph                                │   │
│  │ Steps: CrewConstruction → TaskExecution → EventStreaming          │   │
│  │ Control: Pause/Resume/Kill/Replay at any point                   │   │
│  │ Output: ExecutionResult (or intermediate checkpoint)              │   │
│  │ Owner: OrchestrationEngine + CrewRuntime                          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  PHASE 4: MONITOR                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Input: Execution events (real-time stream)                        │   │
│  │ Action: Observe execution via terminal, metrics, node status      │   │
│  │ Intervene: Pause at HITL, edit agent output, approve/reject       │   │
│  │ Owner: Frontend (ObservabilityTerminal + MetricsDashboard)        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  PHASE 5: ANALYZE                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Input: ExecutionResult + EventLog                                  │   │
│  │ Actions: Token cost analysis, timing analysis, failure analysis   │   │
│  │ Output: ExecutionReport (metrics, timeline, diffs)                │   │
│  │ Owner: MetricsService + ReplayEngine                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  PHASE 6: REUSE                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Input: Successful ExecutionReport                                  │   │
│  │ Actions: Save as template, update agent catalog with performance   │   │
│  │ Output: Template for reuse, agent success metrics                 │   │
│  │ Owner: TemplateService + AgentCatalog                             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘

### 9.2 Lifecycle State Machine with Checkpoints

```typescript
interface ExecutionLifecycleState {
  phase: 'INTENT' | 'PLANNING' | 'PLAN_READY' | 'APPROVING' | 'APPROVED'
       | 'EXECUTING' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'ANALYZING';
  intent?: { status: 'CAPTURED' | 'ANALYZED' };
  planning?: { status: 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'; graph?: OrchestrationGraph };
  approval?: { status: 'PENDING' | 'APPROVED' | 'REJECTED'; reviewedBy?: string };
  execution?: { checkpoint?: Checkpoint; progress: number; agentStates: Record<string, string> };
  analysis?: { report?: ExecutionReport };
}
```

### 9.3 Checkpoint Placement Strategy

```
Checkpoints are placed at EVERY lifecycle boundary:

INTENT ---[CP]--- PLANNING ---[CP]--- APPROVING ---[CP]--- EXECUTING ---[CP]--- COMPLETED
                      |                      |                      |
                      v                      v                      v
                Can restore to        Can replay from        Can replay entire
                planning phase        approved plan           execution

Within EXECUTING:
  T1 ---[CP]--- T2 ---[CP]--- T3 ---[CP]--- T4
              |              |              |
              v              v              v
        Resume from T2  Resume from T3  Execution complete
```

---

## 10. Agent Communication Model

### 10.1 Communication Architecture

Agent communication follows a structured message-passing model rather than shared blackboard or free-form chat. This ensures observability, replayability, and auditability.

```
                    +--------------------------+
                    |   ORCHESTRATION ENGINE   |
                    |   (Message Relay)        |
                    +------------+-------------+
                                 |
                 +---------------+---------------+
                 |               |               |
                 v               v               v
         +------------+   +------------+   +------------+
         |  Agent A   |   |  Agent B   |   |  Agent C   |
         | [Mailbox]  |   | [Mailbox]  |   | [Mailbox]  |
         +------------+   +------------+   +------------+

Communication Patterns:

  SEQUENTIAL: A - B - C (pipeline, each waits for previous)
    Message: TaskOutput(agent="A", task="query", output={...})

  BROADCAST: A - {B, C, D} (fan-out to all)
    Message: Broadcast(agent="A", data={...}, recipients=["B","C"])

  GATHER: {A, B, C} - D (merge results)
    Message: MergeRequest(agent="D", from=["A","B","C"], ...)

  DELEGATE: A - B - A (sub-task with return)
    Message: Delegate(agent="A", to="B", task={...}, request_id="r1")
    Response: DelegateResponse(request_id="r1", result={...})
```

### 10.2 Message Types

```typescript
type AgentMessageType =
  | 'TASK_OUTPUT'        // Agent passes output to next agent
  | 'TASK_REQUEST'       // Agent requests another agent to perform a task
  | 'TASK_RESPONSE'      // Response to a task request
  | 'BROADCAST'          // Fan-out message to multiple agents
  | 'MERGE_REQUEST'      // Request to merge outputs
  | 'MERGE_RESPONSE'     // Merged result
  | 'DELEGATE'           // Delegate sub-task
  | 'DELEGATE_RESPONSE'  // Delegate result
  | 'STATUS_UPDATE'      // Agent status change
  | 'PROGRESS_UPDATE'    // Progress percentage
  | 'BLOCKED'            // Agent waiting for input
  | 'ERROR';             // Agent encountered error

interface AgentMessage {
  id: string;
  type: AgentMessageType;
  from: string;
  to: string | string[];
  workflowId: string;
  executionId: string;
  payload: Record<string, unknown>;
  timestamp: string;
  correlationId: string;
  tokenCost?: number;
  priority: 'low' | 'medium' | 'high';
  ttlMs?: number;
  requiresAck: boolean;
}
```

### 10.3 Orchestration Engine as Message Relay

The orchestration engine acts as the message relay between all agents. All inter-agent communication flows through the relay to ensure:

- **Observability**: Every message is logged as an event
- **Auditability**: Complete message history is persisted
- **Replayability**: Messages can be replayed for debugging
- **Governance**: Messages can be intercepted for HITL

```python
class MessageRelay:
    async def relay(self, message: AgentMessage, mailboxes: dict[str, AgentMailbox]):
        # Emit communication event
        await self._events.publish(AgentCommunicationEvent(message=message))

        # Check if this communication requires HITL
        if await self._governance.requires_approval(message):
            approval = await self._hitl_service.create_approval(message=message)
            await self._events.publish(HITLRequiredEvent(approval_id=approval.id))
            return  # Pause until HITL resolved

        # Deliver to target(s)
        targets = message.to if isinstance(message.to, list) else [message.to]
        for target in targets:
            if target in mailboxes:
                await mailboxes[target].send(message)
```

---

## 11. Runtime Adaptation Architecture

### 11.1 Adaptation Model

Runtime adaptation enables the orchestration to modify its execution plan in response to changing conditions without requiring a full replan.

```
                    ADAPTATION TRIGGERS
  +--------------+  +--------------+  +--------------+  +----------+
  | TOOL FAILURE |  | AGENT ERROR  |  | TOKEN BUDGET |  | NEW INFO |
  +------+-------+  +------+-------+  +------+-------+  +----+-----+
         |                 |                 |               |
         v                 v                 v               v
                    ADAPTATION ENGINE
  +--------------+  +--------------+  +--------------------+
  | CONDITION    |  | ADAPTATION   |  | IMPACT ASSESSOR   |
  | EVALUATOR    |->| SELECTOR     |->|                    |
  +--------------+  +--------------+  +--------------------+
                           |
                           v
                    ADAPTATION EXECUTOR
              Modifies orchestration graph, agent config, or routing
              Emits ADAPTATION_APPLIED event
              Saves pre/post adaptation checkpoint
```

### 11.2 Adaptation Strategies

| Strategy | Trigger | Action |
|----------|---------|--------|
| **RETRY** | Tool failure, timeout | Re-execute failed node with exponential backoff |
| **FALLBACK** | Tool unavailable | Route to alternative tool with same capability |
| **REROUTE** | Agent error | Change task assignment to different agent |
| **SIMPLIFY** | Token budget low | Reduce task complexity (fewer steps, less detail) |
| **REPLAN** | Context change | Re-invoke planning engine for remaining work |
| **ESCALATE** | Unrecoverable | Pause and notify human operator |

### 11.3 Adaptation Decision Flow

```python
class AdaptationEngine:
    async def evaluate_and_adapt(self, trigger, context, graph):
        strategy = await self._select_strategy(trigger, context)
        impact = await self._assess_impact(strategy, context, graph)

        if impact.risk_level == 'HIGH':
            await self._escalate(trigger, strategy, impact)
            return AdaptationResult(status='ESCALATED')

        await self._apply_adaptation(strategy, trigger, context, graph)
        return AdaptationResult(status='ADAPTED', strategy=strategy, impact=impact)

    async def _apply_replan(self, trigger, context, graph):
        """Re-invoke planning engine for remaining work."""
        remaining = self._extract_remaining_tasks(graph, context)
        new_plan = await self._planning_engine.replan(
            current_graph=graph,
            execution_context=context,
            failure_info=FailureInfo(trigger=trigger, remaining_tasks=remaining),
        )
        graph.replace_remaining(remaining, new_plan.graph)
```

---

## 12. Replay-Aware Orchestration

### 12.1 Replay Architecture

Replay-aware orchestration ensures that every execution can be faithfully replayed for debugging, audit, or comparison purposes.

**Replay Modes:**

1. **FULL REPLAY**: Re-execute entire workflow from step 0 using original config snapshot
2. **STEP REPLAY**: Re-execute from specific checkpoint with restored agent/task/memory state
3. **DEBUG REPLAY**: Re-execute with original event log as reference; side-by-side diff comparison
4. **BRANCH REPLAY**: Replay from checkpoint with MODIFIED config for "what if" scenarios

**Replay Requirements:**

- Deterministic node execution order
- Immutable config snapshots (no side effects on original)
- Full event log persistence
- Checkpoint at every node boundary
- Memory isolation (replay gets fresh memory namespace)
- Timestamp normalization for diff comparison

### 12.2 Replay-Conscious Orchestration Engine

```python
class ReplayAwareOrchestrationEngine(OrchestrationEngine):
    async def execute_node(self, node, context):
        pre_state = context.snapshot()
        await self._log_replay_state(node.id, 'PRE', pre_state)

        try:
            if self._execution_mode == ExecutionMode.REPLAY:
                deterministic_context = self._make_deterministic(context, node)
                result = await super().execute_node(node, deterministic_context)
            else:
                result = await super().execute_node(node, context)

            post_state = context.snapshot()
            await self._log_replay_state(node.id, 'POST', post_state)

            if self._execution_mode == ExecutionMode.DEBUG_REPLAY:
                expected = await self._get_original_state(node.id)
                diff = self._compute_diff(expected, post_state)
                await self._log_replay_diff(node.id, diff)

            return result
        except Exception as e:
            await self._log_replay_state(node.id, 'FAILED', {'error': str(e)})
            raise
```

### 12.3 Replay Diff Report

```typescript
interface ReplayDiffReport {
  originalExecutionId: string;
  replayExecutionId: string;
  replayMode: 'FULL' | 'STEP' | 'DEBUG' | 'BRANCH';
  summary: {
    totalSteps: number;
    matchingSteps: number;
    differingSteps: number;
    newErrors: number;
    resolvedErrors: number;
    tokenDelta: number;
    durationDelta: number;
  };
  stepDiffs: Array<{
    step: number;
    nodeId: string;
    nodeType: string;
    outputDiff?: {
      type: 'IDENTICAL' | 'MINOR' | 'MAJOR' | 'NEW_ERROR' | 'RESOLVED_ERROR';
      variance: number;
      originalPreview: string;
      replayPreview: string;
    };
    tokenDiff?: { original: number; replay: number; variance: number };
    timingDiff?: { originalMs: number; replayMs: number; variance: number };
  }>;
}
```

---

## 13. Human-in-the-Loop Orchestration Flow

### 13.1 HITL Integration Levels

HITL is integrated at multiple levels of the orchestration:

| Level | Point | Description |
|-------|-------|-------------|
| **Level 1: Plan Approval** | Before execution | Human reviews and approves generated plan |
| **Level 2: Task Approval** | Between agents | Human approves agent output before passing to next agent |
| **Level 3: Tool Approval** | During execution | Human approves high-risk tool calls before execution |
| **Level 4: Adaptation Escalation** | Runtime | Human approves runtime adaptation before automatic application |
| **Level 5: Intervention** | Mid-execution | Human manually edits agent output and resumes |

### 13.2 HITL Orchestration Flow

```
Agent reaches HITL point
         |
         v
HITL ORCHESTRATOR
  |
  1. CAPTURE STATE
  |  - Snapshot agent state (thought, action, output so far)
  |  - Snapshot workflow context
  |  - Create ApprovalRequest
  |
  2. PAUSE EXECUTION
  |  - Set workflow status to AWAITING_APPROVAL
  |  - Save checkpoint
  |  - Publish HITL_REQUIRED event (SSE to Frontend)
  |
  3. WAIT FOR DECISION
  |  - Frontend shows approval dialog (draft + edit + context)
  |  - User can: Approve | Edit and Approve | Reject | Regenerate
  |  - User action to API to HITL_DECISION event (Redis Pub/Sub)
  |
  4. RESUME EXECUTION
  |  - Restore checkpoint
  |  - Apply decision:
  |    - APPROVE: Continue with original output
  |    - EDIT: Replace output with human-edited version
  |    - REJECT: Log rejection, provide feedback
  |    - REGENERATE: Re-run agent with additional context
  |  - Set status to RUNNING, publish HITL_RESOLVED event
  |  - Continue execution
```

### 13.3 HITL Orchestrator Implementation

```python
class HITLOrchestrator:
    async def request_approval(self, execution_id, task_id, agent_id, agent_output, context):
        # 1. Save checkpoint
        checkpoint = await self._checkpoints.save_hitl(execution_id=execution_id, reason="HITL required")

        # 2. Create approval record
        approval = ApprovalRequest(
            execution_id=execution_id, task_id=task_id, agent_id=agent_id,
            draft_output=agent_output, context=context,
            checkpoint_id=checkpoint.id, status='PENDING',
        )
        await self._db.save_approval(approval)

        # 3. Emit event
        await self._events.publish(HITLRequiredEvent(
            approval_id=approval.id, execution_id=execution_id,
            task_id=task_id, agent_id=agent_id, draft_output=agent_output,
        ))
        return approval

    async def resolve_approval(self, approval_id, decision):
        approval = await self._db.get_approval(approval_id)
        approval.status = decision.decision
        approval.reviewed_by = decision.user_id
        approval.reviewed_at = datetime.utcnow()
        if decision.decision == 'APPROVED':
            approval.edited_output = decision.edits or approval.draft_output
        await self._db.update_approval(approval)

        return HITLResolution(
            approval_id=approval_id, execution_id=approval.execution_id,
            decision=decision.decision,
            output=decision.edits or approval.draft_output if decision.decision == 'APPROVED' else None,
            checkpoint_id=approval.checkpoint_id,
        )
```

---

## 14. Approval Insertion Strategy

### 14.1 Approval Rules Model

Approval points are strategically placed based on risk level, not indiscriminately.

```typescript
enum ApprovalRiskLevel { LOW = 'LOW', MEDIUM = 'MEDIUM', HIGH = 'HIGH', CRITICAL = 'CRITICAL' }

interface ApprovalRule {
  id: string;
  trigger: 'AGENT_OUTPUT' | 'TOOL_CALL' | 'PLAN' | 'ADAPTATION'
        | 'EXTERNAL_API' | 'COST_THRESHOLD' | 'FIRST_RUN';
  riskLevel: ApprovalRiskLevel;
  conditions?: {
    agentRoles?: string[];
    toolNames?: string[];
    costThreshold?: number;
    tokenThreshold?: number;
    isFirstRun?: boolean;
    agentOutputContains?: string[];
  };
  approvalConfig: {
    requiredApprovers: number;
    requiredRoles: string[];
    timeoutMinutes: number;
    escalationRole?: string;
  };
}
```

### 14.2 Default Approval Rules

| Rule | Trigger | Risk | Condition |
|------|---------|------|-----------|
| First run plan | PLAN | HIGH | isFirstRun == true |
| SQL executor | TOOL_CALL | HIGH | toolName in ['sql_executor', 'python_executor'] |
| Cost threshold | COST_THRESHOLD | HIGH | cost > $10.00 |
| External API | EXTERNAL_API | MEDIUM | toolName == 'api_connector' |
| Adaptation | ADAPTATION | HIGH | Any adaptation |

### 14.3 Insertion Points in Orchestration Graph

```
Before execution:
  GOAL -> PLAN GENERATE -> [APPROVAL (if HIGH)] -> EXECUTE

During execution (task boundary):
  AGENT A OUTPUT -> [APPROVAL (if rule match)] -> AGENT B -> [APPROVAL]

During execution (tool call):
  AGENT REQUESTS TOOL -> [APPROVAL (if high risk)] -> EXECUTE TOOL
```

---

## 15. Token Optimization Strategy

### 15.1 Optimization Layers

Token optimization operates at five layers:

| Layer | Techniques |
|-------|------------|
| **Layer 1: Prompt Optimization** | Prompt compression, few-shot minimization, context window management, instruction deduplication |
| **Layer 2: Context Management** | Context summarization, selective injection, sliding window, relevance filtering |
| **Layer 3: Model Selection** | Tiered routing (simple tasks to small models), task complexity analysis, cost-aware selection |
| **Layer 4: Execution Optimization** | Tool result caching, parallel execution, early termination, agent merging |
| **Layer 5: Monitoring and Budgeting** | Real-time token tracking, budget alerts, automatic simplification, post-execution audit |

### 15.2 Token Budget Management

```python
class TokenBudgetManager:
    def __init__(self, total_budget: int):
        self._total_budget = total_budget
        self._used = 0
        self._reserved = int(total_budget * 0.1)  # 10% buffer
        self._available = total_budget - self._reserved
        self._agent_budgets: dict[str, int] = {}

    def allocate_agent(self, agent_id: str) -> int:
        allocation = int(self._available / (len(self._agent_budgets) + 1) * 0.8)
        self._agent_budgets[agent_id] = allocation
        return allocation

    def track(self, agent_id: str, tokens: int) -> str:
        self._used += tokens
        if self._used > self._total_budget:
            return 'EXCEEDED'
        elif self._used > self._total_budget - self._reserved:
            return 'WARNING'
        return 'OK'

    def get_remaining(self) -> int:
        return self._total_budget - self._used
```

### 15.3 Context Compression

```python
class ContextCompressor:
    async def compress(self, context: list, max_tokens: int, task_description: str) -> list:
        current_tokens = self._estimate_tokens(context)
        if current_tokens <= max_tokens:
            return context

        # Strategy 1: Filter irrelevant entries
        relevant = await self._filter_relevant(context, task_description)
        if self._estimate_tokens(relevant) <= max_tokens:
            return relevant

        # Strategy 2: Summarize older entries
        recent = relevant[-5:]
        older = relevant[:-5]
        if older:
            summary = await self._summarize_entries(older, task_description)
            compressed = [{'role': 'system', 'content': f'[Summarized]: {summary}'}] + recent
            if self._estimate_tokens(compressed) <= max_tokens:
                return compressed

        # Strategy 3: Aggressive truncation
        return recent[-3:]
```

---

## 16. Model Routing Architecture

### 16.1 Model Router

The model routing architecture determines which LLM model handles which request based on task requirements, cost constraints, and availability.

```
  MODEL REQUEST: {agentId, taskType, complexity, preferredModel}
         |
         v
  +--------------------------------------------------+
  |                  MODEL ROUTER                      |
  |  +---------------+  +--------------+              |
  |  | TASK TYPE     |  | COST         |              |
  |  | ANALYZER      |->| OPTIMIZER    |              |
  |  +---------------+  +--------------+              |
  |  +---------------+  +--------------+              |
  |  | AVAILABILITY  |  | PERFORMANCE  |              |
  |  | CHECKER       |->| RANKER       |              |
  |  +---------------+  +--------------+              |
  |                         |                          |
  |                         v                          |
  |              MODEL SELECTION ENGINE                 |
  |  score = taskFit*0.4 + costEfficiency*0.3         |
  |          + availability*0.2 + latency*0.1          |
  |  Select highest-scoring model                      |
  +-------------------------+--------------------------+
                            |
                            v
  +---------------------------------------------------+
  |  MODEL ENDPOINT                                     |
  |  OpenAI (gpt-4o, gpt-4o-mini)                      |
  |  Anthropic (claude-sonnet, claude-opus)             |
  |  Ollama (llama3, mistral)                           |
  +---------------------------------------------------+
```

### 16.2 Model Tier Definitions

```python
MODEL_TIERS = {
    'critical': {
        'description': 'Complex reasoning, multi-step, structured output',
        'models': ['gpt-4o', 'claude-opus'],
        'fallback': 'gpt-4o-mini',
    },
    'standard': {
        'description': 'Analysis, code generation, tool use',
        'models': ['gpt-4o-mini', 'claude-sonnet'],
        'fallback': 'llama3-local',
    },
    'economy': {
        'description': 'Simple classification, extraction, summarization',
        'models': ['gpt-4o-mini', 'llama3-local'],
        'fallback': 'llama3-local',
    },
    'local': {
        'description': 'Offline-capable, sensitive data, cost-free',
        'models': ['llama3-local', 'mistral-local'],
        'fallback': 'gpt-4o-mini',
    },
}
```

### 16.3 Scoring Algorithm

```python
async def score_model(name, profile, request, constraints):
    # Task fit (0.0 - 1.0)
    task_fit = 1.0 if request.task_type in profile.strengths else 0.3

    # Cost efficiency (0.0 - 1.0)
    request_cost = estimate_cost(request, profile)
    cost_score = 1.0 - min(request_cost / constraints.remaining_budget, 1.0)

    # Availability (0.0 - 1.0)
    status = await get_model_status(name)
    avail_score = min(status.remaining_rpm / status.max_rpm, 1.0)

    # Weighted combination
    return task_fit * 0.4 + cost_score * 0.3 + avail_score * 0.2 + (1.0 - profile.latency_ms / 10000) * 0.1
```

---

## 17. Ollama Integration Strategy

### 17.1 Integration Architecture

Ollama provides local LLM inference for cost-sensitive, privacy-sensitive, or offline operation.

```
  +--------------------------------------------------+
  |                OLLAMA WRAPPER                      |
  |  +---------------+  +--------------+              |
  |  | MODEL MANAGER |  | CONNECTION   |              |
  |  | - List/pull   |  | - Pooling    |              |
  |  | - Auto-pull   |  | - Health     |              |
  |  | - Cache       |  | - Retry      |              |
  |  +---------------+  +--------------+              |
  |  +----------------------------------------------+ |
  |  | CAPABILITY MAPPING                            | |
  |  | llama3:8b -> simple_reasoning, classification | |
  |  | llama3:70b -> reasoning, analysis             | |
  |  | codellama -> code generation                  | |
  |  | mistral -> reasoning, summarization           | |
  |  | nomic-embed-text -> embeddings                | |
  |  +----------------------------------------------+ |
  |  +----------------------------------------------+ |
  |  | FALLBACK CHAIN                                | |
  |  | ollama/llama3 -> gpt-4o-mini (cloud)          | |
  |  | ollama/codellama -> gpt-4o (cloud)            | |
  |  +----------------------------------------------+ |
  +--------------------------------------------------+
```

### 17.2 Ollama Wrapper Implementation

```python
class OllamaWrapper:
    def __init__(self, base_url: str = "http://ollama:11434"):
        self._base_url = base_url
        self._session: httpx.AsyncClient | None = None
        self._available_models: dict = {}
        self._token_estimator = TokenEstimator()

    async def initialize(self):
        self._session = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)
        await self._discover_models()
        self._refresh_task = asyncio.create_task(self._periodic_refresh())

    async def _discover_models(self):
        response = await self._session.get("/api/tags")
        for model in response.json().get("models", []):
            self._available_models[model["name"]] = {
                "name": model["name"],
                "capabilities": self._map_capabilities(model["name"]),
            }

    def _map_capabilities(self, name: str) -> list[str]:
        name_lower = name.lower()
        if 'codellama' in name_lower or 'deepseek-coder' in name_lower:
            return ['code_generation', 'code_review']
        elif 'embed' in name_lower:
            return ['embeddings']
        elif '70b' in name_lower or '80b' in name_lower:
            return ['reasoning', 'analysis']
        else:
            return ['simple_reasoning', 'classification']

    async def generate(self, model: str, prompt: str, system_prompt: str = None,
                       temperature: float = 0.7, max_tokens: int = 2048):
        if model not in self._available_models:
            await self._pull_model(model)

        payload = {
            "model": model, "prompt": prompt, "system": system_prompt or "",
            "temperature": temperature, "max_tokens": max_tokens, "stream": False,
        }

        response = await self._session.post("/api/generate", json=payload, timeout=120.0)
        data = response.json()

        return {
            "text": data.get("response", ""),
            "input_tokens": self._token_estimator.estimate(prompt),
            "output_tokens": self._token_estimator.estimate(data.get("response", "")),
            "model": model,
        }

    async def _pull_model(self, model: str):
        async with self._session.stream("POST", "/api/pull", json={"name": model}) as response:
            async for line in response.aiter_lines():
                if line and json.loads(line).get("status") == "success":
                    break
        await self._discover_models()
```

### 17.3 Model Capability Mapping

| Ollama Model | Capabilities | Recommended For |
|-------------|-------------|-----------------|
| llama3:8b | simple_reasoning, classification, code | Economy tier tasks |
| llama3:70b | reasoning, analysis, code | Standard tier tasks |
| mistral | reasoning, analysis, summarization | Standard tier, fallback |
| codellama | code_generation, code_review | Code-specific tasks |
| deepseek-coder | advanced code, structured_output | Complex code tasks |
| nomic-embed-text | embeddings | Memory pipeline |

---

## 18. Prompt Template Architecture

### 18.1 Template Registry Structure

All prompts are managed as versioned, composable templates in a dedicated registry:

```
registry/
  agents/                    # Agent-level prompts
    default_agent.yaml       # Base agent prompt
    researcher.yaml          # Research specialization
    analyst.yaml             # Analysis specialization
    engineer.yaml            # Engineering specialization
  tasks/                     # Task-level prompts
    default_task.yaml        # Base task prompt
    hitl_task.yaml           # HITL task wrapper
    delegation.yaml          # Agent delegation prompt
  planners/                  # Planning prompts
    intent_analysis.yaml     # Intent analysis prompt
    graph_design.yaml        # Graph design prompt
    task_decomposition.yaml  # Task decomposition prompt
  tools/                     # Tool-specific prompts
    web_search.yaml          # Web search tool prompt
    sql_query.yaml           # SQL query tool prompt
    python_executor.yaml     # Python executor prompt
  templates/                 # Reusable template fragments
    output_format.yaml       # Output format instructions
    constraints.yaml         # Constraint reminders
    context_summary.yaml     # Context summarization prompt
```

### 18.2 Template Format

```yaml
name: "default_agent"
version: 1
description: "Base prompt for all agents"
variables:
  - name: role
  - name: goal
  - name: backstory
  - name: tools
  - name: context
imports:
  - output_format
  - constraints
content: |
  You are {{role}}. {{backstory}}

  Your goal: {{goal}}

  Available tools: {{tools}}

  Current context: {{context}}

  {{> output_format}}
  {{> constraints}}
```

### 18.3 Template Engine

```python
class PromptTemplateEngine:
    def __init__(self, registry_path: str):
        self._templates: dict[str, PromptTemplate] = {}
        self._fragments: dict[str, str] = {}
        self._load_registry(registry_path)

    def render(self, template_name: str, variables: dict) -> str:
        template = self._templates.get(template_name)
        if not template:
            raise TemplateNotFoundError(template_name)

        content = template.content

        # Substitute variables
        for var_name, var_value in variables.items():
            placeholder = "{{" + var_name + "}}"
            content = content.replace(placeholder, str(var_value))

        # Import fragments
        for import_name in template.imports:
            fragment = self._fragments.get(import_name)
            if fragment:
                placeholder = "{{> " + import_name + "}}"
                content = content.replace(placeholder, fragment)

        # Process conditionals
        content = self._process_conditionals(content, variables)

        return content

    def _process_conditionals(self, content: str, variables: dict) -> str:
        """Process {{#if condition}}...{{/if}} blocks."""
        import re
        pattern = r"\{\{#if (\w+)\}\}(.*?)\{\{/if\}\}"
        return re.sub(pattern, lambda m: m.group(2) if variables.get(m.group(1)) else "", content, flags=re.DOTALL)
```

---

## 19. Orchestration Event Taxonomy

### 19.1 Complete Event Classification

The orchestration event taxonomy classifies every event emitted by the system into a hierarchical structure:

```
ORCHESTRATION EVENTS
  |
  +-- WORKFLOW LIFECYCLE
  |   +-- WORKFLOW_CREATED
  |   +-- WORKFLOW_UPDATED
  |   +-- WORKFLOW_DELETED
  |   +-- WORKFLOW_STARTED
  |   +-- WORKFLOW_COMPLETED
  |   +-- WORKFLOW_FAILED
  |   +-- WORKFLOW_CANCELLED
  |   +-- WORKFLOW_PAUSED
  |   +-- WORKFLOW_RESUMED
  |
  +-- PLANNING EVENTS
  |   +-- PLAN_GENERATED
  |   +-- PLAN_VALIDATED
  |   +-- PLAN_OPTIMIZED
  |   +-- PLAN_APPROVED
  |   +-- PLAN_REJECTED
  |   +-- PLAN_REVISION_REQUESTED
  |
  +-- AGENT EXECUTION
  |   +-- AGENT_STARTED
  |   +-- AGENT_THOUGHT
  |   +-- AGENT_ACTION
  |   +-- AGENT_OBSERVATION
  |   +-- AGENT_COMPLETED
  |   +-- AGENT_FAILED
  |   +-- AGENT_DELEGATED
  |   +-- AGENT_STATUS_CHANGE
  |
  +-- TOOL EXECUTION
  |   +-- TOOL_CALLING
  |   +-- TOOL_RESULT
  |   +-- TOOL_ERROR
  |   +-- TOOL_TIMEOUT
  |   +-- TOOL_FALLBACK
  |   +-- TOOL_RATE_LIMITED
  |
  +-- MEMORY EVENTS
  |   +-- MEMORY_STORED
  |   +-- MEMORY_QUERIED
  |   +-- MEMORY_PRUNED
  |   +-- MEMORY_CLEARED
  |   +-- MEMORY_SNAPSHOT_SAVED
  |   +-- MEMORY_SNAPSHOT_RESTORED
  |
  +-- HITL EVENTS
  |   +-- HITL_REQUIRED
  |   +-- HITL_APPROVED
  |   +-- HITL_REJECTED
  |   +-- HITL_REGENERATED
  |   +-- HITL_ESCALATED
  |   +-- HITL_TIMEOUT
  |
  +-- ADAPTATION EVENTS
  |   +-- ADAPTATION_TRIGGERED
  |   +-- ADAPTATION_APPLIED
  |   +-- ADAPTATION_FAILED
  |   +-- ADAPTATION_ESCALATED
  |
  +-- ORCHESTRATION EVENTS (Engine internal)
  |   +-- NODE_STARTED
  |   +-- NODE_COMPLETED
  |   +-- NODE_FAILED
  |   +-- NODE_RETRYING
  |   +-- NODE_SKIPPED
  |   +-- CHECKPOINT_SAVED
  |   +-- CHECKPOINT_RESTORED
  |   +-- GRAPH_BRANCH_SELECTED
  |
  +-- SYSTEM EVENTS
  |   +-- SYSTEM_HEALTH
  |   +-- SYSTEM_ALERT
  |   +-- LLM_CIRCUIT_OPEN
  |   +-- LLM_CIRCUIT_CLOSED
  |   +-- RATE_LIMIT_WARNING
  |   +-- TOKEN_BUDGET_WARNING
  |   +-- TOKEN_BUDGET_EXCEEDED
  |
  +-- AUDIT EVENTS
      +-- USER_LOGIN
      +-- USER_LOGOUT
      +-- WORKFLOW_EXECUTED
      +-- AGENT_CONFIG_CHANGED
      +-- PERMISSION_CHANGED
      +-- EXPORT_PERFORMED
```

### 19.2 Event Envelope Schema

```typescript
interface OrchestrationEvent {
  id: string;                    // Unique event ID
  type: string;                  // Fully qualified event type
  timestamp: string;             // ISO 8601
  executionId: string;           // Scoping
  workflowId: string;
  correlationId: string;         // Cross-service trace ID
  source: 'engine' | 'runtime' | 'worker' | 'api' | 'frontend' | 'system';
  category: 'workflow' | 'planning' | 'agent' | 'tool' | 'memory'
          | 'hitl' | 'adaptation' | 'orchestration' | 'system' | 'audit';
  severity: 'debug' | 'info' | 'warning' | 'error' | 'critical';
  data: Record<string, unknown>;
  sequence: number;              // Monotonic sequence for ordering
  version: number;               // Schema version
}
```

---

## 20. Orchestration Debugging Strategy

### 20.1 Debugging Architecture

Orchestration debugging provides **full observability** into every aspect of the orchestration engine's operation.

```
+--------------------------------------------------+
|             ORCHESTRATION DEBUGGING                |
+--------------------------------------------------+
|                                                    |
|  LAYER 1: EVENT LOG                                |
|  Full event stream with filtering and search       |
|  Every event type, source, severity, timestamp     |
|                                                    |
|  LAYER 2: GRAPH VISUALIZATION                      |
|  Live orchestration graph with node status         |
|  Current execution position highlighted            |
|  Conditional branches and their evaluation          |
|                                                    |
|  LAYER 3: STATE INSPECTOR                          |
|  Execution context at any point                    |
|  Memory contents per agent                         |
|  Token budget status                               |
|  Checkpoint contents                               |
|                                                    |
|  LAYER 4: REPLAY COMPARISON                        |
|  Side-by-side original vs replay                   |
|  Step-by-step stepping through execution           |
|  Diff highlighting for outputs, tokens, timing     |
|                                                    |
|  LAYER 5: PERFORMANCE PROFILER                     |
|  Per-node execution time                           |
|  LLM call latency breakdown                        |
|  Token consumption per agent/task/tool             |
|  Bottleneck identification                         |
|                                                    |
+--------------------------------------------------+
```

### 20.2 Debugging Tools

```python
class OrchestrationDebugger:
    """
    Debugging interface for the orchestration engine.
    Provides step-through, state inspection, and replay comparison.
    """

    def __init__(self, event_store, checkpoint_manager):
        self._events = event_store
        self._checkpoints = checkpoint_manager

    async def get_execution_trace(self, execution_id: str) -> ExecutionTrace:
        """Return full execution trace with all events in order."""
        events = await self._events.get_execution_events(execution_id)
        return ExecutionTrace(
            execution_id=execution_id,
            events=events,
            total_steps=len(events),
            duration_ms=events[-1].timestamp - events[0].timestamp if len(events) > 1 else 0,
        )

    async def get_graph_state(self, execution_id: str, step: int) -> GraphSnapshot:
        """Return the orchestration graph state at a specific step."""
        checkpoint = await self._checkpoints.load_at_step(execution_id, step)
        return GraphSnapshot(
            step=step,
            node_states=checkpoint.completed_agent_ids + checkpoint.pending_agent_ids,
            context=checkpoint.shared_context,
            tokens=checkpoint.cumulative_tokens,
        )

    async def step_through(
        self,
        execution_id: str,
        start_step: int = 0,
        end_step: int | None = None,
    ) -> AsyncIterator[StepSnapshot]:
        """Step through execution one node at a time for debugging."""
        events = await self._events.get_execution_events(execution_id)
        end = end_step or len(events)

        for i in range(start_step, end):
            event = events[i]
            pre_state = await self.get_graph_state(execution_id, event.sequence - 1)
            yield StepSnapshot(
                step=event.sequence,
                event=event,
                pre_state=pre_state,
                post_state=await self.get_graph_state(execution_id, event.sequence),
            )
```

### 20.3 Debugging Endpoints

```python
# Debugging API endpoints (development only, disabled in production)

@router.get("/debug/execution/{execution_id}/trace")
async def get_execution_trace(execution_id: str):
    """Return full event trace for an execution."""
    return await debugger.get_execution_trace(execution_id)

@router.get("/debug/execution/{execution_id}/graph/{step}")
async def get_graph_at_step(execution_id: str, step: int):
    """Return graph state at a specific step."""
    return await debugger.get_graph_state(execution_id, step)

@router.get("/debug/execution/{execution_id}/compare/{replay_id}")
async def compare_executions(execution_id: str, replay_id: str):
    """Compare original execution with replay execution."""
    return await replay_engine.compare_replay(execution_id, replay_id)

@router.get("/debug/execution/{execution_id}/token-breakdown")
async def get_token_breakdown(execution_id: str):
    """Return per-agent, per-task, per-tool token breakdown."""
    return await metrics_service.get_token_breakdown(execution_id)
```

### 20.4 Debugging Dashboard (Orchestrator View)

```
ORCHESTRATION DEBUG DASHBOARD
+----------------------------------------------------------+
|  EXECUTION: exec_abc123                                   |
|  Status: FAILED at step 7 / 14                           |
|                                                          |
|  GRAPH VIEW:                                              |
|  [GOAL] -> [PLAN] -> [AGENT_A] -> [AGENT_B] -> [FAILED]  |
|                              |            ^               |
|                              v            |               |
|                          [TOOL_X] -> [ERROR: timeout]    |
|                                                          |
|  NODE INSPECTOR (step 7):                                |
|  +----------------------------------------------------+ |
|  | Node: AGENT_B / Task: analyze_results               | |
|  | Status: FAILED                                      | |
|  | Error: Tool timeout (TOOL_X, 30s)                   | |
|  | Tokens used: 2,450 / 5,000 budget                   | |
|  | Duration: 32,000ms                                  | |
|  |                                                     | |
|  | [Event Log] [State] [Memory] [Retry] [Skip] [Edit]  | |
|  +----------------------------------------------------+ |
|                                                          |
|  ACTIONS:                                                 |
|  [Retry Node] [Skip Node] [Edit Config] [Replay From]   |
|  [Branch Replay] [Rollback]                              |
+----------------------------------------------------------+
```

### 20.5 Debugging by Event Category

| Category | Debug Technique | Key Metrics |
|----------|----------------|-------------|
| **Workflow lifecycle** | Trace state transitions, checkpoint availability | State change count, checkpoint frequency |
| **Planning** | Validate graph output, inspect LLM reasoning | Plan generation time, validation results |
| **Agent execution** | Step-through agent thoughts, actions, observations | Agent loop count, token consumption |
| **Tool execution** | Inspect tool inputs/outputs, fallback chain | Tool latency, error rate, fallback usage |
| **Memory operations** | Trace memory reads/writes per agent | Memory hit rate, storage size, query latency |
| **HITL interactions** | Track approval cycle time, decision patterns | Approval time, rejection rate, escalation count |
| **Adaptation** | Log adaptation triggers and applied strategies | Adaptation count, recovery rate |
| **Model routing** | Log model selection decisions and fallbacks | Model distribution, cost per model |

---

## Appendix A: Architecture Decision Records

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration model | DAG-based with state machine | Deterministic, check-pointable, observable |
| Agent communication | Structured message-passing via relay | Auditable, replayable, governable |
| Planning strategy | Multi-phase LLM pipeline with validation | Error containment at each phase |
| Token optimization | Multi-layer (prompt, context, model, execution) | Comprehensive coverage, not single-point |
| Model routing | Scoring-based selection (task fit, cost, availability) | Optimizes for quality within budget |
| HITL insertion | Risk-level-based rules engine | Appropriate oversight without friction |
| Runtime adaptation | Strategy pattern with escalation | Graceful degradation, human fallback |
| Replay model | Linked execution with diff comparison | Full audit trail with actionable insights |
| Prompt management | Versioned, composable YAML templates | Maintainable, testable, iterable |

## Appendix B: Orchestration Data Flow Matrix

| Trigger | Component | Action | Events |
|---------|-----------|--------|--------|
| User submits goal | PlanningEngine | Generate plan | PLAN_GENERATED |
| Plan ready | GovernanceLayer | Check approvals | PLAN_APPROVED / PLAN_REJECTED |
| Execution starts | OrchestrationEngine | Walk graph | NODE_STARTED, WORKFLOW_STARTED |
| Agent starts task | CrewRuntime | Execute agent | AGENT_STARTED, AGENT_THOUGHT |
| Agent calls tool | ToolRouter | Route and execute | TOOL_CALLING, TOOL_RESULT |
| Tool fails | AdaptationEngine | Apply strategy | ADAPTATION_TRIGGERED |
| HITL rule matches | HITLOrchestrator | Pause and request | HITL_REQUIRED |
| Human decides | HITLOrchestrator | Resolve and resume | HITL_APPROVED / HITL_REJECTED |
| Token budget low | TokenBudgetManager | Alert or simplify | TOKEN_BUDGET_WARNING |
| Checkpoint needed | CheckpointManager | Save state | CHECKPOINT_SAVED |
| User replays | ReplayEngine | Create replay execution | WORKFLOW_STARTED (replay) |
| Orchestration ends | OrchestrationEngine | Finalize | WORKFLOW_COMPLETED / FAILED |

---

*End of AI Orchestration Architecture Specification.*