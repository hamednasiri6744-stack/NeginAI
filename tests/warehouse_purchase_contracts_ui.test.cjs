const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('app/static/warehouse-purchase-contracts.js','utf8');
function setup(){
  const elements=new Map();
  const el=id=>{if(!elements.has(id))elements.set(id,{value:'',hidden:false,innerHTML:'',textContent:'',dataset:{},open:false,setAttribute(k,v){this[k]=v},showModal(){this.open=true},close(){this.open=false}});return elements.get(id)};
  const context=vm.createContext({document:{getElementById:el,addEventListener(){},querySelectorAll(){return []}},URLSearchParams,
    has:()=>true,fa:value=>String(value),normalizeSearchText:value=>String(value||''),
    esc:value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))});
  vm.runInContext(source,context);vm.runInContext(fs.readFileSync('app/static/warehouse-purchase-editor.js','utf8'),context);
  for(const file of ['warehouse-purchase-groups.js','warehouse-purchase-group-editor.js','warehouse-purchase-members.js','warehouse-purchase-actions.js'])vm.runInContext(fs.readFileSync('app/static/'+file,'utf8'),context);
  return {context,el};
}

test('member manager adds only uncovered goods in the contract warehouse and period',async()=>{
  const {context,el}=setup();
  context.api=async()=>({items:[{product_code:'A',product_name:'Member',eligible_stock_ids:[1]},
    {product_code:'B',product_name:'Covered',eligible_stock_ids:[1]},
    {product_code:'C',product_name:'Free <item>',eligible_stock_ids:[1]},
    {product_code:'D',product_name:'Other warehouse',eligible_stock_ids:[2]}]});
  vm.runInContext("purchaseState.contracts=[{id:'other',supplier_id:17,stock_id:1,status:'active',product_codes:['B'],start_date:'1405/06/01',end_date:''}]",context);
  await vm.runInContext("openPurchaseMembers({id:'one',revision:3,title:'One',supplier:'Supplier',supplier_id:17,stock_id:1,start_date:'1405/06/01',end_date:'',status:'active',product_codes:['A']},'available')",context);
  assert.deepEqual(Array.from(vm.runInContext('purchaseMembersVisible().map(i=>i.product_code)',context)),['C']);
  assert.match(el('purchaseMembersRows').innerHTML,/Free &lt;item&gt;/);
  vm.runInContext("purchaseMembers.endDates.A='1405/06/10';purchaseMembers.selected.add('C');purchaseMembers.tab='members';renderPurchaseMembers()",context);
  assert.equal(el('purchaseMembersSave').disabled,false);
  let request;context.api=async(url,args)=>{request={url,...args};return {}};context.loadPurchaseContracts=async()=>{};context.toast=()=>{};
  await vm.runInContext('savePurchaseMembers()',context);
  assert.equal(request.url,'/warehouse-assistant/api/purchase-contracts/one/members');
  assert.deepEqual(JSON.parse(request.body),{expected_revision:3,product_codes:['A','C'],product_end_dates:{A:'1405/06/10'}});
  assert.equal(el('purchaseMembersDialog').open,false);
});

test('new contract picker excludes covered products even in draft',()=>{
  const {context,el}=setup();
  el('contractSupplier').value='17';el('contractStock').value='1';el('contractStart').value='1405/06/01';el('contractSelectionMode').value='selected';
  vm.runInContext("purchaseEditor.collection=true;purchaseState.contracts=[{id:'other',supplier_id:17,stock_id:1,status:'active',product_codes:['A'],start_date:'1405/06/01',end_date:''}];purchaseEditor.items=[{product_code:'A',product_name:'Covered',eligible_stock_ids:[1]},{product_code:'B',product_name:'Free',eligible_stock_ids:[1]}]",context);
  assert.deepEqual(Array.from(vm.runInContext('selectionVisibleItems().map(i=>i.product_code)',context)),['B']);
  el('contractStock').value='2';assert.equal(vm.runInContext('selectionVisibleItems().length',context),0);
});

