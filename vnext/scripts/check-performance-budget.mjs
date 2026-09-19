import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const dist = path.join(root, 'dist')
const htmlPath = path.join(dist, 'index.html')

if (!fs.existsSync(htmlPath)) {
  console.error('[perf-budget] dist/index.html not found. Run the production build first.')
  process.exit(1)
}

const html = fs.readFileSync(htmlPath, 'utf8')
const refs = [...html.matchAll(/(?:src|href)="\/assets\/([^"]+)"/g)].map((match) => match[1])
const uniqueRefs = [...new Set(refs)]
const sizes = uniqueRefs.map((file) => {
  const fullPath = path.join(dist, 'assets', file)
  const bytes = fs.existsSync(fullPath) ? fs.statSync(fullPath).size : 0
  return { file, bytes, kb: bytes / 1024 }
})

const entryJs = sizes.find((item) => /^index-.*\.js$/.test(item.file))
const entryCss = sizes.find((item) => /^index-.*\.css$/.test(item.file))
const initialTotalKb = sizes.reduce((sum, item) => sum + item.kb, 0)

const routeFiles = fs.readdirSync(path.join(dist, 'assets'))
  .filter((file) => /^(Visitor|FloatingNeginAi).+\.js$/.test(file))
  .map((file) => {
    const bytes = fs.statSync(path.join(dist, 'assets', file)).size
    return { file, kb: bytes / 1024 }
  })

const budgets = {
  entryJsKb: 370,
  entryCssKb: 235,
  initialTotalKb: 665,
  routeJsKb: 70,
}

const failures = []

function check(label, actual, max) {
  const ok = actual <= max
  console.log(`[perf-budget] ${ok ? 'PASS' : 'FAIL'} ${label}: ${actual.toFixed(1)} KB / ${max} KB`)
  if (!ok) failures.push(`${label} ${actual.toFixed(1)} KB > ${max} KB`)
}

if (!entryJs) failures.push('entry JS asset was not found')
else check('initial entry JS', entryJs.kb, budgets.entryJsKb)

if (!entryCss) failures.push('entry CSS asset was not found')
else check('initial entry CSS', entryCss.kb, budgets.entryCssKb)

check('initial HTML-linked assets', initialTotalKb, budgets.initialTotalKb)

for (const asset of routeFiles) {
  check(`lazy route ${asset.file}`, asset.kb, budgets.routeJsKb)
}

if (failures.length) {
  console.error('\n[perf-budget] Performance regression blocked:')
  for (const failure of failures) console.error(` - ${failure}`)
  console.error('[perf-budget] Split/defer the new feature instead of raising the budget without review.')
  process.exit(1)
}

console.log('\n[perf-budget] All budgets passed.')
