const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
function setup(){
  const nodes={},events={};
  const node=key=>nodes[key]??={value:'',hidden:false,disabled:false,textContent:'',innerHTML:'',dataset:{},
    removeAttribute(key){delete this[key]},setAttribute(){},focus(){},addEventListener(name,fn){this[name]=fn}};
  const c=vm.createContext({document:{addEventListener:(name,fn)=>events[name]=fn,querySelectorAll:()=>[node('#checkbarReference'),node('#note'),node('#date')]},
    $:node,normalizeSearchText:v=>String(v??'').replace(/[۰-۹]/g,x=>x.charCodeAt(0)-1776).trim(),
    esc:v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),fa:String,
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},AbortController,setTimeout,clearTimeout,
    FormData:class{constructor(){this.data={}}append(k,v){(this.data[k]??=[]).push(v)}},confirm:()=>true});
  vm.runInContext(readFileSync('app/static/warehouse-checkbar.js','utf8'),c);
  vm.runInContext(readFileSync('app/static/warehouse-checkbar-image.js','utf8'),c);
  events.DOMContentLoaded();
  node('#checkbarReference').dataset.checkbarMeta='reference_no';node('#note').dataset.checkbarMeta='note';node('#date').dataset.checkbarMeta='date';
  vm.runInContext("checkbarState.source={warehouse:'karaj',supplier:'supplier',order_ids:[],expected_token:'token',lines:[],catalog:[{product_code:'A',product_name:'Product A',manufacturer_product_code:'001',conversion_rate:12},{product_code:'B',product_name:'Product B',conversion_rate:6}]};renderCheckbarLines=()=>{};renderCheckbarProducts=()=>{}",c);
  return {c,nodes,run:code=>vm.runInContext(code,c)};
}
const result={expected_token:'token',supplier:'supplier',metadata:{reference_no:'2222',date:'1405/06/15'},warnings:[],rows:[
  {description:'<unsafe>',supplier_code:'001',quantity_text:'2 cartons',cartons:2,units:0,selected:0,suggestions:[0],problems:[]},
  {description:'B',quantity_text:'unreadable',cartons:null,units:null,selected:1,suggestions:[1],problems:['ناخوانا']} ]};
async function extracted(s,data=result){
  s.c.api=async()=>data;
  s.run("chooseCheckbarImage({type:'image/png',size:10,name:'note.png'})");
  await s.run('readCheckbarImage()');
}

test('completed extraction reopens a closed panel and keeps a visible route back to review',async()=>{
  const s=setup();let finish;
  s.c.api=()=>new Promise(resolve=>{finish=resolve});
  s.run("chooseCheckbarImage({type:'image/png',size:10,name:'note.png'})");
  const reading=s.run('readCheckbarImage()');
  s.run("$('#checkbarImagePanel').open=false");
  finish(result);await reading;
  assert.equal(s.nodes['#checkbarImagePanel'].open,true);
  assert.equal(s.nodes['#checkbarImageResult'].hidden,false);
  assert.equal(s.nodes['#checkbarImageShowResult'].hidden,false);
  assert.match(s.nodes['#checkbarImageShowResult'].textContent,/2/);
  s.nodes['#checkbarImagePanel'].open=false;
  s.nodes['#checkbarImageShowResult'].click();
  assert.equal(s.nodes['#checkbarImagePanel'].open,true);
  s.run('applyCheckbarImage()');
  assert.equal(s.nodes['#checkbarImageShowResult'].hidden,true);
});

test('invalidating extracted rows removes the review shortcut',async()=>{
  const s=setup();await extracted(s);
  s.run('invalidateCheckbarImage()');
  assert.equal(s.nodes['#checkbarImageShowResult'].hidden,true);
});
test('ranked suggestion is selected with escaped reason and can enter unsaved checkbar',async()=>{
  const s=setup();
  const draft=structuredClone(result);
  draft.rows=[{...draft.rows[0],cartons:30,units:0,total_base_units:360,
    match_reason:'پیشنهاد بر اساس بارکد <unsafe>',problems:['شرح نیازمند بررسی است.']}];
  await extracted(s,draft);
  assert.equal(s.run('checkbarImage.rows[0].selected'),'0');
  assert.match(s.nodes['#checkbarImageRows'].innerHTML,/&lt;unsafe>/);
  assert.match(s.nodes['#checkbarImageRows'].innerHTML,/value="0" selected/);
  s.run('applyCheckbarImage()');
  assert.equal(s.run('checkbarState.lines[0].product_code'),'A');
  assert.equal(s.run('checkbarState.lines[0].cartons'),30);
  assert.equal(s.run('checkbarState.saved'),null);
});
test('read preview escapes text and applies counts including zero and blank, without saving',async()=>{
  const s=setup();await extracted(s);
  assert.match(s.nodes['#checkbarImageRows'].innerHTML,/&lt;unsafe>/);
  let calls=0;s.c.api=()=>{calls++;throw new Error('must not save')};
  s.run('applyCheckbarImage()');
  assert.equal(s.run('checkbarState.lines[0].units'),0);
  assert.equal(s.run('checkbarState.lines[1].units'),'');
  assert.equal(s.nodes['#checkbarReference'].value,'2222');
  assert.match(s.nodes['#note'].value,/نیازمند شمارش/);
  assert.equal(s.run('checkbarState.saved'),null);assert.equal(calls,0);
});

