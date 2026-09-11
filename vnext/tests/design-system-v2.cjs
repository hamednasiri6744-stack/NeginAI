const fs = require('node:fs')
const path = require('node:path')

const root = path.resolve(__dirname, '..', 'src', 'design-system', 'v2')
const lab = fs.readFileSync(path.join(root, 'lab', 'DesignSystemLab.tsx'), 'utf8')
const tokens = fs.readFileSync(path.join(root, 'tokens', 'tokens.css'), 'utf8')
const registry = JSON.parse(fs.readFileSync(path.join(root, 'metadata', 'registry.json'), 'utf8'))

for (let i = 0; i <= 17; i += 1) {
  const id = String(i).padStart(2, '0')
  if (!lab.includes(`id="${id}"`)) throw new Error(`Missing lab section ${id}`)
}
for (const token of ['--ng-canvas','--ng-accent','--ng-focus','--ng-success','--ng-warning','--ng-danger','--ng-touch','--ng-radius-card','--ng-standard']) {
  if (!tokens.includes(token)) throw new Error(`Missing token ${token}`)
}
if (registry.components.length < 9) throw new Error('Component families incomplete')
const names = registry.components.flatMap((family) => family.names)
for (const required of ['Button','Combobox','Table','BottomNavigation','AIComposer','MasterDetail','CommercialPreviewShell']) {
  if (!names.includes(required)) throw new Error(`Missing component metadata: ${required}`)
}
if (!registry.accessibility.includes('44PX_TOUCH') || !registry.accessibility.includes('RTL')) throw new Error('Accessibility contract incomplete')
console.log(`Negin AI Design System v2 registry PASS: ${names.length} components, 18 lab sections, ${registry.breakpoints.length} widths`)
