import { moduleCatalog } from '../../app/navigation'

export function ModulesScreen() {
  return (
    <div className="ng-screen" data-trace-id="SCR-S4-01">
      <section className="ng-page-heading">
        <span className="ng-eyebrow">Modules Hub</span>
        <h1>ماژول‌های NeginAI</h1>
        <p>Featureها از Project Map می‌آیند؛ Role فقط دسترسی و اولویت را تعیین می‌کند.</p>
      </section>

      <div className="ng-module-grid">
        {moduleCatalog.map((module) => {
          const Icon = module.icon
          return (
            <button className="ng-module-card" type="button" key={module.id} data-trace-id={module.id}>
              <span className="ng-module-icon"><Icon size={23} /></span>
              <span className="ng-module-copy">
                <strong>{module.label}</strong>
                <small>{module.description}</small>
              </span>
              <span className="ng-module-id">{module.id}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
