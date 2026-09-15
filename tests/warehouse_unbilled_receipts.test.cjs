const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function setup(){
  const elements=new Map();const el=id=>{if(!elements.has(id))elements.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,setAttribute(){}});return elements.get(id)};
  const context=vm.createContext({URLSearchParams,document:{getElementById:el,addEventListener(){}},fa:String,
    normalizeSearchText:v=>String(v??'').replace(/[۰-۹]/g,c=>String(c.charCodeAt(0)-1776)),
    esc:v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')});
  vm.runInContext(fs.readFileSync('app/static/warehouse-unbilled-receipts.js','utf8'),context);
  return {context,el};
}
const rows=[{receipt_id:1,receipt_no:650,receipt_date:'1405/06/16',stock_id:1,stock_name:'مرکزی',supplier_name:'فروشنده',confirmed:true,comment:'شرح <img src=x>',manufacturers:[{id:15,name:'سیلانه'},{id:17,name:'کامان'}]},
  {receipt_id:2,receipt_no:651,receipt_date:'1405/06/17',stock_id:9,stock_name:'گیلان',supplier_name:'دیگر',confirmed:false,comment:'',manufacturers:[{id:null,name:'مشخص نشده'}]}];
test('long comments remain available in an escaped keyboard-accessible disclosure',()=>{
  const {context}=setup();context.comment='شرح <img src=x> '+ 'متن کامل '.repeat(30);
  const html=vm.runInContext('unbilledComment(comment)',context);
  assert.match(html,/<details><summary aria-label=/);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img/);
  assert.ok(html.includes('متن کامل '.repeat(30)));
});
test('date, actual manufacturer, stock and receipt status filter independently; comments are escaped',()=>{
  const {context,el}=setup();context.rows=rows;vm.runInContext('unbilledState.items=rows;unbilledState.loaded=true;renderUnbilledReceipts()',context);
  assert.match(el('unbilledRows').innerHTML,/&lt;img/);assert.doesNotMatch(el('unbilledRows').innerHTML,/<img/);
  el('unbilledManufacturer').value='17';assert.equal(vm.runInContext('filteredUnbilledReceipts().length',context),1);
  el('unbilledStock').value='9';assert.equal(vm.runInContext('filteredUnbilledReceipts().length',context),0);
  el('unbilledStock').value='';el('unbilledManufacturer').value='';el('unbilledFrom').value='۱۴۰۵/۰۶/۱۷';
  assert.equal(vm.runInContext('filteredUnbilledReceipts()[0].receipt_no',context),651);
  el('unbilledFrom').value='';el('unbilledStatus').value='unconfirmed';assert.equal(vm.runInContext('filteredUnbilledReceipts()[0].receipt_no',context),651);
  el('unbilledFrom').value='1405/07/01';el('unbilledTo').value='1405/06/01';vm.runInContext('renderUnbilledReceipts()',context);assert.match(el('unbilledError').textContent,/شروع/);
});
test('old year response and response after logout cannot repopulate receipt data',async()=>{
  const {context,el}=setup();const pending=[];context.api=()=>new Promise(resolve=>pending.push(resolve));
  el('unbilledYear').value='1404';const old=vm.runInContext('loadUnbilledReceipts()',context);
  el('unbilledYear').value='1405';const fresh=vm.runInContext('loadUnbilledReceipts()',context);
  pending[1]({items:rows,year:1405,read_at:'2026-09-08T12:00:00Z'});await fresh;
  pending[0]({items:[],year:1404,read_at:'2026-09-08T12:00:00Z'});await old;
  assert.equal(el('unbilledYear').value,'1405');assert.match(el('unbilledRows').innerHTML,/650/);
  const last=vm.runInContext('loadUnbilledReceipts()',context);vm.runInContext('resetUnbilledReceipts()',context);
  pending[2]({items:rows,year:1405});await last;assert.doesNotMatch(el('unbilledRows').innerHTML,/650/);
});
test('failure removes stale receipts and remains an error rather than a zero result',async()=>{
  const {context,el}=setup();context.rows=rows;vm.runInContext('unbilledState.items=rows;unbilledState.loaded=true',context);
  context.api=async()=>{throw new Error('source unavailable')};await vm.runInContext('loadUnbilledReceipts()',context);
  assert.match(el('unbilledError').textContent,/source unavailable/);assert.doesNotMatch(el('unbilledRows').innerHTML,/650/);
  assert.equal(el('unbilledCount').textContent,'');assert.equal(el('unbilledRefresh').disabled,false);
});

test('header filtering and sorting covers all receipt pages and confirmation controls invoice action',()=>{
  const {context,el}=setup();
  vm.runInContext(fs.readFileSync('app/static/warehouse-table-filters.js','utf8'),context);
  context.rows=Array.from({length:75},(_,i)=>({...rows[0],receipt_id:i+1,receipt_no:i+1,confirmed:i!==74}));
  el('unbilledTable').querySelectorAll=()=>[{dataset:{sharedColumnFilter:'position:3'},value:'فروشنده'}];
  vm.runInContext("unbilledState.items=rows;unbilledState.loaded=true;sharedTableSorts.set(document.getElementById('unbilledTable'),{key:'position:0',direction:'desc'});renderUnbilledReceipts()",context);
  const html=el('unbilledRows').innerHTML;
  assert.ok(html.indexOf('>75</td>')<html.indexOf('>74</td>'));assert.doesNotMatch(html,/data-purchase-receipt="75"/);assert.match(html,/data-purchase-receipt="74"/);
  assert.equal(el('unbilledPage').textContent,'1 تا 50');
  vm.runInContext('unbilledState.page=1;renderUnbilledReceipts()',context);assert.match(el('unbilledRows').innerHTML,/>1<\/td>/);assert.doesNotMatch(el('unbilledRows').innerHTML,/>75<\/td>/);
});


