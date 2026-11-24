import { NavLink } from 'react-router'
import { useEffect, useState, type FormEvent, type ReactNode } from 'react'

import LogoutButton from '../components/LogoutButton'
import AgentActivity from '../components/AgentActivity'
import ProductCard from '../components/ProductCard'
import ProductComparison, {
  type ProductComparisonData,
} from '../components/ProductComparison'

import {
  sendChatMessageStream,
  type ExecutionEvent,
  type ChatProduct,
} from '../services/chat'

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  products?: ChatProduct[]
  comparison?: ProductComparisonData
  executionEvents?: ExecutionEvent[]
}

function parseComparisonResult(value: unknown): ProductComparisonData | null {
  let result = value

  for (let attempt = 0; attempt < 3; attempt++) {
    if (typeof result !== 'string') break
    try {
      result = JSON.parse(result)
    } catch {
      return null
    }
  }

  if (typeof result !== 'object' || result === null || Array.isArray(result)) return null
  const data = result as Record<string, unknown>

  if (!('product_1' in data) || !('product_2' in data)) {
    if (data.result !== undefined) return parseComparisonResult(data.result)
    if (data.output !== undefined) return parseComparisonResult(data.output)
    return null
  }

  const first = data.product_1
  const second = data.product_2
  if (
    typeof first !== 'object' || first === null || Array.isArray(first) ||
    typeof second !== 'object' || second === null || Array.isArray(second)
  ) return null

  const product1 = first as Record<string, unknown>
  const product2 = second as Record<string, unknown>

  function isValidProduct(product: Record<string, unknown>) {
    return (
      typeof product.name === 'string' &&
      typeof product.price === 'number' &&
      (typeof product.avg_rating === 'number' || product.avg_rating === null) &&
      typeof product.review_count === 'number'
    )
  }

  if (!isValidProduct(product1) || !isValidProduct(product2) || typeof data.reason !== 'string') {
    return null
  }

  return {
    product_1: {
      id: typeof product1.id === 'number' ? product1.id : undefined,
      name: product1.name as string,
      price: product1.price as number,
      avg_rating: product1.avg_rating as number | null,
      review_count: product1.review_count as number,
    },
    product_2: {
      id: typeof product2.id === 'number' ? product2.id : undefined,
      name: product2.name as string,
      price: product2.price as number,
      avg_rating: product2.avg_rating as number | null,
      review_count: product2.review_count as number,
    },
    highest_rated: typeof data.highest_rated === 'string' ? data.highest_rated : null,
    lowest_price: typeof data.lowest_price === 'string' ? data.lowest_price : null,
    recommended_product:
      typeof data.recommended_product === 'string' ? data.recommended_product : null,
    reason: data.reason,
  }
}

/** Remove a Markdown product table when the same products are rendered as cards. */
function removeRedundantProductTable(content: string, hasStructuredResults: boolean) {
  if (!hasStructuredResults) return content

  const lines = content.split('\n')
  const output: string[] = []
  let index = 0

  while (index < lines.length) {
    const current = lines[index]
    const next = lines[index + 1] ?? ''
    const looksLikeTableHeader = current.includes('|') && /^\s*\|?\s*:?-{2,}/.test(next)

    if (looksLikeTableHeader) {
      index += 2
      while (index < lines.length && lines[index].includes('|') && lines[index].trim() !== '') {
        index += 1
      }
      continue
    }

    output.push(current)
    index += 1
  }

  return output.join('\n').replace(/\n{3,}/g, '\n\n').trim()
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const tokenPattern = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g
  const parts = text.split(tokenPattern)

  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index} className="font-semibold">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={index} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[0.9em]">{part.slice(1, -1)}</code>
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return <em key={index}>{part.slice(1, -1)}</em>
    }
    return part
  })
}

function AssistantContent({ content, hasStructuredResults }: {
  content: string
  hasStructuredResults: boolean
}) {
  const cleaned = removeRedundantProductTable(content, hasStructuredResults)
  const blocks = cleaned.split(/\n\s*\n/).map((block) => block.trim()).filter(Boolean)

  return (
    <div className="space-y-3 text-sm leading-7 text-slate-700">
      {blocks.map((block, index) => {
        const lines = block.split('\n').map((line) => line.trim()).filter(Boolean)
        const isList = lines.length > 0 && lines.every((line) => /^[-*•]\s+/.test(line))

        if (isList) {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5 marker:text-violet-500">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex}>{renderInlineMarkdown(line.replace(/^[-*•]\s+/, ''))}</li>
              ))}
            </ul>
          )
        }

        return (
          <p key={index}>
            {lines.map((line, lineIndex) => (
              <span key={lineIndex}>
                {renderInlineMarkdown(line)}
                {lineIndex < lines.length - 1 && <br />}
              </span>
            ))}
          </p>
        )
      })}
    </div>
  )
}