test('late member list cannot replace another contract and failed save retains changes',async()=>{
  const {context,el}=setup();let finish;
  context.api=()=>new Promise(resolve=>finish=resolve);
  const pending=vm.runInContext("openPurchaseMembers({id:'one',title:'One',supplier_id:17,status:'active',stock_id:1,product_codes:['A'],start_date:'1405/06/01'})",context);
  vm.runInContext("purchaseMembers.request++;purchaseMembers.items=[{product_code:'new'}]",context);
  finish({items:[{product_code:'stale'}]});await pending;
  assert.equal(vm.runInContext('purchaseMembers.items[0].product_code',context),'new');
  vm.runInContext("purchaseMembers.loading=false;purchaseMembers.selected.add('C')",context);
  context.api=async()=>{throw new Error('concurrent change')};await vm.runInContext('savePurchaseMembers()',context);
  assert.equal(el('purchaseMembersError').textContent,'concurrent change');
  assert.equal(vm.runInContext("purchaseMembers.selected.has('C')",context),true);
});

test('supplier sections lead to one contract row with multiple members',()=>{
  const {context,el}=setup();
  vm.runInContext(`purchaseState.catalog={contract_structure:'supplier_contracts',suppliers:[{id:17,name:'Supplier'},{id:18,name:'Empty'}]};purchaseState.contracts=[{id:'group',scope:'collection',supplier_id:17,title:'Brand agreement',status:'active',product_codes:['A','B'],revision:1,basis:'manufacturer',discount_percent:0,tail_discount_percent:0}]`,context);
  vm.runInContext('renderPurchaseContracts()',context);
  assert.match(el('purchaseSupplierSections').innerHTML,/Supplier/);assert.match(el('purchaseSupplierSections').innerHTML,/Empty/);
  assert.equal(el('purchaseContractsPane').hidden,true);assert.equal(el('purchaseNew').disabled,true);
  el('purchaseSupplier').value='17';vm.runInContext('renderPurchaseContracts()',context);
  assert.equal(el('purchaseSupplierSections').hidden,true);
  assert.match(el('purchaseContractRows').innerHTML,/2 کالا/);
  assert.equal((el('purchaseContractRows').innerHTML.match(/<tr>/g)||[]).length,1);
});

test('brand and group filters preserve selections outside visible results',()=>{
  const {context,el}=setup();
  vm.runInContext("purchaseEditor.collection=true;purchaseEditor.items=[{product_code:'A',brand_id:1,group_id:10},{product_code:'B',brand_id:2,group_id:20}];purchaseEditor.selected=new Set(['A','B'])",context);
  el('contractBrand').value='1';
  assert.deepEqual(Array.from(vm.runInContext('selectionVisibleItems().map(i=>i.product_code)',context)),['A']);
  assert.deepEqual(Array.from(vm.runInContext('selectedProductCodes()',context)),['A','B']);
  el('contractBrand').value='';el('contractGroup').value='20';
  assert.deepEqual(Array.from(vm.runInContext('selectionVisibleItems().map(i=>i.product_code)',context)),['B']);
  assert.deepEqual(Array.from(vm.runInContext('selectedProductCodes()',context)),['A','B']);
});

test('supplier card shows server current coverage and uncovered tab survives reload',async()=>{
  const {context,el}=setup();
  const catalog={today:'1405/06/10',contract_structure:'supplier_contracts',suppliers:[{id:17,name:'Supplier',covered_product_count:1,uncovered_product_count:2,warehouses:[{id:1,name:'Karaj',active:true,product_count:3,uncovered_product_count:2,active_contract_count:1}]}]};
  context.fixture={catalog,contracts:[]};
  vm.runInContext('purchaseState.catalog=fixture.catalog;renderPurchaseContracts()',context);
  assert.match(el('purchaseSupplierSections').innerHTML,/2 کالای فاقد قرارداد/);
  el('purchaseSupplier').value='17';el('purchaseDate').value='1405/08/01';el('purchaseStock').value='1';
  const calls=[];
  context.api=async url=>{calls.push(url);return url.includes('/products?')?{items:[{product_code:'B',product_name:'Uncovered',contract:null}],total:1,uncovered_product_count:2,on_date:'1405/06/10'}:context.fixture};
  await vm.runInContext("purchaseSelectTab('uncovered')",context);
  const query=new URL(calls[0],'http://test').searchParams;
  assert.equal(query.get('without_contract'),'true');assert.equal(query.get('supply_only'),'true');assert.equal(query.get('on_date'),'1405/06/10');assert.equal(query.get('stock_id'),'1');
  assert.equal(el('purchaseProductsPane').hidden,false);assert.equal(el('purchaseContractsPane').hidden,true);assert.equal(el('purchaseDateLabel').hidden,true);
  assert.match(el('purchaseProductRows').innerHTML,/Uncovered/);assert.match(el('purchaseProductRows').innerHTML,/قرارداد جدید برای کالا/);
  await vm.runInContext('loadPurchaseContracts()',context);
  assert.equal(el('purchaseProductsPane').hidden,false);assert.equal(el('purchaseContractsPane').hidden,true);
  assert.match(calls.at(-1),/without_contract=true/);
  vm.runInContext("purchaseSelectTab('contracts')",context);
  assert.equal(el('purchaseProductsPane').hidden,true);assert.equal(el('purchaseContractsPane').hidden,false);
});

