import { useEffect, useMemo, useState } from 'react'
import type { ExecutionEvent } from '../services/chat'

type NodeStatus = 'running' | 'completed' | 'failed' | 'issued'

type ExecutionNode = {
  id: string
  title: string
  subtitle?: string
  status: NodeStatus
  durationMs?: number | null
  details?: unknown
  children: ExecutionNode[]
}

type AgentActivityProps = {
  events: ExecutionEvent[]
  isProcessing: boolean
}

function buildExecutionTree(
  events: ExecutionEvent[],
  isProcessing: boolean,
): ExecutionNode | null {
  let root: ExecutionNode | null = null
  let graphNode: ExecutionNode | null = null

  const llmNodes = new Map<string, ExecutionNode>()
  const toolNodes = new Map<string, ExecutionNode>()
  const pendingToolCalls = new Map<string, ExecutionNode[]>()

  function ensureWorkflow(): ExecutionNode | null {
    if (!root) return null

    if (!graphNode) {
      graphNode = {
        id: 'langgraph-workflow',
        title: 'LangGraph workflow',
        subtitle: 'Processing graph execution',
        status: 'running',
        children: [],
      }
      root.children.push(graphNode)
    }

    return graphNode
  }

  for (const event of events) {
    switch (event.type) {
      case 'request_start': {
        root = {
          id: `request-${event.payload.conversation_id}`,
          title: 'User request',
          subtitle: event.payload.message,
          status: 'running',
          details: { conversation_id: event.payload.conversation_id },
          children: [],
        }
        graphNode = null
        llmNodes.clear()
        toolNodes.clear()
        pendingToolCalls.clear()
        ensureWorkflow()
        break
      }

      case 'graph_start': {
        const workflow = ensureWorkflow()
        if (workflow) {
          workflow.id = event.payload.run_id
          workflow.subtitle = 'Graph execution started'
          workflow.details = { graph_run_id: event.payload.run_id }
        }
        break
      }

      case 'llm_start': {
        const workflow = ensureWorkflow()
        const node: ExecutionNode = {
          id: event.payload.run_id,
          title: `LLM · ${event.payload.node}`,
          subtitle: `Model: ${event.payload.model}`,
          status: 'running',
          details: event.payload,
          children: [],
        }
        workflow?.children.push(node)
        llmNodes.set(event.payload.run_id, node)
        break
      }

      case 'llm_end': {
        const node = llmNodes.get(event.payload.run_id)
        if (node) {
          node.status = 'completed'
          node.durationMs = event.payload.duration_ms
          node.subtitle =
            `Decision: ${event.payload.decision} · ` +
            `${event.payload.tool_call_count} tool call(s)`
          node.details = event.payload
        }
        break
      }

      case 'tool_call': {
        const workflow = ensureWorkflow()
        const parent = llmNodes.get(event.payload.llm_run_id) ?? workflow
        const node: ExecutionNode = {
          id: event.payload.tool_call_id || `${event.payload.llm_run_id}-${event.payload.tool}`,
          title: `Tool call · ${event.payload.tool}`,
          subtitle: 'Selected by the LLM',
          status: 'issued',
          details: {
            tool: event.payload.tool,
            arguments: event.payload.arguments,
            tool_call_id: event.payload.tool_call_id,
          },
          children: [],
        }
        parent?.children.push(node)
        const queue = pendingToolCalls.get(event.payload.tool) ?? []
        pendingToolCalls.set(event.payload.tool, [...queue, node])
        break
      }

      case 'tool_start': {
        const workflow = ensureWorkflow()
        const queue = pendingToolCalls.get(event.payload.tool) ?? []
        const parent = queue.shift()

        if (queue.length > 0) pendingToolCalls.set(event.payload.tool, queue)
        else pendingToolCalls.delete(event.payload.tool)

        if (parent) {
          parent.status = 'completed'
          parent.subtitle = 'Tool call dispatched'
        }

        const executionNode: ExecutionNode = {
          id: event.payload.run_id,
          title: `Tool execution · ${event.payload.tool}`,
          subtitle: 'Executing tool',
          status: 'running',
          details: {
            input: event.payload.input,
            parent_ids: event.payload.parent_ids,
          },
          children: [],
        }
        ;(parent ?? workflow)?.children.push(executionNode)
        toolNodes.set(event.payload.run_id, executionNode)
        break
      }

      case 'tool_end': {
        const node = toolNodes.get(event.payload.run_id)
        if (node) {
          node.status = event.payload.status
          node.durationMs = event.payload.duration_ms
          node.subtitle = event.payload.summary
          node.children.push({
            id: `${event.payload.run_id}-result`,
            title: 'Tool response',
            subtitle: event.payload.summary,
            status: event.payload.status,
            details: event.payload.result,
            children: [],
          })
        }
        break
      }

      case 'final': {
        const workflow = ensureWorkflow()
        if (workflow) {
          workflow.status = 'completed'
          workflow.subtitle = 'Graph execution completed'
          workflow.children.push({
            id: `final-${event.payload.graph_run_id ?? 'response'}`,
            title: 'Final response',
            subtitle: `${event.payload.products?.length ?? 0} product(s) returned`,
            status: 'completed',
            details: {
              answer: event.payload.answer,
              products: event.payload.products,
              graph_run_id: event.payload.graph_run_id,
            },
            children: [],
          })
        }
        if (root) root.status = 'completed'
        break
      }

      default:
        break
    }
  }

  if (root && isProcessing) {
    root.status = 'running'
  } else if (root && !events.some((event) => event.type === 'final')) {
    root.status = 'failed'

    // TypeScript cannot track assignments made to graphNode inside
    // ensureWorkflow(). Find the workflow node through the root instead.
    const workflowNode = root.children.find(
      (node) => node.title === 'LangGraph workflow',
    )
    if (workflowNode) workflowNode.status = 'failed'
  }

  return root
}

