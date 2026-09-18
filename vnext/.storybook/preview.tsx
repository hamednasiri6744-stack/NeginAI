import type { Preview } from '@storybook/react-vite'
import '../src/design-system/core/index.css'
import '../src/design-system/components/components.css'
import '../src/styles/global.css'

const preview: Preview = {
  parameters: {
    layout: 'centered',
    controls: { expanded: true },
    a11y: { test: 'todo' },
  },
  decorators: [
    (Story) => (
      <div dir="rtl" style={{ minWidth: 320, color: 'var(--ng-text)' }}>
        <Story />
      </div>
    ),
  ],
}

export default preview
