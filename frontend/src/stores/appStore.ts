import { create } from 'zustand'

interface ConflictEvent {
  id: string
  event_date: string
  event_type: string
  country: string
  location: string
  latitude: number
  longitude: number
  fatalities: number
  actors: string[]
  notes: string
}

interface Earthquake {
  id: string
  time: number
  latitude: number
  longitude: number
  depth: number
  magnitude: number
  place: string
  alert: string | null
}

interface Wildfire {
  id: string
  latitude: number
  longitude: number
  brightness: number
  confidence: number
  acq_date: string
}

interface Vessel {
  mmsi: string
  name: string
  vessel_type: string
  latitude: number
  longitude: number
  speed: number
  course: number
  flag: string
}

interface MarketQuote {
  symbol: string
  name: string
  price: number
  change: number
  change_percent: number
  asset_type: string
}

interface CyberThreat {
  id: string
  ioc_type: string
  ioc_value: string
  threat_type: string
  malware_family: string | null
  confidence: number
  source: string
}

interface ServiceStatus {
  service: string
  status: string
  last_checked: number
  response_time_ms: number | null
  url: string
}

interface RiskScore {
  country_code: string
  country_name: string
  overall_risk: number
  political_risk: number
  economic_risk: number
  security_risk: number
  climate_risk: number
}

interface Stats {
  conflicts: number
  earthquakes: number
  fires: number
  vessels: number
  aircraft: number
  cyberThreats: number
}

type LayerType = 'conflicts' | 'earthquakes' | 'fires' | 'maritime' | 'military' | 'climate'

interface AppState {
  // Data
  conflicts: ConflictEvent[]
  earthquakes: Earthquake[]
  wildfires: Wildfire[]
  vessels: Vessel[]
  marketQuotes: MarketQuote[]
  cyberThreats: CyberThreat[]
  serviceStatuses: ServiceStatus[]
  riskScores: RiskScore[]
  stats: Stats

  // UI State
  isLoading: boolean
  selectedLayers: LayerType[]
  selectedCountry: string | null
  timeRange: number // days

  // Actions
  fetchAllData: () => Promise<void>
  fetchConflicts: () => Promise<void>
  fetchEarthquakes: () => Promise<void>
  fetchWildfires: () => Promise<void>
  fetchMarkets: () => Promise<void>
  fetchCyberThreats: () => Promise<void>
  fetchInfrastructure: () => Promise<void>
  fetchRiskScores: () => Promise<void>
  toggleLayer: (layer: LayerType) => void
  setTimeRange: (days: number) => void
  setSelectedCountry: (code: string | null) => void
}

