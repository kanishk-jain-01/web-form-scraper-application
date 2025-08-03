import React, { useState } from 'react'
import { useScrapingStore } from '../store/scrapingStore'

interface ScrapingFormProps {
  onStartScraping: (url: string) => void
  onStopScraping: () => void
  className?: string
}

export const ScrapingForm: React.FC<ScrapingFormProps> = ({ 
  onStartScraping, 
  onStopScraping, 
  className = '' 
}) => {
  const { url, setUrl, isActive, clientId, requiresHumanInput, humanInputPrompt } = useScrapingStore()
  const [humanInput, setHumanInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (url && !isActive) {
      onStartScraping(url)
    }
  }

  const handleHumanInputSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!humanInput.trim()) return

    try {
      const response = await fetch('/api/v1/scraping/human-input', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: useScrapingStore.getState().jobId,
          user_input: humanInput
        })
      })

      if (response.ok) {
        setHumanInput('')
        useScrapingStore.getState().setHumanInput(false)
      } else {
        console.error('Failed to submit human input')
      }
    } catch (error) {
      console.error('Error submitting human input:', error)
    }
  }

  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-semibold text-gray-900">Web Scraper</h2>
          <span className="text-sm text-gray-500">Client ID: {clientId.slice(0, 8)}...</span>
        </div>
        <p className="text-gray-600">
          AI-powered web form scraping with LangGraph agents
        </p>
      </div>

      {requiresHumanInput ? (
        <form onSubmit={handleHumanInputSubmit} className="space-y-4">
          <div className="p-4 bg-orange-50 rounded-md border border-orange-200">
            <h3 className="font-medium text-orange-800 mb-2">Human Input Required</h3>
            <p className="text-sm text-orange-700 mb-3">{humanInputPrompt}</p>
            
            <div className="space-y-3">
              <textarea
                value={humanInput}
                onChange={(e) => setHumanInput(e.target.value)}
                placeholder="Enter your response..."
                className="w-full px-3 py-2 border border-orange-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                rows={3}
                required
              />
              
              <div className="flex space-x-2">
                <button
                  type="submit"
                  disabled={!humanInput.trim()}
                  className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Submit Response
                </button>
                <button
                  type="button"
                  onClick={() => useScrapingStore.getState().setHumanInput(false)}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </form>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
              Website URL
            </label>
            <input
              type="url"
              id="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isActive}
              required
            />
          </div>

          <div className="flex space-x-2">
            {!isActive ? (
              <button 
                type="submit"
                disabled={!url}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Start Scraping
              </button>
            ) : (
              <button 
                type="button"
                onClick={onStopScraping}
                className="flex-1 bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                Stop Scraping
              </button>
            )}
          </div>

          {isActive && (
            <div className="flex items-center justify-center p-3 bg-blue-50 rounded-md">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-sm text-blue-700">Scraping in progress...</span>
            </div>
          )}
        </form>
      )}
    </div>
  )
}
