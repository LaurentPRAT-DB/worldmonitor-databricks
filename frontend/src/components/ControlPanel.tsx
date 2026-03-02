import {
  Layers,
  Clock,
  RefreshCw,
  Search
} from 'lucide-react'
import { useState } from 'react'
import { useAppStore } from '../stores/appStore'

const layerOptions = [
  { id: 'conflicts', label: 'Conflicts', color: 'bg-red-500' },
  { id: 'earthquakes', label: 'Seismic', color: 'bg-yellow-500' },
  { id: 'fires', label: 'Wildfires', color: 'bg-orange-500' },
  { id: 'maritime', label: 'Maritime', color: 'bg-cyan-500' },
  { id: 'military', label: 'Military', color: 'bg-purple-500' },
  { id: 'climate', label: 'Climate', color: 'bg-blue-500' },
] as const

const timeRangeOptions = [
  { value: 1, label: '24h' },
  { value: 3, label: '3 days' },
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
]

export default function ControlPanel() {
  const {
    selectedLayers,
    toggleLayer,
    timeRange,
    setTimeRange,
    fetchAllData,
    isLoading
  } = useAppStore()

  const [showLayers, setShowLayers] = useState(false)
  const [showTimeRange, setShowTimeRange] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <div className="h-14 bg-wm-panel border-b border-wm-border flex items-center justify-between px-4">
      {/* Left: Layer Controls */}
      <div className="flex items-center gap-3">
        {/* Layer Toggle */}
        <div className="relative">
          <button
            onClick={() => setShowLayers(!showLayers)}
            className="flex items-center gap-2 px-3 py-1.5 bg-wm-bg rounded-lg hover:bg-wm-border transition-colors"
          >
            <Layers className="w-4 h-4 text-gray-400" />
            <span className="text-sm">Layers</span>
            <span className="text-xs bg-wm-accent/20 text-wm-accent px-1.5 rounded">
              {selectedLayers.length}
            </span>
          </button>

          {showLayers && (
            <div className="absolute top-full left-0 mt-2 w-48 bg-wm-panel border border-wm-border rounded-lg shadow-xl z-50 p-2">
              {layerOptions.map((layer) => (
                <button
                  key={layer.id}
                  onClick={() => toggleLayer(layer.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-wm-border transition-colors"
                >
                  <div className={`w-3 h-3 rounded ${
                    selectedLayers.includes(layer.id) ? layer.color : 'bg-gray-600'
                  }`} />
                  <span className="text-sm">{layer.label}</span>
                  {selectedLayers.includes(layer.id) && (
                    <span className="ml-auto text-xs text-wm-accent">ON</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Time Range */}
        <div className="relative">
          <button
            onClick={() => setShowTimeRange(!showTimeRange)}
            className="flex items-center gap-2 px-3 py-1.5 bg-wm-bg rounded-lg hover:bg-wm-border transition-colors"
          >
            <Clock className="w-4 h-4 text-gray-400" />
            <span className="text-sm">
              {timeRangeOptions.find((o) => o.value === timeRange)?.label || '7 days'}
            </span>
          </button>

          {showTimeRange && (
            <div className="absolute top-full left-0 mt-2 w-32 bg-wm-panel border border-wm-border rounded-lg shadow-xl z-50 p-1">
              {timeRangeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => {
                    setTimeRange(option.value)
                    setShowTimeRange(false)
                  }}
                  className={`w-full px-3 py-1.5 text-sm text-left rounded hover:bg-wm-border transition-colors ${
                    timeRange === option.value ? 'text-wm-accent' : ''
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Refresh */}
        <button
          onClick={() => fetchAllData()}
          disabled={isLoading}
          className="p-2 bg-wm-bg rounded-lg hover:bg-wm-border transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Center: Search */}
      <div className="flex-1 max-w-md mx-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search locations, events..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-1.5 bg-wm-bg border border-wm-border rounded-lg text-sm focus:outline-none focus:border-wm-accent transition-colors"
          />
        </div>
      </div>

      {/* Right: Timestamp */}
      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span>
          Last updated: {new Date().toLocaleTimeString()}
        </span>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 bg-wm-success rounded-full pulse-live"></span>
          <span>LIVE</span>
        </div>
      </div>
    </div>
  )
}
