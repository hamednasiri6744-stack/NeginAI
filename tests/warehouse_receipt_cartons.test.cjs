const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const source=readFileSync('app/static/warehouse-fulfillment.js','utf8');
function setup(){
  const elements={};const inputs=[];const calls=[];
  const context=vm.createContext({
    document:{addEventListener(){},querySelectorAll(){return inputs}},
    $:key=>elements[key]??=( {value:'',checked:false,disabled:false,textContent:'',close(){this.closed=true}}),
    normalizeSearchText:value=>String(value??'').replace(/[۰-۹]/g,c=>String(c.charCodeAt(0)-1776)).replace(/[٠-٩]/g,c=>String(c.charCodeAt(0)-1632)).replace(/٫/g,'.').replace(/[,٬]/g,'').trim(),
    fa:value=>String(value),toast(){},state:{},api:async(...args)=>{calls.push(args);return {orders:[]}},
  });
  vm.runInContext(source,context);vm.runInContext('loadFulfillmentOrders=async()=>{}',context);
  context.order={id:7,fulfillment:{revision:3,status:'awaiting_supply',lines:[
    {product_code:'001',conversion_rate:12,order_quantity:120,received_qty:24},
    {product_code:'002',conversion_rate:24,order_quantity:72,received_qty:0},
  ]}};
  vm.runInContext('fulfillmentState.editing=order;fulfillmentState.editingSnapshotId=87',context);
  for(const [code,value] of [['001','2'],['002','0']]){const loose={value:'0',setAttribute(){},removeAttribute(){}};inputs.push({dataset:{receivedProduct:code},value,loose,closest(){return {querySelector(){return loose}}},disabled:false,setAttribute(){},removeAttribute(){}});}
  return {context,elements,inputs,calls};
}
test('cartons plus loose units accept localized digits and reject fractional cartons',()=>{
  const {context}=setup();
  for(const value of ['۲','٢','2'])assert.equal(vm.runInContext(`receiptBaseUnits(order.fulfillment.lines[0],${JSON.stringify(value)},'۶')`,context),30);
  for(const value of ['','NaN','Infinity','-1','1','10.1','2.5'])assert.throws(()=>vm.runInContext(`receiptBaseUnits(order.fulfillment.lines[0],${JSON.stringify(value)},'0')`,context));
});
test('carton and unit decomposition preserves partial cartons without fractions',()=>{
  const {context}=setup();context.line={conversion_rate:3,received_qty:1,order_quantity:5};
  assert.equal(vm.runInContext("receiptBaseUnits(line,receiptParts(1,line).cartons,receiptParts(1,line).units)",context),1);
  assert.equal(vm.runInContext("receiptBaseUnits(line,receiptParts(5,line).cartons,receiptParts(5,line).units)",context),5);
});
test('full row changes only the chosen product; full all fills remaining rows without posting',()=>{
  const {context,inputs,calls}=setup();
  inputs[0].loose.value='5';inputs[1].loose.value='7';
  vm.runInContext("fillCompleteReceipt('001')",context);
  assert.deepEqual(inputs.map(i=>i.value),['10','0']);assert.equal(calls.length,0);
  assert.deepEqual(inputs.map(i=>i.loose.value),['0','7']);
  vm.runInContext('fillCompleteReceipt()',context);
  assert.deepEqual(inputs.map(i=>i.value),['10','3']);assert.equal(calls.length,0);
  assert.deepEqual(inputs.map(i=>i.loose.value),['0','0']);
  vm.runInContext("order.fulfillment.status='received'",context);inputs[0].value='2';
  vm.runInContext('fillCompleteReceipt()',context);assert.equal(inputs[0].value,'2');
});
test('save still requires ERP confirmation and posts base units with original revision/snapshot',async()=>{
  const {context,elements,inputs,calls}=setup();
  await vm.runInContext('saveFulfillmentReceipt()',context);assert.equal(calls.length,0);
  elements['#fulfillmentReceiptReference'].value='ERP-TEST';
  context.$('#fulfillmentInventoryReflected').checked=true;
  inputs[0].value='۲';inputs[0].loose.value='۶';inputs[1].value='3';
  await vm.runInContext('saveFulfillmentReceipt()',context);
  assert.equal(calls.length,1);
  const payload=JSON.parse(calls[0][1].body);
  assert.equal(payload.snapshot_id,87);assert.equal(payload.expected_revision,3);
  assert.deepEqual(payload.lines,[{product_code:'001',received_qty:30},{product_code:'002',received_qty:72}]);
});
test('invalid quantities never reach the API',async()=>{
  const {context,inputs,calls}=setup();context.$('#fulfillmentReceiptReference').value='TEST';context.$('#fulfillmentInventoryReflected').checked=true;
  inputs[0].value='11';await vm.runInContext('saveFulfillmentReceipt()',context);assert.equal(calls.length,0);
});
