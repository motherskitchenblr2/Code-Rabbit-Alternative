import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'

interface PipelineEvent {
  id: string
  type: 'webhook' | 'ast' | 'rag' | 'critique' | 'github' | 'chat'
  status: 'pending' | 'processing' | 'completed' | 'failed'
  timestamp: string
  data?: any
}

interface WebSocketContextType {
  isConnected: boolean
  events: PipelineEvent[]
  sendMessage: (message: any) => void
  clearEvents: () => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [isConnected, setIsConnected] = useState(false)
  const [events, setEvents] = useState<PipelineEvent[]>([])
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const maxReconnectAttempts = 5

  const connect = useCallback(() => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
    const websocket = new WebSocket(wsUrl)

    websocket.onopen = () => {
      setIsConnected(true)
      setReconnectAttempts(0)
      console.log('WebSocket connected')
    }

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setEvents(prev => [data, ...prev].slice(0, 100))
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    websocket.onclose = () => {
      setIsConnected(false)
      console.log('WebSocket disconnected')
      if (reconnectAttempts < maxReconnectAttempts) {
        setTimeout(() => {
          setReconnectAttempts(prev => prev + 1)
          connect()
        }, Math.min(1000 * 2 ** reconnectAttempts, 30000))
      }
    }

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    setWs(websocket)
  }, [reconnectAttempts])

  useEffect(() => {
    connect()
    return () => {
      if (ws) ws.close()
    }
  }, [connect])

  const sendMessage = useCallback((message: any) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    }
  }, [ws])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        events,
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