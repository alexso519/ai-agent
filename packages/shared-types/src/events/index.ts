// ---------------------------------------------------------------------------
// CrewAI Enterprise Control Center — Event Types
// Governance: Section 6 — Event Schema Governance
// ---------------------------------------------------------------------------

export enum EventType {
  // Workflow lifecycle
  WORKFLOW_STARTED = 'WORKFLOW_STARTED',
  WORKFLOW_CHECKPOINT = 'WORKFLOW_CHECKPOINT',
  WORKFLOW_PAUSED = 'WORKFLOW_PAUSED',
  WORKFLOW_RESUMED = 'WORKFLOW_RESUMED',
  WORKFLOW_COMPLETED = 'WORKFLOW_COMPLETED',
  WORKFLOW_FAILED = 'WORKFLOW_FAILED',
  WORKFLOW_CANCELLED = 'WORKFLOW_CANCELLED',

  // Agent execution
  AGENT_STARTED = 'AGENT_STARTED',
  AGENT_THOUGHT = 'AGENT_THOUGHT',
  AGENT_ACTION = 'AGENT_ACTION',
  AGENT_OBSERVATION = 'AGENT_OBSERVATION',
  TOOL_CALLING = 'TOOL_CALLING',
  TOOL_RESULT = 'TOOL_RESULT',
  TOOL_ERROR = 'TOOL_ERROR',
  AGENT_COMPLETED = 'AGENT_COMPLETED',

  // HITL
  HITL_REQUIRED = 'HITL_REQUIRED',
  HITL_APPROVED = 'HITL_APPROVED',
  HITL_REJECTED = 'HITL_REJECTED',
  HITL_REGENERATED = 'HITL_REGENERATED',

  // Progress and metrics
  TASK_PROGRESS = 'TASK_PROGRESS',
  METRICS_UPDATE = 'METRICS_UPDATE',
  ERROR_OCCURRED = 'ERROR_OCCURRED',
}

export enum EventSource {
  RUNTIME = 'runtime',
  WORKER = 'worker',
  API = 'api',
  SYSTEM = 'system',
}

export interface RuntimeEvent<T = unknown> {
  readonly id: string;
  readonly type: EventType;
  readonly timestamp: string;
  readonly execution_id: string;
  readonly correlation_id: string;
  readonly source: EventSource;
  readonly step: number;
  readonly sequence: number;
  readonly data: T;
  readonly version: number;
}

export interface AgentStartedData {
  agent_id: string;
  agent_role: string;
  task_id: string;
  task_title: string;
}

export interface AgentThoughtData {
  agent_id: string;
  thought: string;
  action: string | null;
  action_input: Record<string, unknown> | null;
}

export interface ToolCallData {
  agent_id: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
  timestamp: string;
}

export interface ToolResultData {
  agent_id: string;
  tool_name: string;
  tool_output: string;
  duration_ms: number;
}

export interface AgentCompletedData {
  agent_id: string;
  output: string;
  tokens: {
    input: number;
    output: number;
    total: number;
  };
}

export interface HITLRequiredData {
  task_id: string;
  agent_id: string;
  agent_role: string;
  draft_output: string;
  task_description: string;
  context: Record<string, unknown>;
}

export interface HITLDecisionData {
  approval_id: string;
  decision: 'APPROVED' | 'REJECTED';
  reason: string | null;
  edits: string | null;
}

export interface ErrorData {
  agent_id: string | null;
  error_type: string;
  error_message: string;
  error_details: Record<string, unknown> | null;
}