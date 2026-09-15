const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('app/static/warehouse-sale-price-contracts.js','utf8');
const html=fs.readFileSync('app/static/warehouse-assistant.html','utf8');
const main=fs.readFileSync('app/static/warehouse-assistant.js','utf8');

function setup(){
  const elements=new Map();
  const el=id=>{if(!elements.has(id))elements.set(id,{value:'',hidden:false,disabled:false,checked:false,required:false,innerHTML:'',textContent:'',dataset:{}});return elements.get(id)};
  const context=vm.createContext({document:{getElementById:el,addEventListener(){}},URLSearchParams,
    has:()=>true,fa:value=>String(value),normalizeSearchText:value=>String(value||'').toLowerCase(),
    esc:value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),confirm:()=>true});
  vm.runInContext(source,context);return {context,el};
}

test('manual rule payload keeps warehouse mapping inputs and explicit markup',()=>{
  const {context,el}=setup();
  vm.runInContext("salePriceState.items=[{product_code:'A'},{product_code:'B'}];salePriceState.selected.add('A')",context);
  el('saleRuleWarehouse').value='tehran';el('saleRuleManufacturer').value='70';el('saleRuleBrand').value='4';el('saleRuleGroup').value='1';el('saleRuleSelectionMode').value='selected';el('saleRuleSampleProduct').value='A';
  el('saleRuleTitle').value='rule';el('saleRuleStart').value='1405/06/17';el('saleRuleEnd').value='';el('saleRuleStatus').value='active';el('saleRuleIncludesTax').checked=true;el('saleRuleMarkup').value='۱۲';el('saleRuleNote').value='note';
  const payload=vm.runInContext('saleRulePayload()',context);
  assert.equal(payload.warehouse_code,'tehran');assert.equal(payload.manufacturer_id,70);assert.equal(payload.product_code,'A');assert.deepEqual(Array.from(payload.product_codes),['A']);assert.equal(payload.filter_brand_id,4);assert.equal(payload.filter_group_id,1);assert.equal(payload.markup_percent,'۱۲');assert.equal(payload.source_includes_tax,true);
});

test('all mode freezes every filtered item while selected mode sends checked goods only',()=>{
  const {context,el}=setup();vm.runInContext("salePriceState.items=[{product_code:'A'},{product_code:'B'}];salePriceState.selected.add('B')",context);
  el('saleRuleSelectionMode').value='all';assert.deepEqual(Array.from(vm.runInContext('selectedSaleProductCodes()',context)),['A','B']);
  el('saleRuleSelectionMode').value='selected';assert.deepEqual(Array.from(vm.runInContext('selectedSaleProductCodes()',context)),['B']);
});

test('render escapes product and request names and exposes manual actions',()=>{
  const {context,el}=setup();
  vm.runInContext(`salePriceState.contracts=[{id:'1',revision:1,warehouse_code:'karaj',warehouse_name:'کرج',order_type_id:2,order_type_name:'<img>',manufacturer_id:70,manufacturer:'افق',scope:'item',product_code:'A',product_name:'<script>',title:'قاعده',start_date:'1405/06/17',end_date:'',source_includes_tax:true,markup_percent:'11',status:'active'}]`,context);
  vm.runInContext('renderSalePriceContracts()',context);
  assert.match(el('salePriceRows').innerHTML,/&lt;img&gt;/);assert.match(el('salePriceRows').innerHTML,/&lt;script&gt;/);assert.doesNotMatch(el('salePriceRows').innerHTML,/<script>/);assert.match(el('salePriceRows').innerHTML,/ویرایش/);assert.match(el('salePriceRows').innerHTML,/بایگانی/);
});

test('preview sends manual price and renders base sale separately from final customer terms',async()=>{
  const {context,el}=setup();
  vm.runInContext("salePriceState.items=[{product_code:'A'}]",context);
  for(const [id,value] of Object.entries({saleRuleWarehouse:'karaj',saleRuleManufacturer:'70',saleRuleBrand:'',saleRuleGroup:'',saleRuleSelectionMode:'all',saleRuleTitle:'rule',saleRuleStart:'1405/06/17',saleRuleEnd:'',saleRuleStatus:'active',saleRuleMarkup:'11',saleRuleSampleProduct:'A',saleRuleSampleDate:'1405/06/17',saleRuleSamplePrice:'653697'}))el(id).value=value;
  el('saleRuleIncludesTax').checked=true;
  let request;context.api=async(url,options)=>{request={url,body:JSON.parse(options.body)};return {net_manufacturer_price:'594270',markup_percent:'11',markup_amount:'65370',tax:'65964',sale_price:'659640',sale_price_with_tax:'725604',price_source:'manual_preview'}};
  await vm.runInContext('previewSalePriceRule()',context);
  assert.equal(request.body.manufacturer_price,'653697');assert.match(el('saleRulePreviewOutput').innerHTML,/659640/);assert.match(el('saleRulePreviewOutput').innerHTML,/725604/);assert.match(el('saleRulePreviewOutput').innerHTML,/قیمت تولید واردشده/);
});

test('preview sample must be one of the selected products',async()=>{
  const {context,el}=setup();let calls=0;context.api=async()=>{calls++};
  vm.runInContext("salePriceState.items=[{product_code:'A'},{product_code:'B'}];salePriceState.selected.add('A')",context);el('saleRuleSelectionMode').value='selected';el('saleRuleSampleProduct').value='B';
  await vm.runInContext('previewSalePriceRule()',context);
  assert.equal(calls,0);assert.match(el('saleRuleError').textContent,/اقلام انتخاب‌شده/);
});

test('warehouse navigation exposes the sale-pricing view and loads its controller',()=>{
  assert.match(html,/data-view="sale-pricing"/);assert.match(html,/id="salePriceView"/);
  assert.match(html,/warehouse-sale-price-contracts\.js\?v=3/);assert.match(html,/id="saleRuleSelectionMode"/);assert.match(html,/id="saleRuleSelectionRows"/);
  assert.match(main,/selected!=="sale-pricing"/);assert.match(main,/loadSalePriceContracts/);
});