test('photo-only mode adds only read products with photo quantity and separate in-transit context',async()=>{
  const s=setup();
  s.run("checkbarState.source.aggregate_open_lines=[{product_code:'A',order_quantity:200,received_qty:0,remaining_qty:200},{product_code:'B',order_quantity:100,received_qty:0,remaining_qty:100}]");
  await extracted(s,{...result,rows:[{...result.rows[0],cartons:0,units:120}]});
  s.run('applyCheckbarImage()');
  assert.equal(s.run('checkbarState.lines.length'),1);
  assert.equal(s.run('checkbarActual(checkbarState.lines[0])'),120);
  assert.equal(s.run('checkbarState.lines[0].remaining_qty'),200);
});

test('supplier total is not doubled and changed carton factor requires explicit count review',async()=>{
  const s=setup();
  s.run('checkbarState.source.catalog[0].conversion_rate=24');
  await extracted(s,{...result,rows:[{...result.rows[0],cartons:70,units:0,total_base_units:1680}]});
  s.run('checkbarImage.products[0].conversion_rate=12;applyCheckbarImage()');
  assert.equal(s.run('checkbarState.lines.length'),0);
  assert.match(s.nodes['#checkbarImageStatus'].textContent,/مقدار کل/);
  s.run('checkbarImage.products[0].conversion_rate=24;applyCheckbarImage()');
  assert.equal(s.run('checkbarActual(checkbarState.lines[0])'),1680);
});

test('explicit quantity edit can override supplier total after warehouse counting',async()=>{
  const s=setup();
  await extracted(s,{...result,rows:[{...result.rows[0],cartons:2,units:0,total_base_units:24}]});
  const row={dataset:{imageRow:'0'}};
  s.nodes['#checkbarImageRows'].input({target:{dataset:{imageField:'cartons'},value:'3',closest:()=>row}});
  s.run('applyCheckbarImage()');
  assert.equal(s.run('checkbarActual(checkbarState.lines[0])'),36);
});

test('all-items mode fills existing products from photo and preserves other uncounted order rows',async()=>{
  const s=setup();
  s.run("checkbarState.includeOrderItems=true;checkbarState.lines=[{preorder_id:null,product_code:'A',conversion_rate:12,cartons:'',units:'',manufacturer_price_new:77},{preorder_id:null,product_code:'B',conversion_rate:6,cartons:'',units:''}]");
  await extracted(s,{...result,rows:[{...result.rows[0],cartons:0,units:120}]});
  s.run('applyCheckbarImage()');
  assert.equal(s.run('checkbarState.lines.length'),2);
  assert.equal(s.run('checkbarActual(checkbarState.lines[0])'),120);
  assert.equal(s.run('checkbarActual(checkbarState.lines[1])'),null);
  assert.equal(s.run('checkbarState.lines[0].manufacturer_price_new'),77);
});