test('membership conflict is supplier and date scoped and ignores the edited contract',()=>{
  const {context,el}=setup();el('contractSupplier').value='17';el('contractStart').value='۱۴۰۵/۰۶/۱۵';el('contractEnd').value='';
  vm.runInContext("purchaseState.contracts=[{id:'other',supplier_id:17,status:'active',product_codes:['A'],start_date:'1405/06/01',end_date:'1405/06/15'}]",context);
  assert.equal(vm.runInContext("supplierMemberConflict('A').id",context),'other');
  el('contractStart').value='1405/06/16';assert.equal(vm.runInContext("supplierMemberConflict('A')",context),undefined);
  el('contractStart').value='1405/06/01';vm.runInContext("purchaseState.editing={id:'other'}",context);
  assert.equal(vm.runInContext("supplierMemberConflict('A')",context),undefined);
});

test('warehouse scope separates membership conflicts and is preserved in payload and sample',()=>{
  const {context,el}=setup();el('contractSupplier').value='17';el('contractStart').value='1405/06/10';
  el('contractAdjustment').value='0';el('contractAdjustmentDirection').value='increase';el('contractDiscount').value='0';
  vm.runInContext("purchaseState.catalog.stocks=[{id:1,name:'Karaj'},{id:2,name:'Tehran'}];purchaseState.contracts=[{id:'other',supplier_id:17,stock_id:1,status:'active',product_codes:['A'],start_date:'1405/06/01',end_date:''}]",context);
  el('contractStock').value='2';assert.equal(vm.runInContext("supplierMemberConflict('A')",context),undefined);
  el('contractStock').value='1';assert.equal(vm.runInContext("supplierMemberConflict('A').id",context),'other');
  el('contractStock').value='';assert.equal(vm.runInContext("supplierMemberConflict('A').id",context),'other');
  el('purchaseStock').value='2';vm.runInContext('setContractStock({},false)',context);
  assert.equal(el('contractStock').value,'2');assert.equal(el('contractSampleStock').value,'2');assert.equal(el('contractSampleStock').disabled,true);
  assert.equal(vm.runInContext('contractPayload().stock_id',context),2);
  vm.runInContext('setContractStock({},true)',context);
  assert.equal(el('contractStock').value,'');assert.equal(el('contractSampleStock').disabled,false);
  assert.equal(vm.runInContext('contractPayload().stock_id',context),null);
});

test('warehouse filter displays only its contracts plus common contracts',()=>{
  const {context,el}=setup();el('purchaseStock').value='2';
  vm.runInContext("purchaseState.catalog={suppliers:[{id:17,name:'Supplier'}]};purchaseState.contracts=[{supplier_id:17,stock_id:1,title:'Karaj'}, {supplier_id:17,stock_id:2,title:'Tehran'}, {supplier_id:17,title:'Common'}]",context);
  assert.deepEqual(Array.from(vm.runInContext('purchaseSupplierRows()[0].contracts.map(r=>r.title)',context)),['Tehran','Common']);
});

