import { BarChart3, Database, FileBarChart, ShieldCheck } from 'lucide-react'

export function ReportsScreen() {
  return (
    <div className="ng-screen" data-trace-id="SCR-S5-03">
      <section className="ng-page-heading">
        <span className="ng-eyebrow">Reports</span>
        <h1>گزارش‌ها و تحلیل</h1>
        <p>Official Varanegar report، Semantic KPI و Raw analytical estimate باید در UI از هم متمایز بمانند.</p>
      </section>

      <div className="ng-action-grid">
        <article className="ng-action-card"><FileBarChart /><strong>گزارش‌های عملیاتی</strong><span>گزارش‌های مجاز Role</span></article>
        <article className="ng-action-card"><BarChart3 /><strong>KPI و روند</strong><span>Semantic-aware</span></article>
        <article className="ng-action-card"><Database /><strong>Data / Schema</strong><span>Catalog و lineage</span></article>
        <article className="ng-action-card"><ShieldCheck /><strong>وضعیت صحت</strong><span>Proven / Partial / Open</span></article>
      </div>

      <div className="ng-semantic-note">
        <strong>Semantic Gate</strong>
        <span>هیچ جمع خامی بدون Semantic Parity به‌عنوان KPI رسمی نمایش داده نمی‌شود.</span>
      </div>
    </div>
  )
}