test('all-items photo overwrite requires confirmation even for prior zero and never sums duplicate arrivals',async()=>{
  const s=setup();
  s.run("checkbarState.includeOrderItems=true;checkbarState.lines=[{product_code:'A',conversion_rate:12,cartons:0,units:0},{product_code:'B',conversion_rate:6,cartons:1,units:0}]");
  await extracted(s,{...result,rows:[{...result.rows[0],cartons:0,units:120}]});
  s.c.confirm=()=>false;s.run('applyCheckbarImage()');
  assert.equal(s.run('checkbarActual(checkbarState.lines[0])'),0);
  s.c.confirm=()=>true;s.run('applyCheckbarImage()');
  assert.equal(s.run('checkbarActual(checkbarState.lines[0])'),120);
  assert.equal(s.run('checkbarActual(checkbarState.lines[1])'),6);
});
test('unmatched row cannot disappear silently, explicit exclusion allows import',async()=>{
  const s=setup();const data=structuredClone(result);data.rows[1].selected=null;await extracted(s,data);
  s.run('applyCheckbarImage()');assert.equal(s.run('checkbarState.lines.length'),0);
  assert.match(s.nodes['#checkbarImageStatus'].textContent,/ردیف 2/);
  s.run('checkbarImage.rows[1].included=false;applyCheckbarImage()');assert.equal(s.run('checkbarState.lines.length'),1);
});
test('duplicate mapping and invalid quantity do not replace draft',async()=>{
  const s=setup();await extracted(s);
  s.run("checkbarImage.rows[1].selected='0';applyCheckbarImage()");assert.equal(s.run('checkbarState.lines.length'),0);
  s.run("checkbarImage.rows[1].selected='1';checkbarImage.rows[0].cartons='-2';applyCheckbarImage()");
  assert.equal(s.run('checkbarState.lines.length'),0);
});
test('replacing existing user input requires confirmation and cancellation preserves metadata',async()=>{
  const s=setup();await extracted(s);s.c.confirm=()=>false;
  s.run("checkbarState.lines=[{product_code:'old'}]");s.nodes['#checkbarReference'].value='1111';
  s.run('applyCheckbarImage()');assert.equal(s.run('checkbarState.lines[0].product_code'),'old');
  assert.equal(s.nodes['#checkbarReference'].value,'1111');
});
test('saved, pending and stale source prevent application',async()=>{
  for(const state of ["checkbarState.saved={id:1}","checkbarState.pending={}","checkbarState.source={}"]){
    const s=setup();await extracted(s);s.run(state+';applyCheckbarImage()');
    assert.equal(s.run('checkbarState.lines.length'),0);
  }
});
test('late response cannot overwrite a reopened or reselected draft',async()=>{
  const s=setup();let resolve;s.c.api=()=>new Promise(r=>resolve=r);
  s.run("chooseCheckbarImage({type:'image/png',size:10})");const pending=s.run('readCheckbarImage()');
  s.run('checkbarState.sequence++;resetCheckbarImage()');resolve(result);await pending;
  assert.equal(s.run('checkbarImage.result'),null);assert.equal(s.nodes['#checkbarImageResult'].hidden,true);
});
test('double click sends one image request; failure allows retry without touching form',async()=>{
  const s=setup();let reject,calls=0;s.c.api=()=>{calls++;return new Promise((_,r)=>reject=r)};
  s.run("chooseCheckbarImage({type:'image/png',size:10})");const pending=s.run('readCheckbarImage()');await s.run('readCheckbarImage()');
  assert.equal(calls,1);reject(new Error('offline'));await pending;
  assert.equal(s.nodes['#checkbarImageRead'].disabled,false);assert.equal(s.run('checkbarState.lines.length'),0);
});
test('file selection rejects wrong type, empty and oversized files',()=>{
  const s=setup();
  for(const f of [{type:'text/html',size:10},{type:'image/png',size:0},{type:'image/png',size:11*1024*1024}]){
    s.c.file=f;s.run('chooseCheckbarImage(file)');assert.equal(s.run('checkbarImage.pages.length'),0);
  }
});

test('multi-select and camera append pages, cancellation preserves them, ordered upload uses one request',async()=>{
  const s=setup(),input=s.nodes['#checkbarImageFile'],camera=s.nodes['#checkbarImageCamera'];
  input.files=[{name:'one.png',type:'image/png',size:10},{name:'two.png',type:'image/png',size:10}];
  input.change({target:input});
  camera.files=[{name:'three.jpg',type:'image/jpeg',size:20}];camera.change({target:camera});
  input.files=[];input.change({target:input});
  assert.equal(s.run('checkbarImage.pages.length'),3);
  let sent;s.c.api=async(_,options)=>{sent=options.body.data;return {...result,page_count:3}};
  await s.run('readCheckbarImage()');
  assert.deepEqual(sent.file.map(f=>f.name),['one.png','two.png','three.jpg']);
  assert.equal(sent.expected_token[0],'token');
});

test('page reorder/remove invalidates extraction, releases previews and blocks stale completion',async()=>{
  const s=setup();let resolve,revoked=[];s.c.URL.revokeObjectURL=url=>revoked.push(url);
  s.run("chooseCheckbarImage([{name:'one',type:'image/png',size:10},{name:'two',type:'image/png',size:10}])");
  s.c.api=()=>new Promise(r=>resolve=r);const pending=s.run('readCheckbarImage()');
  s.run("changeCheckbarImagePage(1,'previous')");resolve({...result,page_count:2});await pending;
  assert.equal(s.run('checkbarImage.pages[0].file.name'),'two');
  assert.equal(s.run('checkbarImage.result'),null);
  s.run("changeCheckbarImagePage(0,'remove')");
  assert.equal(s.run('checkbarImage.pages[0].file.name'),'one');assert.equal(revoked.length,1);
  s.run('resetCheckbarImage()');assert.equal(revoked.length,2);
  assert.equal(s.nodes['#checkbarImageRead'].disabled,true);
});

