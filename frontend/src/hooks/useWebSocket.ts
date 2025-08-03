import { useEffect, useRef, useState } from 'react'
import { io, Socket } from 'socket.io-client'

interface UseWebSocketProps {
  clientId: string
  onMessage?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export const useWebSocket = ({ clientId, onMessage, onConnect, onDisconnect }: UseWebSocketProps) => {
  const [isConnected, setIsConnected] = useState(false)
  const [socket, setSocket] = useState<Socket | null>(null)
  const socketRef = useRef<Socket | null>(null)

  useEffect(() => {
    // Create WebSocket connection
    const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`)
    
    ws.onopen = () => {
      setIsConnected(true)
      onConnect?.()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage?.(data)
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      onDisconnect?.()
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    socketRef.current = ws

    return () => {
      ws.close()
    }
  }, [clientId, onMessage, onConnect, onDisconnect])

  const sendMessage = (message: string) => {
    if (socketRef.current && isConnected) {
      socketRef.current.send(message)
    }
  }

  return {
    isConnected,
    sendMessage
  }
}
