import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CheckCircle2, LocateFixed, MapPin, Navigation, RefreshCw, Route, Store, Volume2, VolumeX } from 'lucide-react'
import { navigateWithParams } from '../../app/router'
import { AsyncState } from '../../components/AsyncState'
import { Alert, Button, Card, Cluster, KeyValue, PageHeader, ResponsivePageContainer, Stack, StatusBadge } from '../../design-system/v2'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'
import {
  customerDisplayName,
  isReviewMode,
  routeQueryValue,
  type NeshanMapConfigResponse,
  type NeshanRouteLeg,
  type NeshanRouteMapLegResponse,
  type NeshanRouteMapCustomer,
  type NeshanRouteMapPlanResponse,
  type NeshanRouteStep,
  type PrevisitSavedRequestsResponse,
  type SellerCustomer,
  type SellerRouteCustomersResponse,
  type SellerVisitPolicyResponse,
} from './contracts'

type Position = { latitude: number; longitude: number; accuracy: number | null; heading: number | null; timestamp: number }
type MapLibreMarker = { setLngLat(coordinates: [number, number]): MapLibreMarker; addTo(map: MapLibreMap): MapLibreMarker; remove(): void; getElement(): HTMLElement }
type MapLibreMap = {
  on(event: string, listener: (event?: { originalEvent?: unknown; error?: Error }) => void): void
  addControl(control: unknown): void
  remove(): void
  flyTo(options: Record<string, unknown>): void
  easeTo(options: Record<string, unknown>): void
  fitBounds(bounds: [[number, number], [number, number]], options?: Record<string, unknown>): void
  isStyleLoaded(): boolean
  getLayer(id: string): unknown
  removeLayer(id: string): void
  getSource(id: string): unknown
  removeSource(id: string): void
  addSource(id: string, source: Record<string, unknown>): void
  addLayer(layer: Record<string, unknown>): void
}
type MapLibreNamespace = {
  Map: new (options: Record<string, unknown>) => MapLibreMap
  Marker: new (options?: Record<string, unknown>) => MapLibreMarker
  NavigationControl: new () => unknown
}

const NESHAN_SDK_CSS = 'https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.css'
const NESHAN_SDK_JS = 'https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.umd.js'
const NESHAN_SDK_CSS_INTEGRITY = 'sha384-pUxsnE8dF8B3YMPiz+kzbxV4L1GsgnjImy1j2p+eOJgVYUBqNJpykDx6naFlBYUx'
const NESHAN_SDK_JS_INTEGRITY = 'sha384-wnbzzSu12Ml7LvCjoLfYgoBhYUTJOyrfNJbFY+Bp4zPxZvg0vf2HbxW+e76zytIQ'
const NESHAN_STYLE = 'https://static.neshan.org/sdk/maplibre/styles/light.json'

const reviewCustomers: SellerCustomer[] = [
  { id: '101', code: 'C-101', store_name: 'فروشگاه سپهر', name: 'علی رضایی', address: 'کرج، گوهردشت', latitude: 35.838, longitude: 50.971, open_invoice_count: 1 },
  { id: '102', code: 'C-102', store_name: 'مارکت پارس', name: 'رضا محمدی', address: 'کرج، رجایی‌شهر', latitude: 35.831, longitude: 50.987, visit_resolution: { status: 'completed', outcome: 'order' } },
  { id: '103', code: 'C-103', store_name: 'سوپر نگین', name: 'مهدی احمدی', address: 'کرج', latitude: 35.821, longitude: 50.956 },
]
const reviewPlan: NeshanRouteMapPlanResponse = {
  route: { id: 'R-01', title: 'مسیر روز' },
  customers: reviewCustomers.map((customer, index) => ({ ...customer, visit_score: 95 - index * 20, priority_tier: index === 0 ? 'high' : index === 1 ? 'medium' : 'low', analysis: {} })),
  missing_location_count: 0,
  ordered_customers: reviewCustomers.map((customer, index) => ({ ...customer, visit_score: 95 - index * 20, priority_tier: index === 0 ? 'high' : index === 1 ? 'medium' : 'low', analysis: {} })),
  unlocated_customers: [],
  has_origin: true,
  polyline: '', legs: [],
  initial_leg: { distance: { text: '۲.۴ کیلومتر', value: 2400 }, duration: { text: '۸ دقیقه', value: 480 }, steps: [{ instruction: 'به سمت مقصد اول حرکت کنید', distance: { text: '۲.۴ کیلومتر', value: 2400 }, duration: { text: '۸ دقیقه', value: 480 }, start_location: [50.97, 35.84] }] },
  route_mode: 'sales_priority', visit_location_policy: { enabled: true, enforced: true, max_distance_meters: 150 }, analytics_available: true,
}

