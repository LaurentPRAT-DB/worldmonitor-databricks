import { useState } from 'react'
import {
  Crosshair,
  Activity,
  Flame,
  Ship,
  Plane,
  ChevronDown,
  ExternalLink
} from 'lucide-react'
import { useAppStore } from '../stores/appStore'
import { format } from 'date-fns'

type EventType = 'conflicts' | 'earthquakes' | 'fires' | 'maritime' | 'military'

interface EventsPanelProps {
  type: EventType
}

export default function EventsPanel({ type }: EventsPanelProps) {
  const { conflicts, earthquakes, wildfires, vessels, militaryFlights, militaryBases } = useAppStore()
  const [expanded, setExpanded] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<string>('date')

  const config = {
    conflicts: {
      title: 'CONFLICT EVENTS',
      icon: Crosshair,
      color: 'text-red-400',
      data: conflicts,
    },
    earthquakes: {
      title: 'SEISMIC ACTIVITY',
      icon: Activity,
      color: 'text-yellow-400',
      data: earthquakes,
    },
    fires: {
      title: 'ACTIVE WILDFIRES',
      icon: Flame,
      color: 'text-orange-400',
      data: wildfires,
    },
    maritime: {
      title: 'VESSEL TRACKING',
      icon: Ship,
      color: 'text-cyan-400',
      data: vessels,
    },
    military: {
      title: 'MILITARY ACTIVITY',
      icon: Plane,
      color: 'text-purple-400',
      data: militaryFlights,
    },
  }

  const { title, icon: Icon, color, data } = config[type]

  return (
    <div className="panel">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-wm-border">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${color}`} />
          <h3 className="text-sm font-medium">{title}</h3>
          <span className="text-xs bg-wm-bg px-2 py-0.5 rounded">{data.length}</span>
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="text-xs bg-wm-bg border border-wm-border rounded px-2 py-1"
        >
          <option value="date">Recent</option>
          <option value="severity">Severity</option>
          <option value="location">Location</option>
        </select>
      </div>

      {/* Event List */}
      <div className="max-h-96 overflow-y-auto">
        {type === 'conflicts' && (
          <ConflictList
            events={conflicts}
            expanded={expanded}
            setExpanded={setExpanded}
          />
        )}
        {type === 'earthquakes' && (
          <EarthquakeList
            events={earthquakes}
            expanded={expanded}
            setExpanded={setExpanded}
          />
        )}
        {type === 'fires' && (
          <FireList fires={wildfires} />
        )}
        {type === 'maritime' && (
          <VesselList vessels={vessels} />
        )}
        {type === 'military' && (
          <MilitaryList flights={militaryFlights} bases={militaryBases} />
        )}
      </div>
    </div>
  )
}