test('selection persists across pagination and filtering; incompatible receipts cannot join it',()=>{
  const {context,el}=setup();context.rows=Array.from({length:55},(_,i)=>({...rows[0],receipt_id:i+1,receipt_no:650+i,supplier_id:17,fiscal_year:1405}));
  context.rows.push({...context.rows[0],receipt_id:80,stock_id:9},{...context.rows[0],receipt_id:81,supplier_id:15},{...context.rows[0],receipt_id:82,fiscal_year:1404},{...context.rows[0],receipt_id:83,confirmed:false});
  vm.runInContext('unbilledState.items=rows;unbilledState.loaded=true;setUnbilledReceiptSelection(1,true);unbilledState.page=1;renderUnbilledReceipts();setUnbilledReceiptSelection(55,true)',context);
  el('unbilledSearch').value='no matching receipt';vm.runInContext('renderUnbilledReceipts()',context);
  assert.equal(vm.runInContext('unbilledState.selected.size',context),2);assert.match(el('unbilledSelectedCount').textContent,/650.*704/);
  for(const [id,reason] of [[80,'انبار'],[81,'تأمین‌کننده'],[82,'سال مالی'],[83,'تأیید']]){
    assert.equal(vm.runInContext(`setUnbilledReceiptSelection(${id},true)`,context),false);assert.ok(el('unbilledError').textContent.includes(reason));
  }
  assert.equal(vm.runInContext('unbilledState.selected.size',context),2);
  vm.runInContext('setUnbilledReceiptSelection(1,false)',context);assert.equal(vm.runInContext('unbilledState.selected.size',context),1);
});

test('twenty-receipt limit permits deselection; logout discards selections',()=>{
  const {context,el}=setup();context.rows=Array.from({length:21},(_,i)=>({...rows[0],receipt_id:i+1,supplier_id:17,fiscal_year:1405}));
  vm.runInContext('unbilledState.items=rows;unbilledState.loaded=true;for(let i=1;i<=20;i++)setUnbilledReceiptSelection(i,true)',context);
  assert.equal(vm.runInContext('setUnbilledReceiptSelection(21,true)',context),false);assert.match(el('unbilledError').textContent,/۲۰/);
  assert.equal(vm.runInContext('setUnbilledReceiptSelection(1,false);setUnbilledReceiptSelection(21,true)',context),true);
  vm.runInContext('resetUnbilledReceipts()',context);assert.equal(vm.runInContext('unbilledState.selected.size',context),0);
});

test('fresh fetch reconciles missing, unconfirmed and changed-identity selections and keeps fresh metadata',async()=>{
  const {context,el}=setup();
  context.rows=Array.from({length:6},(_,i)=>({...rows[0],receipt_id:i+1,receipt_no:650+i,supplier_id:17,fiscal_year:1405}));
  vm.runInContext('unbilledState.items=rows;unbilledState.loaded=true;for(let i=1;i<=6;i++)setUnbilledReceiptSelection(i,true)',context);
  const fresh=[{...context.rows[0],receipt_no:700,comment:'updated'},
    {...context.rows[2],confirmed:false},{...context.rows[3],supplier_id:15},
    {...context.rows[4],stock_id:9},{...context.rows[5],fiscal_year:1404}];
  context.api=async()=>({items:fresh,year:1405,read_at:'2026-09-08T12:00:00Z'});
  await vm.runInContext('loadUnbilledReceipts()',context);
  assert.equal(vm.runInContext('unbilledState.selected.size',context),1);
  assert.equal(vm.runInContext('unbilledState.selected.get(1).comment',context),'updated');
  assert.match(el('unbilledSelectedCount').textContent,/700.*5 رسید از انتخاب‌ها/);
  assert.equal(el('unbilledCreateInvoice').disabled,false);
});

test('failed fetch retains selection but blocks creation until a successful fresh fetch',async()=>{
  const {context,el}=setup();context.rows=[{...rows[0],supplier_id:17,fiscal_year:1405}];
  vm.runInContext('unbilledState.items=rows;unbilledState.loaded=true;setUnbilledReceiptSelection(1,true)',context);
  context.api=async()=>{throw new Error('offline')};await vm.runInContext('loadUnbilledReceipts()',context);
  assert.equal(vm.runInContext('unbilledState.selected.size',context),1);assert.equal(el('unbilledCreateInvoice').disabled,true);
  context.api=async()=>({items:context.rows,year:1405,read_at:'2026-09-08T12:00:00Z'});await vm.runInContext('loadUnbilledReceipts()',context);
  assert.equal(vm.runInContext('unbilledState.selected.size',context),1);assert.equal(el('unbilledCreateInvoice').disabled,false);
});
