export type LivingState =
  | 'idle'
  | 'ambient'
  | 'live'
  | 'updating'
  | 'changed'
  | 'attention'
  | 'active'

export type LivingTone = 'gold' | 'mint' | 'blue' | 'danger'

export function livingClass(...names: Array<string | false | null | undefined>) {
  return names.filter(Boolean).join(' ')
}
