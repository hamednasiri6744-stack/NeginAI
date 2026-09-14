import { useEffect, useMemo, useState } from 'react'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import { createPrototypeDraftId, findPrototypeDraft, savePrototypeDraft } from '../state/visitorDraftStore'
import { clearVisitorOrderWorkspace, readVisitorOrderWorkspace, writeVisitorOrderWorkspace } from '../state/visitorOrderWorkspaceStore'
import { visitorCustomers } from '../data/visitorCustomers'
import {
  BellIcon,
  BoxIcon,
  CartIcon,
  ChartIcon,
  CheckCircleIcon,
  ChevronLeftIcon,
  ClipboardIcon,
  FilterIcon,
  InvoiceIcon,
  HomeIcon,
  MapIcon,
  MicIcon,
  PinIcon,
  PlusIcon,
  SearchIcon,
  StoreIcon,
  TagIcon,
  TrashIcon,
  UserGroupIcon,
} from './Icons'

import { useVisitorNotifications } from '../state/VisitorNotificationsContext'

type Props = {
  onNavigate: (path: string) => void
  customerId?: string | undefined
  draftId?: string | undefined
  visitId?: string | undefined
  returnTo?: string | undefined
}

type View = 'products' | 'catalog' | 'cart'
type Payment = 'credit' | 'cash' | 'cheque'
type OrderType = 'sale' | 'request'

type Product = {
  id: number
  name: string
  code: string
  brand: string
  group: string
  stock: number
  unit: string
  cartonSize: number
  price: number
  consumer: number
  discount: number
}

const customers = visitorCustomers.map((customer) => ({
  id: customer.id,
  name: customer.name,
  code: customer.code,
  area: customer.area,
}))


const products: Product[] = [
  { id: 101, name: 'مایع ظرفشویی ۷۵۰ گرمی', code: '143233101', brand: 'سیلانه سبز', group: 'شوینده', stock: 34, unit: 'کارتن', cartonSize: 12, price: 685000, consumer: 810000, discount: 5 },
  { id: 102, name: 'مایع لباسشویی ۲.۷ لیتری', code: '143233118', brand: 'سیلانه سبز', group: 'شوینده', stock: 18, unit: 'کارتن', cartonSize: 6, price: 1240000, consumer: 1470000, discount: 8 },
  { id: 103, name: 'دستمال کاغذی ۲۰۰ برگ', code: '221045901', brand: 'نرمین', group: 'سلولزی', stock: 52, unit: 'کارتن', cartonSize: 24, price: 910000, consumer: 1080000, discount: 3 },
  { id: 104, name: 'شامپو روزانه ۴۰۰ میل', code: '310224011', brand: 'ویتا', group: 'بهداشت', stock: 9, unit: 'کارتن', cartonSize: 12, price: 1380000, consumer: 1590000, discount: 0 },
  { id: 105, name: 'صابون کرمی ۶ عددی', code: '310224080', brand: 'ویتا', group: 'بهداشت', stock: 0, unit: 'کارتن', cartonSize: 8, price: 760000, consumer: 920000, discount: 4 },
  { id: 106, name: 'کیسه زباله رولی بزرگ', code: '221047755', brand: 'هوم‌پلاس', group: 'مصرفی', stock: 27, unit: 'کارتن', cartonSize: 20, price: 830000, consumer: 995000, discount: 6 },
]

const catalogs = [
  { name: 'شوینده', count: 2, hint: 'ظرفشویی و لباسشویی', icon: '✦' },
  { name: 'سلولزی', count: 1, hint: 'دستمال و سلولزی', icon: '▦' },
  { name: 'بهداشت', count: 2, hint: 'شامپو و صابون', icon: '◌' },
  { name: 'مصرفی', count: 1, hint: 'مصرف روزمره', icon: '◇' },
]

function money(value: number) {
  return new Intl.NumberFormat('fa-IR').format(value)
}

