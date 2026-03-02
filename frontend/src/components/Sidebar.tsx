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

const navItems = [
  { path: '/', icon: Globe, label: 'Overview', color: 'text-blue-400' },
  { path: '/conflicts', icon: Crosshair, label: 'Conflicts', color: 'text-red-400' },
  { path: '/earthquakes', icon: Activity, label: 'Seismic', color: 'text-yellow-400' },
  { path: '/fires', icon: Flame, label: 'Wildfires', color: 'text-orange-400' },
  { path: '/maritime', icon: Ship, label: 'Maritime', color: 'text-cyan-400' },
  { path: '/military', icon: Plane, label: 'Military', color: 'text-purple-400' },
  { path: '/markets', icon: TrendingUp, label: 'Markets', color: 'text-green-400' },
  { path: '/cyber', icon: Shield, label: 'Cyber', color: 'text-pink-400' },
  { path: '/infrastructure', icon: Wifi, label: 'Infra', color: 'text-indigo-400' },
  { path: '/intel', icon: Brain, label: 'Intel', color: 'text-amber-400' },
]

export default function Sidebar() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

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
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                    isActive
                      ? 'bg-wm-accent/20 text-white'
                      : 'text-gray-400 hover:bg-wm-border hover:text-white'
                  }`}
                >
                  <item.icon className={`w-5 h-5 ${isActive ? item.color : ''}`} />
                  {!collapsed && (
                    <span className="text-sm font-medium">{item.label}</span>
                  )}
                </Link>
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
