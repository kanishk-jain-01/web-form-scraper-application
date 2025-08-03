import React, { useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useScrapingStore } from './store/scrapingStore'
import { ScrapingForm } from './components/ScrapingForm'
import { AgentActivity } from './components/AgentActivity'

function App() {
  const {
    clientId,
    isActive,
    setActive,
    setJobId,
    addMessage,
    setConnected,
    setCurrentAction,
    setHumanInput,
    clearMessages
  } = useScrapingStore()

  const { isConnected, sendMessage } = useWebSocket({
    clientId,
    onMessage: (data) => {
      console.log('WebSocket message received:', data)

      // Handle different message types
      switch (data.type) {
        case 'job_started':
          setActive(true)
          setJobId(data.job_id)
          break
        
        case 'job_completed':
        case 'job_stopped':
        case 'job_error':
          setActive(false)
          break
        
        case 'agent_progress':
          setCurrentAction(data.message)
          if (data.data?.requires_human_input) {
            setHumanInput(true, data.data.prompt, data.data.input_type)
          }
          break
        
        case 'human_input_processed':
          setHumanInput(false)
          break
      }

      // Add message to activity log
      addMessage({
        type: data.type,
        message: data.message,
        data: data.data
      })
    },
    onConnect: () => {
      setConnected(true)
      addMessage({
        type: 'connection',
        message: 'Connected to server'
      })
    },
    onDisconnect: () => {
      setConnected(false)
      addMessage({
        type: 'connection',
        message: 'Disconnected from server'
      })
    }
  })

  const handleStartScraping = async (url: string) => {
    try {
      clearMessages()
      
      const response = await fetch('/api/v1/scraping/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url,
          client_id: clientId
        })
      })

      if (!response.ok) {
        const error = await response.json()
        addMessage({
          type: 'error',
          message: `Failed to start scraping: ${error.detail}`
        })
        return
      }

      const result = await response.json()
      setJobId(result.job_id)
      setActive(true)
      
      addMessage({
        type: 'job_started',
        message: result.message
      })

    } catch (error) {
      console.error('Error starting scraping:', error)
      addMessage({
        type: 'error',
        message: `Error starting scraping: ${error}`
      })
    }
  }

  const handleStopScraping = async () => {
    try {
      const response = await fetch(`/api/v1/scraping/stop/${clientId}`, {
        method: 'POST'
      })

      if (!response.ok) {
        const error = await response.json()
        addMessage({
          type: 'error',
          message: `Failed to stop scraping: ${error.detail}`
        })
        return
      }

      const result = await response.json()
      setActive(false)
      setJobId(null)
      
      addMessage({
        type: 'job_stopped',
        message: result.message
      })

    } catch (error) {
      console.error('Error stopping scraping:', error)
      addMessage({
        type: 'error',
        message: `Error stopping scraping: ${error}`
      })
    }
  }

  useEffect(() => {
    setConnected(isConnected)
  }, [isConnected, setConnected])

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <header className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Utility Profit Web Scraper
          </h1>
          <p className="text-gray-600">
            AI-powered web form scraping with LangGraph agents
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ScrapingForm
            onStartScraping={handleStartScraping}
            onStopScraping={handleStopScraping}
          />
          
          <AgentActivity />
        </div>

        {/* Status Bar */}
        <div className="mt-6 bg-white rounded-lg shadow-md p-4">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-4">
              <span className="text-gray-600">Status:</span>
              <span className={`font-medium ${isActive ? 'text-green-600' : 'text-gray-600'}`}>
                {isActive ? 'Active' : 'Idle'}
              </span>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-gray-600">Connection:</span>
              <span className={`font-medium ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
