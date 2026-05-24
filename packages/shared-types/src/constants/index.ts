// ---------------------------------------------------------------------------
// CrewAI Enterprise Control Center — Shared Constants
// Governance: Section 9 — Execution State Machine
// ---------------------------------------------------------------------------

export enum WorkflowStatus {
  PENDING = 'PENDING',
  QUEUED = 'QUEUED',
  RUNNING = 'RUNNING',
  SUSPENDED = 'SUSPENDED',
  AWAITING_APPROVAL = 'AWAITING_APPROVAL',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
  SUCCESS = 'SUCCESS',
}

export enum AgentExecutionStatus {
  IDLE = 'IDLE',
  THINKING = 'THINKING',
  ACTING = 'ACTING',
  TOOL_CALLING = 'TOOL_CALLING',
  OBSERVING = 'OBSERVING',
  AWAITING_HITL = 'AWAITING_HITL',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}

export enum ExecutionQueue {
  HIGH = 'workflow_high',
  DEFAULT = 'workflow_default',
  LOW = 'workflow_low',
  CONTROL = 'workflow_control',
  HITL = 'hitl',
}

export const MAX_TERMINAL_ENTRIES = 10_000;
export const SSE_KEEPALIVE_INTERVAL_MS = 30_000;
export const SSE_MAX_RETRIES = 5;
export const SSE_BACKOFF_MS = [1_000, 2_000, 4_000, 8_000, 16_000] as const;
export const SYNC_DEBOUNCE_MS = 300;
export const CELERY_SOFT_TIME_LIMIT = 3600;
export const CELERY_HARD_TIME_LIMIT = 3900;
export const CELERY_RESULT_EXPIRY_S = 86400;

export const TOKEN_LIMITS = {
  AGENT_THOUGHT_OUTPUT: 1000,
  TOOL_RESULT_OUTPUT: 1000,
  AGENT_COMPLETED_OUTPUT: 2000,
  TERMINAL_ENTRY_MESSAGE: 5000,
} as const;