const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function setup(){
  const elements=new Map();
  const el=id=>{if(!elements.has(id))elements.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,open:false,setAttribute(){},focus(){},showModal(){this.open=true},close(){this.open=false}});return elements.get(id)};
  const calls=[];
  const context=vm.createContext({URLSearchParams,Intl,document:{getElementById:el,addEventListener(){}},fa:String,
    normalizeSearchText:v=>String(v??''),esc:v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'),
    purchaseState:{catalog:{today:'1405/06/17'}},purchaseHeaders:()=>({'Content-Type':'application/json'}),window:{confirm:()=>true},
    api:async(url,options)=>{calls.push({url,body:options?JSON.parse(options.body):null});return {items:[],year:1405,read_at:'2026-09-08T12:00:00Z'}}});
  for(const file of ['warehouse-unbilled-receipts.js','warehouse-purchase-invoice.js'])vm.runInContext(fs.readFileSync('app/static/'+file,'utf8'),context);
  context.receipts=[1,2,3].map(id=>({receipt_id:id,receipt_no:670+id,receipt_date:'1405/06/17',supplier_id:17,supplier_name:'کامان',stock_id:1,stock_name:'کرج',fiscal_year:1405,confirmed:true,comment:'',manufacturers:[]}));
  vm.runInContext('unbilledState.items=receipts;unbilledState.loaded=true;setUnbilledReceiptSelection(1,true);setUnbilledReceiptSelection(2,true);openPurchaseInvoice([1,2])',context);
  el('invoiceSupplierNo').value='999';
  const preview={ready:true,bridge_enabled:true,commit_enabled:true,receipt_ids:[1,2],receipt_nos:[671,672],preview_token:'locked-two-receipts',total:1000,errors:[],items:[{product_code:'123',product_name:'<img src=x>',quantity:7,source_price:200,amounts:{unit_price:150,total:1000},receipt_sources:[{receipt_id:1,receipt_no:671,quantity:3},{receipt_id:2,receipt_no:672,quantity:4}]}]};
  return {context,el,calls,preview};
}

test('opening invoice before contracts are loaded fills valid Persian dates without era suffix',async()=>{
  const {context,el,preview}=setup();
  context.Date=class extends Date {constructor(){super('2026-09-08T21:00:00Z')}};
  context.purchaseState.catalog={suppliers:[]};
  vm.runInContext('openPurchaseInvoice(1)',context);
  // Already the next day in Tehran, regardless of desktop/browser timezone.
  assert.equal(el('invoiceSupplierDate').value,'1405/06/18');
  assert.equal(el('invoiceVoucherDate').value,'1405/06/18');
  el('invoiceSupplierNo').value='999';
  const calls=[];context.api=async(url,options)=>{calls.push(JSON.parse(options.body));return preview};
  await vm.runInContext('previewPurchaseInvoice()',context);
  assert.equal(calls[0].supplier_invoice_date,'1405/06/18');
  assert.equal(calls[0].voucher_date,'1405/06/18');
});

test('dialog names every receipt; preview submits selected IDs and shows source quantities for merged goods',async()=>{
  const {context,el,preview}=setup();const calls=[];
  context.api=async(url,options)=>{calls.push({url,body:JSON.parse(options.body)});return preview};
  assert.match(el('invoiceReceipts').innerHTML,/671.*672/);assert.match(el('invoiceTitle').textContent,/2/);
  await vm.runInContext('previewPurchaseInvoice()',context);
  assert.equal(calls[0].url,'/warehouse-assistant/api/purchase-invoices/preview');assert.deepEqual(calls[0].body.receipt_ids,[1,2]);assert.equal(calls[0].body.supplier_invoice_no,'999');
  assert.match(el('invoiceRows').innerHTML,/671: 3.*672: 4/);assert.match(el('invoiceRows').innerHTML,/&lt;img/);assert.doesNotMatch(el('invoiceRows').innerHTML,/<img/);
  assert.equal(el('invoiceCommit').disabled,false);
});

test('busy preview freezes selection and rejects opening a different invoice',async()=>{
  const {context,el,preview}=setup();let resolve;
  context.api=()=>new Promise(r=>resolve=r);
  const pending=vm.runInContext('previewPurchaseInvoice()',context);
  assert.equal(el('unbilledClearSelection').disabled,true);assert.equal(el('invoiceClose').disabled,true);
  assert.equal(vm.runInContext('setUnbilledReceiptSelection(1,false)',context),false);
  vm.runInContext('openPurchaseInvoice(3)',context);assert.match(el('invoiceReceipts').innerHTML,/671.*672/);
  resolve(preview);await pending;assert.equal(el('unbilledClearSelection').disabled,false);
});