const API_BASE = '/api'

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  conflicts: [],
  earthquakes: [],
  wildfires: [],
  vessels: [],
  marketQuotes: [],
  cyberThreats: [],
  serviceStatuses: [],
  riskScores: [],
  stats: {
    conflicts: 0,
    earthquakes: 0,
    fires: 0,
    vessels: 0,
    aircraft: 0,
    cyberThreats: 0,
  },
  isLoading: false,
  selectedLayers: ['conflicts', 'earthquakes', 'fires'],
  selectedCountry: null,
  timeRange: 7,

  // Fetch all data
  fetchAllData: async () => {
    set({ isLoading: true })
    await Promise.all([
      get().fetchConflicts(),
      get().fetchEarthquakes(),
      get().fetchWildfires(),
      get().fetchMarkets(),
      get().fetchCyberThreats(),
      get().fetchInfrastructure(),
      get().fetchRiskScores(),
    ])
    set({ isLoading: false })
  },

  // Fetch conflict events from ACLED
  fetchConflicts: async () => {
    try {
      const { timeRange } = get()
      const end = Date.now()
      const start = end - timeRange * 24 * 60 * 60 * 1000
      const res = await fetch(`${API_BASE}/list-acled-events?start=${start}&end=${end}`)
      if (res.ok) {
        const data = await res.json()
        set({
          conflicts: data.events,
          stats: { ...get().stats, conflicts: data.total },
        })
      }
    } catch (e) {
      console.error('Failed to fetch conflicts:', e)
    }
  },

  // Fetch earthquakes from USGS
  fetchEarthquakes: async () => {
    try {
      const { timeRange } = get()
      const end = Date.now()
      const start = end - timeRange * 24 * 60 * 60 * 1000
      const res = await fetch(`${API_BASE}/list-earthquakes?start=${start}&end=${end}&min_magnitude=4.0`)
      if (res.ok) {
        const data = await res.json()
        // Map response to expected format
        const earthquakes = data.earthquakes.map((eq: any) => ({
          id: eq.id,
          time: eq.occurred_at,
          latitude: eq.location.latitude,
          longitude: eq.location.longitude,
          depth: eq.location.depth,
          magnitude: eq.magnitude,
          place: eq.place,
          alert: eq.alert_level,
        }))
        set({
          earthquakes,
          stats: { ...get().stats, earthquakes: data.total },
        })
      }
    } catch (e) {
      console.error('Failed to fetch earthquakes:', e)
    }
  },

  // Fetch wildfires from NASA FIRMS
  fetchWildfires: async () => {
    try {
      const res = await fetch(`${API_BASE}/list-fire-detections`)
      if (res.ok) {
        const data = await res.json()
        // Map response to expected format
        const wildfires = (data.fires || []).map((fire: any) => ({
          id: fire.fire_id || `${fire.latitude}_${fire.longitude}`,
          latitude: fire.latitude,
          longitude: fire.longitude,
          brightness: fire.brightness,
          confidence: fire.confidence,
          acq_date: fire.acq_date,
        }))
        set({
          wildfires,
          stats: { ...get().stats, fires: data.total || wildfires.length },
        })
      }
    } catch (e) {
      console.error('Failed to fetch wildfires:', e)
    }
  },

  // Fetch market data
  fetchMarkets: async () => {
    try {
      const res = await fetch(`${API_BASE}/list-market-quotes`)
      if (res.ok) {
        const data = await res.json()
        set({ marketQuotes: data.quotes || [] })
      }
    } catch (e) {
      console.error('Failed to fetch markets:', e)
    }
  },

  // Fetch cyber threats
  fetchCyberThreats: async () => {
    try {
      const { timeRange } = get()
      const res = await fetch(`${API_BASE}/list-cyber-threats?days_back=${timeRange}`)
      if (res.ok) {
        const data = await res.json()
        set({
          cyberThreats: data.threats,
          stats: { ...get().stats, cyberThreats: data.total },
        })
      }
    } catch (e) {
      console.error('Failed to fetch cyber threats:', e)
    }
  },

  // Fetch infrastructure status
  fetchInfrastructure: async () => {
    try {
      const res = await fetch(`${API_BASE}/list-service-statuses`)
      if (res.ok) {
        const data = await res.json()
        set({ serviceStatuses: data.services })
      }
    } catch (e) {
      console.error('Failed to fetch infrastructure:', e)
    }
  },

  // Fetch risk scores
  fetchRiskScores: async () => {
    try {
      const res = await fetch(`${API_BASE}/risk-scores`)
      if (res.ok) {
        const data = await res.json()
        set({ riskScores: data.scores })
      }
    } catch (e) {
      console.error('Failed to fetch risk scores:', e)
    }
  },

  // Toggle layer visibility
  toggleLayer: (layer: LayerType) => {
    const { selectedLayers } = get()
    if (selectedLayers.includes(layer)) {
      set({ selectedLayers: selectedLayers.filter((l) => l !== layer) })
    } else {
      set({ selectedLayers: [...selectedLayers, layer] })
    }
  },

  // Set time range
  setTimeRange: (days: number) => {
    set({ timeRange: days })
    get().fetchAllData()
  },

  // Set selected country
  setSelectedCountry: (code: string | null) => {
    set({ selectedCountry: code })
  },
}))
