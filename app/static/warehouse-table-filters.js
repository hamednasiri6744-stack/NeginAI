// Filters affect visibility only. Original rows and every editable value stay in place.
const sharedColumnAttributes=['column','supplyColumn','autoColumn','preorderColumn','orderColumn','previewColumn','fulfillmentColumn','receiptColumn','catalogColumn','checkbarColumn'];
function columnNeedsFilter(header,index){
  if(header.dataset.filterable==='false')return false;
  const key=tableColumnKey(header,index).split(':').at(-1);
  if(['actions','action','documents','complete','selection','select'].includes(key))return false;
  const title=header.textContent.replaceAll('↔','').trim();
  return !!title&&!['عملیات','انتخاب','تکمیل ردیف','فایل‌ها'].includes(title);
}
function tableColumnKey(cell,index){
  for(const attr of sharedColumnAttributes)if(cell.dataset[attr])return `${attr}:${cell.dataset[attr]}`;
  return cell.dataset.sharedColumnKey||`position:${index}`;
}
function tableFilterText(cell){
  const values=[cell.textContent||''];
  cell.querySelectorAll('input,select,textarea').forEach(control=>{
    if(control.type==='checkbox')values.push(control.checked?'1 true فعال انتخاب شده':'0 false غیرفعال انتخاب نشده');
    else if(control.tagName==='SELECT')values.push(...[...control.selectedOptions].map(option=>option.textContent));
    else values.push(control.value||'');
  });
  return normalizeSearchText(values.join(' '));
}
function tableFilterMatches(values,filters){return filters.every(filter=>(values.get(filter.key)||'').includes(normalizeSearchText(filter.value)))}
// Paged views register their data renderer so ordering/filtering precedes slicing.
const sharedTableAdapters=new WeakMap(),sharedTableSorts=new WeakMap();
function registerSharedTableAdapter(table,changed){
  if(!table)return;
  sharedTableAdapters.set(table,changed);table.dataset.sharedDataSource='true';
}
function getSharedTableQuery(table){
  return {filters:table?[...table.querySelectorAll('thead [data-shared-column-filter]')].map(input=>({key:input.dataset.sharedColumnFilter,value:input.value})).filter(f=>normalizeSearchText(f.value)):[],sort:table?sharedTableSorts.get(table)||null:null};
}
function sharedSortValue(value){
  const text=normalizeSearchText(String(value??'')).replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g,'').trim();
  if(!text||['—','–','-'].includes(text))return {empty:true,text:''};
  const number=text.replace(/[٬,\s]/g,'').replace('٫','.').replace('−','-').replace(/[٪%]$/,'');
  return {text,number:/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(number)?Number(number):null};
}
const sharedSortCollator=new Intl.Collator('fa',{numeric:true,sensitivity:'base'});
function compareSharedTableValues(a,b,direction='desc'){
  const left=sharedSortValue(a),right=sharedSortValue(b);
  if(left.empty||right.empty)return left.empty===right.empty?0:left.empty?1:-1;
  const order=left.number!==null&&right.number!==null?left.number-right.number:sharedSortCollator.compare(left.text,right.text);
  return direction==='asc'?order:-order;
}
function querySharedTableItems(items,query,value){
  const rows=items.filter(item=>query.filters.every(f=>normalizeSearchText(String(value(item,f.key)??'')).includes(normalizeSearchText(f.value))));
  return query.sort?rows.sort((a,b)=>compareSharedTableValues(value(a,query.sort.key),value(b,query.sort.key),query.sort.direction)):rows;
}
function sharedCellSortText(cell){
  if(!cell)return '';
  if(cell.dataset.sortValue!==undefined)return cell.dataset.sortValue;
  const control=cell.querySelector('input:not([type=hidden]),select,textarea');
  if(control)return control.type==='checkbox'?(control.checked?'1':'0'):control.tagName==='SELECT'?[...control.selectedOptions].map(o=>o.textContent).join(' '):control.value;
  // Explanatory notes and truncated disclosure summaries are not the cell value.
  const clone=cell.cloneNode(true);clone.querySelectorAll('small,button,[aria-hidden=true]').forEach(n=>n.remove());
  const disclosure=clone.querySelector('details');if(disclosure){const summary=disclosure.querySelector('summary');if(summary?.title)return summary.title;summary?.remove()}
  return clone.textContent;
}
// Disclosure rows belong to the order declared by aria-controls. Keep the same
// nodes and their hidden state when sorting or temporarily filtering a parent.
function sharedOrderRowGroups(rows,columnCount){
  const groups=[];
  for(const row of rows){
    if(row.cells.length===columnCount){groups.push([row]);continue}
    const group=groups.at(-1),owner=group?.[0].querySelector?.('[data-manual-details][aria-controls]');
    if(!row.id||owner?.getAttribute('aria-controls')!==row.id)return null;
    group.push(row);
  }
  return groups;
}
function applySharedTableSort(table){
  const sort=sharedTableSorts.get(table),headers=[...table.tHead.rows[0].cells];
  headers.forEach((h,index)=>{
    if(!columnNeedsSort(h,index))return;
    h.classList.add('shared-sortable');h.tabIndex=0;
    h.setAttribute('aria-sort',sort?.key===tableColumnKey(h,index)?(sort.direction==='desc'?'descending':'ascending'):'none');
    h.title='کلیک اول: بزرگ به کوچک؛ کلیک دوم: کوچک به بزرگ'+(h.dataset.columnDraggable?' · برای جابه‌جایی بکشید':'');
  });
  if(!sort||sharedTableAdapters.has(table)||table.dataset.sharedDataSource==='true')return;
  const index=headers.findIndex((h,i)=>tableColumnKey(h,i)===sort.key);if(index<0)return;
  const compare=(a,b)=>compareSharedTableValues(sharedCellSortText(a.cells[index]),sharedCellSortText(b.cells[index]),sort.direction);
  for(const body of table.tBodies){
    const old=[...body.rows];
    let desired;
    if(old.some(r=>r.cells.length!==headers.length)){
      const groups=sharedOrderRowGroups(old,headers.length);if(!groups)continue;
      desired=groups.sort((a,b)=>compare(a[0],b[0])).flat();
    }else if(old.some(r=>r.classList.contains('supply-supplier-row'))){
      const groups=[];for(const row of old){if(row.classList.contains('supply-supplier-row')||!groups.length)groups.push([row]);else groups.at(-1).push(row)}
      groups.sort((a,b)=>compare(a[0],b[0]));desired=groups.flatMap(([head,...children])=>[head,...children.sort(compare)]);
    }else desired=[...old].sort(compare);
    // Move existing nodes only: unsaved values, focus handlers and row IDs survive.
    desired.forEach((row,i)=>{if(body.rows[i]!==row)body.insertBefore(row,body.rows[i]||null)});
  }
}
function columnNeedsSort(header,index){return header.dataset.sortable!=='false'&&columnNeedsFilter({...header,dataset:{...header.dataset,filterable:undefined},textContent:header.textContent},index)}
function toggleSharedTableSort(table,header){
  const index=[...table.tHead.rows[0].cells].indexOf(header);if(index<0||!columnNeedsSort(header,index))return;
  const key=tableColumnKey(header,index),previous=sharedTableSorts.get(table);
  sharedTableSorts.set(table,{key,direction:previous?.key===key&&previous.direction==='desc'?'asc':'desc'});
  applySharedTableSort(table);sharedTableAdapters.get(table)?.(getSharedTableQuery(table));
}
function applySharedTableFilters(table){
  const heading=table.tHead?.rows[0];if(!heading)return;
  const headers=[...heading.cells];if(!headers.length)return;
  // Preview layout initialization is asynchronous. Establish the same identities
  // before its first reorder so filters travel with the correct product column.
  if(table.classList.contains('preview-lines-table'))headers.forEach((header,index)=>{
    if(!header.dataset.previewColumn)header.dataset.previewColumn=previewColumnKeys[index];
  });
  let filters=table.tHead.rows[1];
  if(!filters){filters=document.createElement('tr');table.tHead.append(filters)}
  filters.classList.add('shared-filter-row');
  headers.forEach((header,index)=>{
    const key=tableColumnKey(header,index);
    header.dataset.sharedColumnKey=key;
    let cell=[...filters.cells].find((candidate,i)=>tableColumnKey(candidate,i)===key);
    const positional=filters.cells[index];
    if(!cell&&positional&&tableColumnKey(positional,index)===`position:${index}`)cell=positional;
    if(!cell){cell=document.createElement('th');filters.append(cell)}
    for(const attr of sharedColumnAttributes)if(header.dataset[attr])cell.dataset[attr]=header.dataset[attr];
    cell.dataset.sharedColumnKey=key;
    if(cell.hidden!==header.hidden)cell.hidden=header.hidden;
    if(!columnNeedsFilter(header,index)){
      cell.querySelector('[data-shared-column-filter]')?.remove();
      return;
    }
    if(!cell.querySelector('input,select,textarea')){
      const input=document.createElement('input');input.type='search';input.dataset.sharedColumnFilter=key;
      const title=header.textContent.trim()||'انتخاب';input.setAttribute('aria-label',`فیلتر ${title}`);
      input.title=`فیلتر ${title} · فقط نمایش جدول`;input.placeholder='فیلتر';cell.append(input);
    }
    const shared=cell.querySelector('[data-shared-column-filter]');
    if(shared){
      shared.dataset.sharedColumnFilter=key;
      const title=header.textContent.replaceAll('↔','').trim()||'انتخاب';
      shared.setAttribute('aria-label',`فیلتر ${title}`);
      shared.title=`فیلتر ${title} · فقط نمایش جدول`;
    }
  });
  const active=[...filters.querySelectorAll('[data-shared-column-filter]')].map(input=>({key:input.dataset.sharedColumnFilter,value:input.value})).filter(filter=>normalizeSearchText(filter.value));
  if(!sharedTableAdapters.has(table)&&table.dataset?.sharedDataSource!=='true')table.querySelectorAll('tbody tr').forEach(row=>{
    if(row.cells.length<headers.length)return; // Keep server empty-state/colspan messages intact.
    const values=new Map([...row.cells].map((cell,index)=>{
      if(!cell.dataset.sharedColumnKey)cell.dataset.sharedColumnKey=tableColumnKey(headers[index],index);
      return [tableColumnKey(cell,index),active.length?tableFilterText(cell):''];
    }));
    const hidden=!tableFilterMatches(values,active);
    if(row.classList.contains('column-filtered-out')!==hidden)row.classList.toggle('column-filtered-out',hidden);
  });
  for(const body of table.tBodies||[]){
    const groups=sharedOrderRowGroups([...body.rows],headers.length);
    groups?.forEach(([parent,...details])=>details.forEach(detail=>{
      detail.classList.toggle('column-filtered-out',parent.classList.contains('column-filtered-out'));
    }));
  }
  if(table.tBodies)applySharedTableSort(table);
}
let sharedFilterFrame=0;
function refreshSharedTableFilters(){
  if(sharedFilterFrame)return;
  sharedFilterFrame=requestAnimationFrame(()=>{sharedFilterFrame=0;document.querySelectorAll('table').forEach(applySharedTableFilters)});
}
document.addEventListener('DOMContentLoaded',()=>{
  refreshSharedTableFilters();
  new MutationObserver(refreshSharedTableFilters).observe(document.querySelector('body'),{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['hidden']});
  for(const eventName of ['input','change'])document.addEventListener(eventName,event=>{
    const table=event.target.closest('table');if(table){applySharedTableFilters(table);if(event.target.matches('[data-shared-column-filter]'))sharedTableAdapters.get(table)?.(getSharedTableQuery(table))}
  });
  const interactive='input,select,textarea,button,a,summary,[role=button],[data-column-resize]';
  const headerFor=target=>target?.closest?.('thead tr:first-child th');
  let pointer=null,suppressClick=null;
  document.addEventListener('pointerdown',event=>{
    pointer=null;if(event.button!==0||event.target.closest(interactive))return;
    const header=headerFor(event.target);if(header)pointer={header,table:header.closest('table'),x:event.clientX,y:event.clientY,id:event.pointerId};
  },true);
  document.addEventListener('pointermove',event=>{if(pointer?.id===event.pointerId&&Math.hypot(event.clientX-pointer.x,event.clientY-pointer.y)>=6)pointer.moved=true},true);
  document.addEventListener('pointerup',event=>{
    const down=pointer;pointer=null;if(!down||down.id!==event.pointerId)return;
    // Column dragging captures the pointer on the table, so resolve the actual header.
    suppressClick={table:down.table,until:Date.now()+500};
    if(down.moved||Math.hypot(event.clientX-down.x,event.clientY-down.y)>=6)return;
    if(headerFor(document.elementFromPoint(event.clientX,event.clientY))!==down.header)return;
    toggleSharedTableSort(down.table,down.header);
  },true);
  document.addEventListener('pointercancel',()=>{pointer=null});
  document.addEventListener('click',event=>{
    if(event.target.closest(interactive))return;
    const header=headerFor(event.target);if(!header)return;
    const table=header.closest('table');if(suppressClick?.table===table&&Date.now()<suppressClick.until){suppressClick=null;return}
    toggleSharedTableSort(table,header);
  });
  document.addEventListener('keydown',event=>{
    if(!['Enter',' '].includes(event.key)||event.target.closest(interactive))return;
    const header=headerFor(event.target);if(header){event.preventDefault();toggleSharedTableSort(header.closest('table'),header)}
  });
});
