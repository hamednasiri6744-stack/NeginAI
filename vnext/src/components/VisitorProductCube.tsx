import { useRef, useState, type TouchEvent } from 'react'

export type ProductCubeSaleUnit = { name: string; factor: number; ref?: string | number | null }

export type VisitorProductCubeProps = {
  productId: string; name: string; code: string; brand?: string | null; group?: string | null; unit: string
  catalogImageUrl?: string | null; quantity: number; saleUnitName: string; saleUnitFactor: number
  saleUnits: ProductCubeSaleUnit[]; available: number; showStock: boolean; minOrder?: number; maxOrder?: number
  indicativePrice?: number; onQuantityChange: (quantity: number) => void; onSaleUnitFactorChange: (factor: number) => void
}

const SWIPE_THRESHOLD = 44

export function VisitorProductCube(props: VisitorProductCubeProps) {
  const { productId, name, code, brand, group, unit, catalogImageUrl, quantity, saleUnitName, saleUnitFactor, saleUnits, available, showStock, minOrder = 0, maxOrder = 0, indicativePrice = 0, onQuantityChange, onSaleUnitFactorChange } = props
  const [flipped, setFlipped] = useState(false)
  const touchStart = useRef<{ x: number; y: number } | null>(null)
  const factor = Math.max(1, Number(saleUnitFactor) || 1)
  const effectiveMax = maxOrder > 0 ? Math.min(maxOrder, available) : available

  const onTouchStart = (event: TouchEvent<HTMLElement>) => {
    const touch = event.touches[0]
    touchStart.current = touch ? { x: touch.clientX, y: touch.clientY } : null
  }
  const onTouchEnd = (event: TouchEvent<HTMLElement>) => {
    const start = touchStart.current; const touch = event.changedTouches[0]; touchStart.current = null
    if (!start || !touch) return
    const dx = touch.clientX - start.x; const dy = touch.clientY - start.y
    if (Math.abs(dx) >= SWIPE_THRESHOLD && Math.abs(dx) > Math.abs(dy) * 1.2) setFlipped((value) => !value)
  }

  return (
    <article className={`vo-product-cube${flipped ? ' is-flipped' : ''}${quantity > 0 ? ' has-quantity' : ''}`} data-product-id={productId} data-in-cart={quantity > 0 ? 'true' : 'false'} onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
      <div className="vo-product-cube-inner">
        <section className="vo-product-cube-face vo-product-cube-catalog" aria-hidden={flipped}>
          <div className="vo-product-cube-media">
            {catalogImageUrl ? <img src={catalogImageUrl} alt="" loading="lazy" /> : <span className="vo-product-cube-fallback" aria-hidden="true">□</span>}
            {quantity > 0 ? <b className="vo-product-cube-badge">{(quantity / factor).toLocaleString('fa-IR')} {saleUnitName}</b> : null}
          </div>
          <div className="vo-product-cube-copy"><small>{group || brand || 'کاتالوگ محصول'}</small><strong>{name}</strong><span>{code}{brand ? ` · ${brand}` : ''}</span></div>
          <button type="button" className="vo-product-cube-turn" onClick={() => setFlipped(true)} aria-label={`باز کردن سفارش ${name}`}>{quantity > 0 ? 'ویرایش' : 'سفارش'}</button>
        </section>
        <section className="vo-product-cube-face vo-product-cube-order" aria-hidden={!flipped}>
          <header><div><strong>{name}</strong><small>{code}{brand ? ` · ${brand}` : ''}</small></div><button type="button" className="vo-product-cube-back" onClick={() => setFlipped(false)} aria-label={`بازگشت به کاتالوگ ${name}`}>↩</button></header>
          <div className="vo-product-cube-meta"><span>{unit}</span>{showStock ? <span>موجودی: <b>{available}</b></span> : <span>موجودی: NGT</span>}{minOrder > 0 ? <span>حداقل: <b>{minOrder}</b></span> : null}{maxOrder > 0 ? <span>حداکثر: <b>{maxOrder}</b></span> : null}</div>
          {saleUnits.length > 1 ? <div className="vo-product-cube-units" aria-label="واحد فروش">{saleUnits.map((saleUnit) => <button type="button" key={`${saleUnit.ref ?? saleUnit.name}-${saleUnit.factor}`} className={Number(saleUnit.factor) === factor ? 'active' : ''} onClick={() => onSaleUnitFactorChange(Number(saleUnit.factor))}>{saleUnit.name}</button>)}</div> : null}
          <div className="vo-product-cube-price"><strong>{indicativePrice > 0 ? indicativePrice.toLocaleString('fa-IR') : '—'}</strong><small>قیمت نمایشی؛ مبلغ نهایی در Preview رسمی NGT</small></div>
          <div className="vo-product-cube-stepper"><button type="button" onClick={() => onQuantityChange(Math.max(0, quantity - factor))} disabled={quantity <= 0} aria-label={`کاهش ${name}`}>−</button><strong><b>{(quantity / factor).toLocaleString('fa-IR')}</b><small>{saleUnitName}</small></strong><button type="button" onClick={() => onQuantityChange(quantity + factor)} disabled={effectiveMax < quantity + factor} aria-label={`افزایش ${name}`}>+</button></div>
        </section>
      </div>
    </article>
  )
}
