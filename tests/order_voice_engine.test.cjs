const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/static/assistant.js', 'utf8');
const parsingSource = source.slice(
  source.indexOf('const orderSpeechTokenAliases'),
  source.indexOf('async function toggleOrderCommandVoice'),
);
const conversionSource = source.slice(
  source.indexOf('function spokenOrderSaleUnit'),
  source.indexOf('function renderOrderCommandChoices'),
);

globalThis.previsitContext = {
  products: [
    {
      id: '1', name: 'دستمال مرطوب کودک ۲۰ عددی دافی', brand: 'دافی',
      description: 'پوست حساس', group: 'دستمال مرطوب کودک', manufacturer: '',
      unit: 'عدد', available_qty: 100, carton_size: 24,
      sale_units: [
        {ref: 1, name: 'عدد', factor: 1},
        {ref: 2, name: 'بسته', factor: 6},
        {ref: 3, name: 'کارتن', factor: 24},
      ],
    },
    {
      id: '2', name: 'دستمال مرطوب کودک پوست حساس دافی', brand: 'دافی',
      description: 'بدون عطر', group: 'دستمال مرطوب کودک', manufacturer: '',
      unit: 'عدد', available_qty: 80, carton_size: 20,
      sale_units: [{ref: 1, name: 'عدد', factor: 1}, {ref: 3, name: 'کارتن', factor: 20}],
    },
  ],
};
globalThis.previsitProductUnitQuantities = new Map();
globalThis.__cartQuantities = new Map();
globalThis.previsitSaleUnits = (product) => product.sale_units;
globalThis.previsitCartQuantity = (productId) => globalThis.__cartQuantities.get(String(productId)) || 0;
globalThis.previsitListUnitQuantities = (product) => Object.fromEntries(product.sale_units.map((unit) => [`${unit.ref}|${unit.name}|${unit.factor}`, 0]));
globalThis.previsitUnitKey = (unit) => `${unit.ref}|${unit.name}|${unit.factor}`;
globalThis.addPrevisitLine = () => {};

vm.runInThisContext(`${parsingSource}\n${conversionSource}\nglobalThis.orderVoiceEngine = {normalizeOrderCommand, parseOrderCommandItems, commandMatches, previsitVoiceOrderConversion};`);

const engine = globalThis.orderVoiceEngine;
assert.equal(engine.normalizeOrderCommand('دو کارتون و سه پک'), 'دو کارتن و سه بسته');
assert.equal(engine.normalizeOrderCommand('۲ کارتون و ٣ دونه'), '2 کارتن و 3 عدد');
assert.deepEqual(
  engine.parseOrderCommandItems('دو کارتون دستمال مرطوب کودک دافی و سه پک دستمال مرطوب پوست حساس دافی'),
  [
    {quantity: 2, unit: 'کارتن', command: 'دستمال مرطوب کودک دافی'},
    {quantity: 3, unit: 'بسته', command: 'دستمال مرطوب پوست حساس دافی'},
  ],
);
assert.deepEqual(
  engine.parseOrderCommandItems('دستمال مرطوب کودک دافی بیست و سه عدد'),
  [{quantity: 23, unit: 'عدد', command: 'دستمال مرطوب کودک دافی'}],
);
assert.deepEqual(
  engine.parseOrderCommandItems('دو کارتن دستمال مرطوب کودک دافی بده'),
  [{quantity: 2, unit: 'کارتن', command: 'دستمال مرطوب کودک دافی بده'}],
);
assert.ok(engine.commandMatches('دستمال مرطوب کودک پوست حساس').some((match) => match.product.id === '2'));

const carton = engine.previsitVoiceOrderConversion(globalThis.previsitContext.products[0], 2, 'کارتن');
assert.equal(carton.ok, true);
assert.equal(carton.baseQuantity, 48);
const packs = engine.previsitVoiceOrderConversion(globalThis.previsitContext.products[0], 3, 'بسته');
assert.equal(packs.ok, true);
assert.equal(packs.baseQuantity, 18);
const unsupported = engine.previsitVoiceOrderConversion(globalThis.previsitContext.products[1], 2, 'بسته');
assert.equal(unsupported.ok, false);
globalThis.__cartQuantities.set('1', 80);
const exceedsStock = engine.previsitVoiceOrderConversion(globalThis.previsitContext.products[0], 1, 'کارتن');
assert.equal(exceedsStock.ok, false);

console.log('order voice engine: all assertions passed');
