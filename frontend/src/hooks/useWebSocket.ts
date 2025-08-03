import { useEffect, useRef, useState, useCallback } from 'react'

interface UseWebSocketProps {
  clientId: string
  onMessage?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export const useWebSocket = ({ clientId, onMessage, onConnect, onDisconnect }: UseWebSocketProps) => {
  const [isConnected, setIsConnected] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)
  const onConnectRef = useRef(onConnect)
  const onDisconnectRef = useRef(onDisconnect)

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])

  useEffect(() => {
    onConnectRef.current = onConnect
  }, [onConnect])

  useEffect(() => {
    onDisconnectRef.current = onDisconnect
  }, [onDisconnect])

  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      return // Already connected
    }

    // Create WebSocket connection
    const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`)
    
    ws.onopen = () => {
      console.log(`WebSocket connected for client ${clientId}`)
      setIsConnected(true)
      onConnectRef.current?.()
    }

    ws.onmessage = (event) => {
      try {
        // Skip echo messages from backend
        if (event.data.startsWith('Echo:')) {
          return
        }
        
        const data = JSON.parse(event.data)
        onMessageRef.current?.(data)
      } catch (error) {
        console.error('Error parsing WebSocket message:', error, 'Raw message:', event.data)
      }
    }

    ws.onclose = (event) => {
      console.log(`WebSocket disconnected for client ${clientId}`, event.code, event.reason)
      setIsConnected(false)
      onDisconnectRef.current?.()
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    socketRef.current = ws
  }, [clientId])

  const disconnect = useCallback(() => {
    if (socketRef.current && (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING)) {
      socketRef.current.close()
      socketRef.current = null
    }
  }, [])

  const sendMessage = useCallback((message: string) => {
    if (socketRef.current && isConnected) {
      socketRef.current.send(message)
    }
  }, [isConnected])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    isConnected,
    connect,
    disconnect,
    sendMessage
  }
}
