import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import { useAppStore } from '../stores/appStore'

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const markersRef = useRef<maplibregl.Marker[]>([])
  const routeSourceId = 'vessel-routes'
  const routeLayerId = 'vessel-routes-layer'

  const {
    conflicts,
    earthquakes,
    wildfires,
    vessels,
    vesselRoutes,
    selectedLayers,
    showVesselRoutes
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
      // Cluster fires for performance - show only high confidence
      const highConfidenceFires = wildfires.filter((f) => f.confidence >= 80)
      highConfidenceFires.slice(0, 500).forEach((fire) => {
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

  // Update vessel routes when data changes
  useEffect(() => {
    if (!map.current) return

    const currentMap = map.current

    // Wait for map to be loaded
    const updateRoutes = () => {
      // Remove existing layer and source
      if (currentMap.getLayer(routeLayerId)) {
        currentMap.removeLayer(routeLayerId)
      }
      if (currentMap.getSource(routeSourceId)) {
        currentMap.removeSource(routeSourceId)
      }

      // Only add routes if maritime layer is selected and routes are enabled
      if (!selectedLayers.includes('maritime') || !showVesselRoutes || Object.keys(vesselRoutes).length === 0) {
        return
      }

      // Convert routes to GeoJSON LineString features
      const features = Object.entries(vesselRoutes).map(([mmsi, points]) => ({
        type: 'Feature' as const,
        properties: { mmsi },
        geometry: {
          type: 'LineString' as const,
          coordinates: points.map(p => [p.longitude, p.latitude])
        }
      }))

      // Add GeoJSON source
      currentMap.addSource(routeSourceId, {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features
        }
      })

      // Add line layer
      currentMap.addLayer({
        id: routeLayerId,
        type: 'line',
        source: routeSourceId,
        layout: {
          'line-join': 'round',
          'line-cap': 'round'
        },
        paint: {
          'line-color': 'rgba(6, 182, 212, 0.5)',
          'line-width': 2,
          'line-opacity': 0.7
        }
      })
    }

    if (currentMap.loaded()) {
      updateRoutes()
    } else {
      currentMap.on('load', updateRoutes)
    }
  }, [vesselRoutes, selectedLayers, showVesselRoutes])

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
