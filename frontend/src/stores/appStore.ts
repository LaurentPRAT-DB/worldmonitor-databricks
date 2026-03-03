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
  confidence: string  // 'h' (high), 'n' (nominal), 'l' (low)
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

interface RoutePoint {
  latitude: number
  longitude: number
  speed: number
  course: number
  recorded_at: string | null
}

interface VesselRoutes {
  [mmsi: string]: RoutePoint[]
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
  vesselRoutes: VesselRoutes
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
  showVesselRoutes: boolean

  // Actions
  fetchAllData: () => Promise<void>
  fetchConflicts: () => Promise<void>
  fetchEarthquakes: () => Promise<void>
  fetchWildfires: () => Promise<void>
  fetchVessels: () => Promise<void>
  fetchVesselRoutes: () => Promise<void>
  fetchMarkets: () => Promise<void>
  fetchCyberThreats: () => Promise<void>
  fetchInfrastructure: () => Promise<void>
  fetchRiskScores: () => Promise<void>
  toggleLayer: (layer: LayerType) => void
  setActiveLayer: (layer: LayerType | null) => void
  setTimeRange: (days: number) => void
  setSelectedCountry: (code: string | null) => void
  toggleVesselRoutes: () => void
}

const API_BASE = '/api'

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  conflicts: [],
  earthquakes: [],
  wildfires: [],
  vessels: [],
  vesselRoutes: {},
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
  showVesselRoutes: false,

  // Fetch all data
  fetchAllData: async () => {
    set({ isLoading: true })
    await Promise.all([
      get().fetchConflicts(),
      get().fetchEarthquakes(),
      get().fetchWildfires(),
      get().fetchVessels(),
      get().fetchMarkets(),
      get().fetchCyberThreats(),
      get().fetchInfrastructure(),
      get().fetchRiskScores(),
    ])
    set({ isLoading: false })
  },

  // Fetch vessel tracking data
  fetchVessels: async () => {
    try {
      const res = await fetch(`${API_BASE}/list-vessels`)
      if (res.ok) {
        const data = await res.json()
        // Map response to expected format
        const vessels = (data.vessels || []).map((v: any) => ({
          mmsi: v.mmsi,
          name: v.name || v.mmsi,
          vessel_type: v.ship_type === 60 ? 'Passenger' : v.ship_type === 70 ? 'Cargo' : v.ship_type === 80 ? 'Tanker' : 'Other',
          latitude: v.position?.latitude || v.latitude,
          longitude: v.position?.longitude || v.longitude,
          speed: v.speed || 0,
          course: v.course || 0,
          flag: v.flag_country || 'Unknown',
        }))
        set({
          vessels,
          stats: { ...get().stats, vessels: data.total || vessels.length },
        })
      }
    } catch (e) {
      console.error('Failed to fetch vessels:', e)
    }
  },

  // Fetch vessel route history
  fetchVesselRoutes: async () => {
    try {
      const { timeRange } = get()
      // Convert days to hours for API
      const hours = timeRange * 24
      const res = await fetch(`${API_BASE}/routes?hours=${hours}`)
      if (res.ok) {
        const data = await res.json()
        // data.routes is a dict of mmsi -> RoutePoint[]
        set({ vesselRoutes: data.routes || {} })
      }
    } catch (e) {
      console.error('Failed to fetch vessel routes:', e)
    }
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
        // Map response to expected format - API returns nested location object
        const wildfires = (data.fires || []).map((fire: any) => ({
          id: fire.id || fire.fire_id || `${fire.location?.latitude}_${fire.location?.longitude}`,
          latitude: fire.location?.latitude ?? fire.latitude,
          longitude: fire.location?.longitude ?? fire.longitude,
          brightness: fire.brightness || 0,
          confidence: fire.confidence || 'n',
          acq_date: fire.detected_at ? new Date(fire.detected_at).toISOString().split('T')[0] : '',
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

  // Fetch market data (stocks + crypto)
  fetchMarkets: async () => {
    try {
      // Fetch both stocks and crypto in parallel
      const [stocksRes, cryptoRes] = await Promise.all([
        fetch(`${API_BASE}/list-market-quotes`),
        fetch(`${API_BASE}/list-crypto-quotes`),
      ])

      const allQuotes: MarketQuote[] = []

      if (stocksRes.ok) {
        const stocksData = await stocksRes.json()
        const stocks = (stocksData.quotes || []).map((q: any) => ({
          ...q,
          asset_type: 'stock',
        }))
        allQuotes.push(...stocks)
      }

      if (cryptoRes.ok) {
        const cryptoData = await cryptoRes.json()
        const crypto = (cryptoData.quotes || []).map((q: any) => ({
          ...q,
          asset_type: 'crypto',
        }))
        allQuotes.push(...crypto)
      }

      set({ marketQuotes: allQuotes })
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

  // Set active layer (enables only that layer, used by navigation)
  setActiveLayer: (layer: LayerType | null) => {
    if (layer === null) {
      // Overview: show default layers
      set({ selectedLayers: ['conflicts', 'earthquakes', 'fires'] })
    } else {
      // Single view: show only that layer
      set({ selectedLayers: [layer] })
    }
  },

  // Set time range
  setTimeRange: (days: number) => {
    set({ timeRange: days, vesselRoutes: {} })  // Clear routes to refresh
    get().fetchAllData()
    // If routes are enabled, fetch new routes with new time range
    if (get().showVesselRoutes) {
      get().fetchVesselRoutes()
    }
  },

  // Set selected country
  setSelectedCountry: (code: string | null) => {
    set({ selectedCountry: code })
  },

  // Toggle vessel route display
  toggleVesselRoutes: () => {
    const { showVesselRoutes, vesselRoutes } = get()
    if (!showVesselRoutes && Object.keys(vesselRoutes).length === 0) {
      // Fetch routes if not already loaded
      get().fetchVesselRoutes()
    }
    set({ showVesselRoutes: !showVesselRoutes })
  },
}))
