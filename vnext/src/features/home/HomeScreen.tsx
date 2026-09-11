import { Bot, Route, ShoppingCart, Sparkles, Target, WalletCards } from 'lucide-react'
import { navigate } from '../../app/router'
import { Button, Cluster, PageHeader, QuickActionTile, ResponsivePageContainer, Stack, StatusBadge, VisualMetricCard } from '../../design-system/v2'

export function HomeScreen() {
  return (
    <div className="ng-v2" dir="rtl" data-trace-id="PLT-01">
      <ResponsivePageContainer>
        <Stack gap={6}>
          <PageHeader
            eyebrow={'\u0635\u0641\u062d\u0647 \u0627\u0635\u0644\u06cc'}
            title={'\u0627\u0645\u0631\u0648\u0632 \u0631\u0627 \u0628\u0627 \u062a\u0645\u0631\u06a9\u0632 \u0628\u0631 \u0641\u0631\u0648\u0634 \u0628\u0634\u0631\u0648\u0639 \u06a9\u0646\u06cc\u062f'}
            description={'\u0648\u0636\u0639\u06cc\u062a \u0645\u0633\u06cc\u0631\u060c \u0648\u06cc\u0632\u06cc\u062a\u200c\u0647\u0627\u060c \u0641\u0631\u0648\u0634 \u0648 \u0647\u0634\u062f\u0627\u0631\u0647\u0627\u06cc \u0645\u0647\u0645 \u062f\u0631 \u06cc\u06a9 \u0646\u0645\u0627.'}
            actions={<Button size="lg" startIcon={<Route />} onClick={() => navigate('/seller/routes')}>{'\u0634\u0631\u0648\u0639 \u0645\u0633\u06cc\u0631 \u0627\u0645\u0631\u0648\u0632'}</Button>}
          />
          <div className="ng-demo-grid">
            <VisualMetricCard label={'\u0641\u0631\u0648\u0634 \u0627\u0645\u0631\u0648\u0632'} value="۱۲,۴۵۰,۰۰۰" trend="+۱۵٪" values={[22,28,25,34,31,42]} />
            <VisualMetricCard label={'\u0648\u06cc\u0632\u06cc\u062a \u0627\u0645\u0631\u0648\u0632'} value="۳ / ۵" trend="۲ باقی‌مانده" tone="info" values={[12,20,34,42,58,65]} />
            <VisualMetricCard label={'\u062a\u062d\u0642\u0642 \u062a\u0627\u0631\u06af\u062a'} value="۷۲٪" trend="+۸٪" tone="premium" values={[40,44,49,55,63,72]} />
          </div>
          <section>
            <Cluster><StatusBadge label={'\u062f\u0633\u062a\u0631\u0633\u06cc \u0633\u0631\u06cc\u0639'} tone="premium" /></Cluster>
            <div className="ng-action-grid">
              <QuickActionTile icon={<Route />} title={'\u0645\u0633\u06cc\u0631\u0647\u0627\u06cc \u0645\u0646'} meta="۵ مسیر فعال" onClick={() => navigate('/seller/routes')} />
              <QuickActionTile icon={<ShoppingCart />} title={'\u0633\u0641\u0627\u0631\u0634 \u062c\u062f\u06cc\u062f'} meta="از مشتری یا مسیر" tone="success" onClick={() => navigate('/seller/catalog')} />
              <QuickActionTile icon={<Bot />} title={'\u062f\u0633\u062a\u06cc\u0627\u0631 Negin AI'} meta="پیشنهاد و تحلیل" tone="info" onClick={() => navigate('/ai')} />
              <QuickActionTile icon={<WalletCards />} title={'\u0648\u0636\u0639\u06cc\u062a \u0645\u0627\u0644\u06cc'} meta="مانده و اعتبار" tone="warning" onClick={() => navigate('/seller/customer')} />
            </div>
          </section>
          <section className="ng-card"><Cluster><Target/><div><strong>اولویت پیشنهادی امروز</strong><small>۳ مشتری با پتانسیل فروش بالا در مسیر کرج مرکزی</small></div><StatusBadge label="Negin AI" tone="premium"/><Sparkles size={18}/></Cluster></section>
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}
