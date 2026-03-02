import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import {
  Settings,
  Clock,
  Layers,
  RefreshCw,
  Server,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'

export default function SettingsPanel() {
  const { timeRange, setTimeRange, selectedLayers, toggleLayer } = useAppStore()
  const [apiStatus, setApiStatus] = useState<{
    status: string
    database: string
    demo_mode: boolean
  } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setApiStatus(data)
        setLoading(false)
      })
      .catch(() => {
        setApiStatus(null)
        setLoading(false)
      })
  }, [])

  const timeRangeOptions = [
    { value: 1, label: '24 Hours' },
    { value: 3, label: '3 Days' },
    { value: 7, label: '7 Days' },
    { value: 14, label: '14 Days' },
    { value: 30, label: '30 Days' },
  ]

  const layerOptions = [
    { id: 'conflicts', label: 'Conflicts', color: 'bg-red-500' },
    { id: 'earthquakes', label: 'Earthquakes', color: 'bg-yellow-500' },
    { id: 'fires', label: 'Wildfires', color: 'bg-orange-500' },
    { id: 'maritime', label: 'Maritime', color: 'bg-cyan-500' },
    { id: 'military', label: 'Military', color: 'bg-purple-500' },
  ] as const

  return (
    <div className="bg-wm-panel rounded-xl border border-wm-border overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-wm-border flex items-center gap-2">
        <Settings className="w-5 h-5 text-gray-400" />
        <h2 className="font-semibold text-white">Settings</h2>
      </div>

      <div className="p-4 space-y-6">
        {/* Time Range */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-300">Time Range</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {timeRangeOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => setTimeRange(option.value)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  timeRange === option.value
                    ? 'bg-wm-accent text-white'
                    : 'bg-wm-border text-gray-400 hover:text-white'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* Layer Visibility */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Layers className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-300">Default Layers</span>
          </div>
          <div className="space-y-2">
            {layerOptions.map((layer) => (
              <label
                key={layer.id}
                className="flex items-center gap-3 px-3 py-2 rounded-lg bg-wm-border/50 hover:bg-wm-border cursor-pointer transition-colors"
              >
                <input
                  type="checkbox"
                  checked={selectedLayers.includes(layer.id)}
                  onChange={() => toggleLayer(layer.id)}
                  className="sr-only"
                />
                <div className={`w-4 h-4 rounded ${layer.color}`} />
                <span className="text-sm text-gray-300 flex-1">{layer.label}</span>
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                  selectedLayers.includes(layer.id)
                    ? 'bg-wm-accent border-wm-accent'
                    : 'border-gray-500'
                }`}>
                  {selectedLayers.includes(layer.id) && (
                    <CheckCircle className="w-3 h-3 text-white" />
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* API Status */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Server className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-300">System Status</span>
          </div>
          <div className="bg-wm-border/50 rounded-lg p-3 space-y-2">
            {loading ? (
              <div className="flex items-center gap-2 text-gray-400">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span className="text-sm">Checking status...</span>
              </div>
            ) : apiStatus ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">API</span>
                  <div className="flex items-center gap-1">
                    <CheckCircle className="w-4 h-4 text-wm-success" />
                    <span className="text-sm text-wm-success">Healthy</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Database</span>
                  <div className="flex items-center gap-1">
                    {apiStatus.database === 'connected' ? (
                      <>
                        <CheckCircle className="w-4 h-4 text-wm-success" />
                        <span className="text-sm text-wm-success">Connected</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-4 h-4 text-wm-warning" />
                        <span className="text-sm text-wm-warning">Demo Mode</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Mode</span>
                  <span className={`text-sm ${apiStatus.demo_mode ? 'text-wm-warning' : 'text-wm-success'}`}>
                    {apiStatus.demo_mode ? 'Demo' : 'Production'}
                  </span>
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2 text-wm-danger">
                <XCircle className="w-4 h-4" />
                <span className="text-sm">API Unavailable</span>
              </div>
            )}
          </div>
        </div>

        {/* Version Info */}
        <div className="pt-4 border-t border-wm-border">
          <div className="text-xs text-gray-500 space-y-1">
            <div>World Monitor v1.0.0</div>
            <div>Powered by Databricks</div>
          </div>
        </div>
      </div>
    </div>
  )
}
