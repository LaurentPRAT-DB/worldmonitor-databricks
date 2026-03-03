import { Link, useLocation } from 'react-router-dom'
import {
  Globe,
  Crosshair,
  Activity,
  Flame,
  Ship,
  Plane,
  TrendingUp,
  Shield,
  Wifi,
  Brain,
  Settings,
  Menu
} from 'lucide-react'
import { useState } from 'react'
import { useAppStore } from '../stores/appStore'

type LayerType = 'conflicts' | 'earthquakes' | 'fires' | 'maritime' | 'military' | 'climate'

const navItems = [
  { path: '/', icon: Globe, label: 'Overview', color: 'text-blue-400', layer: 'overview' as string },
  { path: '/conflicts', icon: Crosshair, label: 'Conflicts', color: 'text-red-400', layer: 'conflicts' as LayerType },
  { path: '/earthquakes', icon: Activity, label: 'Seismic', color: 'text-yellow-400', layer: 'earthquakes' as LayerType },
  { path: '/fires', icon: Flame, label: 'Wildfires', color: 'text-orange-400', layer: 'fires' as LayerType },
  { path: '/maritime', icon: Ship, label: 'Maritime', color: 'text-cyan-400', layer: 'maritime' as LayerType },
  { path: '/military', icon: Plane, label: 'Military', color: 'text-purple-400', layer: 'military' as LayerType },
  { path: '/markets', icon: TrendingUp, label: 'Markets', color: 'text-green-400', layer: undefined },
  { path: '/cyber', icon: Shield, label: 'Cyber', color: 'text-pink-400', layer: undefined },
  { path: '/infrastructure', icon: Wifi, label: 'Infra', color: 'text-indigo-400', layer: undefined },
  { path: '/intel', icon: Brain, label: 'Intel', color: 'text-amber-400', layer: undefined },
]

export default function Sidebar() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const selectedLayers = useAppStore((state) => state.selectedLayers)
  const toggleLayer = useAppStore((state) => state.toggleLayer)

  const handleLayerToggle = (e: React.MouseEvent, layer: LayerType | undefined) => {
    // Toggle the layer on/off when clicking the layer indicator
    if (layer) {
      e.preventDefault() // Prevent navigation when toggling layer
      toggleLayer(layer)
    }
  }

  const isLayerSelected = (layer: string | LayerType | undefined): boolean => {
    if (!layer || layer === 'overview') return false
    return selectedLayers.includes(layer as LayerType)
  }

  return (
    <aside className={`${collapsed ? 'w-16' : 'w-56'} bg-wm-panel border-r border-wm-border flex flex-col transition-all duration-200`}>
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-wm-border">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <Globe className="w-6 h-6 text-wm-accent" />
            <span className="font-bold text-sm">WORLD MONITOR</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 hover:bg-wm-border rounded-lg transition-colors"
        >
          <Menu className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            const layerSelected = isLayerSelected(item.layer)
            const hasLayer = item.layer && item.layer !== 'overview'

            return (
              <li key={item.path}>
                <div className="flex items-center">
                  {/* Layer toggle indicator */}
                  {hasLayer && (
                    <button
                      onClick={(e) => handleLayerToggle(e, item.layer as LayerType)}
                      className={`w-2 h-8 rounded-l transition-all ${
                        layerSelected
                          ? item.color.replace('text-', 'bg-')
                          : 'bg-gray-700 hover:bg-gray-600'
                      }`}
                      title={layerSelected ? `Hide ${item.label} layer` : `Show ${item.label} layer`}
                    />
                  )}
                  {!hasLayer && <div className="w-2" />}

                  {/* Navigation link */}
                  <Link
                    to={item.path}
                    className={`flex-1 flex items-center gap-3 px-3 py-2.5 rounded-r-lg transition-all ${
                      isActive
                        ? 'bg-wm-accent/20 text-white'
                        : 'text-gray-400 hover:bg-wm-border hover:text-white'
                    } ${hasLayer && layerSelected ? 'border-l-0' : ''}`}
                  >
                    <item.icon className={`w-5 h-5 ${layerSelected ? item.color : isActive ? item.color : ''}`} />
                    {!collapsed && (
                      <>
                        <span className="text-sm font-medium flex-1">{item.label}</span>
                        {hasLayer && (
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            layerSelected
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-gray-700 text-gray-500'
                          }`}>
                            {layerSelected ? 'ON' : 'OFF'}
                          </span>
                        )}
                      </>
                    )}
                  </Link>
                </div>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-wm-border">
        <Link
          to="/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-400 hover:bg-wm-border hover:text-white transition-colors"
        >
          <Settings className="w-5 h-5" />
          {!collapsed && <span className="text-sm">Settings</span>}
        </Link>
        {!collapsed && (
          <div className="mt-3 text-xs text-gray-500 px-3">
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 bg-wm-success rounded-full pulse-live"></span>
              <span>Live Data Active</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