test('invoice layout separates column discounts and post-VAT tail, displaying real contract stages',async()=>{
  const {context,el,preview}=setup();
  preview.items[0].pricing={basis:'manufacturer',includes_tax:true,adjustment_percent:'0',discount_percent:'18',discount_steps:[{percent:'18'}]};
  preview.items[0].tax_rate=10;
  preview.items[0].amounts={unit_price:'1000',gross:'7000',discount:'1260',net_before_tax:'5740',tax:'574',after_tax:'6314'};
  preview.summary={gross:'7000',discount:'1260',net_before_tax:'5740',tax:'574',after_tax:'6314',total:'5800',tail_discounts:[{kind:'percent',basis:'net_before_tax',value:'8.95',base:'5740',amount:'514'}]};
  context.api=async()=>preview;await vm.runInContext('previewPurchaseInvoice()',context);
  assert.match(el('invoiceRows').innerHTML,/18٪/);
  assert.doesNotMatch(el('invoiceRows').innerHTML,/8.95/);
  assert.match(el('invoiceSummary').innerHTML,/جمع با ارزش افزوده.*تخفیف انتهایی 8.95٪.*خالص قبل از مالیات.*قابل پرداخت/s);
  assert.match(el('invoiceSteps').innerHTML,/خارج کردن ارزش افزوده.*مرحلهٔ 1: 18٪/s);
  preview.summary.tail_discounts=[{kind:'fixed',basis:'invoice',value:'514',amount:'514'}];
  await vm.runInContext('previewPurchaseInvoice()',context);
  assert.match(el('invoiceSummary').innerHTML,/تخفیف انتهایی مبلغی/);
  vm.runInContext('openPurchaseInvoice(3)',context);
  assert.equal(el('invoiceSummary').hidden,true);assert.equal(el('invoiceSummary').innerHTML,'');
});

test('failed or cancelled transfer preserves selection; success clears only transferred receipts',async()=>{
  const {context,el,preview}=setup();const calls=[];
  context.api=async(url,options)=>{calls.push({url,body:JSON.parse(options.body)});return url.endsWith('/preview')?preview:{BridgeStatus:'blocked',Message:'مصرف شده'}};
  await vm.runInContext('previewPurchaseInvoice()',context);
  context.window.confirm=()=>false;await vm.runInContext('transferPurchaseInvoice()',context);assert.equal(calls.length,1);
  context.window.confirm=()=>true;await vm.runInContext('transferPurchaseInvoice()',context);
  assert.equal(vm.runInContext('unbilledState.selected.size',context),2);assert.match(el('invoiceMessage').textContent,/مصرف شده/);
  assert.deepEqual(calls[1].body.receipt_ids,[1,2]);assert.equal(calls[1].body.confirmed,true);assert.equal(calls[1].body.preview_token,'locked-two-receipts');
  vm.runInContext('setUnbilledReceiptSelection(3,true)',context);
  context.api=async(url,options)=>url.endsWith('/transfer')?{BridgeStatus:'sent',InvoiceNo:811}:{items:context.receipts.slice(2),year:1405,read_at:'2026-09-08T12:00:00Z'};
  await vm.runInContext('transferPurchaseInvoice()',context);
  assert.equal(vm.runInContext('unbilledState.selected.size',context),1);assert.equal(vm.runInContext('unbilledState.selected.has(3)',context),true);
  assert.match(el('invoiceMessage').textContent,/811.*2 رسید/);assert.equal(el('invoiceCommit').disabled,true);
});

test('single receipt uses collection API too; expired dialog response cannot enable another invoice',async()=>{
  const {context,el,preview}=setup();let resolve;
  context.api=()=>new Promise(r=>resolve=r);
  vm.runInContext('openPurchaseInvoice(3)',context);
  const pending=vm.runInContext('previewPurchaseInvoice()',context);
  assert.equal(vm.runInContext('purchaseInvoice.request.receipt_ids.join()',context),'3');
  vm.runInContext('resetPurchaseInvoice();openPurchaseInvoice(1)',context);
  resolve(preview);await pending;
  assert.equal(vm.runInContext('purchaseInvoice.preview',context),null);assert.equal(el('invoiceCommit').disabled,true);
});

test('invoice source list uses current fetched records rather than stale selected snapshots',()=>{
  const {context,el}=setup();
  vm.runInContext("resetPurchaseInvoice();unbilledState.items=unbilledState.items.map(r=>({...r,receipt_no:r.receipt_no+100,receipt_date:'1405/06/18'}));openPurchaseInvoice([1,2])",context);
  assert.match(el('invoiceReceipts').innerHTML,/771.*1405\/06\/18.*772/);
  assert.doesNotMatch(el('invoiceReceipts').innerHTML,/671|672/);
  vm.runInContext('resetPurchaseInvoice();unbilledState.loaded=false;openPurchaseInvoice([1,2])',context);
  assert.equal(el('purchaseInvoiceDialog').open,false);assert.match(el('unbilledError').textContent,/ابتدا فهرست/);
});
