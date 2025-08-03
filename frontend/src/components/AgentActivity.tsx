import React from 'react'
import { useScrapingStore } from '../store/scrapingStore'

interface AgentActivityProps {
  className?: string
}

export const AgentActivity: React.FC<AgentActivityProps> = ({ className = '' }) => {
  const { messages, currentAction, isConnected, requiresHumanInput, humanInputPrompt } = useScrapingStore()

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getMessageTypeColor = (type: string) => {
    switch (type) {
      case 'job_started':
      case 'browser_ready':
        return 'text-green-600'
      case 'agent_progress':
        return 'text-blue-600'
      case 'job_error':
      case 'agent_error':
        return 'text-red-600'
      case 'human_input_required':
        return 'text-orange-600'
      case 'job_completed':
        return 'text-green-700'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Agent Activity</h2>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className={`text-sm ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {currentAction && (
        <div className="mb-4 p-3 bg-blue-50 rounded-md border-l-4 border-blue-400">
          <p className="text-sm text-blue-800">
            <span className="font-medium">Current Action:</span> {currentAction}
          </p>
        </div>
      )}

      {requiresHumanInput && (
        <div className="mb-4 p-4 bg-orange-50 rounded-md border-l-4 border-orange-400">
          <p className="text-sm text-orange-800 font-medium mb-2">Human Input Required</p>
          <p className="text-sm text-orange-700">{humanInputPrompt}</p>
        </div>
      )}

      <div className="bg-gray-50 rounded-md p-4 h-64 overflow-y-auto">
        {messages.length === 0 ? (
          <p className="text-gray-500 text-center py-8">Agent activity will appear here...</p>
        ) : (
          <div className="space-y-2">
            {messages.map((message) => (
              <div key={message.id} className="flex items-start space-x-2">
                <span className="text-xs text-gray-400 mt-1 min-w-[60px]">
                  {formatTime(message.timestamp)}
                </span>
                <div className="flex-1">
                  <span className={`text-xs font-medium ${getMessageTypeColor(message.type)}`}>
                    [{message.type}]
                  </span>
                  <p className="text-sm text-gray-700 mt-1">{message.message}</p>
                  {message.data && Object.keys(message.data).length > 0 && (
                    <details className="mt-1">
                      <summary className="text-xs text-gray-500 cursor-pointer">Show data</summary>
                      <pre className="text-xs bg-gray-100 p-2 rounded mt-1 overflow-x-auto">
                        {JSON.stringify(message.data, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
