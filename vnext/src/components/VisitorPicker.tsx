import { useMemo, useState } from 'react'
import { CheckCircleIcon, ChevronLeftIcon, SearchIcon } from './Icons'

export type VisitorPickerOption = {
  value: string
  label: string
  meta?: string
  disabled?: boolean
}

type Props = {
  label: string
  value: string
  options: VisitorPickerOption[]
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  sheetTitle?: string
  searchable?: boolean
}

export function VisitorPicker({
  label,
  value,
  options,
  onChange,
  placeholder = 'انتخاب کنید',
  disabled = false,
  className = '',
  sheetTitle,
  searchable,
}: Props) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const selected = options.find((option) => option.value === value)
  const canSearch = searchable ?? options.length > 7
  const visible = useMemo(() => {
    const q = query.trim().toLocaleLowerCase('fa')
    if (!q) return options
    return options.filter((option) =>
      [option.label, option.meta].filter(Boolean).join(' ').toLocaleLowerCase('fa').includes(q),
    )
  }, [options, query])

  return (
    <div className={`vds-picker ${className}`}>
      <span className="vds-picker-label">{label}</span>
      <button
        type="button"
        className="vds-picker-trigger ng-living-interactive"
        disabled={disabled}
        onClick={() => {
          setQuery('')
          setOpen(true)
        }}
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <span>
          <strong>{selected?.label || placeholder}</strong>
          {selected?.meta ? <small>{selected.meta}</small> : null}
        </span>
        <ChevronLeftIcon />
      </button>

      {open ? (
        <div className="vds-picker-backdrop" onClick={() => setOpen(false)}>
          <section
            className="vds-picker-sheet"
            role="dialog"
            aria-modal="true"
            aria-label={sheetTitle || label}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="vds-picker-handle" />
            <header>
              <div>
                <small>انتخاب</small>
                <h2>{sheetTitle || label}</h2>
                <span>{options.length.toLocaleString('fa-IR')} گزینه</span>
              </div>
              <button type="button" className="vds-picker-close" onClick={() => setOpen(false)} aria-label="بستن">×</button>
            </header>

            {canSearch ? (
              <label className="vds-picker-search">
                <SearchIcon />
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="جست‌وجو…" />
              </label>
            ) : null}

            <div className="vds-picker-list">
              {visible.map((option) => {
                const active = option.value === value
                return (
                  <button
                    type="button"
                    key={option.value}
                    className={active ? 'active' : ''}
                    disabled={option.disabled}
                    onClick={() => {
                      if (!option.disabled) onChange(option.value)
                      setOpen(false)
                    }}
                  >
                    <span>
                      <strong>{option.label}</strong>
                      {option.meta ? <small>{option.meta}</small> : null}
                    </span>
                    {active ? <CheckCircleIcon /> : <ChevronLeftIcon />}
                  </button>
                )
              })}
              {!visible.length ? <div className="vds-picker-empty">گزینه‌ای مطابق جست‌وجو پیدا نشد.</div> : null}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  )
}