function mapLibreFromWindow() {
  const value = (window as unknown as { maplibregl?: MapLibreNamespace & { default?: MapLibreNamespace } }).maplibregl
  return value?.default ?? value ?? null
}
async function ensureMapLibre(): Promise<MapLibreNamespace> {
  const existing = mapLibreFromWindow()
  if (existing) return existing
  if (!document.querySelector(`link[href="${NESHAN_SDK_CSS}"]`)) {
    const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = NESHAN_SDK_CSS; link.integrity = NESHAN_SDK_CSS_INTEGRITY; link.crossOrigin = 'anonymous'; document.head.appendChild(link)
  }
  let script = document.querySelector<HTMLScriptElement>(`script[src="${NESHAN_SDK_JS}"]`)
  if (!script) { script = document.createElement('script'); script.src = NESHAN_SDK_JS; script.integrity = NESHAN_SDK_JS_INTEGRITY; script.crossOrigin = 'anonymous'; script.defer = true; document.head.appendChild(script) }
  return new Promise((resolve, reject) => {
    const loaded = mapLibreFromWindow(); if (loaded) return resolve(loaded)
    const cleanup = () => { script?.removeEventListener('load', onLoad); script?.removeEventListener('error', onError) }
    const onLoad = () => { cleanup(); const sdk = mapLibreFromWindow(); if (sdk) resolve(sdk); else reject(new Error('Neshan MapLibre SDK بارگذاری شد ولی در دسترس نیست.')) }
    const onError = () => { cleanup(); reject(new Error('بارگذاری Neshan MapLibre SDK ناموفق بود.')) }
    script?.addEventListener('load', onLoad, { once: true }); script?.addEventListener('error', onError, { once: true })
  })
}
function currentCoordinates(timeout = 12_000): Promise<Position | null> {
  if (!navigator.geolocation) return Promise.resolve(null)
  return new Promise((resolve) => navigator.geolocation.getCurrentPosition(
    (result) => resolve({ latitude: result.coords.latitude, longitude: result.coords.longitude, accuracy: Number.isFinite(result.coords.accuracy) ? result.coords.accuracy : null, heading: Number.isFinite(result.coords.heading) ? result.coords.heading : null, timestamp: result.timestamp || Date.now() }),
    () => resolve(null), { enableHighAccuracy: true, maximumAge: 15_000, timeout },
  ))
}
function distanceMeters(a: { latitude: number; longitude: number }, b: { latitude: number; longitude: number }) {
  const radius = 6_371_000, lat1 = a.latitude * Math.PI / 180, lat2 = b.latitude * Math.PI / 180
  const deltaLat = (b.latitude - a.latitude) * Math.PI / 180, deltaLon = (b.longitude - a.longitude) * Math.PI / 180
  const value = Math.sin(deltaLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2
  return radius * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value))
}
function decodePolyline(encoded: string) {
  const coordinates: Array<[number, number]> = []; let index = 0, latitude = 0, longitude = 0
  while (index < encoded.length) {
    let shift = 0, result = 0, byte: number
    do { byte = encoded.charCodeAt(index++) - 63; result |= (byte & 0x1f) << shift; shift += 5 } while (byte >= 0x20)
    latitude += result & 1 ? ~(result >> 1) : result >> 1; shift = 0; result = 0
    do { byte = encoded.charCodeAt(index++) - 63; result |= (byte & 0x1f) << shift; shift += 5 } while (byte >= 0x20)
    longitude += result & 1 ? ~(result >> 1) : result >> 1; coordinates.push([longitude / 1e5, latitude / 1e5])
  }
  return coordinates
}
function distanceToPolyline(position: Position, encoded: string) {
  const line = decodePolyline(encoded); if (line.length < 2) return 0
  const latitudeScale = 111_320, longitudeScale = latitudeScale * Math.cos(position.latitude * Math.PI / 180); let minimum = Number.POSITIVE_INFINITY
  for (let index = 1; index < line.length; index += 1) {
    const [x1Raw, y1Raw] = line[index - 1], [x2Raw, y2Raw] = line[index]
    const x1 = (x1Raw - position.longitude) * longitudeScale, y1 = (y1Raw - position.latitude) * latitudeScale
    const x2 = (x2Raw - position.longitude) * longitudeScale, y2 = (y2Raw - position.latitude) * latitudeScale
    const dx = x2 - x1, dy = y2 - y1, lengthSquared = dx * dx + dy * dy
    const projection = lengthSquared ? Math.max(0, Math.min(1, -(x1 * dx + y1 * dy) / lengthSquared)) : 0
    minimum = Math.min(minimum, Math.hypot(x1 + projection * dx, y1 + projection * dy))
  }
  return Number.isFinite(minimum) ? minimum : 0
}
function customerStatus(customer: SellerCustomer) {
  if (customer.visit_resolution?.status !== 'completed') return ''
  if (customer.visit_resolution.outcome === 'order') return 'order'
  if (customer.visit_resolution.outcome === 'no_order') return 'no_order'
  if (customer.visit_resolution.outcome === 'no_visit' || customer.visit_resolution.outcome === 'skipped') return 'no_visit'
  return 'completed'
}
function statusLabel(customer: SellerCustomer) { const status = customerStatus(customer); return status === 'order' ? 'سفارش ثبت‌شده' : status === 'no_order' ? 'ویزیت بدون سفارش' : status === 'no_visit' ? 'عدم ویزیت' : status === 'completed' ? 'تکمیل‌شده' : 'در صف ویزیت' }
function statusTone(customer: SellerCustomer): 'success' | 'warning' | 'danger' | 'info' { const status = customerStatus(customer); return status === 'order' ? 'success' : status === 'no_order' ? 'warning' : status === 'no_visit' ? 'danger' : 'info' }
function isMapCustomer(customer: SellerCustomer): customer is NeshanRouteMapCustomer { return 'priority_tier' in customer && 'visit_score' in customer }
function priorityLabel(tier?: string) { return tier === 'high' ? 'اولویت بالا' : tier === 'medium' ? 'اولویت متوسط' : 'اولویت عادی' }
function legText(leg: NeshanRouteLeg | null | undefined) { return [leg?.duration?.text, leg?.distance?.text].filter(Boolean).join(' · ') || 'مسیر زنده هنوز محاسبه نشده' }
function routeStepPosition(step: NeshanRouteStep | undefined) { const point = step?.start_location; if (!Array.isArray(point) || point.length < 2) return null; const longitude = Number(point[0]), latitude = Number(point[1]); return Number.isFinite(latitude) && Number.isFinite(longitude) ? { latitude, longitude } : null }
function fallbackBrowserSpeech(text: string) { if (!('speechSynthesis' in window) || !text) return; window.speechSynthesis.cancel(); const utterance = new SpeechSynthesisUtterance(text); utterance.lang = 'fa-IR'; utterance.rate = .88; const voice = window.speechSynthesis.getVoices().find((item) => /^fa/i.test(item.lang)); if (voice) utterance.voice = voice; window.speechSynthesis.speak(utterance) }