function ConflictList({
  events,
  expanded,
  setExpanded
}: {
  events: any[]
  expanded: string | null
  setExpanded: (id: string | null) => void
}) {
  return (
    <div className="divide-y divide-wm-border">
      {events.slice(0, 50).map((event) => (
        <div
          key={event.id}
          className="p-3 hover:bg-wm-bg/50 cursor-pointer"
          onClick={() => setExpanded(expanded === event.id ? null : event.id)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-red-400">
                  {event.event_type}
                </span>
                {event.fatalities > 0 && (
                  <span className="text-xs bg-red-500/20 text-red-400 px-1.5 rounded">
                    {event.fatalities} killed
                  </span>
                )}
              </div>
              <div className="text-sm mt-1">{event.location}</div>
              <div className="text-xs text-gray-400 mt-0.5">
                {event.country} - {event.event_date}
              </div>
            </div>
            <ChevronDown
              className={`w-4 h-4 text-gray-400 transition-transform ${
                expanded === event.id ? 'rotate-180' : ''
              }`}
            />
          </div>
          {expanded === event.id && (
            <div className="mt-3 pt-3 border-t border-wm-border text-xs text-gray-300">
              <p>{event.notes}</p>
              {event.actors && event.actors.length > 0 && (
                <div className="mt-2">
                  <span className="text-gray-400">Actors: </span>
                  {event.actors.filter(Boolean).join(', ')}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function EarthquakeList({
  events,
  expanded,
  setExpanded
}: {
  events: any[]
  expanded: string | null
  setExpanded: (id: string | null) => void
}) {
  return (
    <div className="divide-y divide-wm-border">
      {events.slice(0, 50).map((eq) => (
        <div
          key={eq.id}
          className="p-3 hover:bg-wm-bg/50 cursor-pointer"
          onClick={() => setExpanded(expanded === eq.id ? null : eq.id)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className={`text-sm font-bold ${getMagnitudeColor(eq.magnitude)}`}>
                  M{eq.magnitude?.toFixed(1)}
                </span>
                {eq.alert && (
                  <span className={`text-xs px-1.5 rounded ${getAlertStyle(eq.alert)}`}>
                    {eq.alert}
                  </span>
                )}
              </div>
              <div className="text-sm mt-1">{eq.place}</div>
              <div className="text-xs text-gray-400 mt-0.5">
                {eq.time ? format(new Date(eq.time), 'MMM d, HH:mm') : 'Unknown'} -
                Depth: {eq.depth?.toFixed(1)} km
              </div>
            </div>
            <ChevronDown
              className={`w-4 h-4 text-gray-400 transition-transform ${
                expanded === eq.id ? 'rotate-180' : ''
              }`}
            />
          </div>
          {expanded === eq.id && (
            <div className="mt-3 pt-3 border-t border-wm-border text-xs">
              <div className="grid grid-cols-2 gap-2 text-gray-400">
                <div>Latitude: {eq.latitude?.toFixed(4)}</div>
                <div>Longitude: {eq.longitude?.toFixed(4)}</div>
                {eq.felt && <div>Felt reports: {eq.felt}</div>}
                {eq.cdi && <div>CDI: {eq.cdi.toFixed(1)}</div>}
              </div>
              {eq.url && (
                <a
                  href={eq.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 mt-2 text-wm-accent hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  View on USGS <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function FireList({ fires }: { fires: any[] }) {
  // Group fires by region (simplified)
  const firesByRegion = fires.reduce((acc, fire) => {
    const region = getRegion(fire.latitude, fire.longitude)
    if (!acc[region]) acc[region] = []
    acc[region].push(fire)
    return acc
  }, {} as Record<string, any[]>)

  return (
    <div className="p-3">
      <div className="grid grid-cols-2 gap-3">
        {(Object.entries(firesByRegion) as [string, any[]][])
          .sort((a, b) => b[1].length - a[1].length)
          .slice(0, 10)
          .map(([region, regionFires]: [string, any[]]) => (
            <div key={region} className="bg-wm-bg rounded p-2">
              <div className="text-xs text-gray-400">{region}</div>
              <div className="text-lg font-bold text-orange-400">
                {regionFires.length}
              </div>
              <div className="text-xs text-gray-500">active fires</div>
            </div>
          ))}
      </div>
      <div className="mt-4 text-xs text-gray-400">
        Total: {fires.length} fire detections in last 24h
      </div>
    </div>
  )
}

function VesselList({ vessels }: { vessels: any[] }) {
  const { selectedVessel, setSelectedVessel } = useAppStore()

  return (
    <div className="divide-y divide-wm-border">
      {vessels.slice(0, 30).map((vessel) => {
        const isSelected = selectedVessel === vessel.mmsi
        return (
          <div
            key={vessel.mmsi}
            className={`p-3 cursor-pointer transition-all ${
              isSelected
                ? 'bg-cyan-500/20 border-l-2 border-cyan-400'
                : 'hover:bg-wm-bg/50 border-l-2 border-transparent'
            }`}
            onClick={() => setSelectedVessel(vessel.mmsi)}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className={`text-sm font-medium ${isSelected ? 'text-cyan-400' : ''}`}>
                  {vessel.name || `MMSI: ${vessel.mmsi}`}
                </div>
                <div className="text-xs text-gray-400">
                  {vessel.vessel_type} - {vessel.flag}
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-cyan-400">
                  {vessel.speed?.toFixed(1)} kn
                </div>
                <div className="text-xs text-gray-400">
                  {vessel.course?.toFixed(0)}°
                </div>
              </div>
            </div>
            {isSelected && (
              <div className="text-xs text-cyan-400/70 mt-1">
                Click again to deselect
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function MilitaryList({ flights, bases }: { flights: any[], bases: any[] }) {
  // Group flights by country
  const flightsByCountry = flights.reduce((acc, flight) => {
    const country = flight.origin_country || 'Unknown'
    if (!acc[country]) acc[country] = []
    acc[country].push(flight)
    return acc
  }, {} as Record<string, any[]>)

  return (
    <div className="p-3 space-y-4">
      {/* Flight Summary by Country */}
      <div>
        <h4 className="text-xs text-gray-400 mb-2">ACTIVE AIRCRAFT BY COUNTRY</h4>
        <div className="grid grid-cols-2 gap-2">
          {(Object.entries(flightsByCountry) as [string, any[]][])
            .sort((a, b) => b[1].length - a[1].length)
            .map(([country, countryFlights]) => (
              <div key={country} className="bg-wm-bg rounded p-2">
                <div className="text-xs text-gray-400">{country}</div>
                <div className="text-lg font-bold text-purple-400">{countryFlights.length}</div>
                <div className="text-xs text-gray-500">aircraft</div>
              </div>
            ))}
        </div>
      </div>

      {/* Active Flights List */}
      <div>
        <h4 className="text-xs text-gray-400 mb-2">ACTIVE FLIGHTS ({flights.length})</h4>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {flights.slice(0, 20).map((flight) => (
            <div key={flight.icao24} className="bg-wm-bg rounded p-2">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-purple-400">
                    {flight.callsign || flight.icao24}
                  </span>
                  <span className="text-xs text-gray-500 ml-2">{flight.origin_country}</span>
                </div>
                <div className="text-xs text-gray-400">
                  {flight.altitude?.toFixed(0) || '?'} ft
                </div>
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {flight.aircraft_type || 'Unknown aircraft'}
                {flight.mission_type && (
                  <span className="text-purple-300 ml-2">• {flight.mission_type}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Military Bases */}
      <div>
        <h4 className="text-xs text-gray-400 mb-2">REGIONAL BASES ({bases.length})</h4>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {bases.map((base) => (
            <div key={base.id} className="bg-wm-bg rounded p-2">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-amber-400">{base.name}</div>
                <span className={`text-xs px-1.5 rounded ${
                  base.status === 'heightened' ? 'bg-orange-500/20 text-orange-400' : 'bg-green-500/20 text-green-400'
                }`}>
                  {base.status}
                </span>
              </div>
              <div className="text-xs text-gray-400">
                {base.country} • {base.base_type.toUpperCase()}
              </div>
              {base.operator && (
                <div className="text-xs text-gray-500">{base.operator}</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Persian Gulf Alert */}
      <div className="bg-orange-500/10 border border-orange-500/30 rounded p-3">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 bg-orange-400 rounded-full animate-pulse" />
          <span className="text-xs font-medium text-orange-400">ELEVATED ALERT - STRAIT OF HORMUZ</span>
        </div>
        <p className="text-xs text-gray-400">
          Iranian naval and air forces conducting increased patrols. IRGC fast boats observed near commercial shipping lanes.
          US 5th Fleet has increased maritime patrol sorties.
        </p>
      </div>
    </div>
  )
}

function getMagnitudeColor(mag: number): string {
  if (mag >= 7) return 'text-red-500'
  if (mag >= 6) return 'text-orange-500'
  if (mag >= 5) return 'text-yellow-500'
  if (mag >= 4) return 'text-yellow-400'
  return 'text-green-400'
}

function getAlertStyle(alert: string): string {
  switch (alert) {
    case 'red':
      return 'bg-red-500/20 text-red-400'
    case 'orange':
      return 'bg-orange-500/20 text-orange-400'
    case 'yellow':
      return 'bg-yellow-500/20 text-yellow-400'
    default:
      return 'bg-green-500/20 text-green-400'
  }
}

function getRegion(lat: number, lon: number): string {
  // Simplified region detection
  if (lat > 50) return 'Northern Hemisphere'
  if (lat < -30) return 'Southern Hemisphere'
  if (lon > 100) return 'Asia-Pacific'
  if (lon < -60) return 'Americas'
  if (lon > 20 && lon < 60) return 'Middle East'
  return 'Africa/Europe'
}
