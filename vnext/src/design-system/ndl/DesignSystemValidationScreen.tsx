import { Bell, Check, CircleAlert, Home, Layers3, MoreHorizontal, Search, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Avatar, Badge, Button, Card, Chip, IconButton, Input, Metric, PasswordInput, Progress, SearchInput, Skeleton, Spinner, Surface } from './components'
import { AIAction, AppHeader, CommandBar, PageHeader, Tabs, type NavigationItem } from './navigation'
import { BottomSheet, Dialog, Toast } from './overlays'
import { SharedAppShell } from './SharedAppShell'
import './ndl.css'

const neutralNavigation: NavigationItem[] = [
  { id: 'one', label: 'نمونه یک', icon: <Home size={20} /> },
  { id: 'two', label: 'نمونه دو', icon: <Layers3 size={20} /> },
  { id: 'three', label: 'بیشتر', icon: <MoreHorizontal size={20} /> },
]

export function DesignSystemValidationScreen() {
  const [activeNav, setActiveNav] = useState('one')
  const [activeTab, setActiveTab] = useState('first')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [toastOpen, setToastOpen] = useState(false)
  return (
    <div className="ndl-validation" dir="rtl" data-trace-id="NDL-VALIDATION-001">
      <PageHeader eyebrow="NDL-1.0 / GOLDEN VALIDATION" title="آزمایشگاه خنثی سیستم طراحی" description="این صفحه فقط رفتار، ظاهر و دسترس‌پذیری اجزای عمومی را بررسی می‌کند و هیچ داده یا معنای کسب‌وکار ندارد." actions={<Badge tone="warning">FIGMA_MAPPING_PENDING</Badge>} />

      <section className="ndl-validation__section" aria-labelledby="foundation-title"><h2 id="foundation-title">رنگ و سطح</h2><div className="ndl-validation__surfaces"><Surface level={1}>سطح پایه</Surface><Surface level={2}>سطح برجسته</Surface><Surface level={3}>سطح انتخابی</Surface><Surface glass>شیشه کنترل‌شده</Surface></div></section>

      <section className="ndl-validation__section" aria-labelledby="actions-title"><h2 id="actions-title">اقدام‌ها و وضعیت‌ها</h2><div className="ndl-validation__row"><Button>اقدام اصلی</Button><Button variant="secondary">اقدام دوم</Button><Button variant="ghost">اقدام آرام</Button><Button variant="danger">اقدام حساس</Button><Button loading>در حال پردازش</Button><IconButton label="اعلان نمونه"><Bell size={19} /></IconButton></div><div className="ndl-validation__row"><Badge>خنثی</Badge><Badge tone="premium">ویژه</Badge><Badge tone="info">اطلاعات</Badge><Badge tone="success">موفق</Badge><Badge tone="warning">هشدار</Badge><Badge tone="danger">خطا</Badge><Chip selected>انتخاب‌شده</Chip><Chip>قابل انتخاب</Chip></div></section>

      <section className="ndl-validation__section" aria-labelledby="inputs-title"><h2 id="inputs-title">ورودی‌ها</h2><div className="ndl-validation__grid"><Input label="برچسب پایدار" placeholder="متن نمونه" hint="راهنمای خنثی ورودی" /><PasswordInput label="رمز نمونه" autoComplete="current-password" /><SearchInput label="جستجوی نمونه" placeholder="عبارت آزمایشی" /><Input label="حالت خطا" defaultValue="مقدار آزمایشی" error="پیام خطای قابل‌خواندن" /></div></section>

      <section className="ndl-validation__section" aria-labelledby="data-title"><h2 id="data-title">نمایش داده خنثی</h2><div className="ndl-validation__grid"><Card><Metric label="شاخص نمونه" value="—" detail="بدون معنای کسب‌وکار" trend="نمونه" tone="info" /></Card><Card><Progress value={64} label="پیشرفت نمایشی" /></Card><Card><div className="ndl-validation__loading"><Spinner /><span>بارگذاری نمونه</span></div></Card><Card><Skeleton lines={3} /></Card><Card><div className="ndl-validation__avatars"><Avatar name="کاربر نمونه" /><Avatar name="Neutral User" size="large" /></div></Card></div></section>

      <section className="ndl-validation__section" aria-labelledby="navigation-title"><h2 id="navigation-title">پوسته و ناوبری</h2><SharedAppShell preview label="نمونه خنثی" navigation={neutralNavigation} activeNavigationId={activeNav} onNavigate={setActiveNav} header={<AppHeader brand="نمونه خنثی" subtitle="پوسته مشترک" actions={[{ label: 'جستجو', icon: <Search size={18} /> }]} profileName="کاربر نمونه" />} commandBar={<CommandBar label="فرمان خنثی" />}><div className="ndl-validation__shell-body"><Tabs items={[{ id: 'first', label: 'بخش نخست', panel: <p>محتوای خنثی بخش نخست.</p> }, { id: 'second', label: 'بخش دوم', panel: <p>محتوای خنثی بخش دوم.</p> }, { id: 'disabled', label: 'غیرفعال', panel: null, disabled: true }]} activeId={activeTab} onChange={setActiveTab} /><AIAction label="اقدام هوشمند نمونه" /></div></SharedAppShell></section>

      <section className="ndl-validation__section" aria-labelledby="overlay-title"><h2 id="overlay-title">لایه‌های موقت</h2><div className="ndl-validation__row"><Button startIcon={<Sparkles size={18} />} onClick={() => setDialogOpen(true)}>بازکردن دیالوگ</Button><Button variant="secondary" onClick={() => setSheetOpen(true)}>بازکردن Bottom Sheet</Button><Button variant="ghost" onClick={() => setToastOpen(true)}>نمایش Toast</Button></div></section>

      <Dialog open={dialogOpen} title="دیالوگ خنثی" description="نمونه رفتار فوکوس، Escape و پس‌زمینه." onClose={() => setDialogOpen(false)} primaryAction={{ label: 'تأیید نمونه', onClick: () => setDialogOpen(false) }}><p>این متن هیچ تصمیم یا اقدام واقعی را نمایندگی نمی‌کند.</p></Dialog>
      <BottomSheet open={sheetOpen} title="برگه پایین خنثی" onClose={() => setSheetOpen(false)}><p>نمونه مناسب نمایش در اندازه‌های موبایل.</p></BottomSheet>
      <Toast open={toastOpen} tone="success" message="پیام نمونه با وضعیت موفق" action={{ label: 'باشه', onClick: () => setToastOpen(false) }} onDismiss={() => setToastOpen(false)} />

      <aside className="ndl-validation__evidence"><Check size={18} /><span>محتوا خنثی است؛ Figma و معنای کسب‌وکار همچنان خارج از این صفحه‌اند.</span><CircleAlert size={18} /><span>نگاشت Figma: FIGMA_MAPPING_PENDING</span></aside>
    </div>
  )
}