export function SellerMapScreen() {
  const review = isReviewMode(), pathId = routeQueryValue('pathId')
  const mapContainerRef = useRef<HTMLDivElement | null>(null), mapRef = useRef<MapLibreMap | null>(null), mapSdkRef = useRef<MapLibreNamespace | null>(null)
  const markersRef = useRef<MapLibreMarker[]>([]), sellerMarkerRef = useRef<MapLibreMarker | null>(null), audioRef = useRef<HTMLAudioElement | null>(null)
  const lastRerouteRef = useRef(0), offRouteSinceRef = useRef<number | null>(null), spokenCueRef = useRef(new Set<string>())
  const positionRef = useRef<Position | null>(null), polylineRef = useRef('')
  const [routeMode, setRouteMode] = useState<'sales_priority' | 'shortest'>('sales_priority')
  const [plan, setPlan] = useState<NeshanRouteMapPlanResponse | null>(review ? reviewPlan : null)
  const [mapConfig, setMapConfig] = useState<NeshanMapConfigResponse | null>(review ? { api_key: 'review' } : null)
  const [position, setPosition] = useState<Position | null>(null), [currentLeg, setCurrentLeg] = useState<NeshanRouteLeg | null>(reviewPlan.initial_leg ?? null), [currentPolyline, setCurrentPolyline] = useState(reviewPlan.polyline)
  const [navigationStarted, setNavigationStarted] = useState(false), [instructionIndex, setInstructionIndex] = useState(0), [voiceEnabled, setVoiceEnabled] = useState(true)
  const [loadingPlan, setLoadingPlan] = useState(false), [mapError, setMapError] = useState(''), [actionError, setActionError] = useState(''), [mapReady, setMapReady] = useState(false)
  const [noVisitCustomer, setNoVisitCustomer] = useState<SellerCustomer | null>(null), [noVisitPolicy, setNoVisitPolicy] = useState<SellerVisitPolicyResponse | null>(null), [noVisitReasonId, setNoVisitReasonId] = useState(''), [noVisitBusy, setNoVisitBusy] = useState(false)

  const routeQuery = useApiQuery<SellerRouteCustomersResponse>(`seller:map-route-customers:${pathId || (review ? 'review' : 'missing')}`, (signal) => review ? Promise.resolve({ route: reviewPlan.route, customer_count: reviewCustomers.length, customers: reviewCustomers }) : pathId ? apiRequest<SellerRouteCustomersResponse>(`/seller-workspace/routes/${encodeURIComponent(pathId)}/customers`, { signal }) : Promise.reject(new Error('شناسه مسیر در URL موجود نیست.')))
  const savedRequestsQuery = useApiQuery<PrevisitSavedRequestsResponse>(`seller:route-saved-requests:${pathId || (review ? 'review' : 'missing')}`, (signal) => review ? Promise.resolve({ requests: [] }) : pathId ? apiRequest<PrevisitSavedRequestsResponse>(`/seller-workspace/routes/${encodeURIComponent(pathId)}/saved-requests`, { signal }) : Promise.reject(new Error('شناسه مسیر در URL موجود نیست.')))
  const orderedCustomers = useMemo(() => plan?.ordered_customers ?? [], [plan?.ordered_customers])
  const activeIndex = useMemo(() => { const pending = orderedCustomers.findIndex((customer) => !customerStatus(customer)); return pending >= 0 ? pending : orderedCustomers.length }, [orderedCustomers])
  const activeCustomer = activeIndex < orderedCustomers.length ? orderedCustomers[activeIndex] : null
  const completedCount = orderedCustomers.filter((customer) => Boolean(customerStatus(customer))).length
  const routeTitle = plan?.route.title || routeQuery.data?.route.title || 'نقشه مسیر فروش'

  const updateSellerMarker = useCallback((next: Position) => {
    const map = mapRef.current, sdk = mapSdkRef.current; if (!map || !sdk || !map.isStyleLoaded()) return
    const coordinates: [number, number] = [next.longitude, next.latitude]
    if (sellerMarkerRef.current) { sellerMarkerRef.current.setLngLat(coordinates); return }
    const element = document.createElement('div'); element.className = 'ng-seller-map__seller-marker'; element.setAttribute('aria-label', 'موقعیت فعلی فروشنده')
    sellerMarkerRef.current = new sdk.Marker({ element }).setLngLat(coordinates).addTo(map)
  }, [])
  const drawRouteLine = useCallback((encoded: string) => {
    const map = mapRef.current; if (!map?.isStyleLoaded()) return
    if (map.getLayer('vnext-route-line')) map.removeLayer('vnext-route-line'); if (map.getSource('vnext-route-line')) map.removeSource('vnext-route-line')
    const line = decodePolyline(encoded); if (line.length < 2) return
    map.addSource('vnext-route-line', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: line } } })
    map.addLayer({ id: 'vnext-route-line', type: 'line', source: 'vnext-route-line', paint: { 'line-color': '#176b54', 'line-width': 5, 'line-opacity': .88 } })
  }, [])
  const speakInstruction = useCallback(async (text: string) => {
    const phrase = text.replace(/<[^>]*>/g, '').trim(); if (!phrase || !voiceEnabled) return
    const android = (window as unknown as { NeginAndroid?: { isPersianVoiceReady?: () => boolean; speakPersian?: (value: string) => boolean } }).NeginAndroid
    try { if (android?.isPersianVoiceReady?.() && android.speakPersian?.(phrase)) return } catch { /* fallback */ }
    try {
      const response = await fetch('/audio/navigation-speech', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', Accept: 'audio/mpeg' }, body: JSON.stringify({ text: phrase }) })
      if (!response.ok) throw new Error('navigation speech unavailable')
      const blob = await response.blob(), url = URL.createObjectURL(blob); audioRef.current?.pause(); const audio = new Audio(url); audioRef.current = audio; audio.addEventListener('ended', () => URL.revokeObjectURL(url), { once: true }); await audio.play()
    } catch { fallbackBrowserSpeech(phrase) }
  }, [voiceEnabled])
  const refreshLeg = useCallback(async (origin: Position, announce = false) => {
    if (!pathId || !activeCustomer) return; setActionError('')
    try {
      const params = new URLSearchParams({ destination_id: String(activeCustomer.id), origin_latitude: String(origin.latitude), origin_longitude: String(origin.longitude) })
      const response = review ? { polyline: '', leg: reviewPlan.initial_leg ?? null } : await apiRequest<NeshanRouteMapLegResponse>(`/seller-workspace/routes/${encodeURIComponent(pathId)}/map-leg?${params}`)
      setCurrentLeg(response.leg ?? null); setCurrentPolyline(response.polyline || ''); setInstructionIndex(0); spokenCueRef.current.clear(); lastRerouteRef.current = Date.now(); offRouteSinceRef.current = null
      if (announce) { const first = response.leg?.steps?.[0]?.instruction; if (first) void speakInstruction(first) }
    } catch (reason) { setActionError(reason instanceof Error ? reason.message : 'محاسبه مسیر زنده ناموفق بود.') }
  }, [activeCustomer, pathId, review, speakInstruction])
  const loadPlan = useCallback(async (mode: 'sales_priority' | 'shortest' = routeMode) => {
    if (review) { setPlan({ ...reviewPlan, route_mode: mode }); setMapConfig({ api_key: 'review' }); setCurrentLeg(reviewPlan.initial_leg ?? null); return }
    if (!pathId) { setMapError('شناسه مسیر در URL موجود نیست.'); return }
    setLoadingPlan(true); setMapError('')
    try {
      const current = await currentCoordinates(); if (current) setPosition(current)
      const params = new URLSearchParams({ route_mode: mode, start_day_route: 'true' }); if (current) { params.set('origin_latitude', String(current.latitude)); params.set('origin_longitude', String(current.longitude)) }
      const [config, nextPlan] = await Promise.all([apiRequest<NeshanMapConfigResponse>('/seller-workspace/map-config'), apiRequest<NeshanRouteMapPlanResponse>(`/seller-workspace/routes/${encodeURIComponent(pathId)}/map-plan?${params}`)])
      setMapConfig(config); setPlan(nextPlan); setCurrentLeg(nextPlan.initial_leg ?? null); setCurrentPolyline(nextPlan.polyline || ''); setInstructionIndex(0); setNavigationStarted(false); spokenCueRef.current.clear()
    } catch (reason) { setMapError(reason instanceof Error ? reason.message : 'بارگذاری نقشه مسیر ناموفق بود.') } finally { setLoadingPlan(false) }
  }, [pathId, review, routeMode])

  useEffect(() => { if (review) return; let cancelled = false; queueMicrotask(() => { if (!cancelled) void loadPlan(routeMode) }); return () => { cancelled = true } }, [loadPlan, review, routeMode])
  useEffect(() => {
    if (review || !plan || !mapConfig || !mapContainerRef.current) return
    let disposed = false, localMap: MapLibreMap | null = null
    void ensureMapLibre().then((sdk) => {
      if (disposed || !mapContainerRef.current) return; mapSdkRef.current = sdk
      const firstLocated = plan.ordered_customers.find((customer) => customer.latitude != null && customer.longitude != null)
      const initialPosition = positionRef.current
      const center: [number, number] = initialPosition ? [initialPosition.longitude, initialPosition.latitude] : firstLocated ? [Number(firstLocated.longitude), Number(firstLocated.latitude)] : [51.4, 35.7]
      localMap = new sdk.Map({ container: mapContainerRef.current, style: NESHAN_STYLE, center, zoom: initialPosition ? 13 : 10, apiKey: mapConfig.api_key, rtl: { lazy: false } }); mapRef.current = localMap; localMap.addControl(new sdk.NavigationControl())
      localMap.on('error', (event) => { if (event?.error?.message) setMapError(`خطای نقشه: ${event.error.message}`) })
      localMap.on('load', () => {
        if (disposed || !localMap) return; setMapReady(true); markersRef.current.forEach((marker) => marker.remove()); markersRef.current = []
        const points: Array<[number, number]> = []
        plan.ordered_customers.forEach((customer, index) => {
          if (customer.latitude == null || customer.longitude == null) return
          const color = customer.priority_tier === 'high' ? '#1d6fea' : customer.priority_tier === 'medium' ? '#d38b18' : '#71807c'
          const marker = new sdk.Marker({ color }).setLngLat([Number(customer.longitude), Number(customer.latitude)]).addTo(localMap!); marker.getElement().title = `${index + 1}. ${customerDisplayName(customer)}`; marker.getElement().setAttribute('role', 'button'); marker.getElement().setAttribute('tabindex', '0')
          const openCustomer = () => navigateWithParams('/seller/customer', { pathId, customerId: customer.id }); marker.getElement().addEventListener('click', openCustomer); marker.getElement().addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openCustomer() } })
          markersRef.current.push(marker); points.push([Number(customer.longitude), Number(customer.latitude)])
        })
        const initialPosition = positionRef.current
        if (initialPosition) { points.push([initialPosition.longitude, initialPosition.latitude]); updateSellerMarker(initialPosition) }
        if (points.length) { const longitudes = points.map(([longitude]) => longitude), latitudes = points.map(([, latitude]) => latitude); localMap.fitBounds([[Math.min(...longitudes), Math.min(...latitudes)], [Math.max(...longitudes), Math.max(...latitudes)]], { padding: 45, maxZoom: 14, duration: 0 }) }
        drawRouteLine(polylineRef.current)
      })
    }).catch((reason) => setMapError(reason instanceof Error ? reason.message : 'SDK نقشه بارگذاری نشد.'))
    return () => { disposed = true; markersRef.current.forEach((marker) => marker.remove()); markersRef.current = []; sellerMarkerRef.current?.remove(); sellerMarkerRef.current = null; localMap?.remove(); if (mapRef.current === localMap) mapRef.current = null; setMapReady(false) }
  }, [drawRouteLine, mapConfig, pathId, plan, review, updateSellerMarker])
  useEffect(() => { positionRef.current = position; if (position && !review) updateSellerMarker(position) }, [position, review, updateSellerMarker])
  useEffect(() => { polylineRef.current = currentPolyline; if (!review) drawRouteLine(currentPolyline) }, [currentPolyline, drawRouteLine, review])
  useEffect(() => {
    if (!navigator.geolocation || review) return
    const watchId = navigator.geolocation.watchPosition((result) => {
      if (Number.isFinite(result.coords.accuracy) && result.coords.accuracy > 100) return
      const next: Position = { latitude: result.coords.latitude, longitude: result.coords.longitude, accuracy: Number.isFinite(result.coords.accuracy) ? result.coords.accuracy : null, heading: Number.isFinite(result.coords.heading) ? result.coords.heading : null, timestamp: result.timestamp || Date.now() }
      setPosition(next); updateSellerMarker(next); if (!navigationStarted || !activeCustomer) return
      const steps = currentLeg?.steps ?? [], step = steps[instructionIndex], stepPosition = routeStepPosition(step)
      if (step && stepPosition) { const distance = distanceMeters(next, stepPosition), threshold = distance <= 25 ? 25 : distance <= 80 ? 80 : distance <= 250 ? 250 : null; if (threshold) { const cueKey = `${instructionIndex}:${threshold}`; if (!spokenCueRef.current.has(cueKey)) { spokenCueRef.current.add(cueKey); void speakInstruction(`${step.instruction || 'ادامه مسیر'}${distance > 25 ? `، تا ${Math.round(distance).toLocaleString('fa-IR')} متر دیگر` : ''}`) } } if (distance <= 25 && instructionIndex < steps.length - 1) setInstructionIndex((value) => Math.min(value + 1, steps.length - 1)) }
      if (!currentPolyline || Date.now() - lastRerouteRef.current < 15_000) return
      const offRouteDistance = distanceToPolyline(next, currentPolyline), threshold = Math.max(65, Number(next.accuracy || 0) * 1.5)
      if (offRouteDistance <= threshold) { offRouteSinceRef.current = null; return }
      offRouteSinceRef.current ??= Date.now(); if (Date.now() - offRouteSinceRef.current >= 5_000) { offRouteSinceRef.current = null; void refreshLeg(next, true) }
    }, () => {}, { enableHighAccuracy: true, maximumAge: 15_000, timeout: 20_000 })
    return () => navigator.geolocation.clearWatch(watchId)
  }, [activeCustomer, currentLeg, currentPolyline, instructionIndex, navigationStarted, refreshLeg, review, speakInstruction, updateSellerMarker])

  async function startNavigation() { setActionError(''); const current = position ?? await currentCoordinates(); if (!current) { setActionError('برای شروع مسیریابی، دسترسی GPS لازم است.'); return } setPosition(current); setNavigationStarted(true); await refreshLeg(current, true); mapRef.current?.easeTo({ center: [current.longitude, current.latitude], zoom: 16.5, bearing: Number.isFinite(current.heading) ? current.heading : 0, pitch: 42, duration: 650, essential: true }) }
  async function recenter() { const current = position ?? await currentCoordinates(); if (!current) { setActionError('موقعیت فعلی در دسترس نیست.'); return } setPosition(current); updateSellerMarker(current); mapRef.current?.flyTo({ center: [current.longitude, current.latitude], zoom: navigationStarted ? 16.5 : 15, essential: true }) }
  async function openNoVisit(customer: SellerCustomer) {
    if (!pathId) return; setActionError(''); setNoVisitCustomer(customer); setNoVisitReasonId('')
    try {
      const policy = review ? { route: reviewPlan.route, customer: { id: customer.id, name: customer.name, store_name: customer.store_name, has_location: true, location_check_exempt: false }, controls: { enabled: true, enforced: false }, missing_required_fields: [], start_blockers: [], order_blockers: [], can_start_visit: true, reasons: { no_visit: [{ id: 'review-reason', title: 'مشتری در محل حضور نداشت' }] }, visit_status_ids: {}, source: 'review' } satisfies SellerVisitPolicyResponse : await apiRequest<SellerVisitPolicyResponse>(`/seller-workspace/previsit/policy?path_id=${encodeURIComponent(pathId)}&customer_id=${encodeURIComponent(String(customer.id))}`)
      setNoVisitPolicy(policy); setNoVisitReasonId(String(policy.reasons?.no_visit?.[0]?.id ?? ''))
    } catch (reason) { setNoVisitPolicy(null); setActionError(reason instanceof Error ? reason.message : 'دریافت دلایل عدم ویزیت ناموفق بود.') }
  }
  async function completeNoVisit() {
    if (!pathId || !noVisitCustomer || !noVisitPolicy || !noVisitReasonId || noVisitBusy) return; setNoVisitBusy(true); setActionError('')
    try {
      const needsLocation = Boolean(noVisitPolicy.controls.enforced) && !noVisitPolicy.customer.location_check_exempt, current = needsLocation ? (position ?? await currentCoordinates()) : null
      if (needsLocation && !current) throw new Error('برای ثبت عدم ویزیت، موقعیت GPS الزامی است.')
      if (review) {
        setPlan((currentPlan) => currentPlan ? { ...currentPlan, customers: currentPlan.customers.map((customer) => String(customer.id) === String(noVisitCustomer.id) ? { ...customer, visit_resolution: { status: 'completed', outcome: 'no_visit', ended_at: new Date().toISOString() } } : customer), ordered_customers: currentPlan.ordered_customers.map((customer) => String(customer.id) === String(noVisitCustomer.id) ? { ...customer, visit_resolution: { status: 'completed', outcome: 'no_visit', ended_at: new Date().toISOString() } } : customer) } : currentPlan)
      } else {
        const visit = await apiRequest<{ visit_id: string }>('/seller-workspace/previsit/visits', { method: 'POST', body: { route_id: pathId, customer_id: String(noVisitCustomer.id), latitude: current?.latitude ?? null, longitude: current?.longitude ?? null, accuracy: current?.accuracy ?? null } })
        await apiRequest(`/seller-workspace/previsit/visits/${encodeURIComponent(visit.visit_id)}/complete`, { method: 'POST', body: { outcome: 'no_visit', reason_id: noVisitReasonId, latitude: current?.latitude ?? null, longitude: current?.longitude ?? null, accuracy: current?.accuracy ?? null } })
        await loadPlan(routeMode); routeQuery.reload()
      }
      setNoVisitCustomer(null); setNoVisitPolicy(null); setNoVisitReasonId('')
    } catch (reason) { setActionError(reason instanceof Error ? reason.message : 'ثبت عدم ویزیت ناموفق بود.') } finally { setNoVisitBusy(false) }
  }

  const instruction = currentLeg?.steps?.[instructionIndex], fallbackCustomers = routeQuery.data?.customers ?? [], visibleCustomers = plan?.ordered_customers.length ? plan.ordered_customers : fallbackCustomers, noVisitReasons = noVisitPolicy?.reasons?.no_visit ?? []
  return <div className="ng-v2 ng-seller-map" dir="rtl" data-trace-id="MAP-01"><ResponsivePageContainer><Stack gap={5}>
    <PageHeader eyebrow="LIVE ROUTE / NESHAN" title={routeTitle} description="نقشه زنده مسیر فروش بر اساس مسیر واقعی فروشنده، موقعیت GPS و سرویس رسمی Neshan." actions={<Cluster><Button variant="secondary" startIcon={<RefreshCw/>} loading={loadingPlan} onClick={() => void loadPlan(routeMode)}>بازآرایی مسیر</Button><Button variant="secondary" startIcon={<LocateFixed/>} onClick={() => void recenter()}>موقعیت من</Button></Cluster>}/>
    {routeQuery.status === 'loading' && !routeQuery.data ? <AsyncState mode="loading" title="در حال دریافت مشتریان مسیر" /> : null}
    {routeQuery.status === 'error' ? <AsyncState mode="error" title="دریافت مشتریان مسیر ناموفق بود" message={routeQuery.error?.message} onRetry={routeQuery.reload} /> : null}
    {mapError ? <Alert title="نقشه Neshan در دسترس نیست" tone="warning">{mapError} فهرست مشتریان همچنان قابل استفاده است.</Alert> : null}
    {actionError ? <Alert title="عملیات مسیر انجام نشد" tone="danger">{actionError}</Alert> : null}
    <section className="ng-seller-map__controls"><label><span>حالت بهینه‌سازی</span><select value={routeMode} onChange={(event) => setRouteMode(event.target.value === 'shortest' ? 'shortest' : 'sales_priority')}><option value="sales_priority">اولویت فروش</option><option value="shortest">کوتاه‌ترین مسیر</option></select></label><div><StatusBadge label={plan?.analytics_available === false ? 'اولویت تحلیلی موقتاً در دسترس نیست' : 'اولویت فروش فعال'} tone={plan?.analytics_available === false ? 'warning' : 'success'}/><StatusBadge label={position ? `GPS ±${Math.round(position.accuracy || 0).toLocaleString('fa-IR')}m` : 'GPS دریافت نشده'} tone={position ? 'success' : 'warning'}/><StatusBadge label={`${savedRequestsQuery.data?.requests.length ?? 0} درخواست ذخیره‌شده امروز`} tone="premium"/></div></section>
    <section className="ng-seller-map__workspace"><div className="ng-seller-map__canvas-shell"><div ref={mapContainerRef} className="ng-seller-map__canvas" aria-label="نقشه زنده مسیر فروش">{review ? <div className="ng-seller-map__review"><Route size={42}/><strong>Review Mode</strong><span>در اجرای واقعی، Neshan MapLibre با کلید map-config نمایش داده می‌شود.</span></div> : null}</div><div className="ng-seller-map__floating"><Button size="lg" startIcon={<Navigation/>} disabled={!activeCustomer || (!mapReady && !review)} onClick={() => void startNavigation()}>{navigationStarted ? 'به‌روزرسانی مسیر زنده' : 'شروع مسیریابی'}</Button><Button variant="secondary" startIcon={voiceEnabled ? <Volume2/> : <VolumeX/>} onClick={() => setVoiceEnabled((value) => !value)}>{voiceEnabled ? 'راهنمای صوتی روشن' : 'راهنمای صوتی خاموش'}</Button></div>{navigationStarted && activeCustomer ? <section className="ng-seller-map__instruction" aria-live="polite"><small>مقصد فعال</small><strong>{customerDisplayName(activeCustomer)}</strong><span>{legText(currentLeg)}</span>{instruction?.instruction ? <p>{instruction.instruction}</p> : null}</section> : null}</div>
      <aside className="ng-seller-map__sidebar"><div className="ng-seller-map__summary"><span>DAY ROUTE</span><strong>{completedCount.toLocaleString('fa-IR')} / {visibleCustomers.length.toLocaleString('fa-IR')}</strong><small>مشتری تکمیل‌شده</small><div><i style={{ width: visibleCustomers.length ? `${Math.round(completedCount / visibleCustomers.length * 100)}%` : '0%' }}/></div></div><Stack gap={2}>{visibleCustomers.map((customer, index) => { const active = String(activeCustomer?.id ?? '') === String(customer.id), completed = Boolean(customerStatus(customer)); return <Card key={String(customer.id)} className={`ng-seller-map__stop${active ? ' is-active' : ''}${completed ? ' is-complete' : ''}`}><Cluster><span className="ng-seller-map__index">{completed ? <CheckCircle2 size={16}/> : index + 1}</span><div style={{ flex: 1 }}><strong>{customerDisplayName(customer)}</strong><small>{customer.address || customer.code || String(customer.id)}</small></div><StatusBadge label={statusLabel(customer)} tone={statusTone(customer)}/></Cluster>{isMapCustomer(customer) ? <KeyValue items={[{ key: 'اولویت', value: priorityLabel(String(customer.priority_tier || '')) }, { key: 'امتیاز ویزیت', value: Number(customer.visit_score || 0).toLocaleString('fa-IR') }, { key: 'فاکتور باز', value: Number(customer.open_invoice_count || 0).toLocaleString('fa-IR') }]}/> : null}<Cluster><Button size="sm" variant="secondary" startIcon={<Store/>} onClick={() => navigateWithParams('/seller/customer', { pathId, customerId: customer.id })}>Customer 360</Button>{!completed ? <><Button size="sm" onClick={() => navigateWithParams('/seller/visit', { pathId, customerId: customer.id })}>ورود به ویزیت</Button><Button size="sm" variant="ghost" onClick={() => void openNoVisit(customer)}>عدم ویزیت</Button></> : null}</Cluster></Card>})}</Stack>{(plan?.unlocated_customers.length ?? 0) > 0 ? <Alert title="مشتریان فاقد مختصات" tone="warning">{plan?.unlocated_customers.length.toLocaleString('fa-IR')} مشتری در ترتیب روز قرار دارند اما روی نقشه pin ندارند.</Alert> : null}</aside>
    </section>
    {noVisitCustomer ? <Card className="ng-seller-map__no-visit"><PageHeader eyebrow="NO VISIT" title={`عدم ویزیت · ${customerDisplayName(noVisitCustomer)}`} description="همان flow رسمی Legacy: دریافت policy، شروع ویزیت محلی و سپس complete با outcome=no_visit."/>{!noVisitPolicy ? <AsyncState mode="loading" title="در حال دریافت دلایل عدم ویزیت"/> : null}{noVisitPolicy ? <>{(!noVisitPolicy.can_start_visit || noVisitPolicy.start_blockers.length) ? <Alert title="عدم ویزیت فعلاً قابل ثبت نیست" tone="danger">{noVisitPolicy.start_blockers.length ? noVisitPolicy.start_blockers.join(' · ') : 'Policy شروع ویزیت را مجاز نمی‌داند.'}</Alert> : null}<label className="ng-seller-map__reason"><span>دلیل رسمی NGT</span><select value={noVisitReasonId} onChange={(event) => setNoVisitReasonId(event.target.value)}><option value="">انتخاب دلیل</option>{noVisitReasons.map((reason) => <option key={String(reason.id)} value={String(reason.id)}>{String(reason.title || reason.id)}</option>)}</select></label><Cluster><Button loading={noVisitBusy} disabled={!noVisitReasonId || !noVisitPolicy.can_start_visit || noVisitPolicy.start_blockers.length > 0} onClick={() => void completeNoVisit()}>ثبت عدم ویزیت</Button><Button variant="secondary" onClick={() => { setNoVisitCustomer(null); setNoVisitPolicy(null); setNoVisitReasonId('') }}>انصراف</Button></Cluster></> : null}</Card> : null}
    <Card><Cluster><MapPin/><div style={{ flex: 1 }}><strong>مرز داده و سرویس نقشه</strong><small>Map key از /map-config، ترتیب روز از /map-plan و مسیر نقطه‌به‌نقطه از /map-leg می‌آید. هیچ مختصات یا ETA ساختگی وارد flow زنده نمی‌شود.</small></div></Cluster></Card>
  </Stack></ResponsivePageContainer></div>
}
