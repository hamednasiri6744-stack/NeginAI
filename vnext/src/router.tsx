import { createBrowserRouter } from 'react-router'
import {
  AppShellRoute,
  LoginRoute,
  NotFoundRoute,
  VisitorCustomer360Route,
  VisitorCustomersRoute,
  VisitorHomeRoute,
  VisitorOrdersRoute,
  VisitorOrderArchiveRoute,
  VisitorReportsRoute,
  VisitorNotificationsRoute,
  VisitorProfileSettingsRoute,
  VisitorRouteVisitRoute,
} from './App'

export const router = createBrowserRouter([
  {
    Component: AppShellRoute,
    children: [
      { path: '/', Component: LoginRoute },
      { path: '/visitor/home', Component: VisitorHomeRoute },
      { path: '/visitor/route', Component: VisitorRouteVisitRoute },
      { path: '/visitor/orders', Component: VisitorOrdersRoute },
      { path: '/visitor/orders/history', Component: VisitorOrderArchiveRoute },
      { path: '/visitor/reports', Component: VisitorReportsRoute },
      { path: '/visitor/notifications', Component: VisitorNotificationsRoute },
      { path: '/visitor/profile', Component: VisitorProfileSettingsRoute },
      { path: '/visitor/customers', Component: VisitorCustomersRoute },
      { path: '/visitor/customers/:customerId', Component: VisitorCustomer360Route },
      { path: '*', Component: NotFoundRoute },
    ],
  },
])