function formatDuration(durationMs?: number | null) {
  if (durationMs === undefined || durationMs === null) return null
  return durationMs >= 1000
    ? `${(durationMs / 1000).toFixed(2)} s`
    : `${Math.round(durationMs)} ms`
}

function StatusBadge({ status }: { status: NodeStatus }) {
  const styles: Record<NodeStatus, string> = {
    running: 'border-sky-200 bg-sky-50 text-sky-700',
    issued: 'border-violet-200 bg-violet-50 text-violet-700',
    completed: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    failed: 'border-rose-200 bg-rose-50 text-rose-700',
  }
  const labels: Record<NodeStatus, string> = {
    running: 'Running',
    issued: 'Dispatched',
    completed: 'Completed',
    failed: 'Failed',
  }

  return (
    <span className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}

function ExecutionTreeNode({ node }: { node: ExecutionNode }) {
  const [expanded, setExpanded] = useState(false)
  const hasDetails = node.details !== undefined && node.details !== null
  const hasChildren = node.children.length > 0
  const canExpand = hasDetails || hasChildren
  const duration = formatDuration(node.durationMs)

  return (
    <div className="min-w-0">
      <div className="min-w-0 rounded-xl border border-slate-200 bg-white p-3 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
          <button
            type="button"
            disabled={!canExpand}
            aria-expanded={canExpand ? expanded : undefined}
            onClick={() => setExpanded((value) => !value)}
            className="flex min-w-0 flex-1 items-center gap-2 text-left disabled:cursor-default"
          >
            <span className="w-3 shrink-0 text-[10px] text-slate-400">
              {canExpand ? (expanded ? '▼' : '▶') : '•'}
            </span>
            <span className="min-w-0 break-words text-sm font-semibold text-slate-800">
              {node.title}
            </span>
          </button>

          <div className="flex shrink-0 items-center gap-2">
            {duration && <span className="text-xs tabular-nums text-slate-500">{duration}</span>}
            <StatusBadge status={node.status} />
          </div>
        </div>

        {node.subtitle && (
          <p className="mt-1 break-words pl-5 text-xs leading-5 text-slate-500">
            {node.subtitle}
          </p>
        )}

        {expanded && hasDetails && (
          <details className="mt-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
            <summary className="cursor-pointer text-xs font-semibold text-slate-600">
              Inspect execution details
            </summary>
            <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words text-[11px] leading-5 text-slate-600">
              {typeof node.details === 'string'
                ? node.details
                : JSON.stringify(node.details, null, 2)}
            </pre>
          </details>
        )}
      </div>

      {expanded && hasChildren && (
        <div className="ml-3 mt-2 space-y-2 border-l-2 border-slate-200 pl-3 sm:ml-5 sm:pl-4">
          {node.children.map((child) => (
            <ExecutionTreeNode key={child.id} node={child} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function AgentActivity({ events, isProcessing }: AgentActivityProps) {
  const tree = useMemo(
    () => buildExecutionTree(events, isProcessing),
    [events, isProcessing],
  )
  const [expanded, setExpanded] = useState(isProcessing)

  useEffect(() => {
    setExpanded(isProcessing)
  }, [isProcessing])

  if (!tree && !isProcessing) return null

  const status = tree?.status ?? (isProcessing ? 'running' : 'failed')
  const eventCount = events.length

  return (
    <section className="my-2 w-full min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 shadow-sm">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full min-w-0 items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-white/70"
      >
        <span className="flex min-w-0 items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-100 text-violet-700">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="M7 4v5m0 0a3 3 0 1 0 0 6m0-6a3 3 0 1 1 0 6m10-11v5m0 0a3 3 0 1 0 0 6m0-6a3 3 0 1 1 0 6M7 15v5m10-5v5" strokeLinecap="round" />
            </svg>
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-slate-800">Agent execution</span>
            <span className="block text-xs text-slate-500">
              {isProcessing ? 'Live workflow activity' : `${eventCount} execution events · View details`}
            </span>
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <StatusBadge status={status} />
          <span className="text-xs text-slate-400">{expanded ? '▼' : '▶'}</span>
        </span>
      </button>

      {expanded && (
        <div className="border-t border-slate-200 p-3 sm:p-4">
          {tree ? (
            <ExecutionTreeNode node={tree} />
          ) : (
            <p className="text-sm text-slate-500">Initializing agent workflow…</p>
          )}
        </div>
      )}
    </section>
  )
}