function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem('blink_ai_messages')
      return saved ? JSON.parse(saved) as ChatMessage[] : []
    } catch {
      return []
    }
  })
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeExecutionEvents, setActiveExecutionEvents] = useState<ExecutionEvent[]>([])

  useEffect(() => {
    try {
      localStorage.setItem('blink_ai_messages', JSON.stringify(messages))
    } catch (storageError) {
      console.error('Could not save Blink AI chat history:', storageError)
      setError('Browser storage is full. Some chat history may not be saved.')
    }
  }, [messages])

  const [conversationId] = useState(() => {
    const savedId = localStorage.getItem('blink_ai_conversation_id')
    if (savedId) return savedId
    const newId = crypto.randomUUID()
    localStorage.setItem('blink_ai_conversation_id', newId)
    return newId
  })

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = input.trim()
    if (!message || loading) return

    setMessages((previous) => [...previous, { role: 'user', content: message }])
    setInput('')
    setError('')
    setActiveExecutionEvents([])
    setLoading(true)

    const requestEvents: ExecutionEvent[] = []
    let comparisonResult: ProductComparisonData | undefined

    try {
      const response = await sendChatMessageStream(message, conversationId, {
        onEvent: async (executionEvent) => {
          requestEvents.push(executionEvent)
          setActiveExecutionEvents([...requestEvents])

          if (
            executionEvent.type === 'tool_end' &&
            executionEvent.payload.tool === 'compare_product_tool'
          ) {
            const parsed = parseComparisonResult(executionEvent.payload.result)
            if (parsed) comparisonResult = parsed
            else console.error('[BLINK COMPARISON PARSE FAILED]', executionEvent.payload.result)
          }

          const delays: Partial<Record<ExecutionEvent['type'], number>> = {
            request_start: 100,
            graph_start: 120,
            llm_start: 140,
            llm_end: 140,
            tool_call: 120,
            tool_start: 140,
            tool_end: 180,
          }
          const delay = delays[executionEvent.type] ?? 0
          if (delay > 0) await new Promise<void>((resolve) => window.setTimeout(resolve, delay))
        },
      })

      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          content: response.answer,
          products: response.products ?? [],
          comparison: comparisonResult,
          executionEvents: requestEvents,
        },
      ])
      setActiveExecutionEvents([])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unable to connect to Blink AI.'
      setError(errorMessage)

      if (requestEvents.length > 0) {
        setMessages((previous) => [
          ...previous,
          {
            role: 'assistant',
            content: `I couldn't complete this request: ${errorMessage}`,
            executionEvents: requestEvents,
          },
        ])
        setActiveExecutionEvents([])
      }
    } finally {
      setLoading(false)
    }
  }

  const suggestedPrompts = [
    'Find organic honey',
    'Compare Organic Raw Honey and Organic Acacia Honey',
    'Find healthy snacks',
    'My preferences',
  ]

  return (
    <div className="flex min-h-dvh w-full overflow-hidden bg-slate-50 text-slate-900">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-5 md:flex lg:w-64">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-violet-700">Blink AI</h1>
          <p className="mt-1 text-xs text-slate-500">Agentic Shopping Assistant</p>
        </div>

        <nav className="mt-9 space-y-1.5" aria-label="Main navigation">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `block rounded-xl px-4 py-3 text-sm transition ${
              isActive ? 'bg-violet-50 font-semibold text-violet-700' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            AI Assistant
          </NavLink>
          <NavLink
            to="/favorites"
            className={({ isActive }) => `block rounded-xl px-4 py-3 text-sm transition ${
              isActive ? 'bg-violet-50 font-semibold text-violet-700' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            Favorites
          </NavLink>
          <NavLink
            to="/profile"
            className={({ isActive }) => `block rounded-xl px-4 py-3 text-sm transition ${
              isActive ? 'bg-violet-50 font-semibold text-violet-700' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            Profile
          </NavLink>
        </nav>

        <div className="mt-auto border-t border-slate-200 pt-4">
          <LogoutButton />
        </div>
      </aside>

      <main className="flex min-h-dvh min-w-0 flex-1 flex-col overflow-hidden">
        <header className="z-10 shrink-0 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur sm:px-6 sm:py-4">
          <div className="mx-auto w-full max-w-5xl">
            <h2 className="text-sm font-semibold text-slate-900 sm:text-base">AI Shopping Assistant</h2>
            <p className="mt-0.5 text-xs text-slate-500 sm:text-sm">Find products through natural conversation</p>
          </div>
        </header>

        <section className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-3 py-5 sm:px-6 sm:py-7">
          {messages.length === 0 ? (
            <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col justify-center py-8 text-center">
              <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-100 text-3xl text-violet-700">✦</div>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">What are you shopping for?</h2>
              <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-500 sm:text-base">
                Tell Blink AI what you need. It can search products, compare options and remember your preferences.
              </p>
              <div className="mt-8 grid gap-3 text-left sm:grid-cols-2">
                {suggestedPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setInput(prompt)}
                    className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-sm transition hover:border-violet-300 hover:bg-violet-50"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
              {messages.map((message, index) => {
                const hasProducts = Boolean(message.products?.length)
                const hasComparison = Boolean(message.comparison)
                const isAssistant = message.role === 'assistant'

                return (
                  <article
                    key={`${message.role}-${index}`}
                    className={`flex w-full min-w-0 flex-col ${message.role === 'user' ? 'items-end' : 'items-start'}`}
                  >
                    {message.role === 'user' ? (
                      <div className="max-w-[92%] break-words rounded-2xl rounded-br-md bg-violet-600 px-4 py-3 text-sm leading-6 text-white shadow-sm sm:max-w-[80%] sm:px-5">
                        {message.content}
                      </div>
                    ) : (
                      <div className="w-full min-w-0 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-4 shadow-sm sm:px-5">
                        <AssistantContent
                          content={message.content}
                          hasStructuredResults={hasProducts || hasComparison}
                        />
                      </div>
                    )}

                    {isAssistant && hasProducts && (
                      <div className="mt-3 w-full min-w-0 space-y-3">
                        <div className="flex items-center justify-between gap-2 px-1">
                          <h3 className="text-sm font-semibold text-slate-700">Products found</h3>
                          <span className="text-xs text-slate-500">{message.products!.length} results</span>
                        </div>
                        <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                          {message.products!.map((product) => (
                            <ProductCard key={product.id} product={product} />
                          ))}
                        </div>
                      </div>
                    )}

                    {isAssistant && message.comparison && (
                      <div className="mt-3 w-full min-w-0">
                        <ProductComparison comparison={message.comparison} />
                      </div>
                    )}

                    {isAssistant && message.executionEvents && message.executionEvents.length > 0 && (
                      <div className="mt-3 w-full min-w-0">
                        <AgentActivity events={message.executionEvents} isProcessing={false} />
                      </div>
                    )}
                  </article>
                )
              })}

              {loading && activeExecutionEvents.length > 0 && (
                <div className="w-full min-w-0">
                  <AgentActivity events={activeExecutionEvents} isProcessing />
                </div>
              )}

              {loading && activeExecutionEvents.length === 0 && (
                <div className="self-start rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
                  Blink AI is starting the workflow…
                </div>
              )}
            </div>
          )}
        </section>

        {error && (
          <div className="mx-auto w-full max-w-4xl shrink-0 px-3 pb-2 sm:px-6">
            <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {error}
            </p>
          </div>
        )}

        <footer className="shrink-0 border-t border-slate-200 bg-white px-3 py-3 sm:px-6 sm:py-4">
          <form onSubmit={handleSubmit} className="mx-auto flex w-full max-w-4xl min-w-0 items-center gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm focus-within:border-violet-300 focus-within:ring-4 focus-within:ring-violet-100">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask Blink AI to find or compare products…"
              aria-label="Message Blink AI"
              className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="shrink-0 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50 sm:px-5"
            >
              {loading ? 'Sending…' : 'Send'}
            </button>
          </form>
          <p className="mx-auto mt-2 hidden max-w-4xl text-center text-[11px] text-slate-400 sm:block">
            Blink AI can search and compare products. It does not place orders or make purchases.
          </p>
        </footer>
      </main>
    </div>
  )
}

export default ChatPage
