import { useState, useRef, useEffect } from 'react'
import {
  Brain,
  Globe,
  AlertTriangle,
  TrendingUp,
  Shield,
  RefreshCw,
  MessageSquare,
  Send,
  Loader2
} from 'lucide-react'
import { useAppStore } from '../stores/appStore'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export default function IntelPanel() {
  const { riskScores } = useAppStore()
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null)
  const [briefLoading, setBriefLoading] = useState(false)
  const [countryBrief, setCountryBrief] = useState<{
    country_code: string
    current_situation: string
    key_risks: string[]
    outlook: string
  } | null>(null)

  // Ask AI state
  const [question, setQuestion] = useState('')
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
  const [askLoading, setAskLoading] = useState(false)
  const chatContainerRef = useRef<HTMLDivElement>(null)

  const fetchCountryBrief = async (countryCode: string) => {
    setBriefLoading(true)
    try {
      const res = await fetch(`/api/country-brief/${countryCode}`)
      if (res.ok) {
        const data = await res.json()
        setCountryBrief(data)
      }
    } catch (e) {
      console.error('Failed to fetch country brief:', e)
    } finally {
      setBriefLoading(false)
    }
  }

  const handleCountrySelect = (code: string) => {
    setSelectedCountry(code)
    setCountryBrief(null)
    fetchCountryBrief(code)
  }

  // Ask AI handler
  const handleAskAI = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || askLoading) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: question.trim(),
      timestamp: new Date().toISOString(),
    }

    setChatHistory((prev) => [...prev, userMessage])
    setQuestion('')
    setAskLoading(true)

    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage.content,
          context: selectedCountry ? `User is viewing ${selectedCountry} risk profile` : undefined,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: data.answer,
          timestamp: data.generated_at,
        }
        setChatHistory((prev) => [...prev, assistantMessage])
      } else {
        const errorMessage: ChatMessage = {
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          timestamp: new Date().toISOString(),
        }
        setChatHistory((prev) => [...prev, errorMessage])
      }
    } catch (e) {
      console.error('Ask AI error:', e)
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Unable to connect to the AI service. Please check your connection.',
        timestamp: new Date().toISOString(),
      }
      setChatHistory((prev) => [...prev, errorMessage])
    } finally {
      setAskLoading(false)
    }
  }

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [chatHistory])

  return (
    <div className="space-y-4">
      {/* Risk Overview */}
      <div className="panel p-4">
        <div className="flex items-center gap-2 mb-4">
          <Brain className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-medium">AI INTELLIGENCE</h3>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-4">
          {riskScores.slice(0, 6).map((score) => (
            <button
              key={score.country_code}
              onClick={() => handleCountrySelect(score.country_code)}
              className={`p-2 rounded-lg text-left transition-colors ${
                selectedCountry === score.country_code
                  ? 'bg-wm-accent/20 border border-wm-accent'
                  : 'bg-wm-bg hover:bg-wm-border'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{score.country_code}</span>
                <span className={`text-xs ${getRiskClass(score.overall_risk)}`}>
                  {score.overall_risk}
                </span>
              </div>
              <div className="text-xs text-gray-400 truncate">{score.country_name}</div>
            </button>
          ))}
        </div>

        {/* Quick risk view for all countries */}
        <select
          value={selectedCountry || ''}
          onChange={(e) => handleCountrySelect(e.target.value)}
          className="w-full bg-wm-bg border border-wm-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Select a country...</option>
          {riskScores.map((score) => (
            <option key={score.country_code} value={score.country_code}>
              {score.country_name} ({score.overall_risk})
            </option>
          ))}
        </select>
      </div>

      {/* Country Risk Breakdown */}
      {selectedCountry && (
        <div className="panel p-4">
          <h4 className="text-sm font-medium mb-3">
            {riskScores.find((s) => s.country_code === selectedCountry)?.country_name} Risk Profile
          </h4>

          {(() => {
            const score = riskScores.find((s) => s.country_code === selectedCountry)
            if (!score) return null

            return (
              <div className="space-y-3">
                <RiskBar label="Overall" value={score.overall_risk} icon={Globe} />
                <RiskBar label="Political" value={score.political_risk} icon={AlertTriangle} />
                <RiskBar label="Economic" value={score.economic_risk} icon={TrendingUp} />
                <RiskBar label="Security" value={score.security_risk} icon={Shield} />
                <RiskBar label="Climate" value={score.climate_risk} icon={RefreshCw} />
              </div>
            )
          })()}
        </div>
      )}

      {/* AI-Generated Brief */}
      {selectedCountry && (
        <div className="panel p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-amber-400" />
              <h4 className="text-sm font-medium">Intelligence Brief</h4>
            </div>
            <button
              onClick={() => fetchCountryBrief(selectedCountry)}
              disabled={briefLoading}
              className="text-xs text-wm-accent hover:text-wm-accent-hover disabled:opacity-50"
            >
              {briefLoading ? 'Generating...' : 'Refresh'}
            </button>
          </div>

          {briefLoading ? (
            <div className="space-y-2 animate-pulse">
              <div className="h-4 bg-wm-bg rounded w-3/4"></div>
              <div className="h-4 bg-wm-bg rounded w-full"></div>
              <div className="h-4 bg-wm-bg rounded w-5/6"></div>
              <div className="h-4 bg-wm-bg rounded w-2/3"></div>
            </div>
          ) : countryBrief ? (
            <div className="space-y-4 text-sm">
              {/* Current Situation */}
              <div>
                <h5 className="text-xs text-gray-400 mb-1">CURRENT SITUATION</h5>
                <p className="text-gray-300">{countryBrief.current_situation}</p>
              </div>

              {/* Key Risks */}
              <div>
                <h5 className="text-xs text-gray-400 mb-1">KEY RISKS</h5>
                <ul className="space-y-1">
                  {countryBrief.key_risks.map((risk, i) => (
                    <li key={i} className="flex items-start gap-2 text-gray-300">
                      <span className="text-red-400 mt-0.5">•</span>
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Outlook */}
              <div>
                <h5 className="text-xs text-gray-400 mb-1">OUTLOOK</h5>
                <p className="text-gray-300">{countryBrief.outlook}</p>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-400">
              Select a country to generate an intelligence brief using AI.
            </div>
          )}
        </div>
      )}

      {/* AI Chat */}
      <div className="panel p-4">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-4 h-4 text-amber-400" />
          <h4 className="text-sm font-medium">Ask AI</h4>
          {chatHistory.length > 0 && (
            <button
              onClick={() => setChatHistory([])}
              className="ml-auto text-xs text-gray-500 hover:text-gray-300"
            >
              Clear
            </button>
          )}
        </div>

        {/* Chat History */}
        {chatHistory.length > 0 && (
          <div
            ref={chatContainerRef}
            className="mb-3 max-h-64 overflow-y-auto space-y-3 scrollbar-thin scrollbar-thumb-wm-border"
          >
            {chatHistory.map((msg, idx) => (
              <div
                key={idx}
                className={`text-sm ${
                  msg.role === 'user' ? 'text-right' : 'text-left'
                }`}
              >
                <div
                  className={`inline-block max-w-[90%] p-2 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-wm-accent/20 text-gray-200'
                      : 'bg-wm-bg text-gray-300'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
            {askLoading && (
              <div className="text-left">
                <div className="inline-block bg-wm-bg p-2 rounded-lg">
                  <div className="flex items-center gap-2 text-gray-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Analyzing...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Input Form */}
        <form onSubmit={handleAskAI} className="relative">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about global events, risks, analysis..."
            disabled={askLoading}
            className="w-full bg-wm-bg border border-wm-border rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:border-wm-accent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!question.trim() || askLoading}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-wm-accent disabled:opacity-50 disabled:hover:text-gray-400"
          >
            {askLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
        <p className="text-xs text-gray-500 mt-2">
          Powered by Claude Sonnet 4.5 via Databricks Foundation Models
        </p>
      </div>
    </div>
  )
}

function RiskBar({
  label,
  value,
  icon: Icon
}: {
  label: string
  value: number
  icon: React.ElementType
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <div className="flex items-center gap-1.5">
          <Icon className="w-3 h-3 text-gray-400" />
          <span className="text-gray-400">{label}</span>
        </div>
        <span className={getRiskClass(value)}>{value}</span>
      </div>
      <div className="w-full h-2 bg-wm-bg rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${getRiskBgClass(value)}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}

function getRiskClass(value: number): string {
  if (value >= 75) return 'text-red-400'
  if (value >= 50) return 'text-orange-400'
  if (value >= 25) return 'text-yellow-400'
  return 'text-green-400'
}

function getRiskBgClass(value: number): string {
  if (value >= 75) return 'bg-red-500'
  if (value >= 50) return 'bg-orange-500'
  if (value >= 25) return 'bg-yellow-500'
  return 'bg-green-500'
}
