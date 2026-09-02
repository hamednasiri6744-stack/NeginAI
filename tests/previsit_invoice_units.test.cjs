const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/static/assistant.js', 'utf8');
const start = source.indexOf('function previsitInvoiceUnitBreakdown');
const end = source.indexOf('function previsitUnitKey');
assert.ok(start >= 0, 'invoice unit-breakdown helper must exist');

globalThis.previsitSaleUnits = () => [
  {name: 'عدد', factor: 1},
  {name: 'بسته', factor: 6},
  {name: 'کارتن 1', factor: 24},
];
vm.runInThisContext(`${source.slice(start, end)}\nglobalThis.invoiceBreakdown = previsitInvoiceUnitBreakdown;`);

const result = globalThis.invoiceBreakdown({id: '10'}, 242);
assert.deepEqual(result, {
  cartonQuantity: 10,
  remainderQuantity: 2,
  unitsPerCarton: 24,
});

globalThis.previsitSaleUnits = () => [{name: 'عدد', factor: 1}];
assert.deepEqual(globalThis.invoiceBreakdown({id: '11'}, 5), {
  cartonQuantity: 0,
  remainderQuantity: 5,
  unitsPerCarton: 0,
});

assert.equal(globalThis.previsitInvoiceBaseQuantity(10, 2, 24), 242);
assert.equal(globalThis.previsitInvoiceBaseQuantity(0, 7, 0), 7);

console.log('previsit invoice unit columns: all assertions passed');
