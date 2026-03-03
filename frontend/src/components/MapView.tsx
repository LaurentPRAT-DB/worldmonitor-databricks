import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import { useAppStore } from '../stores/appStore'

// Color palette for different vessels - visually distinct colors
const VESSEL_COLORS = [
  '#06b6d4', // cyan
  '#f59e0b', // amber
  '#10b981', // emerald
  '#8b5cf6', // violet
  '#ef4444', // red
  '#3b82f6', // blue
  '#ec4899', // pink
  '#84cc16', // lime
  '#f97316', // orange
  '#6366f1', // indigo
  '#14b8a6', // teal
  '#a855f7', // purple
  '#eab308', // yellow
  '#22c55e', // green
  '#e11d48', // rose
]

// Get consistent color for a vessel based on its index
function getVesselColor(_mmsi: string, index: number): string {
  // Use index for consistent color assignment across the session
  return VESSEL_COLORS[index % VESSEL_COLORS.length]
}

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const markersRef = useRef<maplibregl.Marker[]>([])
  const routePopupRef = useRef<maplibregl.Popup | null>(null)
  const routeSourceId = 'vessel-routes'
  const routeLayerId = 'vessel-routes-layer'
  const arrowSourceId = 'vessel-route-arrows'
  const arrowLayerId = 'vessel-routes-arrows'
  const routePointsLayerId = 'vessel-routes-points'

  const {
    conflicts,
    earthquakes,
    wildfires,
    vessels,
    vesselRoutes,
    selectedLayers,
    showVesselRoutes,
    fetchVesselRoutes
  } = useAppStore()

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'carto-dark': {
            type: 'raster',
            tiles: [
              'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
              'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
              'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
            ],
            tileSize: 256,
            attribution: '&copy; OpenStreetMap, &copy; CARTO',
          },
        },
        layers: [
          {
            id: 'carto-dark-layer',
            type: 'raster',
            source: 'carto-dark',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: [0, 20],
      zoom: 2,
      minZoom: 1.5,
      maxZoom: 18,
    })

    map.current.addControl(new maplibregl.NavigationControl(), 'bottom-right')
    map.current.addControl(new maplibregl.ScaleControl(), 'bottom-left')

    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [])

  // Update markers when data changes
  useEffect(() => {
    if (!map.current) return

    // Clear existing markers
    markersRef.current.forEach((m) => m.remove())
    markersRef.current = []

    // Add conflict markers
    if (selectedLayers.includes('conflicts')) {
      conflicts.forEach((event) => {
        if (isValidCoordinate(event.latitude, event.longitude)) {
          const el = createMarkerElement('conflict', event.fatalities)
          const popup = new maplibregl.Popup({ offset: 25, closeButton: false })
            .setHTML(`
              <div class="text-xs">
                <div class="font-bold text-red-400">${event.event_type}</div>
                <div class="text-gray-300">${event.location}, ${event.country}</div>
                <div class="text-gray-400">${event.event_date}</div>
                ${event.fatalities > 0 ? `<div class="text-red-400">Fatalities: ${event.fatalities}</div>` : ''}
              </div>
            `)

          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([event.longitude, event.latitude])
            .setPopup(popup)
            .addTo(map.current!)

          markersRef.current.push(marker)
        }
      })
    }

    // Add earthquake markers
    if (selectedLayers.includes('earthquakes')) {
      earthquakes.forEach((eq) => {
        if (isValidCoordinate(eq.latitude, eq.longitude)) {
          const el = createMarkerElement('earthquake', eq.magnitude)
          const popup = new maplibregl.Popup({ offset: 25, closeButton: false })
            .setHTML(`
              <div class="text-xs">
                <div class="font-bold text-yellow-400">M${eq.magnitude?.toFixed(1) || '?'} Earthquake</div>
                <div class="text-gray-300">${eq.place || 'Unknown location'}</div>
                <div class="text-gray-400">Depth: ${eq.depth?.toFixed(1) || '?'} km</div>
                ${eq.alert ? `<div class="text-orange-400">Alert: ${eq.alert}</div>` : ''}
              </div>
            `)

          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([eq.longitude, eq.latitude])
            .setPopup(popup)
            .addTo(map.current!)

          markersRef.current.push(marker)
        }
      })
    }

    // Add wildfire markers
    if (selectedLayers.includes('fires')) {
      // Filter fires - confidence is 'h' (high), 'n' (nominal), or 'l' (low)
      // Show high and nominal confidence fires
      const filteredFires = wildfires.filter(
        (f) => f.confidence === 'h' || f.confidence === 'n' || f.confidence === 'high' || f.confidence === 'nominal'
      )
      // If no fires match the filter, show all fires (backwards compatibility)
      const firesToShow = filteredFires.length > 0 ? filteredFires : wildfires
      firesToShow.slice(0, 500).forEach((fire) => {
        if (isValidCoordinate(fire.latitude, fire.longitude)) {
          const el = createMarkerElement('fire', fire.brightness)
          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([fire.longitude, fire.latitude])
            .addTo(map.current!)

          markersRef.current.push(marker)
        }
      })
    }

    // Add vessel markers
    if (selectedLayers.includes('maritime')) {
      vessels.forEach((vessel) => {
        if (isValidCoordinate(vessel.latitude, vessel.longitude)) {
          const el = createMarkerElement('vessel', 1)
          const popup = new maplibregl.Popup({ offset: 25, closeButton: false })
            .setHTML(`
              <div class="text-xs">
                <div class="font-bold text-cyan-400">${vessel.name || vessel.mmsi}</div>
                <div class="text-gray-300">${vessel.vessel_type}</div>
                <div class="text-gray-400">Speed: ${vessel.speed?.toFixed(1) || '?'} kn</div>
                <div class="text-gray-400">Flag: ${vessel.flag}</div>
              </div>
            `)

          const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([vessel.longitude, vessel.latitude])
            .setPopup(popup)
            .addTo(map.current!)

          markersRef.current.push(marker)
        }
      })
    }
  }, [conflicts, earthquakes, wildfires, vessels, selectedLayers])

  // Fetch routes immediately when showVesselRoutes becomes true
  useEffect(() => {
    if (showVesselRoutes && Object.keys(vesselRoutes).length === 0) {
      fetchVesselRoutes()
    }
  }, [showVesselRoutes, vesselRoutes, fetchVesselRoutes])

  // Update vessel routes when data changes
  useEffect(() => {
    if (!map.current) return

    const currentMap = map.current

    // Create arrow image for a specific color
    const createArrowImage = async (color: string, imageId: string) => {
      if (!currentMap.hasImage(imageId)) {
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
          <polygon points="4,8 18,12 4,16 8,12" fill="${color}" stroke="#ffffff" stroke-width="1.5"/>
        </svg>`
        const svgBlob = new Blob([svg], { type: 'image/svg+xml' })
        const url = URL.createObjectURL(svgBlob)

        const img = new Image(24, 24)
        img.src = url

        await new Promise<void>((resolve) => {
          img.onload = () => {
            if (!currentMap.hasImage(imageId)) {
              currentMap.addImage(imageId, img)
            }
            URL.revokeObjectURL(url)
            resolve()
          }
          img.onerror = () => {
            URL.revokeObjectURL(url)
            resolve()
          }
        })
      }
    }

    // Wait for map to be loaded
    const updateRoutes = async () => {
      // Remove existing layers and sources
      if (currentMap.getLayer(routePointsLayerId)) {
        currentMap.removeLayer(routePointsLayerId)
      }
      if (currentMap.getLayer(arrowLayerId)) {
        currentMap.removeLayer(arrowLayerId)
      }
      if (currentMap.getLayer(routeLayerId)) {
        currentMap.removeLayer(routeLayerId)
      }
      if (currentMap.getSource(routeSourceId)) {
        currentMap.removeSource(routeSourceId)
      }
      if (currentMap.getSource(arrowSourceId)) {
        currentMap.removeSource(arrowSourceId)
      }

      // Clean up popup
      if (routePopupRef.current) {
        routePopupRef.current.remove()
        routePopupRef.current = null
      }

      // Only add routes if maritime layer is selected and routes are enabled
      if (!selectedLayers.includes('maritime') || !showVesselRoutes || Object.keys(vesselRoutes).length === 0) {
        return
      }

      // Create vessel name and color lookup by MMSI
      const vesselNameMap: Record<string, string> = {}
      const vesselColorMap: Record<string, string> = {}
      const mmsiList = Object.keys(vesselRoutes)

      vessels.forEach(v => {
        vesselNameMap[v.mmsi] = v.name || v.mmsi
      })

      // Assign colors to vessels
      mmsiList.forEach((mmsi, index) => {
        vesselColorMap[mmsi] = getVesselColor(mmsi, index)
      })

      // Create arrow images for each color used
      const uniqueColors = [...new Set(Object.values(vesselColorMap))]
      for (const color of uniqueColors) {
        await createArrowImage(color, `arrow-${color.replace('#', '')}`)
      }

      // Convert routes to GeoJSON LineString features with color property
      const lineFeatures = mmsiList.map((mmsi) => {
        const points = vesselRoutes[mmsi]
        const color = vesselColorMap[mmsi]
        return {
          type: 'Feature' as const,
          properties: {
            mmsi,
            vesselName: vesselNameMap[mmsi] || mmsi,
            color
          },
          geometry: {
            type: 'LineString' as const,
            coordinates: points.map(p => [p.longitude, p.latitude])
          }
        }
      })

      // Create arrow point features - one every 10 points (10 * 4h = 40h intervals)
      const arrowFeatures: GeoJSON.Feature[] = []
      mmsiList.forEach((mmsi) => {
        const points = vesselRoutes[mmsi]
        const color = vesselColorMap[mmsi]
        const vesselName = vesselNameMap[mmsi] || mmsi

        // Place an arrow every 10 points
        for (let i = 10; i < points.length; i += 10) {
          const p = points[i]
          const prevP = points[i - 1]

          // Calculate bearing from previous point to current point
          const bearing = calculateBearing(
            prevP.latitude, prevP.longitude,
            p.latitude, p.longitude
          )

          arrowFeatures.push({
            type: 'Feature',
            properties: {
              mmsi,
              vesselName,
              color,
              bearing,
              arrowImage: `arrow-${color.replace('#', '')}`
            },
            geometry: {
              type: 'Point',
              coordinates: [p.longitude, p.latitude]
            }
          })
        }
      })

      // Create point features for hover interaction (sample every few points for performance)
      const pointFeatures: GeoJSON.Feature[] = []
      mmsiList.forEach((mmsi) => {
        const points = vesselRoutes[mmsi]
        const vesselName = vesselNameMap[mmsi] || mmsi
        const color = vesselColorMap[mmsi]

        // Sample points - take every 3rd point to reduce density
        points.forEach((p, idx) => {
          if (idx % 3 === 0 || idx === points.length - 1) {
            pointFeatures.push({
              type: 'Feature',
              properties: {
                mmsi,
                vesselName,
                color,
                recordedAt: p.recorded_at,
                speed: p.speed,
                course: p.course
              },
              geometry: {
                type: 'Point',
                coordinates: [p.longitude, p.latitude]
              }
            })
          }
        })
      })

      // Add GeoJSON source for lines
      currentMap.addSource(routeSourceId, {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [...lineFeatures, ...pointFeatures]
        }
      })

      // Add separate source for arrows (point-based)
      currentMap.addSource(arrowSourceId, {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: arrowFeatures
        }
      })

      // Add line layer with data-driven color
      currentMap.addLayer({
        id: routeLayerId,
        type: 'line',
        source: routeSourceId,
        filter: ['==', '$type', 'LineString'],
        layout: {
          'line-join': 'round',
          'line-cap': 'round'
        },
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 2.5,
          'line-opacity': 0.8
        }
      })

      // Add arrow symbols as points with rotation based on bearing
      currentMap.addLayer({
        id: arrowLayerId,
        type: 'symbol',
        source: arrowSourceId,
        layout: {
          'icon-image': ['get', 'arrowImage'],
          'icon-size': 0.9,
          'icon-rotate': ['get', 'bearing'],
          'icon-rotation-alignment': 'map',
          'icon-allow-overlap': true,
          'icon-ignore-placement': true
        }
      })

      // Add invisible points layer for hover interaction
      currentMap.addLayer({
        id: routePointsLayerId,
        type: 'circle',
        source: routeSourceId,
        filter: ['==', '$type', 'Point'],
        paint: {
          'circle-radius': 8,
          'circle-color': 'transparent',
          'circle-stroke-width': 0
        }
      })

      // Create popup for hover
      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        className: 'route-hover-popup'
      })
      routePopupRef.current = popup

      // Add hover handlers
      currentMap.on('mouseenter', routePointsLayerId, (e) => {
        currentMap.getCanvas().style.cursor = 'pointer'

        if (e.features && e.features.length > 0) {
          const feature = e.features[0]
          const coords = (feature.geometry as GeoJSON.Point).coordinates.slice() as [number, number]
          const props = feature.properties as {
            vesselName: string
            color: string
            recordedAt: string | null
            speed: number
            course: number
          }

          // Format the date
          let dateStr = 'Unknown'
          if (props.recordedAt) {
            const date = new Date(props.recordedAt)
            dateStr = date.toLocaleString('en-US', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })
          }

          popup
            .setLngLat(coords)
            .setHTML(`
              <div class="text-xs">
                <div class="font-bold" style="color: ${props.color}">${props.vesselName}</div>
                <div class="text-gray-300">${dateStr}</div>
                <div class="text-gray-400">${props.speed?.toFixed(1) || '?'} kn · ${props.course?.toFixed(0) || '?'}°</div>
              </div>
            `)
            .addTo(currentMap)
        }
      })

      currentMap.on('mouseleave', routePointsLayerId, () => {
        currentMap.getCanvas().style.cursor = ''
        popup.remove()
      })
    }

    if (currentMap.loaded()) {
      updateRoutes()
    } else {
      currentMap.on('load', updateRoutes)
    }
  }, [vesselRoutes, vessels, selectedLayers, showVesselRoutes])

// Calculate bearing between two points in degrees
function calculateBearing(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const toRad = (deg: number) => deg * Math.PI / 180
  const toDeg = (rad: number) => rad * 180 / Math.PI

  const dLon = toRad(lon2 - lon1)
  const lat1Rad = toRad(lat1)
  const lat2Rad = toRad(lat2)

  const y = Math.sin(dLon) * Math.cos(lat2Rad)
  const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) -
            Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon)

  let bearing = toDeg(Math.atan2(y, x))
  return (bearing + 360) % 360
}

  return (
    <div ref={mapContainer} className="w-full h-full" />
  )
}

function createMarkerElement(type: string, intensity: number): HTMLDivElement {
  const el = document.createElement('div')
  el.className = `marker marker-${type}`

  const size = type === 'earthquake'
    ? Math.max(8, Math.min(24, intensity * 4))
    : type === 'fire'
    ? 6
    : type === 'conflict'
    ? Math.max(6, Math.min(16, intensity / 2 + 6))
    : 8

  const colors: Record<string, string> = {
    conflict: 'rgba(239, 68, 68, 0.8)',
    earthquake: 'rgba(234, 179, 8, 0.8)',
    fire: 'rgba(249, 115, 22, 0.8)',
    vessel: 'rgba(6, 182, 212, 0.8)',
    aircraft: 'rgba(147, 51, 234, 0.8)',
  }

  // Use fixed positioning styles to prevent layout issues
  el.style.cssText = `
    width: ${size}px;
    height: ${size}px;
    border-radius: 50%;
    background-color: ${colors[type] || 'rgba(59, 130, 246, 0.8)'};
    border: 1px solid rgba(255, 255, 255, 0.3);
    cursor: pointer;
    box-sizing: border-box;
    pointer-events: auto;
    transition: box-shadow 0.15s ease-in-out;
  `

  // Use box-shadow for hover instead of transform to prevent displacement
  el.addEventListener('mouseenter', () => {
    el.style.boxShadow = `0 0 ${size}px ${size/2}px ${colors[type] || 'rgba(59, 130, 246, 0.6)'}`
  })
  el.addEventListener('mouseleave', () => {
    el.style.boxShadow = 'none'
  })

  return el
}

function isValidCoordinate(lat: number, lng: number): boolean {
  return (
    typeof lat === 'number' &&
    typeof lng === 'number' &&
    !isNaN(lat) &&
    !isNaN(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180
  )
}
