import type { Meta, StoryObj } from '@storybook/react-vite'

function AtlasFoundation() {
  return (
    <main className="ng-stage" style={{ width: 'min(860px, 92vw)', padding: '24px' }}>
      <header style={{ marginBottom: 20 }}>
        <small className="ng-tone-gold">NeginAI Design System Atlas</small>
        <h2 style={{ margin: '6px 0' }}>Spatial Enterprise Neo</h2>
        <p style={{ color: 'var(--ng-muted)', margin: 0 }}>
          Living, tactile, RTL-first and depth-first component foundation.
        </p>
      </header>
      <section className="ng-connected-stack">
        <article className="ng-surface" style={{ padding: 18 }}>
          <strong>Connected Surface</strong>
          <p style={{ color: 'var(--ng-muted)' }}>سطح متصل برای اطلاعات و عملیات اصلی.</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="ng-action-primary ng-interactive">اقدام اصلی</button>
            <button className="ng-action-secondary ng-interactive">اقدام ثانویه</button>
            <button className="ng-action-ghost ng-interactive">جزئیات</button>
          </div>
        </article>
        <article className="ng-detail-surface" style={{ padding: 18 }}>
          <strong>Semantic states</strong>
          <div style={{ display: 'flex', gap: 12, marginTop: 12, flexWrap: 'wrap' }}>
            <span className="ng-tone-mint">● Success</span>
            <span className="ng-tone-warning">● Warning</span>
            <span className="ng-tone-danger">● Risk</span>
            <span className="ng-tone-info">● Info</span>
          </div>
        </article>
      </section>
    </main>
  )
}

const meta = {
  title: 'Design System/Atlas Foundation',
  component: AtlasFoundation,
  tags: ['autodocs'],
} satisfies Meta<typeof AtlasFoundation>

export default meta
type Story = StoryObj<typeof meta>
export const Foundation: Story = {}
