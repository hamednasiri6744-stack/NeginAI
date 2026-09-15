const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
function setup(){const ctx=vm.createContext({document:{addEventListener(){}},normalizeSearchText:v=>String(v??'').replace(/[۰-۹]/g,c=>c.charCodeAt(0)-1776).replace(/[٠-٩]/g,c=>c.charCodeAt(0)-1632).toLowerCase().trim()});vm.runInContext(readFileSync('app/static/warehouse-table-filters.js','utf8'),ctx);return ctx}
test('only data columns receive filters, never actions or selection',()=>{
  const c=setup();
  for(const title of ['عملیات','انتخاب','تکمیل ردیف','فایل‌ها','']){
    c.header={dataset:{},textContent:title};assert.equal(vm.runInContext('columnNeedsFilter(header,0)',c),false);
  }
  c.header={dataset:{previewColumn:'actions'},textContent:'حذف'};assert.equal(vm.runInContext('columnNeedsFilter(header,0)',c),false);
  for(const title of ['کد کالا','تعداد کل','فعال','نام کالا']){
    c.header={dataset:{},textContent:title};assert.equal(vm.runInContext('columnNeedsFilter(header,0)',c),true);
  }
});
test('filters combine with AND and accept Persian/English digits',()=>{const c=setup();assert.equal(vm.runInContext("tableFilterMatches(new Map([['code','00123'],['name','soap']]),[{key:'code',value:'۱۲۳'},{key:'name',value:'soap'}])",c),true);assert.equal(vm.runInContext("tableFilterMatches(new Map([['code','00123']]),[{key:'code',value:'124'}])",c),false)});
test('column identity follows reordered headers, not physical position',()=>{const c=setup();c.cell={dataset:{previewColumn:'brand'}};assert.equal(vm.runInContext('tableColumnKey(cell,0)',c),vm.runInContext('tableColumnKey(cell,9)',c))});

test('sorting compares localized numeric values and dates, placing empty values last both ways',()=>{
  const c=setup();
  for(const [a,b,direction,sign] of [['۱٬۲۰۰','90','desc',-1],['١٢٫٥','۲','asc',1],['−۵','0','desc',1],['۱۴۰۵/۶/۱۷','1405/06/2','desc',-1],['۱۲٪','۹٪','asc',1],['—','0','desc',1],['','0','asc',1]]){
    c.args=[a,b,direction];assert.equal(Math.sign(vm.runInContext('compareSharedTableValues(...args)',c)),sign,JSON.stringify(c.args));
  }
});

test('paged data is filtered and sorted before taking the visible page, leaving source intact',()=>{
  const c=setup();c.rows=Array.from({length:120},(_,i)=>({id:i+1,name:i>100?'سیلانه':'کامان'}));
  const query={filters:[{key:'name',value:'سیلانه'}],sort:{key:'id',direction:'desc'}};c.query=query;
  assert.deepEqual(Array.from(vm.runInContext('querySharedTableItems(rows,query,(row,key)=>row[key]).slice(0,3).map(r=>r.id)',c)),[120,119,118]);
  assert.equal(c.rows[0].id,1);assert.equal(c.rows.length,120);
});

test('headers toggle descending then ascending and changing column restarts descending',()=>{
  const c=setup(),headers=['code','name'].map(key=>({dataset:{column:key},textContent:key,classList:{add(){}},setAttribute(k,v){this[k]=v}}));
  const table={dataset:{},tHead:{rows:[{cells:headers}]},querySelectorAll:()=>[]};c.table=table;c.header=headers[0];c.next=headers[1];c.queries=[];
  vm.runInContext('registerSharedTableAdapter(table,q=>queries.push(q));toggleSharedTableSort(table,header);toggleSharedTableSort(table,header);toggleSharedTableSort(table,next)',c);
  assert.deepEqual(JSON.parse(JSON.stringify(c.queries.map(q=>q.sort))),[{key:'column:code',direction:'desc'},{key:'column:code',direction:'asc'},{key:'column:name',direction:'desc'}]);
  assert.equal(headers[1]['aria-sort'],'descending');assert.equal(headers[0]['aria-sort'],'none');
  c.header={dataset:{},textContent:'عملیات'};assert.equal(vm.runInContext('columnNeedsSort(header,0)',c),false);
});