test('supplier card shows separate warehouse counts and direct uncovered links',()=>{
  const {context,el}=setup();
  vm.runInContext("purchaseState.catalog={supply_scope_known:true,suppliers:[{id:17,name:'Supplier',active_warehouse_count:2,warehouses:[{id:1,name:'Karaj',active:true,uncovered_product_count:6,active_contract_count:2},{id:2,name:'Tehran',active:true,uncovered_product_count:0,active_contract_count:1},{id:9,name:'Gilan',active:false,uncovered_product_count:0}]}]};renderSupplierContracts()",context);
  const cards=el('purchaseSupplierSections').innerHTML;
  assert.match(cards,/2 انبار فعال/);assert.match(cards,/data-purchase-stock="1"/);assert.match(cards,/6 کالای فاقد قرارداد/);
  assert.match(cards,/data-purchase-stock="2"/);assert.doesNotMatch(cards,/data-purchase-stock="9"/);
  assert.equal(el('purchaseStockLabel').hidden,true);
});

test('bulk selection creates one agreement with current supplier and warehouse',()=>{
  const {context,el}=setup();let input;
  context.editSupplierContract=r=>input=r;
  el('purchaseSupplier').value='17';el('purchaseStock').value='2';
  vm.runInContext("purchaseState.selectedUncovered=new Set(['A','B']);createPurchaseFromSelection()",context);
  assert.equal(input.supplier_id,17);assert.equal(input.stock_id,2);
  assert.deepEqual(Array.from(input.product_codes),['A','B']);
});

test('product picker excludes goods outside chosen warehouse but retains existing members for review',()=>{
  const {context,el}=setup();el('contractStock').value='2';el('contractSelectionMode').value='selected';
  context.items=[{product_code:'A',eligible_stock_ids:[1]},{product_code:'B',eligible_stock_ids:[2]}];
  assert.deepEqual(Array.from(vm.runInContext('items.filter(supplierSelectionMatches).map(i=>i.product_code)',context)),['B']);
  el('contractSelectionMode').value='members';vm.runInContext("purchaseEditor.selected.add('A')",context);
  assert.deepEqual(Array.from(vm.runInContext('items.filter(supplierSelectionMatches).map(i=>i.product_code)',context)),['A']);
});

test('late warehouse catalog response cannot replace the selected warehouse',async()=>{
  const {context,el}=setup();let finishFirst;
  context.api=url=>url.endsWith('stock_id=1')?new Promise(r=>finishFirst=r):Promise.resolve({contracts:[],catalog:{contract_structure:'supplier_contracts',today:'1405/06/10',stock_id:2,suppliers:[]}});
  el('purchaseStock').value='1';const first=vm.runInContext('loadPurchaseContracts()',context);
  el('purchaseStock').value='2';await vm.runInContext('loadPurchaseContracts()',context);
  finishFirst({contracts:[],catalog:{stock_id:1,suppliers:[]}});await first;
  assert.equal(vm.runInContext('purchaseState.catalog.stock_id',context),2);
});
test('clearing supplier cancels an older product response instead of showing the wrong supplier',async()=>{
  const {context,el}=setup();let resolve;
  context.api=()=>new Promise(r=>resolve=r);
  el('purchaseSupplier').value='17';el('purchaseDate').value='1405/06/17';
  const pending=vm.runInContext('loadPurchaseProducts(true)',context);
  el('purchaseSupplier').value='';await vm.runInContext('loadPurchaseProducts(true)',context);
  resolve({items:[{product_code:'wrong-supplier',product_name:'old',tax_status:'known',tax_rate:10}],total:1});await pending;
  assert.doesNotMatch(el('purchaseProductRows').innerHTML,/wrong-supplier/);
  assert.match(el('purchaseProductRows').innerHTML,/تأمین‌کننده را انتخاب کنید/);
});
test('product rules distinguish zero, unknown, inherited and editable item rules; names are escaped',async()=>{
  const {context,el}=setup();el('purchaseSupplier').value='17';
  context.api=async()=>({items:[{product_code:'A',product_name:'<img src=x>',brand:'brand',tax_status:'known',tax_rate:0,contract:{scope:'item',title:'item-rule',basis:'manufacturer',revision:2,discount_percent:0,tail_discount_percent:0}},
    {product_code:'B',product_name:'unknown',tax_status:'unknown',tax_rate:null,contract:null}],total:2,on_date:'1405/06/17'});
  await vm.runInContext('loadPurchaseProducts(true)',context);
  const html=el('purchaseProductRows').innerHTML;
  assert.match(html,/0٪ · معاف/);assert.match(html,/نامشخص/);assert.match(html,/بدون قرارداد معتبر/);
  assert.match(html,/ویرایش قاعدهٔ کالا/);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img/);
});

