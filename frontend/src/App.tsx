import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import MapView from './components/MapView'
import ControlPanel from './components/ControlPanel'
import DataPanel from './components/DataPanel'
import EventsPanel from './components/EventsPanel'
import StatsPanel from './components/StatsPanel'
import IntelPanel from './components/IntelPanel'
import SettingsPanel from './components/SettingsPanel'
import { useAppStore } from './stores/appStore'

function App() {
  const {
    isLoading,
    fetchAllData
  } = useAppStore()

  useEffect(() => {
    fetchAllData()
    // Refresh data every 5 minutes
    const interval = setInterval(fetchAllData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchAllData])

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-wm-bg">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative">
        {/* Top Control Bar */}
        <ControlPanel />

        {/* Map Container */}
        <div className="flex-1 relative">
          <MapView />

          {/* Overlay Panels */}
          <div className="absolute top-4 right-4 w-96 space-y-4 max-h-[calc(100vh-120px)] overflow-y-auto">
            <Routes>
              <Route path="/" element={<StatsPanel />} />
              <Route path="/conflicts" element={<EventsPanel type="conflicts" />} />
              <Route path="/earthquakes" element={<EventsPanel type="earthquakes" />} />
              <Route path="/fires" element={<EventsPanel type="fires" />} />
              <Route path="/maritime" element={<EventsPanel type="maritime" />} />
              <Route path="/military" element={<EventsPanel type="military" />} />
              <Route path="/markets" element={<DataPanel type="markets" />} />
              <Route path="/cyber" element={<DataPanel type="cyber" />} />
              <Route path="/infrastructure" element={<DataPanel type="infrastructure" />} />
              <Route path="/intel" element={<IntelPanel />} />
              <Route path="/settings" element={<SettingsPanel />} />
            </Routes>
          </div>
        </div>

        {/* Bottom Data Strip */}
        <div className="h-16 bg-wm-panel border-t border-wm-border flex items-center px-4 gap-6">
          <DataStrip />
        </div>
      </div>

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="text-wm-accent animate-pulse">Loading data...</div>
        </div>
      )}
    </div>
  )
}

function DataStrip() {
  const { stats, marketQuotes } = useAppStore()

  return (
    <>
      <div className="flex items-center gap-2">
        <span className="text-gray-400 text-xs">CONFLICTS</span>
        <span className="text-lg font-bold text-wm-danger">{stats.conflicts || 0}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-gray-400 text-xs">EARTHQUAKES</span>
        <span className="text-lg font-bold text-wm-warning">{stats.earthquakes || 0}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-gray-400 text-xs">FIRES</span>
        <span className="text-lg font-bold text-orange-500">{stats.fires || 0}</span>
      </div>
      <div className="w-px h-8 bg-wm-border mx-2" />
      {marketQuotes.slice(0, 4).map((quote) => (
        <div key={quote.symbol} className="flex items-center gap-1">
          <span className="text-gray-400 text-xs">{quote.symbol}</span>
          <span className={`text-sm font-medium ${
            quote.change >= 0 ? 'text-wm-success' : 'text-wm-danger'
          }`}>
            {quote.change >= 0 ? '+' : ''}{quote.change_percent?.toFixed(2)}%
          </span>
        </div>
      ))}
    </>
  )
}

export default App
