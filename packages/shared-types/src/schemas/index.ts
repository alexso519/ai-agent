// ---------------------------------------------------------------------------
// CrewAI Enterprise Control Center — Zod Validation Schemas
// Governance: Section 6 — Event Schema Governance
// ---------------------------------------------------------------------------

import { z } from 'zod';
import { WorkflowStatus } from '../constants';
import { EventType, EventSource } from '../events';

// ─── Event Envelope Schema ──────────────────────────────────────────────

export const RuntimeEventSchema = z.object({
  id: z.string(),
  type: z.nativeEnum(EventType),
  timestamp: z.string().datetime(),
  execution_id: z.string(),
  correlation_id: z.string(),
  source: z.nativeEnum(EventSource),
  step: z.number().int().nonnegative(),
  sequence: z.number().int().nonnegative(),
  data: z.record(z.unknown()).default({}),
  version: z.number().int().positive().default(1),
});

// ─── Event Data Schemas ─────────────────────────────────────────────────

export const AgentStartedDataSchema = z.object({
  agent_id: z.string(),
  agent_role: z.string(),
  task_id: z.string(),
  task_title: z.string(),
});

export const AgentThoughtDataSchema = z.object({
  agent_id: z.string(),
  thought: z.string(),
  action: z.string().nullable().default(null),
  action_input: z.record(z.unknown()).nullable().default(null),
});

export const ToolCallDataSchema = z.object({
  agent_id: z.string(),
  tool_name: z.string(),
  tool_input: z.record(z.unknown()),
  timestamp: z.string().datetime(),
});

export const ToolResultDataSchema = z.object({
  agent_id: z.string(),
  tool_name: z.string(),
  tool_output: z.string(),
  duration_ms: z.number().int().nonnegative(),
});

export const AgentCompletedDataSchema = z.object({
  agent_id: z.string(),
  output: z.string(),
  tokens: z.object({
    input: z.number().int().nonnegative(),
    output: z.number().int().nonnegative(),
    total: z.number().int().nonnegative(),
  }),
});

export const HITLRequiredDataSchema = z.object({
  task_id: z.string(),
  agent_id: z.string(),
  agent_role: z.string(),
  draft_output: z.string(),
  task_description: z.string(),
  context: z.record(z.unknown()).default({}),
});

export const HITLDecisionDataSchema = z.object({
  approval_id: z.string(),
  decision: z.enum(['APPROVED', 'REJECTED']),
  reason: z.string().nullable().default(null),
  edits: z.string().nullable().default(null),
});

export const ErrorDataSchema = z.object({
  agent_id: z.string().nullable().default(null),
  error_type: z.string(),
  error_message: z.string(),
  error_details: z.record(z.unknown()).nullable().default(null),
});

// ─── Workflow Schemas ───────────────────────────────────────────────────

export const WorkflowConfigSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().max(2000).default(''),
  agents: z.array(z.object({
    role: z.string().min(1),
    goal: z.string().min(1),
    backstory: z.string().default(''),
    llm: z.object({
      provider: z.string(),
      model: z.string(),
      temperature: z.number().min(0).max(2).default(0.7),
      max_tokens: z.number().int().positive().default(4096),
    }),
    tools: z.array(z.string()).default([]),
    allow_delegation: z.boolean().default(false),
    max_iterations: z.number().int().positive().default(15),
  })),
  tasks: z.array(z.object({
    title: z.string().min(1),
    description: z.string(),
    expected_output: z.string(),
    agent_role: z.string(),
    dependencies: z.array(z.string()).default([]),
    requires_approval: z.boolean().default(false),
    priority: z.enum(['low', 'medium', 'high']).default('medium'),
    timeout_ms: z.number().int().positive().default(300000),
    max_retries: z.number().int().nonnegative().default(3),
  })),
  process_type: z.enum(['sequential', 'hierarchical']).default('sequential'),
});

// ─── Execution Schemas ──────────────────────────────────────────────────

export const ExecutionStatusSchema = z.nativeEnum(WorkflowStatus);

export const RunWorkflowRequestSchema = z.object({
  workflow_id: z.string(),
});

export const RunWorkflowResponseSchema = z.object({
  execution_id: z.string(),
  status: ExecutionStatusSchema,
});

// ─── Validation Helper ──────────────────────────────────────────────────

export function validateEventData<T>(schema: z.ZodSchema<T>, data: unknown): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new Error(`Event data validation failed: ${result.error.message}`);
  }
  return result.data;
}