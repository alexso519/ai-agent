# CrewAI Enterprise Control Center — Frontend Architecture

> **Document Type**: Frontend Architecture Specification  
> **Status**: Pre-Implementation Design  
> **Version**: 1.0  
> **Architecture Source**: [`ARCHITECTURAL_ANALYSIS.md`](../ARCHITECTURAL_ANALYSIS.md)

---

## Table of Contents

1. [Module Boundaries & Dependency Rules](#1-module-boundaries--dependency-rules)
2. [Frontend Type Contracts](#2-frontend-type-contracts)
3. [Next.js App Router Structure](#3-nextjs-app-router-structure)
4. [Zustand Slice Strategy](#4-zustand-slice-strategy)
5. [React Flow Integration Architecture](#5-react-flow-integration-architecture)
6. [Canvas Rendering Architecture](#6-canvas-rendering-architecture)
7. [YAML↔Store Synchronization Architecture](#7-yaml↔store-synchronization-architecture)
8. [Event Subscription Architecture](#8-event-subscription-architecture)
9. [Inspector Architecture](#9-inspector-architecture)
10. [Terminal Streaming Architecture](#10-terminal-streaming-architecture)
11. [API Service Boundaries](#11-api-service-boundaries)
12. [Shared Component Architecture](#12-shared-component-architecture)
13. [Complete Frontend Folder Structure](#13-complete-frontend-folder-structure)
14. [Hook Strategy](#14-hook-strategy)
15. [Performance Architecture](#15-performance-architecture)
16. [Observability Architecture](#16-observability-architecture)

---

## 1. Module Boundaries & Dependency Rules

### 1.1 Frontend Internal Module Map

```
┌────────────────────────────────────────────────────────────────────────┐
│                          apps/web (Frontend)                            │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │  App Router │  │  Components  │  │   Store    │  │   Services    │  │
│  │  (pages)    │──▶  (UI layer)  │──▶  (state)   │──▶  (API calls)  │  │
│  └─────────────┘  └──────────────┘  └────────────┘  └───────┬───────┘  │
│                          │                        requests    │          │
│                          │                           to        │          │
│                          ▼                           ▼        ▼          │
│                  ┌──────────────┐          ┌─────────────────────┐       │
│                  │   Hooks      │          │   SSE Stream        │       │
│                  │  (logic)     │          │   (real-time)       │       │
│                  └──────────────┘          └─────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│                  ┌──────────────┐                                        │
│                  │   Lib       │                                        │
│                  │  (sync,     │                                        │
│                  │   stream)   │                                        │
│                  └──────────────┘                                        │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Strict Dependency Rules

```
┌──────────────────────────────────────────────────┐
│                  DEPENDENCY FLOW                    │
├──────────────────────────────────────────────────┤
│                                                     │
│  app/ → components, hooks, services, store, lib     │
│  components/ → hooks, store, services (via hooks)   │
│  components/ → lib (sync engine, stream client)     │
│  hooks/ → store, services, lib                      │
│  store/ → services (async actions)                  │
│  services/ → types (response/request types)         │
│  lib/ → types                                       │
│                                                     │
│  FORBIDDEN:                                         │
│  - components/ → components/canvas directly         │
│    (cross-domain component imports only via hooks)  │
│  - lib/ → store (sync engine injects store,         │
│    does not import it)                              │
│  - services/ → store (keep API layer pure)          │
│  - store/ → lib (no direct sync/stream coupling)    │
│                                                     │
└──────────────────────────────────────────────────┘
```

### 1.3 External Dependency Rules

```
apps/web:
  → packages/shared-types       (types, events, schemas, constants)
  → packages/ui                (shared UI components)
  → NO direct imports to:
    - apps/api/**
    - apps/worker/**
    - packages/crew-runtime/**
```

---

## 2. Frontend Type Contracts

### 2.1 Source of Truth

All domain types, event types, and validation schemas live in [`packages/shared-types/src/`](../../packages/shared-types/src/). The frontend imports from this package exclusively. **No type duplication allowed.**

### 2.2 Frontend-Specific Types

Types that are **purely UI concerns** (not domain) live in [`apps/web/src/types/`](types/).

```typescript
// apps/web/src/types/canvas.ts

import type { Node, Edge, Viewport } from '@xyflow/react';

/** Typed React Flow node data for agent nodes */
export interface AgentNodeData {
  role: string;
  goal: string;
  backstory: string;
  llmModel: string;
  memoryEnabled: boolean;
  tools: string[];
  status: 'idle' | 'running' | 'success' | 'failed' | 'waiting-human';
  tokenCount: number;
  temperature: number;
  maxTokens: number;
  iterations: number;
  rpmLimit: number;
}

/** Typed React Flow node data for task nodes */
export interface TaskNodeData {
  title: string;
  description: string;
  expectedOutput: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'awaiting-approval';
  progress: number;
  timeout: number;
  retries: number;
  requiresApproval: boolean;
  priority: 'low' | 'medium' | 'high';
}

/** Typed React Flow node data for tool nodes */
export interface ToolNodeData {
  toolType: 'web_search' | 'sql' | 'api_connector' | 'file_reader' | 'python_executor' | 'vector_search';
  permissions: string[];
  config: Record<string, unknown>;
}

/** Union of all node data types */
export type WorkflowNodeData = AgentNodeData | TaskNodeData | ToolNodeData;

/** Typed React Flow node */
export type WorkflowNode = Node<WorkflowNodeData, 'agent' | 'task' | 'tool'>;

/** Typed React Flow edge */
export type WorkflowEdge = Edge<{ animated: boolean; label?: string }>;

/** Canvas viewport state */
export interface CanvasViewport {
  x: number;
  y: number;
  zoom: number;
}
```

```typescript
// apps/web/src/types/ui.ts

/** IDE panel layout configuration */
export interface PanelLayout {
  leftSidebar: { width: number; collapsed: boolean };
  rightInspector: { width: number; collapsed: boolean };
  bottomPanel: { height: number; collapsed: boolean; activeTab: 'terminal' | 'metrics' };
}

/** Editor tab identifiers */
export type SidebarTab = 'agents' | 'tasks' | 'tools' | 'templates';

/** Bottom panel tab identifiers */
export type BottomTab = 'terminal' | 'metrics';

/** Modal/dialog identifiers */
export type DialogType = 'hitl-approval' | 'confirm-delete' | 'error-detail' | 'template-save' | 'workflow-settings';
```

```typescript
// apps/web/src/types/terminal.ts

import type { EventType, EventSource } from '@shared/types';

/** Log entry displayed in terminal */
export interface TerminalLogEntry {
  id: string;
  eventType: EventType;
  source: EventSource;
  agentId: string | null;
  taskId: string | null;
  message: string;
  timestamp: string;
  correlationId: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  data: Record<string, unknown>;
}

/** Terminal filter criteria */
export interface TerminalFilter {
  agentId: string | null;
  level: string | null;
  eventType: EventType | null;
  searchQuery: string;
}

/** Terminal state */
export type TerminalScrollMode = 'auto-scroll' | 'paused';
```

```typescript
// apps/web/src/types/metrics.ts

export interface TokenMetrics {
  workflowId: string;
  agentId: string | null;
  taskId: string | null;
  step: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  estimatedCost: number;
  durationMs: number;
  timestamp: string;
}

export interface ExecutionTimelineEntry {
  agentId: string;
  taskId: string;
  status: string;
  startTime: string;
  endTime: string | null;
  durationMs: number | null;
}

export interface FailureMetric {
  agentId: string;
  taskId: string;
  errorType: string;
  count: number;
  lastOccurrence: string;
}
```

```typescript
// apps/web/src/types/sync.ts

/** Result of parsing YAML input */
export interface YAMLParseResult {
  success: boolean;
  data: WorkflowGraph | null;
  errors: YAMLValidationError[];
  version: number;
}

export interface YAMLValidationError {
  path: string;
  message: string;
  code: string;
}

/** Graph change event for sync engine */
export interface GraphChange {
  type: 'node-added' | 'node-removed' | 'node-moved' | 'node-updated' | 'edge-added' | 'edge-removed';
  nodeId?: string;
  edgeId?: string;
  timestamp: number;
}
```

---

## 3. Next.js App Router Structure

### 3.1 Route Tree

```typescript
// apps/web/src/app/

app/
├── layout.tsx                          // Root layout: providers, auth guard, global styles
├── page.tsx                            // Redirect to /workflows
├── (dashboard)/
│   ├── layout.tsx                      // Dashboard layout: sidebar + main area + right panel
│   ├── workflows/
│   │   ├── page.tsx                    // Workflow list page
│   │   ├── [workflowId]/
│   │   │   ├── layout.tsx              // Workflow detail layout: canvas shell
│   │   │   ├── page.tsx                // Canvas editor page (default)
│   │   │   ├── execution/
│   │   │   │   └── page.tsx            // Execution history for specific workflow
│   │   │   └── settings/
│   │   │       └── page.tsx            // Workflow configuration/settings
│   │   └── new/
│   │       └── page.tsx                // Create new workflow page
│   ├── approvals/
│   │   ├── page.tsx                    // Approval inbox list
│   │   └── [approvalId]/
│   │       └── page.tsx                // Approval detail (HITL)
│   ├── templates/
│   │   ├── page.tsx                    // Template library
│   │   └── [templateId]/
│   │       └── page.tsx                // Template detail
│   └── settings/
│       └── page.tsx                    // User/project settings
├── auth/
│   ├── login/
│   │   └── page.tsx                    // Login page
│   └── callback/
│       └── page.tsx                    // Auth callback (OAuth)
├── error.tsx                           // Global error boundary
├── loading.tsx                         // Global loading state
└── not-found.tsx                       // 404 page
```

### 3.2 Layout Responsibilities

| Layout | Responsibility |
|--------|---------------|
| [`app/layout.tsx`](app/layout.tsx) | Providers (Theme, Store, Auth), global error boundary, font loading |
| [`app/(dashboard)/layout.tsx`](app/(dashboard)/layout.tsx) | IDE shell: `ResizablePanelGroup` with left sidebar, main area, right inspector, bottom panel |
| [`app/(dashboard)/workflows/[workflowId]/layout.tsx`](app/(dashboard)/workflows/[workflowId]/layout.tsx) | Workflow-specific providers: SSE connection, sync engine, execution state listener |

### 3.3 Route Protection

```
app/layout.tsx → AuthProvider (checks JWT, redirects to /auth/login if unauthenticated)
app/(dashboard)/layout.tsx → Protected route group (requires auth)
app/auth/layout.tsx → Public route group (no auth required)
```

---

## 4. Zustand Slice Strategy

### 4.1 Slice Architecture

State is split into **domain slices** with **strict separation**. No slice imports another slice's internals. Cross-slice communication happens via **Zustand's `getState()` or `subscribe()`**, never direct imports.

```typescript
// apps/web/src/store/

store/
├── index.ts                            // Combined store with all slices
├── slices/
│   ├── canvas-slice.ts                 // Workflow graph state
│   ├── execution-slice.ts              // Workflow execution runtime
│   ├── terminal-slice.ts               // Observability log stream
│   ├── hitl-slice.ts                   // Human-in-the-loop approvals
│   ├── ui-slice.ts                     // UI layout, modals, sidebar state
│   ├── metrics-slice.ts                // Token/metrics data
│   └── sync-slice.ts                   // Sync engine version tracking
├── selectors/
│   ├── canvas-selectors.ts             // Derived canvas state
│   ├── execution-selectors.ts          // Derived execution state
│   ├── terminal-selectors.ts           // Filtered log views
│   ├── hitl-selectors.ts               // Approval queue counts
│   └── ui-selectors.ts                 // Panel visibility states
└── middleware/
    ├── logger.ts                       // Dev-only action logging
    └── sync-middleware.ts              // Triggers sync engine on canvas changes
```

### 4.2 Canvas Slice

```typescript
// apps/web/src/store/slices/canvas-slice.ts

interface CanvasSlice {
  // State
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  viewport: CanvasViewport;

  // Node actions
  addNode: (type: 'agent' | 'task' | 'tool', position: { x: number; y: number }) => string;
  removeNode: (id: string) => void;
  updateNodeData: <T extends keyof WorkflowNodeData>(id: string, data: Partial<WorkflowNodeData[T]>) => void;
  moveNode: (id: string, position: { x: number; y: number }) => void;
  selectNode: (id: string | null) => void;

  // Edge actions
  addEdge: (source: string, target: string) => void;
  removeEdge: (id: string) => void;
  selectEdge: (id: string | null) => void;

  // Viewport actions
  setViewport: (viewport: CanvasViewport) => void;
  fitView: () => void;

  // Batch actions
  replaceGraph: (nodes: WorkflowNode[], edges: WorkflowEdge[]) => void;
  clearCanvas: () => void;
}
```

### 4.3 Execution Slice

```typescript
// apps/web/src/store/slices/execution-slice.ts

interface ExecutionSlice {
  // State
  workflowStatus: WorkflowStatus;
  activeExecutionId: string | null;
  agentStates: Record<string, AgentExecutionStatus>;
  taskStates: Record<string, 'pending' | 'running' | 'completed' | 'failed'>;
  overallProgress: number; // 0–100
  startedAt: string | null;
  completedAt: string | null;
  error: string | null;

  // Actions
  runWorkflow: (workflowId: string) => Promise<void>;
  pauseWorkflow: (executionId: string) => Promise<void>;
  resumeWorkflow: (executionId: string) => Promise<void>;
  stopWorkflow: (executionId: string) => Promise<void>;
  retryWorkflow: (executionId: string) => Promise<void>;

  // Internal event handlers (called by SSE stream, not components)
  _handleWorkflowStarted: (event: WorkflowStartedEvent) => void;
  _handleWorkflowCompleted: (event: WorkflowCompletedEvent) => void;
  _handleWorkflowFailed: (event: WorkflowFailedEvent) => void;
  _handleAgentStateChange: (event: AgentStateChangeEvent) => void;
  _handleTaskProgress: (event: TaskProgressEvent) => void;
  _handleWorkflowSuspended: (event: WorkflowSuspendedEvent) => void;
  _handleWorkflowResumed: (event: WorkflowResumedEvent) => void;

  // State mutations (internal)
  _setStatus: (status: WorkflowStatus) => void;
  _setAgentState: (agentId: string, state: AgentExecutionStatus) => void;
  _setTaskState: (taskId: string, state: 'pending' | 'running' | 'completed' | 'failed') => void;
  _setProgress: (progress: number) => void;
}
```

### 4.4 Terminal Slice

```typescript
// apps/web/src/store/slices/terminal-slice.ts

interface TerminalSlice {
  // State
  entries: TerminalLogEntry[];
  maxEntries: number; // limit: 10,000 to prevent memory overflow
  filter: TerminalFilter;
  scrollMode: TerminalScrollMode;
  highlightedEventId: string | null;

  // Actions
  appendEntry: (entry: TerminalLogEntry) => void;
  appendEntries: (entries: TerminalLogEntry[]) => void;
  setFilter: (filter: Partial<TerminalFilter>) => void;
  resetFilter: () => void;
  setScrollMode: (mode: TerminalScrollMode) => void;
  clear: () => void;
  exportLogs: () => string;
  highlightEvent: (id: string | null) => void;
}
```

### 4.5 HITL Slice

```typescript
// apps/web/src/store/slices/hitl-slice.ts

interface HITLSlice {
  // State
  pendingApprovals: ApprovalRequest[];
  activeApprovalId: string | null;
  approvalHistory: ApprovalRequest[];

  // Actions
  setPendingApprovals: (approvals: ApprovalRequest[]) => void;
  selectApproval: (id: string | null) => void;
  approve: (id: string, edits?: string) => Promise<void>;
  reject: (id: string, reason: string) => Promise<void>;
  regenerate: (id: string) => Promise<void>;
  _handleHitlRequired: (event: HITLRequiredEvent) => void;
  _handleHitlResolved: (event: HITLResolvedEvent) => void;
}
```

### 4.6 UI Slice

```typescript
// apps/web/src/store/slices/ui-slice.ts

interface UISlice {
  // Layout state
  panelLayout: PanelLayout;
  activeSidebarTab: SidebarTab;
  activeBottomTab: BottomTab;
  activeDialog: DialogType | null;

  // Actions
  setPanelLayout: (layout: Partial<PanelLayout>) => void;
  toggleLeftSidebar: () => void;
  toggleRightInspector: () => void;
  toggleBottomPanel: () => void;
  setActiveSidebarTab: (tab: SidebarTab) => void;
  setActiveBottomTab: (tab: BottomTab) => void;
  openDialog: (dialog: DialogType) => void;
  closeDialog: () => void;
}
```

### 4.7 Metrics Slice

```typescript
// apps/web/src/store/slices/metrics-slice.ts

interface MetricsSlice {
  // State
  tokenMetrics: TokenMetrics[];
  executionTimeline: ExecutionTimelineEntry[];
  failureMetrics: FailureMetric[];
  selectedTimeRange: '5m' | '15m' | '1h' | 'all';

  // Actions
  setTokenMetrics: (metrics: TokenMetrics[]) => void;
  appendTokenMetric: (metric: TokenMetrics) => void;
  setExecutionTimeline: (timeline: ExecutionTimelineEntry[]) => void;
  setFailureMetrics: (metrics: FailureMetric[]) => void;
  setTimeRange: (range: string) => void;
  _handleMetricsUpdate: (event: MetricsUpdateEvent) => void;
}
```

### 4.8 Combined Store

```typescript
// apps/web/src/store/index.ts

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

export type AppStore = CanvasSlice
  & ExecutionSlice
  & TerminalSlice
  & HITLSlice
  & UISlice
  & MetricsSlice;

export const useStore = create<AppStore>()(
  subscribeWithSelector((...a) => ({
    ...createCanvasSlice(...a),
    ...createExecutionSlice(...a),
    ...createTerminalSlice(...a),
    ...createHITLSlice(...a),
    ...createUISlice(...a),
    ...createMetricsSlice(...a),
  }))
);
```

### 4.9 Selector Pattern

```typescript
// apps/web/src/store/selectors/canvas-selectors.ts

import { useStore } from '../index';

// Memoized selectors using shallow comparison
export const useSelectedNode = () =>
  useStore((s) => {
    if (!s.selectedNodeId) return null;
    return s.nodes.find((n) => n.id === s.selectedNodeId) ?? null;
  }, shallow);

export const useAgentNodes = () =>
  useStore((s) => s.nodes.filter((n) => n.type === 'agent'), shallow);

export const useTaskNodes = () =>
  useStore((s) => s.nodes.filter((n) => n.type === 'task'), shallow);

export const useNodeById = (id: string) =>
  useStore((s) => s.nodes.find((n) => n.id === id) ?? null, shallow);

export const useIsCanvasEmpty = () =>
  useStore((s) => s.nodes.length === 0 && s.edges.length === 0);
```

---

## 5. React Flow Integration Architecture

### 5.1 Architecture Overview

React Flow is isolated within a **canvas wrapper component** that manages:
- Node/edge registration
- Viewport state synchronization with Zustand
- Event handler delegation (drag, connect, select)
- Performance optimization (node memoization, lazy rendering)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CanvasShell (layout wrapper)                     │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                      WorkflowCanvas                                │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  <ReactFlow>                                                   │  │  │
│  │  │    <Background />                                              │  │  │
│  │  │    <Controls />                                                │  │  │
│  │  │    <MiniMap />                                                 │  │  │
│  │  │    <AgentNode />  (nodeTypes.agent)                            │  │  │
│  │  │    <TaskNode />    (nodeTypes.task)                             │  │  │
│  │  │    <ToolNode />    (nodeTypes.tool)                             │  │  │
│  │  │    <AnimatedEdge /> (edgeTypes.default)                        │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                      YAMLEditor (collapsible)                      │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Canvas Component

```typescript
// apps/web/src/components/canvas/workflow-canvas.tsx

'use client';

import React, { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  SelectionMode,
  type NodeTypes,
  type EdgeTypes,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type NodeDragHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { AgentNode } from './nodes/agent-node';
import { TaskNode } from './nodes/task-node';
import { ToolNode } from './nodes/tool-node';
import { AnimatedEdge } from './edges/animated-edge';

import { useStore } from '@/store';
import { useCanvasHandlers } from '@/hooks/use-canvas-handlers';
import { useCanvasSync } from '@/hooks/use-canvas-sync';

const nodeTypes: NodeTypes = {
  agent: AgentNode,
  task: TaskNode,
  tool: ToolNode,
};

const edgeTypes: EdgeTypes = {
  default: AnimatedEdge,
};

export function WorkflowCanvas() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const selectedNodeId = useStore((s) => s.selectedNodeId);

  const {
    onNodesChange,
    onEdgesChange,
    onConnect,
    onNodeClick,
    onNodeDragStart,
    onNodeDragStop,
    onPaneClick,
    onMoveEnd,
  } = useCanvasHandlers();

  // Sync canvas changes to YAML engine
  useCanvasSync();

  const defaultEdgeOptions = useMemo(() => ({
    animated: true,
    style: { strokeWidth: 2 },
  }), []);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      defaultEdgeOptions={defaultEdgeOptions}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={onNodeClick}
      onNodeDragStart={onNodeDragStart}
      onNodeDragStop={onNodeDragStop}
      onPaneClick={onPaneClick}
      onMoveEnd={onMoveEnd}
      fitView
      selectionMode={SelectionMode.Partial}
      deleteKeyCode={['Backspace', 'Delete']}
      multiSelectionKeyCode="Shift"
      panOnDrag={[1, 2]} // Middle + right mouse button
      selectNodesOnDrag={false}
    >
      <Background variant="dots" gap={20} size={1} />
      <Controls showInteractive={false} />
      <MiniMap
        nodeStrokeColor={(n) => {
          const data = n.data as { status?: string };
          const statusColors: Record<string, string> = {
            running: '#3b82f6',
            success: '#22c55e',
            failed: '#ef4444',
            'waiting-human': '#f97316',
          };
          return statusColors[data.status ?? 'idle'] ?? '#94a3b8';
        }}
        maskColor="rgba(0,0,0,0.1)"
      />
    </ReactFlow>
  );
}
```

### 5.3 Node Component Architecture

Each node type follows the **exact same pattern**:

```
nodes/
├── agent-node.tsx            // AgentNode — renders role, LLM, status glow
├── task-node.tsx             // TaskNode — renders title, progress bar
├── tool-node.tsx             // ToolNode — renders icon, permissions
├── base/
│   ├── node-wrapper.tsx      // Shared wrapper: drag handle, selection, status glow
│   └── node-status-badge.tsx // Status indicator with animated pulse
└── shared/
    ├── progress-bar.tsx      // Reusable progress bar component
    └── status-dot.tsx        // Animated status dot
```

### 5.4 Node Design Pattern

```typescript
// apps/web/src/components/canvas/base/node-wrapper.tsx

import { memo, type ReactNode } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { cn } from '@/lib/utils';

interface NodeWrapperProps {
  children: ReactNode;
  selected: boolean;
  status: 'idle' | 'running' | 'success' | 'failed' | 'waiting-human';
  label: string;
  icon?: ReactNode;
  onDoubleClick?: () => void;
}

const statusColors: Record<string, string> = {
  idle: 'border-slate-300',
  running: 'border-blue-500 shadow-blue-500/50 animate-pulse',
  success: 'border-green-500 shadow-green-500/50',
  failed: 'border-red-500 shadow-red-500/50',
  'waiting-human': 'border-orange-500 shadow-orange-500/50',
};

export const NodeWrapper = memo(function NodeWrapper({
  children,
  selected,
  status,
  label,
  icon,
  onDoubleClick,
}: NodeWrapperProps) {
  return (
    <div
      className={cn(
        'rounded-lg border-2 bg-white p-3 shadow-sm min-w-[200px]',
        'transition-all duration-200',
        statusColors[status],
        selected && 'ring-2 ring-blue-400 ring-offset-2',
      )}
      onDoubleClick={onDoubleClick}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400" />
      
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-lg">{icon}</span>}
        <span className="font-medium text-sm text-slate-800 truncate">{label}</span>
      </div>
      
      {children}
      
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-400"
      />
    </div>
  );
});
```

---

## 6. Canvas Rendering Architecture

### 6.1 Performance Strategy

| Technique | Application | Reason |
|-----------|------------|--------|
| **Node memoization** | `React.memo` on all custom nodes | Prevents unnecessary re-renders on viewport change |
| **Zustand selectors** | `shallow` comparison on all node selections | Only re-render nodes when their data changes |
| **Lazy node rendering** | `onlyRenderVisibleElements` (React Flow built-in) | Don't render off-screen nodes |
| **Edge optimization** | Path caching on edges | Reduce SVG path calculations |
| **Event delegation** | Single handler per event type on `<ReactFlow>` | Avoid per-node event listeners |

### 6.2 Render Pipeline

```
User Action (drag, select, connect)
       │
       ▼
React Flow internal state (onNodesChange)
       │
       ▼
Zustand store update (via useCanvasHandlers hook)
       │
       ▼
SyncEngine.onUIChange()  ──→ Debounced YAML update
       │
       ▼
Re-render affected nodes only (React.memo + shallow selectors)
```

### 6.3 Status Update Rendering (Execution)

When execution events arrive via SSE, only affected nodes re-render:

```
SSE Event: AGENT_STATE_CHANGE (agentId: "agent_2", status: "running")
       │
       ▼
ExecutionSlice._setAgentState("agent_2", "running")
       │
       ▼
Zustand state change (agentStates["agent_2"] = "running")
       │
       ▼
useAgentStatus(agentId: "agent_2") hook fires
       │
       ▼
AgentNode(id: "agent_2") re-renders with new status glow
(No other nodes re-render)
```

### 6.4 Node Status Hook

```typescript
// apps/web/src/hooks/use-agent-status.ts

import { useStore } from '@/store';
import { shallow } from 'zustand/shallow';

export function useAgentStatus(agentId: string) {
  return useStore(
    (state) => ({
      status: state.agentStates[agentId] ?? 'idle',
      progress: state.taskStates[agentId] !== undefined ? undefined : undefined,
    }),
    shallow,
  );
}
```

---

## 7. YAML↔Store Synchronization Architecture

### 7.1 Three-Phase Sync Model

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SYNC ENGINE ARCHITECTURE                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────┐          ┌──────────────────────────┐        │
│  │   Monaco Editor      │          │   Zustand Store           │        │
│  │   (YAML input)       │◄────────►│   (Canonical Source of    │        │
│  │                      │   sync   │    Truth)                 │        │
│  └──────────┬───────────┘          └────────────┬─────────────┘        │
│             │                                   │                        │
│             │                                   │                        │
│             ▼                                   ▼                        │
│  ┌──────────────────────────────────────────────────────┐               │
│  │                   SyncEngine                          │               │
│  │                                                       │               │
│  │  ┌──────────────┐  ┌────────────┐  ┌──────────────┐  │               │
│  │  │ YAML Parser  │  │ Validator  │  │ Version      │  │               │
│  │  │ (js-yaml)   │──▶│ (Zod)     │──▶│ Tracker     │  │               │
│  │  └──────────────┘  └────────────┘  └──────────────┘  │               │
│  │                                                       │               │
│  │  ┌──────────────┐  ┌────────────┐  ┌──────────────┐  │               │
│  │  │ Serializer    │  │ Debouncer  │  │ Conflict     │  │               │
│  │  │ (store→YAML) │──▶│ (300ms)   │──▶│ Resolver    │  │               │
│  │  └──────────────┘  └────────────┘  └──────────────┘  │               │
│  └──────────────────────────────────────────────────────┘               │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Sync Engine Implementation

```typescript
// apps/web/src/lib/sync/sync-engine.ts

import type { WorkflowNode, WorkflowEdge, GraphChange, YAMLParseResult } from '@/types';
import type { AppStore } from '@/store';

/**
 * Synchronization Engine
 * 
 * Manages bidirectional sync between Zustand store (canonical source of truth)
 * and Monaco YAML editor. Uses version tracking to prevent sync loops and
 * resolve conflicts.
 * 
 * Phase 1: UI Change → Store (canonical) → Debounced YAML write
 * Phase 2: YAML Paste → Zod validation → Store update (on success)
 * Phase 3: Conflict resolution via version counter
 */
export class SyncEngine {
  private store: AppStore;
  private version: number = 0;
  private editorRef: { setValue: (yaml: string) => void } | null = null;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private isSyncing: boolean = false;

  private readonly DEBOUNCE_MS = 300;
  private readonly yamlParser: YAMLParser;
  private readonly validator: WorkflowValidator;

  constructor(store: AppStore) {
    this.store = store;
    this.yamlParser = new YAMLParser();
    this.validator = new WorkflowValidator();
  }

  /** Register Monaco editor instance for YAML updates */
  registerEditor(editor: { setValue: (yaml: string) => void }): void {
    this.editorRef = editor;
  }

  /** Called when user interacts with canvas or inspector */
  onUIChange(change: GraphChange): void {
    if (this.isSyncing) return;
    this.version++;
    this.scheduleYAMLSync();
  }

  /** Called when user types or pastes YAML in Monaco */
  onYAMLChange(yaml: string): YAMLParseResult {
    if (this.isSyncing) return { success: true, data: null, errors: [], version: this.version };

    // Phase 2: Validate YAML
    const parsed = this.yamlParser.parse(yaml);
    if (!parsed.success) {
      return { success: false, data: null, errors: parsed.errors, version: this.version };
    }

    // Check version conflict
    if (parsed.version > this.version) {
      this.isSyncing = true;
      this.version = parsed.version;
      
      // Phase 2b: Update store (triggers canvas re-render)
      this.store.replaceGraph(parsed.data.nodes, parsed.data.edges);
      
      this.isSyncing = false;
      return { success: true, data: parsed.data, errors: [], version: this.version };
    }

    // Version conflict: last-write-wins with notification
    return {
      success: false,
      data: null,
      errors: [{ path: '', message: 'Version conflict detected', code: 'VERSION_CONFLICT' }],
      version: this.version,
    };
  }

  /** Schedule a debounced YAML sync from store → editor */
  private scheduleYAMLSync(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    this.debounceTimer = setTimeout(() => {
      this.syncStoreToYAML();
    }, this.DEBOUNCE_MS);
  }

  /** Serialize store state to YAML and update editor */
  private syncStoreToYAML(): void {
    if (!this.editorRef) return;

    this.isSyncing = true;
    
    const nodes = this.store.nodes;
    const edges = this.store.edges;
    const yaml = this.yamlParser.serialize(nodes, edges, this.version);
    
    this.editorRef.setValue(yaml);
    
    this.isSyncing = false;
  }

  getCurrentVersion(): number {
    return this.version;
  }
}
```

### 7.3 Sync Middleware

```typescript
// apps/web/src/store/middleware/sync-middleware.ts

import { type StateCreator } from 'zustand';
import type { SyncEngine } from '@/lib/sync/sync-engine';
import type { AppStore } from '../index';

/**
 * Zustand middleware that intercepts canvas state changes
 * and notifies the SyncEngine.
 */
export const createSyncMiddleware = (syncEngine: SyncEngine) =>
  (config: StateCreator<AppStore>): StateCreator<AppStore> =>
    (set, get, api) => {
      const store = config(set, get, api);

      return {
        ...store,
        addNode: (...args) => {
          store.addNode(...args);
          syncEngine.onUIChange({ type: 'node-added', timestamp: Date.now() });
        },
        removeNode: (...args) => {
          store.removeNode(...args);
          syncEngine.onUIChange({ type: 'node-removed', timestamp: Date.now() });
        },
        updateNodeData: (...args) => {
          store.updateNodeData(...args);
          syncEngine.onUIChange({ type: 'node-updated', timestamp: Date.now() });
        },
        moveNode: (...args) => {
          store.moveNode(...args);
          syncEngine.onUIChange({ type: 'node-moved', timestamp: Date.now() });
        },
        replaceGraph: (...args) => {
          store.replaceGraph(...args);
          syncEngine.onUIChange({ type: 'node-updated', timestamp: Date.now() });
        },
      };
    };
```

---

## 8. Event Subscription Architecture

### 8.1 SSE Client Manager

```typescript
// apps/web/src/lib/stream/sse-client.ts

import type { RuntimeEvent } from '@shared/types';

export type EventHandler = (event: RuntimeEvent<unknown>) => void;

interface ConnectionState {
  source: EventSource | null;
  workflowId: string;
  handlers: EventHandler[];
  reconnectAttempts: number;
  lastEventId: string | null;
  status: 'disconnected' | 'connecting' | 'connected' | 'reconnecting';
}

/**
 * SSE Client Manager
 * 
 * Manages SSE connections to the API for real-time workflow events.
 * Supports:
 * - Multiple concurrent connections (one per workflow)
 * - Exponential backoff reconnection
 * - Last-Event-Id replay on reconnect
 * - Status tracking per connection
 * - Automatic cleanup on unmount
 */
export class SSEClientManager {
  private connections: Map<string, ConnectionState> = new Map();
  private readonly maxRetries = 5;
  private readonly backoffMs = [1000, 2000, 4000, 8000, 16000];

  /** Connect to workflow event stream */
  connect(workflowId: string, handler: EventHandler): void {
    const existing = this.connections.get(workflowId);
    
    if (existing) {
      // Add handler to existing connection
      existing.handlers.push(handler);
      return;
    }

    const state: ConnectionState = {
      source: null,
      workflowId,
      handlers: [handler],
      reconnectAttempts: 0,
      lastEventId: null,
      status: 'connecting',
    };

    this.connections.set(workflowId, state);
    this.establishConnection(workflowId);
  }

  /** Disconnect from workflow event stream */
  disconnect(workflowId: string, handler: EventHandler): void {
    const state = this.connections.get(workflowId);
    if (!state) return;

    // Remove specific handler
    state.handlers = state.handlers.filter((h) => h !== handler);

    // Only close connection when no more handlers
    if (state.handlers.length === 0) {
      state.source?.close();
      this.connections.delete(workflowId);
    }
  }

  /** Disconnect all connections (on unmount) */
  disconnectAll(): void {
    for (const [workflowId] of this.connections) {
      const state = this.connections.get(workflowId);
      state?.source?.close();
    }
    this.connections.clear();
  }

  /** Get connection status for a workflow */
  getConnectionStatus(workflowId: string): ConnectionState['status'] {
    return this.connections.get(workflowId)?.status ?? 'disconnected';
  }

  private establishConnection(workflowId: string): void {
    const state = this.connections.get(workflowId);
    if (!state) return;

    state.status = 'connecting';

    const url = `/api/workflow/stream/${workflowId}${state.lastEventId ? `?lastEventId=${state.lastEventId}` : ''}`;
    const source = new EventSource(url);

    source.onopen = () => {
      state.status = 'connected';
      state.reconnectAttempts = 0;
    };

    source.addEventListener('message', (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data) as RuntimeEvent<unknown>;
        state.lastEventId = event.lastEventId || parsed.id;
        
        // Dispatch to all registered handlers
        for (const handler of state.handlers) {
          handler(parsed);
        }
      } catch {
        console.error('[SSEClient] Failed to parse event:', event.data);
      }
    });

    source.onerror = () => {
      source.close();
      state.source = null;
      state.status = 'reconnecting';
      this.scheduleReconnect(workflowId);
    };

    state.source = source;
  }

  private scheduleReconnect(workflowId: string): void {
    const state = this.connections.get(workflowId);
    if (!state) return;

    if (state.reconnectAttempts >= this.maxRetries) {
      state.status = 'disconnected';
      console.error(`[SSEClient] Max retries reached for workflow ${workflowId}`);
      return;
    }

    const delay = this.backoffMs[state.reconnectAttempts] ?? this.backoffMs[this.backoffMs.length - 1];
    state.reconnectAttempts++;

    setTimeout(() => {
      this.establishConnection(workflowId);
    }, delay);
  }
}

// Singleton instance
export const sseClient = new SSEClientManager();
```

### 8.2 Event Router Hook

```typescript
// apps/web/src/hooks/use-workflow-stream.ts

import { useEffect, useRef } from 'react';
import { useStore } from '@/store';
import { sseClient } from '@/lib/stream/sse-client';
import type { RuntimeEvent } from '@shared/types';

/**
 * Hook that subscribes to SSE stream for a workflow.
 * Routes events to the appropriate store slice based on event type.
 * 
 * Automatically connects on mount and disconnects on unmount.
 */
export function useWorkflowStream(workflowId: string | null): void {
  const handlerRef = useRef<((event: RuntimeEvent<unknown>) => void) | null>(null);

  const handleWorkflowStarted = useStore((s) => s._handleWorkflowStarted);
  const handleWorkflowCompleted = useStore((s) => s._handleWorkflowCompleted);
  const handleWorkflowFailed = useStore((s) => s._handleWorkflowFailed);
  const handleAgentStateChange = useStore((s) => s._handleAgentStateChange);
  const handleTaskProgress = useStore((s) => s._handleTaskProgress);
  const handleWorkflowSuspended = useStore((s) => s._handleWorkflowSuspended);
  const handleWorkflowResumed = useStore((s) => s._handleWorkflowResumed);
  const appendEntry = useStore((s) => s.appendEntry);
  const handleHitlRequired = useStore((s) => s._handleHitlRequired);
  const handleMetricsUpdate = useStore((s) => s._handleMetricsUpdate);

  useEffect(() => {
    if (!workflowId) return;

    const handler = (event: RuntimeEvent<unknown>) => {
      // Route event to appropriate handler based on type
      switch (event.type) {
        // Workflow lifecycle
        case 'WORKFLOW_STARTED':
          handleWorkflowStarted(event);
          break;
        case 'WORKFLOW_COMPLETED':
          handleWorkflowCompleted(event);
          break;
        case 'WORKFLOW_FAILED':
          handleWorkflowFailed(event);
          break;
        case 'WORKFLOW_PAUSED':
          handleWorkflowSuspended(event);
          break;
        case 'WORKFLOW_RESUMED':
          handleWorkflowResumed(event);
          break;

        // Agent execution
        case 'AGENT_THOUGHT':
        case 'AGENT_ACTION':
        case 'AGENT_OBSERVATION':
        case 'AGENT_TOOL_CALL':
        case 'AGENT_TOOL_ERROR':
        case 'AGENT_COMPLETED':
          handleAgentStateChange(event);
          break;

        // Progress
        case 'TASK_PROGRESS':
          handleTaskProgress(event);
          break;

        // HITL
        case 'HITL_REQUIRED':
          handleHitlRequired(event);
          break;

        // Metrics
        case 'METRICS_UPDATE':
          handleMetricsUpdate(event);
          break;
      }

      // Always append to terminal
      appendEntry({
        id: event.id,
        eventType: event.type,
        source: event.source,
        agentId: (event.data as Record<string, unknown>)?.agentId as string ?? null,
        taskId: (event.data as Record<string, unknown>)?.taskId as string ?? null,
        message: formatEventMessage(event),
        timestamp: event.timestamp,
        correlationId: event.correlationId,
        level: event.type === 'AGENT_TOOL_ERROR' || event.type === 'WORKFLOW_FAILED' || event.type === 'ERROR_OCCURRED'
          ? 'ERROR'
          : 'INFO',
        data: event.data as Record<string, unknown>,
      });
    };

    handlerRef.current = handler;
    sseClient.connect(workflowId, handler);

    return () => {
      if (handlerRef.current) {
        sseClient.disconnect(workflowId, handlerRef.current);
        handlerRef.current = null;
      }
    };
  }, [
    workflowId,
    handleWorkflowStarted,
    handleWorkflowCompleted,
    handleWorkflowFailed,
    handleAgentStateChange,
    handleTaskProgress,
    handleWorkflowSuspended,
    handleWorkflowResumed,
    appendEntry,
    handleHitlRequired,
    handleMetricsUpdate,
  ]);
}

function formatEventMessage(event: RuntimeEvent<unknown>): string {
  const data = event.data as Record<string, unknown>;
  switch (event.type) {
    case 'AGENT_THOUGHT':
      return `[${data.agentId}] ${data.thought}`;
    case 'AGENT_ACTION':
      return `[${data.agentId}] Action: ${data.action}`;
    case 'AGENT_TOOL_CALL':
      return `[${data.agentId}] Tool: ${data.tool} → ${data.output}`;
    case 'AGENT_TOOL_ERROR':
      return `[${data.agentId}] Tool Error: ${data.error}`;
    case 'AGENT_OBSERVATION':
      return `[${data.agentId}] Observation: ${data.observation}`;
    case 'AGENT_COMPLETED':
      return `[${data.agentId}] Completed`;
    case 'TASK_PROGRESS':
      return `Task ${data.taskId}: ${data.progress}%`;
    case 'WORKFLOW_STARTED':
      return `Workflow started`;
    case 'WORKFLOW_COMPLETED':
      return `Workflow completed`;
    case 'WORKFLOW_FAILED':
      return `Workflow failed: ${data.error}`;
    case 'HITL_REQUIRED':
      return `[${data.agentId}] Waiting for human approval`;
    default:
      return `${event.type}: ${JSON.stringify(data)}`;
  }
}
```

---

## 9. Inspector Architecture

### 9.1 Dynamic Inspector Panel

The inspector renders a **dynamic form** based on the currently selected node type.

```
┌──────────────────────────────────────────┐
│           RightInspectorPanel              │
├──────────────────────────────────────────┤
│                                           │
│  ┌──────────────────────────────────────┐ │
│  │  InspectorHeader                     │ │
│  │  [Node Icon] [Node Name] [Close ✕]  │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  ┌──────────────────────────────────────┐ │
│  │  InspectorTabs                        │ │
│  │  [Config] [Memory] [LLM] [Tools]    │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  ┌──────────────────────────────────────┐ │
│  │  InspectorContent (dynamic)           │ │
│  │                                       │ │
│  │  AgentInspector ──────────────────┐   │ │
│  │  │ role: [___________]          │   │ │
│  │  │ goal: [___________]          │   │ │
│  │  │ backstory: [markdown...]     │   │ │
│  │  │ [✨ AI Enhance]              │   │ │
│  │  └──────────────────────────────┘   │ │
│  │                                       │ │
│  │  OR TaskInspector ────────────────┐   │ │
│  │  │ title: [___________]          │   │ │
│  │  │ description: [markdown...]   │   │ │
│  │  │ timeout: [____] retries: [_] │   │ │
│  │  └──────────────────────────────┘   │ │
│  │                                       │ │
│  │  OR ToolInspector ────────────────┐   │ │
│  │  │ type: [web_search ▼]          │   │ │
│  │  │ permissions: [☐ ☑ ☑]         │   │ │
│  │  └──────────────────────────────┘   │ │
│  └──────────────────────────────────────┘ │
│                                           │
└──────────────────────────────────────────┘
```

### 9.2 Inspector Component Tree

```
inspector/
├── right-inspector-panel.tsx          // Container: reads selectedNodeId, renders appropriate inspector
├── inspector-header.tsx               // Title bar with node name, icon, close button
├── inspector-tabs.tsx                 // Tab navigation (config, memory, LLM, tools)
├── agent/
│   ├── agent-inspector.tsx            // Agent config form
│   ├── agent-persona-form.tsx         // Role, goal, backstory fields
│   ├── agent-memory-matrix.tsx        // Memory toggles + clear button
│   ├── agent-llm-routing.tsx          // LLM model dropdown + parameters
│   ├── agent-tool-assignment.tsx      // Tool selection checkboxes
│   └── ai-enhancer-button.tsx         // AI prompt expander
├── task/
│   ├── task-inspector.tsx             // Task config form
│   ├── task-config-form.tsx           // Description, timeout, retries
│   └── task-approval-toggle.tsx       // HITL requirement toggle
├── tool/
│   ├── tool-inspector.tsx             // Tool config form
│   └── tool-permissions.tsx           // Permission checkboxes
└── shared/
    ├── form-field.tsx                 // Label + input wrapper
    ├── markdown-editor.tsx            // Simple markdown textarea (expandable)
    └── section-header.tsx             // Collapsible section header
```

### 9.3 Inspector Dispatch Pattern

```typescript
// apps/web/src/components/inspector/right-inspector-panel.tsx

'use client';

import { useStore } from '@/store';
import { useSelectedNode } from '@/store/selectors/canvas-selectors';
import { AgentInspector } from './agent/agent-inspector';
import { TaskInspector } from './task/task-inspector';
import { ToolInspector } from './tool/tool-inspector';
import { InspectorHeader } from './inspector-header';

/**
 * Right inspector panel.
 * Dynamically renders the appropriate inspector based on selected node type.
 * Shows empty state when no node is selected.
 */
export function RightInspectorPanel() {
  const selectedNode = useSelectedNode();
  const selectNode = useStore((s) => s.selectNode);

  if (!selectedNode) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400 text-sm">
        Select a node to inspect
      </div>
    );
  }

  const renderInspector = () => {
    switch (selectedNode.type) {
      case 'agent':
        return <AgentInspector nodeId={selectedNode.id} />;
      case 'task':
        return <TaskInspector nodeId={selectedNode.id} />;
      case 'tool':
        return <ToolInspector nodeId={selectedNode.id} />;
      default:
        return <div>Unknown node type</div>;
    }
  };

  return (
    <div className="flex h-full flex-col">
      <InspectorHeader
        label={selectedNode.data.label}
        type={selectedNode.type}
        onClose={() => selectNode(null)}
      />
      <div className="flex-1 overflow-y-auto p-4">
        {renderInspector()}
      </div>
    </div>
  );
}
```

---

## 10. Terminal Streaming Architecture

### 10.1 Terminal Component

```
terminal/
├── observability-terminal.tsx          // Main container: handles SSE stream from store
├── terminal-header.tsx                 // Toolbar: filter, search, pause, export, clear
├── terminal-output.tsx                 // Virtualized log list with auto-scroll
├── terminal-entry.tsx                  // Individual log line with colored tag
├── terminal-search.tsx                 // Search input with highlight
├── terminal-filter-bar.tsx             // Agent/level/event-type filter chips
└── terminal-empty-state.tsx            // "No logs yet" placeholder
```

### 10.2 Virtualized Log List

```typescript
// apps/web/src/components/terminal/terminal-output.tsx

'use client';

import { useRef, useEffect, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useStore } from '@/store';
import { TerminalEntry } from './terminal-entry';

const ESTIMATED_ROW_HEIGHT = 24;

/**
 * Virtualized terminal output.
 * Uses @tanstack/react-virtual for efficient rendering of large log streams.
 * Handles auto-scroll and pause-scroll behavior.
 */
export function TerminalOutput() {
  const parentRef = useRef<HTMLDivElement>(null);
  const scrollMode = useStore((s) => s.scrollMode);
  const useFilteredEntries = () =>
    useStore((s) => {
      const { agentId, level, eventType, searchQuery } = s.filter;
      return s.entries.filter((entry) => {
        if (agentId && entry.agentId !== agentId) return false;
        if (level && entry.level !== level) return false;
        if (eventType && entry.eventType !== eventType) return false;
        if (searchQuery && !entry.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
        return true;
      });
    });

  const filteredEntries = useFilteredEntries();

  const virtualizer = useVirtualizer({
    count: filteredEntries.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ESTIMATED_ROW_HEIGHT,
    overscan: 20,
  });

  // Auto-scroll when new entries arrive
  const lastCountRef = useRef(filteredEntries.length);
  useEffect(() => {
    if (scrollMode === 'auto-scroll' && filteredEntries.length > lastCountRef.current) {
      virtualizer.scrollToIndex(filteredEntries.length - 1, { align: 'end' });
    }
    lastCountRef.current = filteredEntries.length;
  }, [filteredEntries.length, scrollMode, virtualizer]);

  return (
    <div
      ref={parentRef}
      className="h-full overflow-auto bg-slate-950 font-mono text-xs"
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <TerminalEntry entry={filteredEntries[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 10.3 Terminal Entry

```typescript
// apps/web/src/components/terminal/terminal-entry.tsx

import { memo } from 'react';
import { cn } from '@/lib/utils';
import type { TerminalLogEntry } from '@/types/terminal';

const tagColors: Record<string, string> = {
  'PLANNING': 'text-purple-400',
  'THOUGHT': 'text-blue-400',
  'ACTION': 'text-amber-400',
  'OBSERVATION': 'text-green-400',
  'TOOL': 'text-cyan-400',
  'ERROR': 'text-red-400 bg-red-400/10',
  'WORKFLOW': 'text-slate-400',
};

interface TerminalEntryProps {
  entry: TerminalLogEntry;
}

export const TerminalEntry = memo(function TerminalEntry({ entry }: TerminalEntryProps) {
  const tag = entry.eventType.replace('AGENT_', '').replace('_', ' ');

  return (
    <div
      className={cn(
        'flex items-start gap-2 px-3 py-0.5 hover:bg-slate-800/50 transition-colors',
        entry.level === 'ERROR' && 'bg-red-950/20',
      )}
    >
      <span className="text-slate-600 shrink-0 w-16">
        {entry.timestamp.split('T')[1]?.slice(0, 8) ?? ''}
      </span>
      <span className={cn('shrink-0 font-semibold uppercase', tagColors[tag] ?? 'text-slate-500')}>
        [{tag}]
      </span>
      {entry.agentId && (
        <span className="text-slate-500 shrink-0">[{entry.agentId}]</span>
      )}
      <span className="text-slate-300 truncate">{entry.message}</span>
    </div>
  );
});
```

---

## 11. API Service Boundaries

### 11.1 Service Layer Architecture

```
services/
├── index.ts                              // Re-exports
├── api-client.ts                         // Base HTTP client with auth, retry, error handling
├── workflow-service.ts                   // Workflow CRUD + execution endpoints
├── agent-service.ts                      // Agent CRUD
├── task-service.ts                       // Task CRUD
├── execution-service.ts                  // Execution control (run, pause, resume, stop, retry)
├── approval-service.ts                   // HITL approval operations
├── template-service.ts                   // Template CRUD
├── metrics-service.ts                    // Metrics/history queries
└── types.ts                             // Request/Response types per service
```

### 11.2 Base API Client

```typescript
// apps/web/src/services/api-client.ts

/**
 * Typed API client with:
 * - JWT auth header injection
 * - Automatic retry on 5xx errors
 * - Request timeout
 * - Error normalization
 * - Request cancellation via AbortController
 */

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface RequestConfig {
  method: HttpMethod;
  path: string;
  body?: unknown;
  params?: Record<string, string>;
  signal?: AbortSignal;
  timeout?: number;
}

interface ApiError {
  status: number;
  message: string;
  code: string;
  details?: Record<string, unknown>;
}

const DEFAULT_TIMEOUT = 30_000;
const MAX_RETRIES = 3;
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? '/api';

export class ApiClient {
  private getAuthToken(): string | null {
    // Read from secure cookie or in-memory store
    return null;
  }

  async request<T>(config: RequestConfig): Promise<T> {
    const token = this.getAuthToken();
    const url = new URL(`${BASE_URL}${config.path}`, window.location.origin);

    if (config.params) {
      for (const [key, value] of Object.entries(config.params)) {
        url.searchParams.set(key, value);
      }
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout ?? DEFAULT_TIMEOUT);

    let lastError: Error | null = null;

    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      try {
        const response = await fetch(url.toString(), {
          method: config.method,
          headers,
          body: config.body ? JSON.stringify(config.body) : undefined,
          signal: config.signal ?? controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorBody = await response.json().catch(() => ({}));
          throw {
            status: response.status,
            message: errorBody.message ?? response.statusText,
            code: errorBody.code ?? 'UNKNOWN_ERROR',
            details: errorBody.details,
          } as ApiError;
        }

        return response.json() as Promise<T>;
      } catch (error) {
        lastError = error as Error;
        
        // Don't retry on 4xx errors
        if ((error as ApiError).status && (error as ApiError).status < 500) {
          throw error;
        }

        // Don't retry on abort
        if (error instanceof DOMException && error.name === 'AbortError') {
          throw { status: 0, message: 'Request timed out', code: 'TIMEOUT' } as ApiError;
        }

        // Exponential backoff
        if (attempt < MAX_RETRIES - 1) {
          await new Promise((resolve) => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
        }
      }
    }

    throw lastError ?? { status: 0, message: 'Request failed', code: 'UNKNOWN_ERROR' };
  }

  get<T>(path: string, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ method: 'GET', path, ...config });
  }

  post<T>(path: string, body?: unknown, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ method: 'POST', path, body, ...config });
  }

  put<T>(path: string, body?: unknown, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ method: 'PUT', path, body, ...config });
  }

  patch<T>(path: string, body?: unknown, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ method: 'PATCH', path, body, ...config });
  }

  delete<T>(path: string, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ method: 'DELETE', path, ...config });
  }
}

export const apiClient = new ApiClient();
```

### 11.3 Service Definitions

```typescript
// apps/web/src/services/execution-service.ts

import { apiClient } from './api-client';
import type { WorkflowStatus } from '@shared/types';

export interface RunWorkflowResponse {
  executionId: string;
  status: WorkflowStatus;
}

export interface ExecutionStatusResponse {
  executionId: string;
  workflowId: string;
  status: WorkflowStatus;
  progress: number;
  startedAt: string;
  completedAt: string | null;
  error: string | null;
}

export const executionService = {
  runWorkflow(workflowId: string): Promise<RunWorkflowResponse> {
    return apiClient.post<RunWorkflowResponse>(`/workflow/run`, { workflowId });
  },

  pauseWorkflow(executionId: string): Promise<void> {
    return apiClient.post<void>(`/workflow/pause`, { executionId });
  },

  resumeWorkflow(executionId: string): Promise<void> {
    return apiClient.post<void>(`/workflow/resume`, { executionId });
  },

  stopWorkflow(executionId: string): Promise<void> {
    return apiClient.post<void>(`/workflow/kill`, { executionId });
  },

  retryWorkflow(executionId: string): Promise<RunWorkflowResponse> {
    return apiClient.post<RunWorkflowResponse>(`/workflow/replay/${executionId}`);
  },

  getStatus(executionId: string): Promise<ExecutionStatusResponse> {
    return apiClient.get<ExecutionStatusResponse>(`/workflow/status/${executionId}`);
  },
};
```

```typescript
// apps/web/src/services/workflow-service.ts

import { apiClient } from './api-client';
import type { WorkflowNode, WorkflowEdge } from '@/types/canvas';

export interface WorkflowSummary {
  id: string;
  name: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  agentCount: number;
}

export interface WorkflowDetail {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  version: number;
  createdAt: string;
  updatedAt: string;
}

export const workflowService = {
  listWorkflows(): Promise<WorkflowSummary[]> {
    return apiClient.get<WorkflowSummary[]>('/workflows');
  },

  getWorkflow(id: string): Promise<WorkflowDetail> {
    return apiClient.get<WorkflowDetail>(`/workflows/${id}`);
  },

  createWorkflow(data: { name: string; description?: string }): Promise<WorkflowDetail> {
    return apiClient.post<WorkflowDetail>('/workflows', data);
  },

  updateWorkflow(id: string, data: Partial<WorkflowDetail>): Promise<WorkflowDetail> {
    return apiClient.put<WorkflowDetail>(`/workflows/${id}`, data);
  },

  deleteWorkflow(id: string): Promise<void> {
    return apiClient.delete<void>(`/workflows/${id}`);
  },
};
```

```typescript
// apps/web/src/services/approval-service.ts

import { apiClient } from './api-client';

export interface ApprovalRequestDTO {
  id: string;
  workflowId: string;
  taskId: string;
  agentId: string;
  draftOutput: string;
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string;
}

export interface ApproveRequest {
  edits?: string;
}

export interface RejectRequest {
  reason: string;
}

export const approvalService = {
  listPendingApprovals(): Promise<ApprovalRequestDTO[]> {
    return apiClient.get<ApprovalRequestDTO[]>('/approvals/pending');
  },

  getApprovalDetail(id: string): Promise<ApprovalRequestDTO> {
    return apiClient.get<ApprovalRequestDTO>(`/approvals/${id}`);
  },

  approve(id: string, data?: ApproveRequest): Promise<void> {
    return apiClient.post<void>(`/approvals/${id}/approve`, data);
  },

  reject(id: string, data: RejectRequest): Promise<void> {
    return apiClient.post<void>(`/approvals/${id}/reject`, data);
  },

  regenerate(id: string): Promise<void> {
    return apiClient.post<void>(`/approvals/${id}/regenerate`);
  },
};
```

```typescript
// apps/web/src/services/metrics-service.ts

import { apiClient } from './api-client';
import type { TokenMetrics, ExecutionTimelineEntry, FailureMetric } from '@/types/metrics';

export const metricsService = {
  getTokenMetrics(workflowId: string): Promise<TokenMetrics[]> {
    return apiClient.get<TokenMetrics[]>(`/metrics/${workflowId}/tokens`);
  },

  getExecutionTimeline(workflowId: string): Promise<ExecutionTimelineEntry[]> {
    return apiClient.get<ExecutionTimelineEntry[]>(`/metrics/${workflowId}/timeline`);
  },

  getFailureMetrics(workflowId: string): Promise<FailureMetric[]> {
    return apiClient.get<FailureMetric[]>(`/metrics/${workflowId}/failures`);
  },
};
```

---

## 12. Shared Component Architecture

### 12.1 Shared Components

```
shared/
├── status-dot.tsx                    // Animated colored dot for node status
├── progress-bar.tsx                  // Thin progress bar for task nodes
├── icon-button.tsx                   // Icon + tooltip button
├── empty-state.tsx                   // "Nothing here" placeholder
├── loading-spinner.tsx               // Atomic spinner
├── error-banner.tsx                  // Dismissible error banner
├── confirmation-dialog.tsx           // Confirm action modal
├── search-input.tsx                  // Debounced search input
├── filter-chips.tsx                  // Horizontal chip filter bar
├── kbd-shortcut.tsx                  // Keyboard shortcut display
├── collapsible-section.tsx           // Expandable section wrapper
└── index.ts                          // Re-exports
```

### 12.2 Pattern: Status Dot

```typescript
// apps/web/src/components/shared/status-dot.tsx

import { memo } from 'react';
import { cn } from '@/lib/utils';

type StatusSize = 'sm' | 'md' | 'lg';
type StatusColor = 'idle' | 'running' | 'success' | 'failed' | 'waiting-human';

interface StatusDotProps {
  status: StatusColor;
  size?: StatusSize;
  pulse?: boolean;
  className?: string;
}

const sizeClasses: Record<StatusSize, string> = {
  sm: 'w-2 h-2',
  md: 'w-3 h-3',
  lg: 'w-4 h-4',
};

const colorClasses: Record<StatusColor, string> = {
  idle: 'bg-slate-400',
  running: 'bg-blue-500',
  success: 'bg-green-500',
  failed: 'bg-red-500',
  'waiting-human': 'bg-orange-500',
};

const pulseClasses: Partial<Record<StatusColor, string>> = {
  running: 'animate-pulse',
};

export const StatusDot = memo(function StatusDot({
  status,
  size = 'md',
  pulse,
  className,
}: StatusDotProps) {
  return (
    <span
      className={cn(
        'rounded-full inline-block',
        sizeClasses[size],
        colorClasses[status],
        pulse && pulseClasses[status],
        className,
      )}
    />
  );
});
```

---

## 13. Complete Frontend Folder Structure

```
apps/web/src/
│
├── app/                                        # Next.js App Router
│   ├── layout.tsx                              # Root layout (providers, fonts, global styles)
│   ├── page.tsx                                # Redirect to /workflows
│   ├── error.tsx                               # Global error boundary
│   ├── loading.tsx                             # Global loading
│   ├── not-found.tsx                           # 404 page
│   │
│   ├── (dashboard)/
│   │   ├── layout.tsx                          # IDE shell layout
│   │   ├── workflows/
│   │   │   ├── page.tsx                        # Workflow list
│   │   │   ├── [workflowId]/
│   │   │   │   ├── layout.tsx                  # Workflow detail layout
│   │   │   │   ├── page.tsx                    # Canvas editor (default)
│   │   │   │   ├── execution/
│   │   │   │   │   └── page.tsx                # Execution history
│   │   │   │   └── settings/
│   │   │   │       └── page.tsx                # Workflow settings
│   │   │   └── new/
│   │   │       └── page.tsx                    # Create workflow
│   │   ├── approvals/
│   │   │   ├── page.tsx                        # Approval inbox
│   │   │   └── [approvalId]/
│   │   │       └── page.tsx                    # Approval detail
│   │   ├── templates/
│   │   │   ├── page.tsx                        # Template library
│   │   │   └── [templateId]/
│   │   │       └── page.tsx                    # Template detail
│   │   └── settings/
│   │       └── page.tsx                        # User settings
│   │
│   └── auth/
│       ├── login/
│       │   └── page.tsx                        # Login
│       └── callback/
│           └── page.tsx                        # OAuth callback
│
├── components/
│   ├── canvas/                                 # React Flow canvas
│   │   ├── workflow-canvas.tsx                 # Main React Flow wrapper
│   │   ├── nodes/
│   │   │   ├── agent-node.tsx                  # Agent visual node
│   │   │   ├── task-node.tsx                   # Task visual node
│   │   │   └── tool-node.tsx                   # Tool visual node
│   │   ├── edges/
│   │   │   └── animated-edge.tsx               # Animated workflow edge
│   │   ├── base/
│   │   │   ├── node-wrapper.tsx                # Shared node frame
│   │   │   └── node-status-badge.tsx           # Status indicator
│   │   ├── shared/
│   │   │   ├── progress-bar.tsx                # Task progress bar
│   │   │   └── status-dot.tsx                  # Status dot
│   │   └── palette/
│   │       ├── agent-palette.tsx               # Draggable agent templates
│   │       ├── task-palette.tsx                # Draggable task templates
│   │       └── tool-palette.tsx                # Draggable tool templates
│   │
│   ├── inspector/                              # Right panel inspectors
│   │   ├── right-inspector-panel.tsx           # Dynamic inspector container
│   │   ├── inspector-header.tsx                # Inspector title bar
│   │   ├── inspector-tabs.tsx                  # Tab navigation
│   │   ├── agent/
│   │   │   ├── agent-inspector.tsx             # Agent form container
│   │   │   ├── agent-persona-form.tsx          # Role/goal/backstory
│   │   │   ├── agent-memory-matrix.tsx         # Memory toggles
│   │   │   ├── agent-llm-routing.tsx           # LLM config
│   │   │   ├── agent-tool-assignment.tsx       # Tool selection
│   │   │   └── ai-enhancer-button.tsx          # AI expand button
│   │   ├── task/
│   │   │   ├── task-inspector.tsx              # Task form container
│   │   │   ├── task-config-form.tsx            # Task fields
│   │   │   └── task-approval-toggle.tsx        # HITL toggle
│   │   ├── tool/
│   │   │   ├── tool-inspector.tsx              # Tool form container
│   │   │   └── tool-permissions.tsx            # Permission checkboxes
│   │   └── shared/
│   │       ├── form-field.tsx                  # Label + input wrapper
│   │       └── markdown-editor.tsx             # Markdown textarea
│   │
│   ├── terminal/                               # Observability terminal
│   │   ├── observability-terminal.tsx          # Terminal container
│   │   ├── terminal-header.tsx                 # Toolbar
│   │   ├── terminal-output.tsx                 # Virtualized log list
│   │   ├── terminal-entry.tsx                  # Log line
│   │   ├── terminal-search.tsx                 # Search input
│   │   ├── terminal-filter-bar.tsx             # Filter chips
│   │   └── terminal-empty-state.tsx            # Empty state
│   │
│   ├── metrics/                                # Metrics dashboard
│   │   ├── metrics-dashboard.tsx               # Dashboard container
│   │   ├── token-cost-chart.tsx                # Token usage chart
│   │   ├── gantt-timeline.tsx                  # Execution Gantt
│   │   ├── failure-heatmap.tsx                 # Failure visualization
│   │   └── metrics-empty-state.tsx             # Empty state
│   │
│   ├── layout/                                 # IDE layout shell
│   │   ├── ide-shell.tsx                       # Root resizable panel group
│   │   ├── left-sidebar.tsx                    # Left panel container
│   │   ├── sidebar-tabs.tsx                    # Tab navigation
│   │   ├── main-area.tsx                       # Center panel container
│   │   ├── execution-toolbar.tsx               # Run/pause/resume buttons
│   │   ├── yaml-editor.tsx                     # Monaco editor wrapper
│   │   └── bottom-panel.tsx                    # Terminal/metrics tabs
│   │
│   ├── hitl/                                   # Human-in-the-loop
│   │   ├── hitl-dialog.tsx                     # Approval modal
│   │   ├── approval-card.tsx                   # Approval summary card
│   │   ├── approval-detail-view.tsx            # Side-by-side compare
│   │   └── approval-actions.tsx                # Approve/reject/regenerate
│   │
│   └── shared/                                 # Reusable primitives
│       ├── status-dot.tsx                      # Animated status dot
│       ├── progress-bar.tsx                    # Progress bar
│       ├── icon-button.tsx                     # Icon button with tooltip
│       ├── empty-state.tsx                     # Empty placeholder
│       ├── loading-spinner.tsx                 # Loading spinner
│       ├── error-banner.tsx                    # Error banner
│       ├── confirmation-dialog.tsx             # Confirm modal
│       ├── search-input.tsx                    # Search input
│       ├── filter-chips.tsx                    # Filter chips
│       ├── kbd-shortcut.tsx                    # Keyboard shortcut
│       ├── collapsible-section.tsx             # Collapsible section
│       └── index.ts                            # Re-exports
│
├── store/                                      # Zustand state management
│   ├── index.ts                                # Combined store
│   ├── slices/
│   │   ├── canvas-slice.ts                     # Workflow graph state
│   │   ├── execution-slice.ts                  # Execution runtime state
│   │   ├── terminal-slice.ts                   # Observability log state
│   │   ├── hitl-slice.ts                       # HITL approval state
│   │   ├── ui-slice.ts                         # UI/layout state
│   │   ├── metrics-slice.ts                    # Metrics data
│   │   └── sync-slice.ts                       # Sync version tracking
│   ├── selectors/
│   │   ├── canvas-selectors.ts                 # Derived canvas state
│   │   ├── execution-selectors.ts              # Derived execution state
│   │   ├── terminal-selectors.ts               # Filtered log views
│   │   ├── hitl-selectors.ts                   # Approval queue counts
│   │   └── ui-selectors.ts                     # Panel visibility
│   └── middleware/
│       ├── logger.ts                           # Dev action logging
│       └── sync-middleware.ts                  # Sync trigger on canvas changes
│
├── hooks/                                      # Custom React hooks
│   ├── use-canvas-handlers.ts                  # React Flow event handlers
│   ├── use-canvas-sync.ts                      # Canvas → YAML sync hook
│   ├── use-workflow-stream.ts                  # SSE event subscription
│   ├── use-agent-status.ts                     # Agent execution status
│   ├── use-node-drag.ts                        # Drag-and-drop palette → canvas
│   ├── use-workflow-actions.ts                 # Run/pause/resume actions
│   ├── use-terminal-export.ts                  # Log export logic
│   ├── use-debounce.ts                         # Generic debounce
│   └── use-keyboard-shortcuts.ts               # Global keyboard bindings
│
├── services/                                   # API client layer
│   ├── api-client.ts                           # Base HTTP client
│   ├── workflow-service.ts                     # Workflow CRUD
│   ├── agent-service.ts                        # Agent CRUD
│   ├── task-service.ts                         # Task CRUD
│   ├── execution-service.ts                    # Execution control
│   ├── approval-service.ts                     # HITL approval ops
│   ├── template-service.ts                     # Template CRUD
│   ├── metrics-service.ts                      # Metrics/history
│   └── types.ts                                # Service request/response types
│
├── lib/                                        # Core utilities
│   ├── sync/
│   │   ├── sync-engine.ts                      # YAML↔Store bidirectional sync
│   │   ├── yaml-parser.ts                      # YAML serialize/deserialize
│   │   └── workflow-validator.ts               # Zod-based workflow validation
│   ├── stream/
│   │   └── sse-client.ts                       # SSE connection manager
│   ├── utils/
│   │   ├── cn.ts                               # Tailwind merge utility
│   │   ├── id.ts                               # ID generation
│   │   └── format.ts                           # Date/number formatters
│   └── validation/
│       └── index.ts                            # Shared Zod schema wrappers
│
├── types/                                      # Frontend-specific types
│   ├── canvas.ts                               # React Flow node/edge data types
│   ├── ui.ts                                   # Layout, panels, tabs
│   ├── terminal.ts                             # Log entry types
│   ├── metrics.ts                              # Chart data types
│   └── sync.ts                                 # Sync engine types
│
└── providers/                                  # React context providers
    ├── store-provider.tsx                      # Zustand store initialization
    ├── auth-provider.tsx                       # Auth state and redirects
    └── theme-provider.tsx                      # Theme configuration
```

---

## 14. Hook Strategy

### 14.1 Hook Responsibilities

| Hook | Reads | Writes | Side Effects |
|------|-------|--------|-------------|
| [`useCanvasHandlers`](hooks/use-canvas-handlers.ts) | Store nodes/edges | Store nodes/edges | None (pure store updates) |
| [`useCanvasSync`](hooks/use-canvas-sync.ts) | Store nodes/edges | None | Triggers SyncEngine.onUIChange |
| [`useWorkflowStream`](hooks/use-workflow-stream.ts) | Store handlers | Store entries | SSE connect/disconnect |
| [`useAgentStatus`](hooks/use-agent-status.ts) | Store agentStates | None | None |
| [`useNodeDrag`](hooks/use-node-drag.ts) | None | Store addNode | DnD event binding |
| [`useWorkflowActions`](hooks/use-workflow-actions.ts) | Store executionId | Store workflowStatus | API calls via services |
| [`useTerminalExport`](hooks/use-terminal-export.ts) | Store entries | None | File download |
| [`useKeyboardShortcuts`](hooks/use-keyboard-shortcuts.ts) | None | Store actions | Keydown listener |

### 14.2 Hook: useCanvasHandlers

```typescript
// apps/web/src/hooks/use-canvas-handlers.ts

import { useCallback } from 'react';
import {
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type NodeDragHandler,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from '@xyflow/react';
import { useStore } from '@/store';

/**
 * Hook that provides React Flow event handlers.
 * All handlers are wrapped in useCallback for stable references.
 * Updates go directly to the Zustand canvas slice.
 */
export function useCanvasHandlers() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const setNodes = useStore((s) => (nodes: typeof s.nodes) => s.replaceGraph(nodes, s.edges));
  const setEdges = useStore((s) => (edges: typeof s.edges) => s.replaceGraph(s.nodes, edges));
  const selectNode = useStore((s) => s.selectNode);
  const selectEdge = useStore((s) => s.selectEdge);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      setNodes(applyNodeChanges(changes, nodes));
    },
    [nodes, setNodes],
  );

  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      setEdges(applyEdgeChanges(changes, edges));
    },
    [edges, setEdges],
  );

  const onConnect: OnConnect = useCallback(
    (connection) => {
      setEdges(addEdge({ ...connection, animated: true }, edges));
    },
    [edges, setEdges],
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: { id: string }) => {
      selectNode(node.id);
    },
    [selectNode],
  );

  const onNodeDragStart: NodeDragHandler = useCallback(() => {
    // Future: could mark drag state
  }, []);

  const onNodeDragStop: NodeDragHandler = useCallback(
    (_, node) => {
      // Position is already updated via onNodesChange
    },
    [],
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
    selectEdge(null);
  }, [selectNode, selectEdge]);

  const onMoveEnd = useCallback(
    (_: unknown, viewport: { x: number; y: number; zoom: number }) => {
      useStore.getState().setViewport(viewport);
    },
    [],
  );

  return {
    onNodesChange,
    onEdgesChange,
    onConnect,
    onNodeClick,
    onNodeDragStart,
    onNodeDragStop,
    onPaneClick,
    onMoveEnd,
  };
}
```

---

## 15. Performance Architecture

### 15.1 Render Optimization Strategy

```
┌────────────────────────────────────────────────────────────────────────┐
│                      RENDER PERFORMANCE STRATEGY                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Problem: React Flow canvas with hundreds of nodes + SSE events          │
│  Solution: Multi-layer optimization                                     │
│                                                                         │
│  Layer 1: React Flow Built-in                                          │
│  ├── onlyRenderVisibleElements = true                                  │
│  ├── nodeTypes/edgeTypes defined outside component (stable refs)       │
│  └── nodeExtent restricts node movement boundaries                     │
│                                                                         │
│  Layer 2: Zustand Selectors                                            │
│  ├── All component selectors use `shallow` comparison                  │
│  ├── Nodes re-render only when their data changes                      │
│  ├── Terminal virtualizes rendering (only visible rows)                │
│  └── Metrics charts re-render only on data append                      │
│                                                                         │
│  Layer 3: React Optimization                                           │
│  ├── All node components wrapped in React.memo                         │
│  ├── Event handlers wrapped in useCallback                             │
│  ├── Expensive computations wrapped in useMemo                         │
│  └── No inline objects in render (const defaultEdgeOptions)            │
│                                                                         │
│  Layer 4: Terminal Memory Management                                  │
│  ├── Max 10,000 log entries in store (ring buffer)                    │
│  ├── Virtual scrolling via @tanstack/react-virtual                     │
│  └── Filter is applied in selector (memoized)                         │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 15.2 Terminal Ring Buffer

```typescript
// apps/web/src/store/slices/terminal-slice.ts (excerpt)

interface TerminalSlice {
  entries: TerminalLogEntry[];
  maxEntries: number; // 10,000
  // ...
}

// In the appendEntry implementation:
appendEntry: (entry) =>
  set((state) => ({
    entries: state.entries.length >= state.maxEntries
      ? [...state.entries.slice(1), entry]  // Ring buffer: remove oldest
      : [...state.entries, entry],
  })),
```

### 15.3 SSE Event Throttling

The terminal store limits the rate of state updates during high-throughput event bursts:

```typescript
// In useWorkflowStream hook (excerpt)

// Batch append for high-frequency events
const batchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
const batchRef = useRef<TerminalLogEntry[]>([]);

const flushBatch = useCallback(() => {
  if (batchRef.current.length > 0) {
    store.appendEntries(batchRef.current);
    batchRef.current = [];
  }
}, []);

// For non-critical events, batch every 50ms
if (event.type === 'AGENT_THOUGHT' || event.type === 'AGENT_OBSERVATION') {
  batchRef.current.push(entry);
  if (!batchTimerRef.current) {
    batchTimerRef.current = setTimeout(() => {
      flushBatch();
      batchTimerRef.current = null;
    }, 50);
  }
} else {
  // Critical events flush immediately
  flushBatch();
  store.appendEntry(entry);
}
```

---

## 16. Observability Architecture

### 16.1 Frontend Observability Layers

```
┌────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND OBSERVABILITY                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Layer 1: User-Facing (Terminal + Metrics)                             │
│  ├── ObservabilityTerminal — real-time log stream                      │
│  ├── MetricsDashboard — token costs, timing, failures                  │
│  └── Node status glows on canvas                                       │
│                                                                         │
│  Layer 2: Developer (Console + Debug)                                  │
│  ├── Zustand middleware logger (dev only)                              │
│  ├── SSE connection status log                                         │
│  ├── Sync engine version tracking                                      │
│  └── React DevTools component insights                                 │
│                                                                         │
│  Layer 3: Error Boundaries                                              │
│  ├── Global error boundary (app/error.tsx)                             │
│  ├── Canvas error boundary (isolated canvas crashes)                   │
│  ├── Terminal error boundary (non-blocking)                            │
│  └── Inspector error boundary (isolated form crashes)                  │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 16.2 Error Boundary Architecture

```typescript
// apps/web/src/components/shared/error-boundary.tsx

'use client';

import { Component, type ErrorInfo, type ReactNode } from 'react';
import { ErrorBanner } from './error-banner';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  name: string; // Component name for logging
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Generic error boundary that catches component errors
 * and displays a fallback UI instead of crashing the app.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error(`[ErrorBoundary:${this.props.name}]`, error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <ErrorBanner
          title={`${this.props.name} encountered an error`}
          message={this.state.error?.message ?? 'Unknown error'}
          onRetry={() => this.setState({ hasError: false, error: null })}
        />
      );
    }
    return this.props.children;
  }
}
```

### 16.3 Error Boundary Placement

```
app/layout.tsx
  └── ErrorBoundary (name="Root", global fallback → error.tsx)

app/(dashboard)/layout.tsx
  └── ErrorBoundary (name="Dashboard")

components/canvas/workflow-canvas.tsx
  └── ErrorBoundary (name="Canvas", fallback → "Canvas crashed, reload?")
        └── <ReactFlow /> (isolated)

components/terminal/observability-terminal.tsx
  └── ErrorBoundary (name="Terminal", fallback → "Terminal unavailable")
        └── <TerminalOutput /> (non-blocking)

components/inspector/right-inspector-panel.tsx
  └── ErrorBoundary (name="Inspector", fallback → "Inspector unavailable")
        └── Dynamic inspector content (isolated)
```

---

## Appendix A: Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State management | Zustand with slices | Single store, no provider nesting, slices keep concerns separated, `subscribeWithSelector` for cross-slice sync |
| Graph rendering | React Flow | Built for DAG workflows, virtualization, custom nodes, edge animations |
| SSE client | Custom `SSEClientManager` | Full control over reconnection, event routing, multi-workflow connections |
| Log virtualization | `@tanstack/react-virtual` | Efficient rendering of thousands of log lines, built-in scroll-to-index |
| YAML sync | Custom `SyncEngine` | Three-phase model prevents sync loops, version tracking prevents conflicts |
| Inspector | Dynamic dispatch by node type | No conditional rendering chains, each inspector is independently testable |
| Layout | `react-resizable-panels` | IDE-style resizable panels, accessible, no layout shift |
| Types | Shared `@shared/types` package | Single source of truth, no duplication between frontend/backend |
| API layer | Pure service classes | No state coupling, retry logic centralized, typed response interfaces |

## Appendix B: Data Flow Matrix

```
┌─────────────────────┬──────────────────┬───────────────────┬───────────────────┐
│ User Action         │ Component        │ Store Mutation    │ API / SSE         │
├─────────────────────┼──────────────────┼───────────────────┼───────────────────┤
│ Drag node to canvas │ AgentPalette     │ CanvasSlice.addNode│ —                 │
│ Select node         │ WorkflowCanvas   │ CanvasSlice.selectNode│ —              │
│ Edit node config    │ AgentInspector   │ CanvasSlice.updateNode│ PUT /agents/:id  │
│ Click Run           │ ExecutionToolbar │ ExecutionSlice.run │ POST /workflow/run │
│ SSE event received  │ useWorkflowStream│ ExecutionSlice._handle* │ SSE stream   │
│ Append log entry    │ useWorkflowStream│ TerminalSlice.appendEntry│ —            │
│ Approve HITL        │ ApprovalActions  │ HITLSlice.approve │ POST /approvals/:id │
│ Edit YAML           │ YAMLEditor       │ CanvasSlice.replaceGraph│ —             │
│ View token metrics  │ MetricsDashboard │ MetricsSlice.setMetrics│ GET /metrics  │
│ Filter terminal     │ TerminalFilterBar│ TerminalSlice.setFilter │ —              │
└─────────────────────┴──────────────────┴───────────────────┴───────────────────┘
```

---

*End of Frontend Architecture Specification.*
