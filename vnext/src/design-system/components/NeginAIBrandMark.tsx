export function NeginAIBrandMark({ className = "" }: { className?: string }) {
  return (
    <img
      className={`ng-brand-symbol ${className}`.trim()}
      src="/brand/neginai-logo-canonical.webp"
      alt=""
      aria-hidden="true"
      draggable={false}
    />
  )
}