test('all supplier product pages are loaded before header filtering and missing dated price is visible',async()=>{
  const {context,el}=setup();el('purchaseSupplier').value='17';el('purchaseStock').value='1';
  const calls=[];context.api=async url=>{calls.push(url);return calls.length===1?{items:[{product_code:'A',product_name:'first',tax_status:'known',tax_rate:10,contract:null}],total:2,on_date:'1405/06/17'}:{items:[{product_code:'B',product_name:'last',tax_status:'known',tax_rate:10,contract:{scope:'item',title:'rule',basis:'manufacturer',revision:1,discount_percent:18,tail_discount_percent:0},price_validation:{status:'missing',message:'این کالا قیمت تولید ندارد <x>'}}],total:2}};
  await vm.runInContext('loadPurchaseProducts(true)',context);
  assert.equal(calls.length,2);assert.match(calls[0],/stock_id=1/);assert.match(calls[1],/offset=1/);
  assert.match(el('purchaseProductRows').innerHTML,/first/);assert.match(el('purchaseProductRows').innerHTML,/last/);
  assert.match(el('purchaseProductRows').innerHTML,/این کالا قیمت تولید ندارد &lt;x&gt;/);assert.equal(el('purchaseMore').hidden,true);
});
test('contract submission keeps explicit zero discounts distinct from missing input',()=>{
  const {context,el}=setup();el('contractDiscount').value='0';el('contractTail').value='';el('contractAdjustment').value='0';
  el('contractAdjustmentDirection').value='increase';
  const payload=vm.runInContext('contractPayload()',context);
  assert.equal(payload.discount_percent,'0');assert.equal(payload.tail_discount.value,'');assert.equal(payload.adjustment_percent,'0');
});

test('sequential column percentages round trip into the payload and readable labels',()=>{
  const {context,el}=setup();el('contractDiscount').value='20';el('contractDiscountFollowing').value='۵، ۲';
  el('contractAdjustment').value='60';el('contractAdjustmentDirection').value='decrease';
  const payload=vm.runInContext('contractPayload()',context);
  assert.equal(payload.adjustment_percent,'-60');assert.equal(payload.discount_percent,'20');
  assert.equal(JSON.stringify(payload.discount_steps),JSON.stringify([{percent:'20'},{percent:'۵'},{percent:'۲'}]));
  assert.equal(vm.runInContext("purchaseDiscountLabel({discount_percent:'20',discount_steps:[{percent:'20'},{percent:'5'}]})",context),'20٪ سپس 5٪');
  el('contractDiscountFollowing').value='5،';assert.throws(()=>vm.runInContext('contractPayload()',context),/مرحله/);
});

test('base price direction round-trips existing signed rules and accepts unsigned Persian percentages',()=>{
  const {context,el}=setup();
  el('contractDiscount').value='0';
  for(const [stored,direction,magnitude] of [['-5.25','decrease','5.25'],['5','increase','5'],['0','increase','0']]){
    vm.runInContext(`setContractAdjustment(${JSON.stringify(stored)})`,context);
    assert.equal(el('contractAdjustmentDirection').value,direction);
    assert.equal(el('contractAdjustment').value,magnitude);
    assert.equal(vm.runInContext('contractPayload().adjustment_percent',context),stored);
  }
  el('contractAdjustmentDirection').value='decrease';el('contractAdjustment').value='۵٫۲۵';
  assert.equal(vm.runInContext('contractPayload().adjustment_percent',context),'-5.25');
  el('contractAdjustmentDirection').value='increase';
  assert.equal(vm.runInContext('contractPayload().adjustment_percent',context),'5.25');
  for(const invalid of ['','-5','+5','101','abc']){
    el('contractAdjustment').value=invalid;
    assert.throws(()=>vm.runInContext('contractPayload()',context),/بدون علامت/);
  }
});

