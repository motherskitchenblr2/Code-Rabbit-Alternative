import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react'

interface PipelineEvent {
  id: string
  type: string
  status: string
  timestamp: string
  data?: any
}

interface FeedTotals {
  events_processed: number
  comments_dispatched: number
  reviews_created: number
}

interface WebSocketContextType {
  isConnected: boolean
  events: PipelineEvent[]
  totals: Record<string, number>
  pipeline: FeedTotals
  sendMessage: (message: any) => void
  clearEvents: () => void
}

const POLL_MS = 4000

// The Flask worker has no WebSocket server, so the "live" stream is a short
// poll against the real /api/v1/events feed. Same public surface as before.
export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false)
  const [events, setEvents] = useState<PipelineEvent[]>([])
  const [totals, setTotals] = useState<Record<string, number>>({})
  const [pipeline, setPipeline] = useState<FeedTotals>({
    events_processed: 0,
    comments_dispatched: 0,
    reviews_created: 0,
  })
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    const poll = async () => {
      const token = localStorage.getItem('access_token')
      try {
        const response = await fetch('/api/v1/events', {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (!response.ok) {
          setIsConnected(false)
          return
        }
        const data = await response.json()
        setEvents((data.events || []).slice(0, 100))
        setTotals(data.totals || {})
        setPipeline(data.pipeline || { events_processed: 0, comments_dispatched: 0, reviews_created: 0 })
        setIsConnected(true)
      } catch {
        setIsConnected(false)
      }
    }

    poll()
    timerRef.current = window.setInterval(poll, POLL_MS)
    return () => {
      if (timerRef.current !== null) window.clearInterval(timerRef.current)
    }
  }, [])

  const sendMessage = useCallback((_message: any) => {
    // Kept for API compatibility; the feed is polled, not pushed.
  }, [])

  const clearEvents = useCallback(() => {
    setEvents([])
    setTotals({})
  }, [])

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        events,
        totals,
        pipeline,
        sendMessage,
        clearEvents,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)