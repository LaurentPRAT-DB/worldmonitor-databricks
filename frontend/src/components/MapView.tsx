import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import { useAppStore } from '../stores/appStore'

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const markersRef = useRef<maplibregl.Marker[]>([])
  const routePopupRef = useRef<maplibregl.Popup | null>(null)
  const routeSourceId = 'vessel-routes'
  const routeLayerId = 'vessel-routes-layer'
  const arrowLayerId = 'vessel-routes-arrows'
  const routePointsLayerId = 'vessel-routes-points'

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

    // Create arrow image if it doesn't exist
    const createArrowImage = async () => {
      if (!currentMap.hasImage('route-arrow')) {
        // Create a larger, more visible arrow SVG with white outline
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
          <polygon points="4,10 24,16 4,22 10,16" fill="#06b6d4" stroke="#ffffff" stroke-width="2"/>
        </svg>`
        const svgBlob = new Blob([svg], { type: 'image/svg+xml' })
        const url = URL.createObjectURL(svgBlob)

        const img = new Image(32, 32)
        img.src = url

        await new Promise<void>((resolve) => {
          img.onload = () => {
            currentMap.addImage('route-arrow', img)
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
      // Remove existing layers and source
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

      // Clean up popup
      if (routePopupRef.current) {
        routePopupRef.current.remove()
        routePopupRef.current = null
      }

      // Only add routes if maritime layer is selected and routes are enabled
      if (!selectedLayers.includes('maritime') || !showVesselRoutes || Object.keys(vesselRoutes).length === 0) {
        return
      }

      // Create arrow image
      await createArrowImage()

      // Create vessel name lookup by MMSI
      const vesselNameMap: Record<string, string> = {}
      vessels.forEach(v => {
        vesselNameMap[v.mmsi] = v.name || v.mmsi
      })

      // Convert routes to GeoJSON LineString features
      const lineFeatures = Object.entries(vesselRoutes).map(([mmsi, points]) => ({
        type: 'Feature' as const,
        properties: {
          mmsi,
          vesselName: vesselNameMap[mmsi] || mmsi
        },
        geometry: {
          type: 'LineString' as const,
          coordinates: points.map(p => [p.longitude, p.latitude])
        }
      }))

      // Create point features for hover interaction (sample every few points for performance)
      const pointFeatures: GeoJSON.Feature[] = []
      Object.entries(vesselRoutes).forEach(([mmsi, points]) => {
        const vesselName = vesselNameMap[mmsi] || mmsi
        // Sample points - take every 3rd point to reduce density
        points.forEach((p, idx) => {
          if (idx % 3 === 0 || idx === points.length - 1) {
            pointFeatures.push({
              type: 'Feature',
              properties: {
                mmsi,
                vesselName,
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

      // Add GeoJSON source with both lines and points
      currentMap.addSource(routeSourceId, {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [...lineFeatures, ...pointFeatures]
        }
      })

      // Add line layer
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
          'line-color': 'rgba(6, 182, 212, 0.5)',
          'line-width': 2,
          'line-opacity': 0.7
        }
      })

      // Add arrow symbols along the route to show direction
      currentMap.addLayer({
        id: arrowLayerId,
        type: 'symbol',
        source: routeSourceId,
        filter: ['==', '$type', 'LineString'],
        layout: {
          'symbol-placement': 'line',
          'symbol-spacing': 80,
          'icon-image': 'route-arrow',
          'icon-size': 0.8,
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
          'icon-rotation-alignment': 'map'
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
                <div class="font-bold text-cyan-400">${props.vesselName}</div>
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