test('invalid adjustment prevents both preview and save requests',async()=>{
  const {context,el}=setup();el('contractAdjustment').value='-5';el('contractAdjustmentDirection').value='decrease';
  let calls=0;context.api=()=>{calls++;throw new Error('should not send')};
  await vm.runInContext('previewPurchaseContract()',context);
  await vm.runInContext('savePurchaseContract({preventDefault(){}})',context);
  assert.equal(calls,0);assert.match(el('contractError').textContent,/بدون علامت/);
});

test('changing manufacturer discards an older catalog response and prior selections',async()=>{
  const {context,el}=setup();const pending=[];
  context.api=()=>new Promise(resolve=>pending.push(resolve));
  vm.runInContext("purchaseState.catalog.manufacturers=[{id:17,name:'Kaman'},{id:15,name:'Silaneh'}];purchaseEditor.selected.add('old')",context);
  el('contractSelectionMode').value='selected';el('contractManufacturer').value='17';
  const first=vm.runInContext("loadContractSelection('manufacturer')",context);
  el('contractManufacturer').value='15';const second=vm.runInContext("loadContractSelection('manufacturer')",context);
  const result=(id,name,code)=>({brands:[],groups:[],suppliers:[{id,name}],items:[{product_code:code,product_name:name,brand:'',supplier_ids:[id],tax_status:'known',tax_rate:10}]});
  pending[1](result(15,'Silaneh','NEW'));await second;pending[0](result(17,'Kaman','OLD'));await first;
  assert.match(el('contractSelectionRows').innerHTML,/NEW/);assert.doesNotMatch(el('contractSelectionRows').innerHTML,/OLD/);
  assert.equal(vm.runInContext('purchaseEditor.selected.size',context),0);
});

test('all selects the frozen filtered list, while explicit mode sends only checked goods',()=>{
  const {context,el}=setup();
  vm.runInContext("purchaseEditor.items=[{product_code:'A'},{product_code:'B'}];purchaseEditor.selected.add('B')",context);
  el('contractSelectionMode').value='all';assert.deepEqual(Array.from(vm.runInContext('selectedProductCodes()',context)),['A','B']);
  el('contractSelectionMode').value='selected';assert.deepEqual(Array.from(vm.runInContext('selectedProductCodes()',context)),['B']);
});

test('manual settings preserve agreement reference and discovery provenance',()=>{
  const {context,el}=setup();el('contractDiscount').value='0';el('contractAdjustment').value='0';el('contractAdjustmentDirection').value='increase';
  el('contractAgreementReference').value='الحاقیه ۱۲';el('contractSourceMode').value='discovered';el('contractEvidenceRunId').value='run-123';
  const payload=vm.runInContext('contractPayload()',context);
  assert.equal(payload.agreement_reference,'الحاقیه ۱۲');assert.equal(payload.source_mode,'discovered');assert.equal(payload.evidence_run_id,'run-123');
});

test('discovery renders evidence safely and never labels a proposal as active',()=>{
  const {context,el}=setup();
  vm.runInContext(`renderPurchaseDiscovery({supplier:'<x>',rows_read:4,eligible_count:3,rejected_count:1,from_year:1404,to_year:1405,rejections:{'<bad>':1},warnings:['review'],proposals:[{label:'<rule>',confidence:'high',evidence_count:3,invoice_count:2,product_count:2,coverage_percent:'75'}]})`,context);
  const html=el('purchaseDiscoveryBody').innerHTML;
  assert.match(html,/&lt;rule&gt;/);assert.match(html,/&lt;bad&gt;/);assert.doesNotMatch(html,/<rule>/);assert.doesNotMatch(html,/فعال شد/);
});


