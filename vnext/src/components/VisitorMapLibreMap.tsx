import { useEffect, useMemo, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  getRouteMapLeg,
  getRouteMapPlan,
  type NeshanRouteMapPlanResponse,
} from '../api/neginApi'

type Props = {
  routeId: string | null
  mode: 'sales' | 'shortest'
  selectedCustomerId: string
  recenterNonce: number
  onSelectCustomer: (id: string) => void
  onPrimaryCustomer: (id: string) => void
  onNotice: (message: string) => void
}

type Pos = { latitude: number; longitude: number }

const ROUTE_CLUSTER_RADIUS_KM = 200
const MAX_ROUTE_GPS_DISTANCE_KM = 200

function createBasemapStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: 'ط¢آ© OpenStreetMap contributors',
      },
    },
    layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
  }
}

function geo(): Promise<Pos | null> {
  if (!navigator.geolocation) return Promise.resolve(null)

  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        }),
      () => resolve(null),
      { enableHighAccuracy: true, maximumAge: 15000, timeout: 15000 },
    )
  })
}

function decodePolyline(encoded: string) {
  const coordinates: Array<[number, number]> = []
  let index = 0
  let latitude = 0
  let longitude = 0

  while (index < encoded.length) {
    let shift = 0
    let result = 0
    let byte = 0

    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 31) << shift
      shift += 5
    } while (byte >= 32)

    latitude += result & 1 ? ~(result >> 1) : result >> 1
    shift = 0
    result = 0

    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 31) << shift
      shift += 5
    } while (byte >= 32)

    longitude += result & 1 ? ~(result >> 1) : result >> 1
    coordinates.push([longitude / 1e5, latitude / 1e5])
  }

  return coordinates
}

function distanceKm(a: Pos, b: Pos) {
  const radius = 6371
  const toRad = (value: number) => (value * Math.PI) / 180
  const dLat = toRad(b.latitude - a.latitude)
  const dLon = toRad(b.longitude - a.longitude)
  const latitude1 = toRad(a.latitude)
  const latitude2 = toRad(b.latitude)
  const haversine =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(latitude1) * Math.cos(latitude2) * Math.sin(dLon / 2) ** 2

  return 2 * radius * Math.asin(Math.min(1, Math.sqrt(haversine)))
}

function routeCluster(plan: NeshanRouteMapPlanResponse) {
  const located = plan.ordered_customers.filter(
    (customer) => customer.latitude != null && customer.longitude != null,
  )

  if (located.length <= 2) return located

  let best = located
  let bestCount = 0

  for (const anchor of located) {
    const origin = {
      latitude: Number(anchor.latitude),
      longitude: Number(anchor.longitude),
    }
    const nearby = located.filter(
      (customer) =>
        distanceKm(origin, {
          latitude: Number(customer.latitude),
          longitude: Number(customer.longitude),
        }) <= ROUTE_CLUSTER_RADIUS_KM,
    )

    if (nearby.length > bestCount) {
      best = nearby
      bestCount = nearby.length
    }
  }

  return bestCount >= Math.max(2, Math.ceil(located.length * 0.5)) ? best : located
}

function gpsMatchesPlan(position: Pos, plan: NeshanRouteMapPlanResponse) {
  return routeCluster(plan).some(
    (customer) =>
      distanceKm(position, {
        latitude: Number(customer.latitude),
        longitude: Number(customer.longitude),
      }) <= MAX_ROUTE_GPS_DISTANCE_KM,
  )
}

function drawRoute(map: maplibregl.Map, encoded: string) {
  if (!map.isStyleLoaded()) return

  if (map.getLayer('maplibre-route')) map.removeLayer('maplibre-route')
  if (map.getSource('maplibre-route')) map.removeSource('maplibre-route')

  if (!encoded) return
  const coordinates = decodePolyline(encoded)
  if (coordinates.length < 2) return

  map.addSource('maplibre-route', {
    type: 'geojson',
    data: {
      type: 'Feature',
      properties: {},
      geometry: { type: 'LineString', coordinates },
    },
  })

  map.addLayer({
    id: 'maplibre-route',
    type: 'line',
    source: 'maplibre-route',
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': '#e8b64f',
      'line-width': 5,
      'line-opacity': 0.9,
    },
  })
}

