import type { ComponentProps, HTMLAttributes, PropsWithChildren } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import './composition.css'

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ')
}

type BoxProps = PropsWithChildren<HTMLAttributes<HTMLElement>>

export function AppScene({ className, ...props }: BoxProps) {
  return <section {...props} className={cx('ngc-scene', className)} />
}

export function ContextStrip({ className, ...props }: BoxProps) {
  return <section {...props} className={cx('ngc-context-strip', className)} />
}

export function FocusSurface({ className, ...props }: BoxProps) {
  return <section {...props} className={cx('ngc-focus-surface', className)} />
}
export function ActionRail({ className, ...props }: BoxProps) {
  return <nav {...props} className={cx('ngc-action-rail', className)} />
}

type PressableProps = ComponentProps<typeof motion.button> & {
  emphasis?: 'quiet' | 'standard' | 'primary'
}

export function Pressable({
  className,
  children,
  emphasis = 'standard',
  type = 'button',
  ...props
}: PressableProps) {
  const reducedMotion = useReducedMotion()

  return (
    <motion.button
      {...props}
      type={type}
      className={cx('ngc-pressable', 'is-' + emphasis, className)}
      {...(reducedMotion ? {} : { whileTap: { scale: 0.975, y: 1 } })}
      transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
    >
      {children}
    </motion.button>
  )
}
