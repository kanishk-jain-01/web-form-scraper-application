import { create } from 'zustand'

interface AgentMessage {
  id: string
  type: string
  message: string
  timestamp: Date
  data?: any
}

interface ScrapingState {
  // Job state
  isActive: boolean
  jobId: string | null
  clientId: string
  url: string
  
  // Agent activity
  messages: AgentMessage[]
  currentAction: string
  
  // WebSocket connection
  isConnected: boolean
  
  // Human input
  requiresHumanInput: boolean
  humanInputPrompt: string
  humanInputType: string
  
  // Actions
  setActive: (active: boolean) => void
  setJobId: (jobId: string | null) => void
  setUrl: (url: string) => void
  setConnected: (connected: boolean) => void
  addMessage: (message: Omit<AgentMessage, 'id' | 'timestamp'>) => void
  setCurrentAction: (action: string) => void
  setHumanInput: (required: boolean, prompt?: string, type?: string) => void
  clearMessages: () => void
  generateClientId: () => void
}

export const useScrapingStore = create<ScrapingState>((set, get) => ({
  // Initial state
  isActive: false,
  jobId: null,
  clientId: crypto.randomUUID(),
  url: '',
  messages: [],
  currentAction: '',
  isConnected: false,
  requiresHumanInput: false,
  humanInputPrompt: '',
  humanInputType: 'text',

  // Actions
  setActive: (active) => set({ isActive: active }),
  
  setJobId: (jobId) => set({ jobId }),
  
  setUrl: (url) => set({ url }),
  
  setConnected: (connected) => set({ isConnected: connected }),
  
  addMessage: (message) => set((state) => ({
    messages: [
      ...state.messages,
      {
        ...message,
        id: crypto.randomUUID(),
        timestamp: new Date()
      }
    ]
  })),
  
  setCurrentAction: (action) => set({ currentAction: action }),
  
  setHumanInput: (required, prompt = '', type = 'text') => set({
    requiresHumanInput: required,
    humanInputPrompt: prompt,
    humanInputType: type
  }),
  
  clearMessages: () => set({ messages: [] }),
  
  generateClientId: () => set({ clientId: crypto.randomUUID() })
}))
