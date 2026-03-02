import { useState } from 'react'
import {
  TrendingUp,
  Shield,
  Wifi,
  AlertCircle,
  CheckCircle,
  XCircle,
  ExternalLink
} from 'lucide-react'
import { useAppStore } from '../stores/appStore'

type DataType = 'markets' | 'cyber' | 'infrastructure'

interface DataPanelProps {
  type: DataType
}

export default function DataPanel({ type }: DataPanelProps) {
  const config = {
    markets: {
      title: 'FINANCIAL MARKETS',
      icon: TrendingUp,
      color: 'text-green-400',
    },
    cyber: {
      title: 'CYBER THREATS',
      icon: Shield,
      color: 'text-pink-400',
    },
    infrastructure: {
      title: 'INFRASTRUCTURE STATUS',
      icon: Wifi,
      color: 'text-indigo-400',
    },
  }

  const { title, icon: Icon, color } = config[type]

  return (
    <div className="panel">
      <div className="flex items-center gap-2 p-4 border-b border-wm-border">
        <Icon className={`w-5 h-5 ${color}`} />
        <h3 className="text-sm font-medium">{title}</h3>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {type === 'markets' && <MarketsPanel />}
        {type === 'cyber' && <CyberPanel />}
        {type === 'infrastructure' && <InfrastructurePanel />}
      </div>
    </div>
  )
}

function MarketsPanel() {
  const { marketQuotes } = useAppStore()
  const [filter, setFilter] = useState<string>('all')

  const filteredQuotes = marketQuotes.filter((q) =>
    filter === 'all' ? true : q.asset_type === filter
  )

  return (
    <div>
      {/* Filter tabs */}
      <div className="flex gap-2 p-3 border-b border-wm-border">
        {['all', 'stock', 'crypto', 'forex', 'commodity'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 text-xs rounded ${
              filter === f
                ? 'bg-wm-accent text-white'
                : 'bg-wm-bg text-gray-400 hover:text-white'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Quotes table */}
      <table className="data-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th className="text-right">Price</th>
            <th className="text-right">Change</th>
          </tr>
        </thead>
        <tbody>
          {filteredQuotes.map((quote) => (
            <tr key={quote.symbol}>
              <td>
                <div className="font-medium">{quote.symbol}</div>
                <div className="text-xs text-gray-400">{quote.name}</div>
              </td>
              <td className="text-right">
                ${quote.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </td>
              <td className="text-right">
                <span className={quote.change >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {quote.change >= 0 ? '+' : ''}{quote.change_percent?.toFixed(2)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CyberPanel() {
  const { cyberThreats } = useAppStore()
  const [filter, setFilter] = useState<string>('all')

  const filteredThreats = cyberThreats.filter((t) =>
    filter === 'all' ? true : t.ioc_type === filter
  )

  // Get threat stats
  const threatStats = cyberThreats.reduce((acc, t) => {
    acc[t.ioc_type] = (acc[t.ioc_type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div>
      {/* Stats */}
      <div className="grid grid-cols-4 gap-2 p-3 border-b border-wm-border">
        <div className="bg-wm-bg rounded p-2 text-center">
          <div className="text-lg font-bold text-pink-400">{threatStats.url || 0}</div>
          <div className="text-xs text-gray-400">URLs</div>
        </div>
        <div className="bg-wm-bg rounded p-2 text-center">
          <div className="text-lg font-bold text-pink-400">{threatStats.ip || 0}</div>
          <div className="text-xs text-gray-400">IPs</div>
        </div>
        <div className="bg-wm-bg rounded p-2 text-center">
          <div className="text-lg font-bold text-pink-400">{threatStats.domain || 0}</div>
          <div className="text-xs text-gray-400">Domains</div>
        </div>
        <div className="bg-wm-bg rounded p-2 text-center">
          <div className="text-lg font-bold text-pink-400">{threatStats.hash || 0}</div>
          <div className="text-xs text-gray-400">Hashes</div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2 p-3 border-b border-wm-border">
        {['all', 'url', 'ip', 'domain', 'hash'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 text-xs rounded ${
              filter === f
                ? 'bg-pink-500/20 text-pink-400'
                : 'bg-wm-bg text-gray-400 hover:text-white'
            }`}
          >
            {f.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Threat list */}
      <div className="divide-y divide-wm-border">
        {filteredThreats.slice(0, 30).map((threat) => (
          <div key={threat.id} className="p-3 hover:bg-wm-bg/50">
            <div className="flex items-center gap-2">
              <span className={`text-xs px-1.5 rounded ${getIOCTypeStyle(threat.ioc_type)}`}>
                {threat.ioc_type}
              </span>
              <span className={`text-xs ${getConfidenceColor(threat.confidence)}`}>
                {threat.confidence}%
              </span>
            </div>
            <div className="text-xs font-mono text-gray-300 mt-1 truncate">
              {threat.ioc_value}
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-gray-400">
                {threat.malware_family || threat.threat_type}
              </span>
              <span className="text-xs text-gray-500">{threat.source}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function InfrastructurePanel() {
  const { serviceStatuses } = useAppStore()

  return (
    <div className="divide-y divide-wm-border">
      {serviceStatuses.map((service) => (
        <div key={service.service} className="p-3 hover:bg-wm-bg/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {service.status === 'operational' ? (
                <CheckCircle className="w-4 h-4 text-green-400" />
              ) : service.status === 'degraded' ? (
                <AlertCircle className="w-4 h-4 text-yellow-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span className="font-medium">{service.service}</span>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded ${getStatusStyle(service.status)}`}>
              {service.status}
            </span>
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-gray-400">
            <span>
              Response: {service.response_time_ms ? `${service.response_time_ms}ms` : 'N/A'}
            </span>
            <a
              href={service.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-wm-accent"
            >
              Status page <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      ))}
    </div>
  )
}

function getIOCTypeStyle(type: string): string {
  switch (type) {
    case 'url':
      return 'bg-blue-500/20 text-blue-400'
    case 'ip':
      return 'bg-red-500/20 text-red-400'
    case 'domain':
      return 'bg-purple-500/20 text-purple-400'
    case 'hash':
      return 'bg-green-500/20 text-green-400'
    default:
      return 'bg-gray-500/20 text-gray-400'
  }
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 80) return 'text-green-400'
  if (confidence >= 50) return 'text-yellow-400'
  return 'text-red-400'
}

function getStatusStyle(status: string): string {
  switch (status) {
    case 'operational':
      return 'bg-green-500/20 text-green-400'
    case 'degraded':
      return 'bg-yellow-500/20 text-yellow-400'
    case 'outage':
      return 'bg-red-500/20 text-red-400'
    default:
      return 'bg-gray-500/20 text-gray-400'
  }
}
