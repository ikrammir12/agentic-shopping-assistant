const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ''
).replace(/\/$/, '')

export type ChatProduct = {
  id: number
  name: string
  category: string
  description: string
  price: number
  is_organic: number
  average_rating: number | null
  review_count: number
}

export type ChatResponse = {
  conversation_id: string
  graph_run_id?: string
  answer: string
  products: ChatProduct[]
}

export type ToolStartEvent = {
  run_id: string
  parent_ids: string[]
  tool: string
  input: Record<string, unknown>
  status: 'running'
}

export type ToolEndEvent = {
  run_id: string
  tool: string
  status: 'completed' | 'failed'
  duration_ms: number | null
  summary: string
  result?: unknown
}

export type ExecutionEvent =
  | {
      type: 'request_start'
      payload: {
        conversation_id: string
        message: string
      }
    }
  | {
      type: 'graph_start'
      payload: {
        run_id: string
        node: string
      }
    }
  | {
      type: 'llm_start'
      payload: {
        run_id: string
        parent_ids: string[]
        node: string
        model: string
        status: string
      }
    }
  | {
      type: 'llm_end'
      payload: {
        run_id: string
        node: string
        model: string
        duration_ms: number | null
        decision: string
        tool_call_count: number
        status: string
      }
    }
  | {
      type: 'tool_call'
      payload: {
        tool_call_id?: string
        tool: string
        arguments: Record<string, unknown>
        llm_run_id: string
      }
    }
  | {
      type: 'tool_start'
      payload: ToolStartEvent
    }
  | {
      type: 'tool_end'
      payload: ToolEndEvent
    }
  | {
      type: 'final'
      payload: ChatResponse
    }

type StreamCallbacks = {
  onEvent?: (event: ExecutionEvent) => void | Promise<void>

  // Keep these for compatibility with the existing ChatPage.
  onToolStart?: (event: ToolStartEvent) => void | Promise<void>
  onToolEnd?: (event: ToolEndEvent) => void | Promise<void>
}

export async function sendChatMessageStream(
  message: string,
  conversationId: string,
  callbacks: StreamCallbacks = {}
): Promise<ChatResponse> {
  const token = localStorage.getItem('access_token')

  if (!token) {
    throw new Error('Please log in to continue.')
  }

  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
    }),
  })

  if (!response.ok) {
    const errorText = await response.text()

    let detail = 'Unable to get a response from Blink AI.'

    try {
      const errorData = JSON.parse(errorText)

      if (typeof errorData?.detail === 'string') {
        detail = errorData.detail
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(detail)
  }

  if (!response.body) {
    throw new Error('Streaming response is not available.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  let buffer = ''
  let finalResponse: ChatResponse | null = null

  // Send all events to the React component.
  async function emitEvent(event: ExecutionEvent) {
    console.log('[BLINK EXECUTION EVENT]', event.type, event.payload)
    await callbacks.onEvent?.(event)
  }

  // Process one Server-Sent Event.
  async function processEvent(frame: string): Promise<void> {
    let eventName = ''
    const dataLines: string[] = []

    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart())
      }
    }

    if (!eventName || dataLines.length === 0) {
      return
    }

    const payload = JSON.parse(dataLines.join('\n'))

    switch (eventName) {
      case 'request_start':
        await emitEvent({ type: 'request_start', payload })
        break

      case 'graph_start':
        await emitEvent({ type: 'graph_start', payload })
        break

      case 'llm_start':
        await emitEvent({ type: 'llm_start', payload })
        break

      case 'llm_end':
        await emitEvent({ type: 'llm_end', payload })
        break

      case 'tool_call':
        await emitEvent({ type: 'tool_call', payload })
        break

      case 'tool_start': {
        const toolEvent = payload as ToolStartEvent

        await emitEvent({ type: 'tool_start', payload: toolEvent })
        await callbacks.onToolStart?.(toolEvent)
        break
      }

      case 'tool_end': {
        const toolEvent = payload as ToolEndEvent

        await emitEvent({ type: 'tool_end', payload: toolEvent })
        await callbacks.onToolEnd?.(toolEvent)
        break
      }

      case 'final': {
        const finalEvent = payload as ChatResponse

        finalResponse = finalEvent
        await emitEvent({ type: 'final', payload: finalEvent })
        break
      }

      case 'error':
        throw new Error(
          payload.message || 'Blink AI could not complete your request.'
        )

      default:
        console.warn('[BLINK UNKNOWN EVENT]', eventName)
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()

      const decodedChunk = decoder.decode(value, {
        stream: !done,
      })

      if (decodedChunk) {
        buffer += decodedChunk
      }

      const frames = buffer.split(/\r?\n\r?\n/)
      buffer = frames.pop() ?? ''

      // Process each event in order.
      for (const frame of frames) {
        await processEvent(frame)
      }

      if (done) {
        if (buffer.trim()) {
          await processEvent(buffer)
        }
        break
      }
    }
  } finally {
    reader.releaseLock()
  }

  if (!finalResponse) {
    throw new Error('Blink AI ended without returning a final response.')
  }

  return finalResponse
}