test('invalid additions and page/total limits leave existing pages intact',()=>{
  const s=setup();s.run("chooseCheckbarImage({name:'one',type:'image/png',size:10})");
  for(const files of [
    [{type:'image/png',size:10},{type:'text/html',size:1}],
    Array.from({length:10},()=>({type:'image/png',size:1})),
    Array.from({length:3},()=>({type:'image/png',size:10*1024*1024}))]){
    s.c.files=files;s.run('chooseCheckbarImage(files)');assert.equal(s.run('checkbarImage.pages.length'),1);
  }
});
test('manual search stays within selected supplier catalog and preserves source order identities',()=>{
  const s=setup();s.run("checkbarImage.products=checkbarImageProducts(checkbarState.source)");
  assert.match(s.run("checkbarImageOptions({search:'001',selected:'',suggestions:[]})"),/Product A/);
  assert.doesNotMatch(s.run("checkbarImageOptions({search:'001',selected:'',suggestions:[]})"),/Product B/);
  const products=JSON.parse(s.run("JSON.stringify(checkbarImageProducts({lines:[{product_code:'A',preorder_id:1},{product_code:'A',preorder_id:2}],catalog:[{product_code:'A'},{product_code:'B'}]}))"));
  assert.equal(products.length,3);assert.equal(products[1].preorder_id,2);
});

test('PDF and Excel can be mixed with photos and one file may yield multiple pages',async()=>{
  const s=setup();
  s.run("chooseCheckbarImage([{name:'invoice.PDF',type:'application/pdf',size:100},{name:'invoice.xlsx',type:'',size:100},{name:'invoice.xls',type:'application/vnd.ms-excel',size:100}])");
  assert.equal(s.run('checkbarImage.pages.length'),3);
  assert.match(s.nodes['#checkbarImagePages'].innerHTML,/XLSX/);
  assert.doesNotMatch(s.nodes['#checkbarImagePages'].innerHTML,/<img/);
  let sent;s.c.api=async(_,options)=>{sent=options.body.data;return {...result,file_count:3,page_count:6,
    rows:result.rows.map((r,i)=>({...r,source_label:'invoice.xlsx · برگه '+i}))}};
  await s.run('readCheckbarImage()');
  assert.equal(sent.file.length,3);assert.equal(s.nodes['#checkbarImageResult'].hidden,false);
  assert.match(s.nodes['#checkbarImageRows'].innerHTML,/invoice.xlsx · برگه 1/);
  s.run('applyCheckbarImage()');assert.equal(s.run('checkbarState.lines.length'),2);
});

test('unsupported document additions and partial file response preserve draft',async()=>{
  const s=setup();s.run("chooseCheckbarImage({name:'invoice.xlsx',type:'',size:10});chooseCheckbarImage({name:'macro.xlsm',type:'',size:10})");
  assert.equal(s.run('checkbarImage.pages.length'),1);
  s.c.api=async()=>({...result,file_count:2,page_count:2});
  await s.run('readCheckbarImage()');
  assert.equal(s.run('checkbarImage.result'),null);assert.equal(s.run('checkbarState.lines.length'),0);
});

test('reading clears stale empty-table alert, blocks save, then exposes explicit import step',async()=>{
  const s=setup();let resolve;
  s.run("checkbarNotice('error','ابتدا حداقل یک کالا به چک بار اضافه کنید.');chooseCheckbarImage({name:'note.png',type:'image/png',size:10})");
  s.c.api=()=>new Promise(r=>resolve=r);
  const pending=s.run('readCheckbarImage()');
  assert.match(s.nodes['#checkbarNotice'].textContent,/در حال خواندن/);
  assert.equal(s.nodes['#checkbarNotice'].className,'checkbar-notice info');
  assert.equal(s.nodes['#checkbarIssue'].disabled,true);
  await s.run('issueCheckbar()');assert.equal(s.run('checkbarState.saved'),null);
  resolve(result);await pending;
  assert.match(s.nodes['#checkbarNotice'].textContent,/وارد کردن اقلام به چک‌بار/);
  assert.equal(s.nodes['#checkbarIssue'].disabled,true);
  assert.equal(s.run('checkbarState.lines.length'),0);
  s.run('applyCheckbarImage()');assert.equal(s.run('checkbarState.lines.length'),2);
});

test('failed extraction appears at top of form, retains files and allows retry',async()=>{
  const s=setup();s.run("chooseCheckbarImage({type:'image/png',size:10})");
  s.c.api=async()=>{throw new Error('خواندن حواله کامل نشد؛ فایل واضح‌تر بفرستید.')};
  await s.run('readCheckbarImage()');
  assert.match(s.nodes['#checkbarNotice'].textContent,/فایل واضح‌تر/);
  assert.equal(s.nodes['#checkbarNotice'].className,'checkbar-notice error');
  assert.equal(s.run('checkbarImage.pages.length'),1);
  assert.equal(s.nodes['#checkbarImageRead'].disabled,false);
});
