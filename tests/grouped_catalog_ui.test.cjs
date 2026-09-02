const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/static/assistant.js', 'utf8');
const groupedProductSource = source.slice(
  source.indexOf('function previsitGroupedProductHtml'),
  source.indexOf('function renderPrevisitGroupedCatalogs'),
);

globalThis.previsitCartQuantity = () => 0;
globalThis.previsitCatalogUnitRows = () => '<div class="unit-rows">units</div>';
globalThis.esc = (value) => String(value ?? '');

vm.runInThisContext(`${groupedProductSource}\nglobalThis.groupedProductHtml = previsitGroupedProductHtml;`);

const html = globalThis.groupedProductHtml({
  id: '10',
  code: 'SKU-10',
  name: 'دستمال مرطوب کودک دافی',
  brand: 'دافی',
  group: 'دستمال مرطوب',
  unit: 'عدد',
  available_qty: 48,
  indicative_price: 100000,
  catalog_tax_percent: 10,
  catalog_tax_inclusive_price: 110000,
  manufacturer_price: 125000,
  consumer_price: 150000,
});

assert.match(html, /class="previsit-grouped-prices"/);
assert.match(html, /قیمت پایه با احتساب .*٪ ارزش افزوده/);
assert.match(html, /قیمت تولیدکننده/);
assert.match(html, /قیمت مصرف‌کننده/);
assert.match(html, /۱۱۰٬۰۰۰ ریال/);
assert.match(html, /۱۲۵٬۰۰۰ ریال/);
assert.match(html, /۱۵۰٬۰۰۰ ریال/);
assert.match(html, /unit-rows/);

const calculatedTaxHtml = globalThis.groupedProductHtml({
  id: '12', name: 'کالای مشمول مالیات', unit: 'عدد', indicative_price: 200000,
  catalog_tax_percent: 10, manufacturer_price: 240000, consumer_price: 260000,
});
assert.match(calculatedTaxHtml, /۲۲۰٬۰۰۰ ریال/);
assert.match(calculatedTaxHtml, /قیمت پایه با احتساب .*٪ ارزش افزوده/);

const untaxed = globalThis.groupedProductHtml({
  id: '11', name: 'کالای بدون مالیات', unit: 'عدد', indicative_price: 90000,
});
assert.match(untaxed, /<small>قیمت پایه<\/small>/);
assert.doesNotMatch(untaxed, /قیمت نامشخص/);

console.log('grouped catalog UI: all assertions passed');