test('DOM sort moves existing rows without changing drafts, and preserves supplier group relationships',()=>{
  const c=setup();
  const header={dataset:{column:'qty'},textContent:'تعداد',classList:{add(){}},setAttribute(){}};
  const makeRow=(qty,group=false)=>({cells:[{dataset:{sortValue:String(qty)}}],classList:{contains:x=>group&&x==='supply-supplier-row'},draft:{value:'۱۲۳'}});
  const a=makeRow(30,true),b=makeRow(10),d=makeRow(20),e=makeRow(90,true),f=makeRow(90);
  const body={rows:[a,b,d,e,f],insertBefore(row,before){this.rows.splice(this.rows.indexOf(row),1);this.rows.splice(before?this.rows.indexOf(before):this.rows.length,0,row)}};
  c.table={dataset:{},tHead:{rows:[{cells:[header]}]},tBodies:[body]};c.header=header;
  vm.runInContext('toggleSharedTableSort(table,header)',c);
  assert.deepEqual(body.rows,[e,f,a,d,b]);assert.equal(b.draft.value,'۱۲۳');
  vm.runInContext('toggleSharedTableSort(table,header)',c);assert.deepEqual(body.rows,[a,b,d,e,f]);
});

function manualOrderTable(c){
  const classes=()=>{const values=new Set();return {add:x=>values.add(x),contains:x=>values.has(x),toggle:(x,on)=>on?values.add(x):values.delete(x)}};
  const cell=(text='',key)=>({dataset:key?{column:key}:{},textContent:text,hidden:false,children:[],append(x){this.children.push(x)},querySelector(selector){return this.children.find(x=>selector.includes('data-shared')?x.dataset.sharedColumnFilter:x.tagName==='INPUT')||null},querySelectorAll(){return this.children}});
  const row=(cells=[])=>({cells,classList:classes(),append(x){this.cells.push(x)},querySelectorAll(){return this.cells.flatMap(x=>x.children)}});
  c.document.createElement=tag=>tag==='tr'?row():tag==='th'?cell():{dataset:{},tagName:'INPUT',value:'',setAttribute(k,v){this[k]=v}};
  const headers=[cell('شماره','number'),cell('تأمین‌کننده','supplier')];
  headers.forEach(h=>{h.classList=classes();h.setAttribute=function(k,v){this[k]=v}});
  const makeOrder=(id,name,expanded)=>{
    const parent=row([cell(String(id)),cell(name)]),detail=row([cell('اقلام سفارش')]);
    parent.cells.forEach(x=>x.dataset.sortValue=x.textContent);
    detail.id=`manual-order-details-${id}`;detail.hidden=!expanded;
    const button={getAttribute:()=>detail.id};parent.querySelector=selector=>selector==='[data-manual-details][aria-controls]'?button:null;
    detail.draft={value:'۱۲۳'};return [parent,detail];
  };
  const [z,zd]=makeOrder(1,'Zeta',true),[a,ad]=makeOrder(2,'Alpha',false);
  const body={rows:[z,zd,a,ad],insertBefore(r,before){this.rows.splice(this.rows.indexOf(r),1);this.rows.splice(before?this.rows.indexOf(before):this.rows.length,0,r)}};
  const table={dataset:{},classList:{contains:()=>false},tHead:{rows:[row(headers)],append(x){this.rows.push(x)}},tBodies:[body],querySelectorAll:()=>body.rows};
  c.table=table;c.header=headers[1];return {table,body,z,zd,a,ad};
}

test('manual orders sort as parent/detail pairs while preserving expanded state and original nodes',()=>{
  const c=setup(),{body,z,zd,a,ad}=manualOrderTable(c);
  vm.runInContext('toggleSharedTableSort(table,header);toggleSharedTableSort(table,header)',c);
  assert.deepEqual(body.rows,[a,ad,z,zd]);
  assert.equal(zd.hidden,false);assert.equal(ad.hidden,true);assert.equal(zd.draft.value,'۱۲۳');
  vm.runInContext('toggleSharedTableSort(table,header)',c);
  assert.deepEqual(body.rows,[z,zd,a,ad]);
});

test('manual order filtering hides expanded details with their parent and restores expansion when cleared',()=>{
  const c=setup(),{table,z,zd,a,ad}=manualOrderTable(c);
  vm.runInContext('applySharedTableFilters(table)',c);
  const input=table.tHead.rows[1].cells[1].children[0];input.value='Alpha';
  vm.runInContext('applySharedTableFilters(table)',c);
  assert.equal(z.classList.contains('column-filtered-out'),true);
  assert.equal(zd.classList.contains('column-filtered-out'),true);
  assert.equal(a.classList.contains('column-filtered-out'),false);
  assert.equal(ad.hidden,true);assert.equal(zd.hidden,false);
  input.value='';vm.runInContext('applySharedTableFilters(table)',c);
  assert.equal(zd.classList.contains('column-filtered-out'),false);assert.equal(zd.hidden,false);
  assert.equal(ad.hidden,true);assert.equal(zd.draft.value,'۱۲۳');
});

