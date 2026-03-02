import {
  Crosshair,
  Activity,
  Flame,
  Shield,
  TrendingUp,
  TrendingDown,
  AlertTriangle
} from 'lucide-react'
import { useAppStore } from '../stores/appStore'

export default function StatsPanel() {
  const { stats, riskScores, serviceStatuses, marketQuotes } = useAppStore()

  // Get top risk countries
  const topRiskCountries = [...riskScores]
    .sort((a, b) => b.overall_risk - a.overall_risk)
    .slice(0, 5)

  // Get service status summary
  const statusCounts = serviceStatuses.reduce(
    (acc, s) => {
      acc[s.status] = (acc[s.status] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  return (
    <div className="space-y-4">
      {/* Global Stats */}
      <div className="panel p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">GLOBAL ACTIVITY</h3>
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            icon={Crosshair}
            label="Conflicts"
            value={stats.conflicts}
            color="text-red-400"
          />
          <StatCard
            icon={Activity}
            label="Earthquakes"
            value={stats.earthquakes}
            color="text-yellow-400"
          />
          <StatCard
            icon={Flame}
            label="Active Fires"
            value={stats.fires}
            color="text-orange-400"
          />
          <StatCard
            icon={Shield}
            label="Cyber Threats"
            value={stats.cyberThreats}
            color="text-pink-400"
          />
        </div>
      </div>

      {/* Risk Assessment */}
      <div className="panel p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">HIGH RISK REGIONS</h3>
        <div className="space-y-2">
          {topRiskCountries.map((country) => (
            <div
              key={country.country_code}
              className="flex items-center justify-between py-1"
            >
              <span className="text-sm">{country.country_name}</span>
              <div className="flex items-center gap-2">
                <RiskBar value={country.overall_risk} />
                <span className={`text-xs font-medium ${getRiskColor(country.overall_risk)}`}>
                  {country.overall_risk}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Market Movers */}
      <div className="panel p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">MARKET MOVERS</h3>
        <div className="space-y-2">
          {marketQuotes.slice(0, 5).map((quote) => (
            <div
              key={quote.symbol}
              className="flex items-center justify-between py-1"
            >
              <div>
                <span className="text-sm font-medium">{quote.symbol}</span>
                <span className="text-xs text-gray-400 ml-2">${quote.price?.toFixed(2)}</span>
              </div>
              <div className={`flex items-center gap-1 ${
                quote.change >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {quote.change >= 0 ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <TrendingDown className="w-3 h-3" />
                )}
                <span className="text-xs font-medium">
                  {quote.change >= 0 ? '+' : ''}{quote.change_percent?.toFixed(2)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Infrastructure Status */}
      <div className="panel p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">SERVICE STATUS</h3>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            <span className="text-xs">{statusCounts.operational || 0} OK</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
            <span className="text-xs">{statusCounts.degraded || 0} Degraded</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 bg-red-500 rounded-full"></span>
            <span className="text-xs">{statusCounts.outage || 0} Outage</span>
          </div>
        </div>
        <div className="mt-3 space-y-1">
          {serviceStatuses.filter((s) => s.status !== 'operational').map((service) => (
            <div
              key={service.service}
              className="flex items-center gap-2 text-xs"
            >
              <AlertTriangle className={`w-3 h-3 ${
                service.status === 'outage' ? 'text-red-400' : 'text-yellow-400'
              }`} />
              <span>{service.service}</span>
              <span className="text-gray-400">- {service.status}</span>
            </div>
          ))}
          {serviceStatuses.every((s) => s.status === 'operational') && (
            <div className="text-xs text-green-400">All systems operational</div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  color
}: {
  icon: React.ElementType
  label: string
  value: number
  color: string
}) {
  return (
    <div className="bg-wm-bg rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <span className={`text-xl font-bold ${color}`}>{value.toLocaleString()}</span>
    </div>
  )
}

function RiskBar({ value }: { value: number }) {
  return (
    <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
      <div
        className={`h-full ${getRiskBgColor(value)}`}
        style={{ width: `${value}%` }}
      />
    </div>
  )
}

function getRiskColor(value: number): string {
  if (value >= 75) return 'text-red-400'
  if (value >= 50) return 'text-orange-400'
  if (value >= 25) return 'text-yellow-400'
  return 'text-green-400'
}

function getRiskBgColor(value: number): string {
  if (value >= 75) return 'bg-red-500'
  if (value >= 50) return 'bg-orange-500'
  if (value >= 25) return 'bg-yellow-500'
  return 'bg-green-500'
}
