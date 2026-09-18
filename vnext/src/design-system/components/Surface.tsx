import type { HTMLAttributes, ReactNode } from 'react'
import { cx } from './utils'

export type SurfaceTone = 'stage' | 'surface' | 'detail' | 'floating' | 'inset'
type SurfaceTag = 'div' | 'section' | 'article' | 'header' | 'aside'

type SurfaceProps = HTMLAttributes<HTMLElement> & {
  as?: SurfaceTag
  tone?: SurfaceTone
  interactive?: boolean
  children: ReactNode
}

const toneClass: Record<SurfaceTone, string> = {
  stage: 'ng-stage',
  surface: 'ng-surface',
  detail: 'ng-detail-surface',
  floating: 'ng-floating-surface',
  inset: 'ng-inset-surface',
}

export function Surface({
  as = 'div',
  tone = 'surface',
  interactive = false,
  className,
  children,
  ...props
}: SurfaceProps) {
  const Tag = as
  return (
    <Tag className={cx(toneClass[tone], interactive && 'ng-interactive', className)} {...props}>
      {children}
    </Tag>
  )
}
