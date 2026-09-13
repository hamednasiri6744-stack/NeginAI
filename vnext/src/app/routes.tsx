import type { ComponentType } from 'react'
import { AIScreen } from '../features/ai/AIScreen'
import { HomeScreen } from '../features/home/HomeScreen'
import { ModulesScreen } from '../features/modules/ModulesScreen'
import { MoreScreen } from '../features/more/MoreScreen'
import { ReportsScreen } from '../features/reports/ReportsScreen'
import { SellerRoutesScreen } from '../features/seller/SellerRoutesScreen'
import { SellerDayRouteScreen } from '../features/seller/SellerDayRouteScreen'
import { SellerRouteCustomersScreen } from '../features/seller/SellerRouteCustomersScreen'
import { SellerMapScreen } from '../features/seller/SellerMapScreen'
import { Customer360Screen } from '../features/seller/Customer360Screen'
import { VisitScreen } from '../features/seller/VisitScreen'
import { CatalogScreen } from '../features/seller/CatalogScreen'
import { CartScreen } from '../features/seller/CartScreen'
import { DesignSystemLab } from '../design-system/v2/lab/DesignSystemLab'
import type { PrimaryDestination } from './navigation'

export type AppRouteId =
  | 'home' | 'modules' | 'ai' | 'reports' | 'more' | 'seller-routes'
  | 'seller-day-route' | 'seller-customers' | 'seller-map' | 'seller-customer'
  | 'seller-visit' | 'seller-catalog' | 'seller-cart' | 'design-system'

export type AppRouteDefinition = {
  id: AppRouteId
  path: string
  primary: PrimaryDestination
  screen: ComponentType
  traceId: string
  contractStatus: 'VERIFIED' | 'NEEDS_VALIDATION'
}

export const appRoutes: readonly AppRouteDefinition[] = [
  { id: 'home', path: '/', primary: 'home', screen: HomeScreen, traceId: 'SCR-01-HOME', contractStatus: 'VERIFIED' },
  { id: 'modules', path: '/modules', primary: 'modules', screen: ModulesScreen, traceId: 'SCR-00-MODULES', contractStatus: 'VERIFIED' },
  { id: 'ai', path: '/ai', primary: 'ai', screen: AIScreen, traceId: 'SCR-02-AI', contractStatus: 'VERIFIED' },
  { id: 'reports', path: '/reports', primary: 'reports', screen: ReportsScreen, traceId: 'SCR-15-REPORTS', contractStatus: 'VERIFIED' },
  { id: 'more', path: '/more', primary: 'more', screen: MoreScreen, traceId: 'SCR-00-MORE', contractStatus: 'VERIFIED' },
  { id: 'seller-routes', path: '/seller/routes', primary: 'modules', screen: SellerRoutesScreen, traceId: 'SEL-01', contractStatus: 'VERIFIED' },
  { id: 'seller-day-route', path: '/seller/day-route', primary: 'modules', screen: SellerDayRouteScreen, traceId: 'SEL-02', contractStatus: 'VERIFIED' },
  { id: 'seller-customers', path: '/seller/customers', primary: 'modules', screen: SellerRouteCustomersScreen, traceId: 'SEL-03', contractStatus: 'VERIFIED' },
  { id: 'seller-map', path: '/seller/map', primary: 'modules', screen: SellerMapScreen, traceId: 'MAP-01', contractStatus: 'NEEDS_VALIDATION' },
  { id: 'seller-customer', path: '/seller/customer', primary: 'modules', screen: Customer360Screen, traceId: 'CUS-01', contractStatus: 'VERIFIED' },
  { id: 'seller-visit', path: '/seller/visit', primary: 'modules', screen: VisitScreen, traceId: 'VIS-01', contractStatus: 'VERIFIED' },
  { id: 'seller-catalog', path: '/seller/catalog', primary: 'modules', screen: CatalogScreen, traceId: 'ORD-01', contractStatus: 'VERIFIED' },
  { id: 'seller-cart', path: '/seller/cart', primary: 'modules', screen: CartScreen, traceId: 'ORD-04', contractStatus: 'NEEDS_VALIDATION' },
  { id: 'design-system', path: '/design-system', primary: 'more', screen: DesignSystemLab, traceId: 'NG-DS-V2-LAB', contractStatus: 'NEEDS_VALIDATION' },
] as const

export function primaryForPath(pathname: string): PrimaryDestination {
  const direct = appRoutes.find((route) => route.path === pathname)
  if (direct) return direct.primary
  if (pathname.startsWith('/seller/')) return 'modules'
  return 'home'
}