export function VisitorOrdersScreen({ onNavigate, customerId, draftId, visitId, returnTo }: Props) {
  const { unreadCount } = useVisitorNotifications()
  const { activeVisit, attachDraft, completeVisit } = useVisitorWorkflow()
  const effectiveVisitId = visitId ?? activeVisit?.id
  const visitCustomerId = activeVisit && (!visitId || activeVisit.id === visitId) ? activeVisit.customerId : undefined
  const requestedDraft = findPrototypeDraft(draftId)
  const draftConflict = Boolean(requestedDraft && visitCustomerId && requestedDraft.customerId !== visitCustomerId)
  const restoredDraft = requestedDraft && !draftConflict ? requestedDraft : undefined
  const storedWorkspace = readVisitorOrderWorkspace()
  const canRestoreWorkspace = !draftId && !restoredDraft && storedWorkspace
    && (!visitId || storedWorkspace.visitId === visitId)
    && (!customerId || storedWorkspace.customerId === customerId)
  const effectiveCustomerId = visitCustomerId ?? restoredDraft?.customerId ?? (canRestoreWorkspace ? storedWorkspace?.customerId : undefined) ?? customerId ?? '1'
  const initialCustomer = customers.find((customer) => customer.id === effectiveCustomerId) ?? customers[0]!
  const [view, setView] = useState<View>(() => canRestoreWorkspace ? storedWorkspace?.view ?? 'products' : 'products')
  const [selectedCustomer, setSelectedCustomer] = useState(initialCustomer)
  const [query, setQuery] = useState('')
  const [brand, setBrand] = useState('همه')
  const [group, setGroup] = useState('همه')
  const [inStockOnly, setInStockOnly] = useState(true)
  const [cart, setCart] = useState<Record<number, number>>(() => restoredDraft?.cart ?? (canRestoreWorkspace ? storedWorkspace?.cart ?? {} : {}))
  const [payment, setPayment] = useState<Payment>(restoredDraft?.payment ?? (canRestoreWorkspace ? storedWorkspace?.payment ?? 'credit' : 'credit'))
  const [orderType, setOrderType] = useState<OrderType>(restoredDraft?.orderType ?? (canRestoreWorkspace ? storedWorkspace?.orderType ?? 'sale' : 'sale'))
  const [notice, setNotice] = useState<string | null>(() => draftConflict ? 'این پیش‌نویس متعلق به مشتری دیگری است؛ ابتدا بازدید فعال را تعیین‌تکلیف کن' : null)
  const [customerPicker, setCustomerPicker] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [pendingCustomer, setPendingCustomer] = useState<(typeof customers)[number] | null>(null)
  const [activeDraftId, setActiveDraftId] = useState<string | undefined>(restoredDraft?.id ?? (canRestoreWorkspace ? storedWorkspace?.draftId : undefined))
  const visitLocked = Boolean(effectiveVisitId && activeVisit)

  useEffect(() => {
    writeVisitorOrderWorkspace({
      version: 1,
      customerId: selectedCustomer.id,
      visitId: effectiveVisitId,
      draftId: activeDraftId,
      cart,
      payment,
      orderType,
      view,
      updatedAt: Date.now(),
    })
  }, [activeDraftId, cart, effectiveVisitId, orderType, payment, selectedCustomer.id, view])

  const brands = ['همه', ...Array.from(new Set(products.map((product) => product.brand)))]

  const visibleProducts = useMemo(() => products.filter((product) => {
    const q = query.trim()
    const matchesQuery = !q || `${product.name} ${product.code} ${product.brand}`.includes(q)
    const matchesBrand = brand === 'همه' || product.brand === brand
    const matchesGroup = group === 'همه' || product.group === group
    const matchesStock = !inStockOnly || product.stock > 0
    return matchesQuery && matchesBrand && matchesGroup && matchesStock
  }), [brand, group, inStockOnly, query])

  const cartLines = useMemo(() => products
    .filter((product) => (cart[product.id] ?? 0) > 0)
    .map((product) => ({ ...product, quantity: cart[product.id] ?? 0 })), [cart])

  const cartCount = cartLines.reduce((sum, line) => sum + line.quantity, 0)
  const gross = cartLines.reduce((sum, line) => sum + line.price * line.quantity, 0)
  const discount = cartLines.reduce((sum, line) => sum + line.price * line.quantity * (line.discount / 100), 0)
  const taxable = Math.max(0, gross - discount)
  const tax = Math.round(taxable * 0.10)
  const payable = Math.round(taxable + tax)

  function flash(message: string) {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2200)
  }

  function setQuantity(product: Product, quantity: number) {
    const next = Math.max(0, Math.min(product.stock, quantity))
    if (quantity > product.stock) flash(`حداکثر موجودی ${product.stock} ${product.unit} است`)
    setCart((current) => {
      const updated = { ...current }
      if (next === 0) delete updated[product.id]
      else updated[product.id] = next
      return updated
    })
  }

  function openCatalog(name: string) {
    setGroup(name)
    setView('products')
    flash(`کاتالوگ ${name} فعال شد`)
  }

  function saveDraft() {
    if (!cartLines.length) {
      flash('سبد سفارش خالی است')
      return null
    }
    const id = activeDraftId ?? createPrototypeDraftId()
    savePrototypeDraft({
      id,
      customerId: selectedCustomer.id,
      customer: selectedCustomer.name,
      area: selectedCustomer.area,
      cart,
      payment,
      orderType,
      amount: payable,
      updatedAt: Date.now(),
      visitId: effectiveVisitId,
    })
    setActiveDraftId(id)
    attachDraft(id)
    flash(`پیش‌نویس ${id} روی این دستگاه ذخیره شد`)
    return id
  }

  function submitOrder() {
    if (!cartLines.length) {
      flash('برای ادامه حداقل یک کالا اضافه کن')
      return
    }
    setReviewOpen(true)
  }

  function applyCustomerChange(customer: (typeof customers)[number]) {
    setSelectedCustomer(customer)
    setCart({})
    setActiveDraftId(undefined)
    attachDraft(null)
    clearVisitorOrderWorkspace()
    setCustomerPicker(false)
    setPendingCustomer(null)
    flash('مشتری تغییر کرد؛ سبد برای جلوگیری از انتقال اشتباه کالا پاک شد')
  }

  function requestCustomerChange(customer: (typeof customers)[number]) {
    if (customer.id === selectedCustomer.id) {
      setCustomerPicker(false)
      return
    }
    if (visitLocked) {
      flash('مشتری سفارش در بازدید فعال قابل تغییر نیست')
      return
    }
    if (cartLines.length) {
      setPendingCustomer(customer)
      setCustomerPicker(false)
      return
    }
    applyCustomerChange(customer)
  }

  function finishVisitWithDraft() {
    const id = saveDraft()
    if (!id) return
    completeVisit(selectedCustomer.id, 'order-draft')
    clearVisitorOrderWorkspace()
    setReviewOpen(false)
    onNavigate(returnTo || `/visitor/route?customer=${selectedCustomer.id}`)
  }

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vo-shell">
        <header className="vh-header">
          <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">و</span>
            <span className="vh-profile-copy"><strong>ویزیتور</strong><small><PinIcon /> منطقه کرج</small></span>
            <ChevronLeftIcon />
          </button>
          <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}><BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}</button>
          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="vo-heading">
          <div><span>Order Workspace</span><h1>{activeDraftId ? 'ادامه پیش‌نویس' : 'سفارش جدید'}</h1><p>{activeDraftId ? `پیش‌نویس ${activeDraftId} بازیابی شده است` : effectiveVisitId ? 'این سفارش به بازدید فعال متصل است' : canRestoreWorkspace ? 'سفارش نیمه‌تمام بازیابی شد' : 'انتخاب کالا، کاتالوگ و سبد در یک جریان واحد'}</p></div>
          <div className="vo-heading-actions">
            <button type="button" className="vo-history" onClick={() => onNavigate(`/visitor/ai?context=order&customer=${selectedCustomer.id}${visitId ? `&visit=${visitId}` : ``}${activeDraftId ? `&draft=${activeDraftId}` : ``}`)}><span>AI</span><span>دستیار</span></button>
            <button type="button" className="vo-history" onClick={() => onNavigate('/visitor/orders/history')}><InvoiceIcon /><span>سوابق</span></button>
            <button type="button" className="vo-voice" onClick={() => flash('سفارش صوتی در فاز اتصال سرویس فعال می‌شود')}><MicIcon /><span>صوتی</span></button>
          </div>
        </section>

        <button type="button" className={visitLocked ? 'vo-customer locked' : 'vo-customer'} onClick={() => visitLocked ? flash('مشتری این سفارش از بازدید فعال تعیین شده است') : setCustomerPicker(true)}>
          <span className="vo-customer-icon"><StoreIcon /></span>
          <span className="vo-customer-copy"><small>مشتری سفارش</small><strong>{selectedCustomer.name}</strong><span>{selectedCustomer.code} · {selectedCustomer.area}</span></span>
          {visitLocked ? <span className="vo-customer-lock">قفل بازدید</span> : <ChevronLeftIcon />}
        </button>

        <section className="vo-tabs" role="tablist" aria-label="بخش سفارش">
          <button type="button" role="tab" aria-selected={view === 'products'} className={view === 'products' ? 'active' : ''} onClick={() => setView('products')}>محصولات</button>
          <button type="button" role="tab" aria-selected={view === 'catalog'} className={view === 'catalog' ? 'active' : ''} onClick={() => setView('catalog')}>کاتالوگ</button>
          <button type="button" role="tab" aria-selected={view === 'cart'} className={view === 'cart' ? 'active cart-tab' : 'cart-tab'} onClick={() => setView('cart')}>سبد <b>{cartCount}</b></button>
        </section>

        {view === 'products' ? (
          <section className="vo-products">
            <div className="vo-search-row">
              <label className="vo-search"><SearchIcon /><input aria-label="جست‌وجوی کالا" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="نام، کد یا برند کالا" /></label>
              <button type="button" aria-pressed={inStockOnly} className={inStockOnly ? 'active' : ''} onClick={() => setInStockOnly((current) => !current)}><FilterIcon /><span>موجود</span></button>
            </div>

            <div className="vo-filter-strip" role="group" aria-label="فیلتر برند">
              {brands.map((item) => <button type="button" key={item} aria-pressed={brand === item} className={brand === item ? 'active' : ''} onClick={() => setBrand(item)}>{item}</button>)}
            </div>

            {group !== 'همه' ? <div className="vo-active-filter"><TagIcon /><span>گروه: {group}</span><button type="button" onClick={() => setGroup('همه')}>×</button></div> : null}

            <div className="vo-list-head"><strong>{visibleProducts.length} کالا</strong><span>قیمت‌ها به تومان</span></div>
            <div className="vo-product-list">
              {visibleProducts.map((product) => {
                const quantity = cart[product.id] ?? 0
                return (
                  <article className={`vo-product ${product.stock === 0 ? 'unavailable' : ''}`} key={product.id}>
                    <div className="vo-product-top">
                      <span className="vo-product-icon"><BoxIcon /></span>
                      <div className="vo-product-copy"><strong>{product.name}</strong><span>{product.brand} · {product.group}</span><small>کد {product.code} · {product.cartonSize} عدد در {product.unit}</small></div>
                      {product.discount ? <span className="vo-discount">٪{product.discount}</span> : null}
                    </div>
                    <div className="vo-stock-row">
                      <span className={product.stock > 0 ? 'stock-ok' : 'stock-zero'}>موجودی: {product.stock} {product.unit}</span>
                      <span>مصرف‌کننده: {money(product.consumer)}</span>
                    </div>
                    <div className="vo-product-bottom">
                      <div className="vo-price"><small>قیمت فروش</small><strong>{money(product.price)}</strong></div>
                      {product.stock > 0 ? (
                        quantity > 0 ? (
                          <div className="vo-stepper" aria-label={`تعداد ${product.name}`}>
                            <button type="button" aria-label={`کاهش تعداد ${product.name}`} onClick={() => setQuantity(product, quantity - 1)}>−</button>
                            <strong>{quantity}</strong>
                            <button type="button" aria-label={`افزایش تعداد ${product.name}`} onClick={() => setQuantity(product, quantity + 1)}>+</button>
                          </div>
                        ) : <button type="button" className="vo-add" onClick={() => setQuantity(product, 1)}><PlusIcon /> افزودن</button>
                      ) : <span className="vo-out">ناموجود</span>}
                    </div>
                  </article>
                )
              })}
            </div>
          </section>
        ) : null}

        {view === 'catalog' ? (
          <section className="vo-catalog-view">
            <div className="vo-catalog-head"><div><strong>کاتالوگ گروهی</strong><span>ورود سریع به گروه‌های کالا</span></div><span>{products.length} کالا</span></div>
            <div className="vo-catalog-grid">
              {catalogs.map((catalog) => (
                <button type="button" key={catalog.name} onClick={() => openCatalog(catalog.name)}>
                  <span className="vo-catalog-symbol">{catalog.icon}</span>
                  <strong>{catalog.name}</strong>
                  <small>{catalog.hint}</small>
                  <b>{catalog.count} کالا</b>
                </button>
              ))}
            </div>
            <article className="vo-catalog-note"><BoxIcon /><div><strong>حالت کاتالوگ آفلاین</strong><span>تصاویر و Cache کاتالوگ در مرحله اتصال داده فعال می‌شوند؛ ساختار آن حذف نشده است.</span></div></article>
          </section>
        ) : null}

        {view === 'cart' ? (
          <section className="vo-cart-view">
            <div className="vo-cart-head"><div><strong>سبد سفارش</strong><span>{cartLines.length} قلم · {cartCount} واحد فروش</span></div><button type="button" onClick={saveDraft}><ClipboardIcon /> ذخیره پیش‌نویس</button></div>

            {cartLines.length ? <div className="vo-cart-lines">
              {cartLines.map((line) => (
                <article key={line.id} className="vo-cart-line">
                  <span className="vo-cart-icon"><BoxIcon /></span>
                  <div className="vo-cart-copy"><strong>{line.name}</strong><span>{line.brand} · {line.unit}</span><small>{money(line.price)} × {line.quantity}</small></div>
                  <button type="button" className="vo-trash" onClick={() => setQuantity(line, 0)} aria-label={`حذف ${line.name}`}><TrashIcon /></button>
                  <div className="vo-cart-stepper" aria-label={`تعداد ${line.name}`}><button type="button" aria-label={`کاهش تعداد ${line.name}`} onClick={() => setQuantity(line, line.quantity - 1)}>−</button><strong>{line.quantity}</strong><button type="button" aria-label={`افزایش تعداد ${line.name}`} onClick={() => setQuantity(line, line.quantity + 1)}>+</button></div>
                  <strong className="vo-line-total">{money(Math.round(line.price * line.quantity * (1 - line.discount / 100)))}</strong>
                </article>
              ))}
            </div> : <div className="vo-empty"><CartIcon /><strong>سبد سفارش خالی است</strong><span>از بخش محصولات کالا اضافه کن.</span><button type="button" onClick={() => setView('products')}>رفتن به محصولات</button></div>}

            <section className="vo-choice-block">
              <div><strong>نوع پرداخت</strong><span>براساس دسترسی و شرایط مشتری</span></div>
              <div className="vo-choice-row">
                <button type="button" aria-pressed={payment === 'credit'} className={payment === 'credit' ? 'active' : ''} onClick={() => setPayment('credit')}>اعتباری</button>
                <button type="button" aria-pressed={payment === 'cash'} className={payment === 'cash' ? 'active' : ''} onClick={() => setPayment('cash')}>نقدی</button>
                <button type="button" aria-pressed={payment === 'cheque'} className={payment === 'cheque' ? 'active' : ''} onClick={() => setPayment('cheque')}>چک</button>
              </div>
            </section>

            <section className="vo-choice-block compact">
              <div><strong>نوع سفارش</strong></div>
              <div className="vo-choice-row two">
                <button type="button" aria-pressed={orderType === 'sale'} className={orderType === 'sale' ? 'active' : ''} onClick={() => setOrderType('sale')}>فروش</button>
                <button type="button" aria-pressed={orderType === 'request'} className={orderType === 'request' ? 'active' : ''} onClick={() => setOrderType('request')}>درخواست / پیش‌فاکتور</button>
              </div>
            </section>

            <section className="vo-summary">
              <div><span>جمع کالا</span><strong>{money(gross)}</strong></div>
              <div className="discount"><span>تخفیف</span><strong>− {money(Math.round(discount))}</strong></div>
              <div><span>مالیات</span><strong>{money(tax)}</strong></div>
              <div className="total"><span>قابل پرداخت</span><strong>{money(payable)} <small>تومان</small></strong></div>
            </section>

            <div className="vo-submit-row">
              <button type="button" className="draft" onClick={saveDraft}>ذخیره پیش‌نویس</button>
              <button type="button" className="submit" onClick={submitOrder}><CheckCircleIcon /> بررسی سفارش</button>
            </div>
          </section>
        ) : null}

        {customerPicker ? (
          <div className="vo-sheet-backdrop" onClick={() => setCustomerPicker(false)}>
            <section className="vo-sheet" role="dialog" aria-modal="true" aria-label="انتخاب مشتری" onClick={(event) => event.stopPropagation()}>
              <div className="vo-sheet-handle" />
              <h2>انتخاب مشتری سفارش</h2>
              <div className="vo-customer-list">
                {customers.map((customer) => <button type="button" key={customer.id} className={selectedCustomer.id === customer.id ? 'active' : ''} onClick={() => requestCustomerChange(customer)}><StoreIcon /><span><strong>{customer.name}</strong><small>{customer.code} · {customer.area}</small></span>{selectedCustomer.id === customer.id ? <CheckCircleIcon /> : <ChevronLeftIcon />}</button>)}
              </div>
            </section>
          </div>
        ) : null}

        {reviewOpen ? (
          <div className="vo-sheet-backdrop" onClick={() => setReviewOpen(false)}>
            <section className="vo-success" role="dialog" aria-modal="true" aria-label="بررسی سفارش" onClick={(event) => event.stopPropagation()}>
              <span className="vo-success-icon"><CheckCircleIcon /></span>
              <small>ثبت نهایی هنوز به سرویس سازمانی متصل نیست</small>
              <h2>سفارش آماده بررسی است</h2>
              <p>{selectedCustomer.name}</p>
              <div><span>وضعیت</span><strong>هنوز ثبت یا ارسال نشده</strong></div>
              <div><span>مبلغ محاسبه‌شده</span><strong>{money(payable)} تومان</strong></div>
              {effectiveVisitId ? <div><span>بازدید مرتبط</span><strong>فعال</strong></div> : null}
              <button type="button" className="primary" onClick={() => setReviewOpen(false)}>بازگشت به سبد</button>
              {effectiveVisitId ? (
                <button type="button" onClick={finishVisitWithDraft}>ذخیره پیش‌نویس و پایان بازدید</button>
              ) : (
                <button type="button" onClick={() => { const id = saveDraft(); if (id) { setReviewOpen(false); clearVisitorOrderWorkspace(); onNavigate('/visitor/orders/history') } }}>ذخیره پیش‌نویس و مشاهده سوابق</button>
              )}
            </section>
          </div>
        ) : null}

        {pendingCustomer ? (
          <div className="vo-sheet-backdrop" onClick={() => setPendingCustomer(null)}>
            <section className="vo-success" role="dialog" aria-modal="true" aria-label="تأیید تغییر مشتری" onClick={(event) => event.stopPropagation()}>
              <span className="vo-success-icon"><StoreIcon /></span>
              <h2>تغییر مشتری سفارش؟</h2>
              <p>سبد فعلی متعلق به {selectedCustomer.name} است.</p>
              <div className="vo-change-warning">برای جلوگیری از انتقال اشتباه کالا بین مشتریان، با تغییر مشتری سبد فعلی پاک می‌شود.</div>
              <button type="button" className="primary" onClick={() => applyCustomerChange(pendingCustomer)}>تغییر مشتری و پاک‌کردن سبد</button>
              <button type="button" onClick={() => setPendingCustomer(null)}>انصراف</button>
            </section>
          </div>
        ) : null}

        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order active" type="button" aria-current="page" onClick={() => setView('cart')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