test('pointer capture clicks sort once; filter controls, resizing and column dragging never sort',()=>{
  const listeners=new Map();const document={addEventListener(name,fn){if(!listeners.has(name))listeners.set(name,[]);listeners.get(name).push(fn)},querySelector(){return {}},querySelectorAll(){return []}};
  const c=vm.createContext({document,normalizeSearchText:v=>String(v??''),requestAnimationFrame:()=>1,MutationObserver:class{observe(){}}});
  vm.runInContext(readFileSync('app/static/warehouse-table-filters.js','utf8'),c);
  const table={dataset:{},tHead:{rows:[]},querySelectorAll:()=>[]};
  const header={dataset:{column:'qty'},textContent:'تعداد',classList:{add(){}},setAttribute(){},closest:selector=>selector==='table'?table:selector.startsWith('thead')?header:null};
  table.tHead.rows=[{cells:[header]}];document.elementFromPoint=()=>header;c.table=table;c.calls=0;
  vm.runInContext('registerSharedTableAdapter(table,()=>calls++)',c);
  listeners.get('DOMContentLoaded')[0]();
  const emit=(name,target=header,extra={})=>listeners.get(name)?.forEach(fn=>fn({target,button:0,pointerId:1,clientX:10,clientY:10,preventDefault(){},...extra}));
  emit('pointerdown');emit('pointerup');emit('click');assert.equal(c.calls,1);
  emit('keydown',header,{key:'Enter'});assert.equal(c.calls,2);assert.equal(vm.runInContext('getSharedTableQuery(table).sort.direction',c),'asc');
  const control={closest:selector=>selector.startsWith('input')?control:selector==='table'?table:null};
  emit('pointerdown',control);emit('pointerup',control);emit('click',control);assert.equal(c.calls,2);
  emit('pointerdown');emit('pointermove',header,{clientX:90});emit('pointerup');emit('click');assert.equal(c.calls,2,'drag out and back is still a drag');
});
test('numeric drafts participate without being rewritten',()=>{const c=setup();const input={type:'text',tagName:'INPUT',value:'۱۲۳'};c.cell={textContent:'',querySelectorAll:()=>[input]};assert.equal(vm.runInContext('tableFilterText(cell)',c),'123');assert.equal(input.value,'۱۲۳')});

test('preview filters acquire stable identity before asynchronous layout reorders and retain drafts',()=>{
  const c=setup();
  const classes=()=>{const set=new Set();return {add:x=>set.add(x),contains:x=>set.has(x),toggle:(x,on)=>on?set.add(x):set.delete(x)}};
  function cell(text=''){return {dataset:{},hidden:false,textContent:text,children:[],append(x){this.children.push(x)},querySelector(selector){return this.children.find(x=>selector.includes('data-shared')?x.dataset.sharedColumnFilter:x.tagName==='INPUT')||null},querySelectorAll(){return this.children}}}
  function row(cells=[]){return {cells,classList:classes(),append(x){this.cells.push(x)},querySelectorAll(){return this.cells.flatMap(x=>x.children)}}}
  c.document.createElement=tag=>tag==='tr'?row():tag==='th'?cell():{dataset:{},tagName:'INPUT',value:'',setAttribute(k,v){this[k]=v}};
  c.previewColumnKeys=['product_code','product_name'];
  const h=[cell('کد کالا'),cell('نام کالا')],data=row([cell('00123'),cell('Soap')]);
  const draft={tagName:'INPUT',type:'text',value:'۲'};data.cells[1].children.push(draft);
  const table={classList:{contains:x=>x==='preview-lines-table'},tHead:{rows:[row(h)],append(x){this.rows.push(x)}},querySelectorAll:()=>[data]};c.table=table;
  vm.runInContext('applySharedTableFilters(table)',c);
  const filter=table.tHead.rows[1].cells[0].children[0];
  assert.equal(filter.dataset.sharedColumnFilter,'previewColumn:product_code');
  table.tHead.rows[0].cells.reverse();table.tHead.rows[1].cells.reverse();data.cells.reverse();
  filter.value='۱۲۳';vm.runInContext('applySharedTableFilters(table)',c);assert.equal(data.classList.contains('column-filtered-out'),false);
  filter.value='999';vm.runInContext('applySharedTableFilters(table)',c);assert.equal(data.classList.contains('column-filtered-out'),true);assert.equal(draft.value,'۲');
  filter.value='';vm.runInContext('applySharedTableFilters(table)',c);assert.equal(data.classList.contains('column-filtered-out'),false);
});