test('product expiry controls conflict boundary and is rendered with history',async()=>{
  const {context,el}=setup();
  context.api=async()=>({items:[{product_code:'A',product_name:'Item',eligible_stock_ids:[1]}]});
  vm.runInContext("purchaseState.contracts=[{id:'old',supplier_id:17,stock_id:1,status:'active',product_codes:['A'],start_date:'1405/06/01',end_date:'',product_end_dates:{A:'1405/06/10'}}]",context);
  el('contractSupplier').value='17';el('contractStock').value='1';el('contractStart').value='1405/06/10';
  assert.equal(vm.runInContext("supplierMemberConflict('A').id",context),'old');
  el('contractStart').value='1405/06/11';
  assert.equal(vm.runInContext("supplierMemberConflict('A')",context),undefined);
  await vm.runInContext("openPurchaseMembers(purchaseState.contracts[0])",context);
  assert.match(el('purchaseMembersRows').innerHTML,/1405\/06\/10/);
  assert.match(el('purchaseMembersRows').innerHTML,/سابقهٔ کالا/);
  vm.runInContext("purchaseMembers.endDates.A='1405/06/12';renderPurchaseMembers()",context);
  assert.equal(el('purchaseMembersSave').disabled,false);
  assert.match(el('purchaseMembersRows').innerHTML,/data-purchase-member-end/);
  assert.equal(vm.runInContext("purchaseMembers.selected.has('A')",context),true);
});


test('bulk removal dates only checked members and never erases membership',async()=>{
  const {context,el}=setup();context.api=async()=>({items:[{product_code:'A'},{product_code:'B'}]});
  await vm.runInContext("openPurchaseMembers({id:'one',revision:1,title:'One',status:'active',product_codes:['A','B'],stock_id:1,start_date:'1405/06/01',end_date:''})",context);
  vm.runInContext("purchaseMembers.checked.add('A');deleteSelectedPurchaseMembers()",context);
  assert.match(el('purchaseMembersError').textContent,/تاریخ پایان/);
  assert.equal(vm.runInContext('Object.keys(purchaseMembers.endDates).length',context),0);
  el('purchaseMembersBulkDate').value='۱۴۰۵/۰۶/۲۳';vm.runInContext('deleteSelectedPurchaseMembers()',context);
  assert.deepEqual(JSON.parse(vm.runInContext('JSON.stringify(purchaseMembers.endDates)',context)),{A:'1405/06/23'});
  assert.deepEqual(Array.from(vm.runInContext('[...purchaseMembers.selected]',context)),['A','B']);
  assert.equal(vm.runInContext('purchaseMembers.checked.size',context),0);
});

test('whole contract ending sends only revision and end date and retains failed input',async()=>{
  const {context,el}=setup();context.loadPurchaseContracts=async()=>{};context.toast=()=>{};
  vm.runInContext("openPurchaseEnd({id:'one',revision:4,title:'One',supplier:'S',stock_id:null,status:'active',product_codes:['A','B']})",context);
  assert.match(el('purchaseEndSummary').textContent,/همهٔ انبارها/);
  el('purchaseEndDate').value='1405/06/20';context.api=async()=>{throw new Error('invoice 701')};
  await vm.runInContext('savePurchaseEnd({preventDefault(){}})',context);
  assert.equal(el('purchaseEndDialog').open,true);assert.equal(el('purchaseEndError').textContent,'invoice 701');
  let sent;context.api=async(url,args)=>{sent={url,body:JSON.parse(args.body)}};
  await vm.runInContext('savePurchaseEnd({preventDefault(){}})',context);
  assert.deepEqual(sent,{url:'/warehouse-assistant/api/purchase-contracts/one/end',body:{expected_revision:4,end_date:'1405/06/20'}});
  assert.equal(el('purchaseEndDialog').open,false);
});

test('warehouse products default to current covered section and preserve uncovered switch',async()=>{
  const {context,el}=setup();el('purchaseSupplier').value='17';el('purchaseStock').value='1';
  vm.runInContext("purchaseState.catalog={contract_structure:'supplier_contracts',today:'1405/06/23',suppliers:[{id:17,name:'S'}]}",context);
  const calls=[];context.api=async url=>{calls.push(url);return {items:[],total:0,on_date:'1405/06/23',coverage_counts:{covered:0,uncovered:1}}};
  await vm.runInContext("purchaseSelectTab('products')",context);
  assert.match(calls[0],/coverage=covered/);assert.match(calls[0],/on_date=1405%2F06%2F23/);
  assert.equal(el('purchaseProductSelectionControls').hidden,true);
  await vm.runInContext("purchaseSelectTab('uncovered')",context);
  assert.match(calls.at(-1),/coverage=uncovered/);assert.equal(el('purchaseProductSelectionControls').hidden,false);
});