export function VisitorMapLibreMap({
  routeId,
  mode,
  selectedCustomerId,
  recenterNonce,
  onSelectCustomer,
  onPrimaryCustomer,
  onNotice,
}: Props) {
  const host = useRef<HTMLDivElement | null>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const markers = useRef<maplibregl.Marker[]>([])
  const selectedIdRef = useRef(selectedCustomerId)
  const selectCustomerRef = useRef(onSelectCustomer)
  const primaryCustomerRef = useRef(onPrimaryCustomer)
  const focusTokenRef = useRef('')

  selectedIdRef.current = selectedCustomerId
  selectCustomerRef.current = onSelectCustomer
  primaryCustomerRef.current = onPrimaryCustomer

  const [plan, setPlan] = useState<NeshanRouteMapPlanResponse | null>(null)
  const [position, setPosition] = useState<Pos | null>(null)
  const [legPolyline, setLegPolyline] = useState('')
  const [error, setError] = useState('')
  const [mapReady, setMapReady] = useState(false)

  const trustedCustomers = useMemo(() => (plan ? routeCluster(plan) : []), [plan])
  const trustedPosition = useMemo(
    () =>
      position &&
      plan &&
      String(plan.route.id) === String(routeId) &&
      gpsMatchesPlan(position, plan)
        ? position
        : null,
    [position, plan, routeId],
  )
  const selected = useMemo(
    () =>
      trustedCustomers.find((customer) => String(customer.id) === selectedCustomerId) ??
      null,
    [trustedCustomers, selectedCustomerId],
  )
  const polyline = legPolyline || plan?.polyline || ''

  useEffect(() => {
    if (!routeId || position || !navigator.geolocation || !navigator.permissions) return

    let cancelled = false

    void navigator.permissions
      .query({ name: 'geolocation' })
      .then((status) => {
        if (cancelled || status.state !== 'granted') return
        return geo().then((nextPosition) => {
          if (!cancelled && nextPosition) setPosition(nextPosition)
        })
      })
      .catch(() => undefined)

    return () => {
      cancelled = true
    }
  }, [routeId, position])

  useEffect(() => {
    if (!routeId) {
      setPlan(null)
      setLegPolyline('')
      return
    }

    let cancelled = false
    setError('')
    setLegPolyline('')

    void getRouteMapPlan(
      routeId,
      mode === 'sales' ? 'sales_priority' : 'shortest',
      trustedPosition,
    )
      .then((nextPlan) => {
        if (cancelled) return
        setPlan(nextPlan)
        const first = routeCluster(nextPlan)[0]
        if (first) primaryCustomerRef.current(String(first.id))
      })
      .catch((reason) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Map plan unavailable')
        }
      })

    return () => {
      cancelled = true
    }
  }, [routeId, mode, trustedPosition])

  useEffect(() => {
    if (!host.current || map.current) return

    const instance = new maplibregl.Map({
      container: host.current,
      style: createBasemapStyle(),
      center: [51.4, 35.7],
      zoom: 10,
    })

    map.current = instance
    instance.addControl(new maplibregl.NavigationControl(), 'top-left')

    const observer = new ResizeObserver(() => {
      window.requestAnimationFrame(() => instance.resize())
    })
    observer.observe(host.current)

    instance.on('load', () => {
      setMapReady(true)
      window.requestAnimationFrame(() => instance.resize())
    })

    instance.on('error', (event: any) => {
      console.warn('[MapLibre map]', event.error?.message ?? 'Map rendering failed')
    })

    return () => {
      observer.disconnect()
      markers.current.forEach((marker) => marker.remove())
      markers.current = []
      instance.remove()
      map.current = null
      setMapReady(false)
    }
  }, [])

  useEffect(() => {
    if (!mapReady || !map.current) return

    markers.current.forEach((marker) => marker.remove())
    markers.current = []

    trustedCustomers.forEach((customer, index) => {
      const element = document.createElement('button')
      element.type = 'button'
      element.className =
        'vr-map-live-marker' +
        (String(customer.id) === selectedIdRef.current ? ' selected' : '')
      element.textContent = String(index + 1)
      element.setAttribute(
        'aria-label',
        String(customer.name || `Customer ${index + 1}`),
      )
      element.setAttribute(
        'aria-pressed',
        String(String(customer.id) === selectedIdRef.current),
      )
      element.dataset.customerId = String(customer.id)
      element.onclick = () => selectCustomerRef.current(String(customer.id))

      markers.current.push(
        new maplibregl.Marker({ element })
          .setLngLat([Number(customer.longitude), Number(customer.latitude)])
          .addTo(map.current!),
      )
    })

    if (trustedPosition) {
      const element = document.createElement('span')
      element.className = 'vr-map-live-seller'
      markers.current.push(
        new maplibregl.Marker({ element })
          .setLngLat([trustedPosition.longitude, trustedPosition.latitude])
          .addTo(map.current),
      )
    }
  }, [mapReady, trustedCustomers, trustedPosition])

  useEffect(() => {
    if (!host.current) return

    host.current
      .querySelectorAll<HTMLElement>('.vr-map-live-marker')
      .forEach((element) => {
        const selectedNow = element.dataset.customerId === selectedCustomerId
        element.classList.toggle('selected', selectedNow)
        element.setAttribute('aria-pressed', String(selectedNow))
      })
  }, [selectedCustomerId, mapReady, trustedCustomers])

  useEffect(() => {
    if (!mapReady || !map.current) return

    const first = trustedCustomers[0]
    const focus =
      trustedCustomers.find(
        (customer) => String(customer.id) === selectedCustomerId,
      ) ?? first

    if (!focus) return

    const token = `${routeId ?? ''}|${mode}|${selectedCustomerId}`
    if (focusTokenRef.current === token) return
    focusTokenRef.current = token

    if (
      trustedPosition &&
      distanceKm(trustedPosition, {
        latitude: Number(focus.latitude),
        longitude: Number(focus.longitude),
      }) <= 80
    ) {
      map.current.fitBounds(
        [
          [trustedPosition.longitude, trustedPosition.latitude],
          [Number(focus.longitude), Number(focus.latitude)],
        ],
        { padding: 48, maxZoom: 14, duration: 0 },
      )
    } else {
      map.current.jumpTo({
        center: [Number(focus.longitude), Number(focus.latitude)],
        zoom: 14,
      })
    }
  }, [
    mapReady,
    routeId,
    mode,
    selectedCustomerId,
    trustedCustomers,
    trustedPosition,
  ])

  useEffect(() => {
    if (!mapReady || !map.current) return
    drawRoute(map.current, polyline)
  }, [polyline, mapReady])

  useEffect(() => {
    if (!routeId || !trustedPosition || !selected) {
      setLegPolyline('')
      return
    }

    let cancelled = false

    void getRouteMapLeg(routeId, String(selected.id), trustedPosition)
      .then((response) => {
        if (!cancelled) setLegPolyline(response.polyline || '')
      })
      .catch((reason) => {
        if (!cancelled) {
          onNotice(
            reason instanceof Error ? reason.message : 'Live route unavailable',
          )
        }
      })

    return () => {
      cancelled = true
    }
  }, [routeId, trustedPosition, selected, onNotice])

  useEffect(() => {
    if (!recenterNonce) return

    let cancelled = false

    void geo().then((nextPosition) => {
      if (cancelled) return

      if (!nextPosition) {
        onNotice('ط·آ¯ط·آ³ط·ع¾ط·آ±ط·آ³ط؛إ’ GPS ط·آ¨ط·آ±ط¸â€ڑط·آ±ط·آ§ط·آ± ط¸â€ ط·آ´ط·آ¯.')
        return
      }

      setPosition(nextPosition)

      if (!plan || gpsMatchesPlan(nextPosition, plan)) {
        map.current?.flyTo({
          center: [nextPosition.longitude, nextPosition.latitude],
          zoom: 14,
          duration: 650,
          essential: true,
        })
      } else {
        onNotice('ط¸â€¦ط¸ث†ط¸â€ڑط·آ¹ط؛إ’ط·ع¾ GPS ط·آ¨ط·آ§ ط¸â€¦ط·آ­ط·آ¯ط¸ث†ط·آ¯ط¸â€، ط¸â€¦ط·آ³ط؛إ’ط·آ± ط·آ§ط¸â€ ط·ع¾ط·آ®ط·آ§ط·آ¨أ¢â‚¬إ’ط·آ´ط·آ¯ط¸â€، ط¸â€،ط¸â€¦أ¢â‚¬إ’ط·آ®ط¸ث†ط·آ§ط¸â€ ط؛إ’ ط¸â€ ط·آ¯ط·آ§ط·آ±ط·آ¯.')
      }
    })

    return () => {
      cancelled = true
    }
  }, [recenterNonce, onNotice, plan])

  return (
    <div className="vr-map-live-shell">
      <div
        ref={host}
        className="vr-map-live"
        aria-label="ط¸â€ ط¸â€ڑط·آ´ط¸â€، ط·آ²ط¸â€ ط·آ¯ط¸â€، ط¸â€¦ط·آ³ط؛إ’ط·آ± ط¸ظ¾ط·آ±ط¸ث†ط·آ´"
      />
      {!plan && !error ? (
        <span className="vr-map-live-state">ط·آ¯ط·آ± ط·آ­ط·آ§ط¸â€‍ ط·آ¨ط·آ§ط·آ±ط¹آ¯ط·آ°ط·آ§ط·آ±ط؛إ’ ط¸â€ ط¸â€ڑط·آ´ط¸â€،أ¢â‚¬آ¦</span>
      ) : null}
      {error ? (
        <button
          type="button"
          className="vr-map-live-state error"
          onClick={() => onNotice(error)}
        >
          ط¸â€ ط¸â€ڑط·آ´ط¸â€، ط·آ¯ط·آ± ط·آ¯ط·آ³ط·ع¾ط·آ±ط·آ³ ط¸â€ ط؛إ’ط·آ³ط·ع¾
        </button>
      ) : null}
    </div>
  )
}
