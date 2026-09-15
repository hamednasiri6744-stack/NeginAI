// Stable column identities: sorting never rebuilds a row or changes order inputs.
const productIdentityColumns=['product_code','manufacturer_product_code','barcode','product_name','brand','manufacturer','group_level3','tax_rate','conversion_rate'];
const columnLayouts={tables:{},saved:[],available:false};
let activeColumnDrag=null;
let activeColumnResize=null;
function boundedColumnWidth(width){return Math.max(56,Math.min(640,Math.round(width)))}
function resizedColumnWidth(startWidth,startX,currentX,rtl=true){return boundedColumnWidth(startWidth+(currentX-startX)*(rtl?-1:1))}
function setColumnWidth(key,column,width){
  const current=columnLayouts.tables[key];if(!current?.available.includes(column))return;
  current.widths||={};
  if(width===null)delete current.widths[column];else current.widths[column]=boundedColumnWidth(width);
  applyColumnWidths(key);fitFixedTableColumns($(workViews[key].table));fitTableWrapsToViewport();
}
function applyColumnWidths(key){
  const current=columnLayouts.tables[key];
  layoutHeaders(key).forEach(header=>{
    const value=current.widths?.[layoutCellKey(key,header)];
    if(value===undefined)delete header.dataset.userColumnWidth;else header.dataset.userColumnWidth=String(value);
    const handle=header.querySelector?.('[data-column-resize]');
    if(handle)handle.setAttribute('aria-valuenow',String(value??(parseFloat(header.style.width)||112)));
  });
}
function finishColumnResize(cancel=false){
  if(!activeColumnResize)return;
  const resize=activeColumnResize;activeColumnResize=null;
  if(resize.handle.hasPointerCapture(resize.pointerId))resize.handle.releasePointerCapture(resize.pointerId);
  document.body.classList.remove('column-resizing');
  if(cancel)setColumnWidth(resize.key,resize.column,resize.previous??null);
}
function bindColumnResizing(key,table){
  layoutHeaders(key).forEach(header=>{
    const column=layoutCellKey(key,header),handle=document.createElement('span');
    if(getComputedStyle(header).position==='static')header.style.position='relative';
    handle.dataset.columnResize=column;handle.className='column-resize-handle';handle.tabIndex=0;
    handle.setAttribute('role','separator');handle.setAttribute('aria-orientation','vertical');
    handle.setAttribute('aria-label',`تغییر عرض ${header.textContent.trim()}`);
    handle.setAttribute('aria-valuemin','56');handle.setAttribute('aria-valuemax','640');
    handle.title='برای تغییر عرض بکشید؛ دوبار کلیک برای عرض استاندارد. کلیدهای چپ و راست هم فعال‌اند.';
    header.append(handle);
    handle.addEventListener('pointerdown',event=>{
      if(event.button!==0)return;
      event.preventDefault();event.stopPropagation();finishColumnDrag();finishColumnResize(true);
      activeColumnResize={key,column,handle,pointerId:event.pointerId,startX:event.clientX,
        startWidth:parseFloat(header.style.width)||header.getBoundingClientRect().width,
        previous:columnLayouts.tables[key].widths?.[column],rtl:getComputedStyle(table).direction==='rtl'};
      handle.setPointerCapture(event.pointerId);document.body.classList.add('column-resizing');
    });
    handle.addEventListener('dblclick',event=>{event.preventDefault();event.stopPropagation();setColumnWidth(key,column,null)});
    handle.addEventListener('keydown',event=>{
      if(!['ArrowLeft','ArrowRight','Home'].includes(event.key))return;
      event.preventDefault();event.stopPropagation();
      const width=parseFloat(header.style.width)||112,step=event.shiftKey?40:10;
      setColumnWidth(key,column,event.key==='Home'?null:resizedColumnWidth(width,0,event.key==='ArrowLeft'?-step:step,getComputedStyle(table).direction==='rtl'));
    });
    handle.addEventListener('lostpointercapture',()=>{if(activeColumnResize?.handle===handle)finishColumnResize(true)});
  });
  document.addEventListener('pointermove',event=>{
    const resize=activeColumnResize;if(resize?.key!==key||resize.pointerId!==event.pointerId)return;
    event.preventDefault();setColumnWidth(key,resize.column,resizedColumnWidth(resize.startWidth,resize.startX,event.clientX,resize.rtl));
  });
  document.addEventListener('pointerup',event=>{if(activeColumnResize?.key===key&&activeColumnResize.pointerId===event.pointerId)finishColumnResize()});
  document.addEventListener('pointercancel',event=>{if(activeColumnResize?.key===key&&activeColumnResize.pointerId===event.pointerId)finishColumnResize(true)});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&activeColumnResize?.key===key){event.preventDefault();finishColumnResize(true)}});
  window.addEventListener('blur',()=>{if(activeColumnResize?.key===key)finishColumnResize(true)});
}
function outsideColumnHeader(point,heading,scope){
  const inside=point.x>=scope.left&&point.x<=scope.right&&point.y>=scope.top&&point.y<=scope.bottom;
  const nearHeading=point.x>=heading.left-8&&point.x<=heading.right+8&&point.y>=heading.top-8&&point.y<=heading.bottom+8;
  return inside&&!nearHeading;
}
function hideDraggedColumn(key,column){
  const headers=layoutHeaders(key),header=headers.find(th=>layoutCellKey(key,th)===column);
  if(!header||header.hidden)return;
  const visible=headers.filter(th=>!th.hidden).map(th=>layoutCellKey(key,th));
  if(visible.length<=1){toast('آخرین ستون نمایان را نمی‌توان پنهان کرد.',true);return}
  layoutVisibility(key,visible.filter(value=>value!==column));
  const current=columnLayouts.tables[key];
  current.hiddenByDrag=[...new Set([...(current.hiddenByDrag||[]),column])];
  renderHiddenColumns(key);
  toast('ستون از نمایش پنهان شد؛ داده حذف نشده است. برای ماندگاری، طرح را ذخیره کنید.');
}
function undoHiddenColumn(key,column){
  const current=columnLayouts.tables[key];if(!current.hiddenByDrag?.includes(column))return;
  const visible=layoutHeaders(key).filter(th=>!th.hidden).map(th=>layoutCellKey(key,th));
  current.hiddenByDrag=current.hiddenByDrag.filter(value=>value!==column);
  layoutVisibility(key,[...new Set([...visible,column])]);
  renderHiddenColumns(key);
}
function renderHiddenColumns(key){
  const current=columnLayouts.tables[key],headers=layoutHeaders(key);
  const hidden=new Map(headers.filter(th=>th.hidden).map(th=>[layoutCellKey(key,th),th]));
  // A work-view switch or checkbox can also restore a column: remove stale chips.
  current.hiddenByDrag=(current.hiddenByDrag||[]).filter(column=>hidden.has(column));
  const tray=current.hiddenTray;if(!tray)return;
  tray.hidden=!current.hiddenByDrag.length;
  const signature=JSON.stringify(current.hiddenByDrag);
  if(tray.dataset.columns===signature)return; // No DOM churn during table fitting.
  tray.dataset.columns=signature;
  const buttons=current.hiddenByDrag.map(column=>{
    const button=document.createElement('button');button.type='button';button.dataset.restoreColumn=column;
    button.textContent=`بازگرداندن «${hidden.get(column).textContent.trim()}»`;
    button.title=button.textContent;button.addEventListener('click',()=>undoHiddenColumn(key,column));
    return button;
  });
  tray.replaceChildren(...buttons);
}
function finishColumnDrag(){
  if(!activeColumnDrag)return;
  const {key,pointerId}=activeColumnDrag,current=columnLayouts.tables[key];
  activeColumnDrag=null;
  const table=$(workViews[key].table);
  if(table.hasPointerCapture(pointerId))table.releasePointerCapture(pointerId);
  current.dropZone.hidden=true;current.dropZone.classList.remove('is-over');
  $(workViews[key].table).querySelectorAll('.column-dragging').forEach(th=>th.classList.remove('column-dragging'));
}
function completeColumnOrder(available,requested=[]){
  return [...new Set([...requested,...available])].filter(key=>available.includes(key));
}
function preserveDesignedColumnWidths(table){
  table.querySelectorAll('thead tr:first-child th').forEach(header=>{
    if(!header.dataset.defaultColumnWidth&&header.dataset.userColumnWidth){
      header.dataset.defaultColumnWidth=header.dataset.userColumnWidth;
    }
  });
}
function upgradePreviewLayoutColumns(columns=[]){
  const replacement=['physical_procurement_qty','in_transit_qty','pending_receipt_qty','inventory_position_qty'];
  return columns.flatMap(column=>column==='effective_procurement_qty'?replacement:column);
}
function standardColumnOrder(available){
  const order=completeColumnOrder(available,available.includes('product_code')?productIdentityColumns:[]);
  if(order.includes('transfer_supply')){
    order.splice(order.indexOf('transfer_supply'),1);order.splice(order.indexOf('product_name')+1,0,'transfer_supply');
  }
  if(order.includes('final_order_cartons')){
    order.splice(order.indexOf('final_order_cartons'),1);order.splice(order.indexOf('product_name')+1,0,'final_order_cartons');
  }
  return order;
}
function moveColumnCells(row,order,keyOf){
  const cells=[...row.children],byKey=new Map(cells.map(cell=>[keyOf(cell),cell]));
  const sorted=order.map(key=>byKey.get(key)).filter(Boolean);
  let next=0;
  // Unkeyed select-all and colspan/empty cells retain their own positions.
  const desired=cells.map(cell=>keyOf(cell)?sorted[next++]:cell);
  desired.forEach((cell,index)=>{if(cell&&row.children[index]!==cell)row.insertBefore(cell,row.children[index]||null)});
}
function layoutCellKey(key,cell){return key==='preview'?cell.dataset.previewColumn:cell.dataset[workViews[key].attribute]}
function layoutHeaders(key){return [...$(workViews[key].table).querySelectorAll('thead tr:first-child th')].filter(th=>layoutCellKey(key,th))}
function layoutTableKey(key){return workViews[key].preference||(key==='preview'?'preorder_preview':key)}
function applyColumnOrder(key){
  const current=columnLayouts.tables[key];if(!current)return;
  const table=$(workViews[key].table);
  refreshUniversalPresets(key);
  table.querySelectorAll('tr').forEach(row=>moveColumnCells(row,current.order,cell=>layoutCellKey(key,cell)));
  if(workViews[key].generic&&current.visible){
    const visible=new Set(current.visible);
    table.querySelectorAll('[data-layout-column]').forEach(cell=>cell.hidden=!visible.has(cell.dataset.layoutColumn));
  }
  if(key==='preview'&&current.visible){
    const visible=new Set(current.visible);
    table.querySelectorAll('[data-preview-column]').forEach(cell=>cell.hidden=!visible.has(cell.dataset.previewColumn));
  }
}
function applyAllColumnOrders(){Object.keys(columnLayouts.tables).forEach(key=>{applyColumnOrder(key);applyColumnWidths(key);renderHiddenColumns(key)})}
function setColumnOrder(key,order){
  const current=columnLayouts.tables[key],table=$(workViews[key].table),wrap=table.closest('.table-wrap');
  if(wrap)rememberTableScroll(wrap);
  current.order=completeColumnOrder(current.available,order);
  applyColumnOrder(key);fitTableWrapsToViewport();
  if(wrap)restoreTableScroll(wrap);
}
function moveColumnTo(key,column,position){
  const current=columnLayouts.tables[key];
  if(!current?.order.includes(column))return;
  const order=current.order.filter(value=>value!==column);
  order.splice(Math.max(0,Math.min(order.length,position)),0,column);
  setColumnOrder(key,order);
}
function layoutVisibility(key,columns){
  const config=workViews[key],visible=new Set(columns);
  if(!visible.size)return;
  if(key==='preview'){
    columnLayouts.tables[key].visible=[...visible];
    previewWorkView='custom';applyColumnOrder(key);
  }else if(config.generic){
    columnLayouts.tables[key].visible=[...visible];
    $(config.table).querySelectorAll('[data-layout-column]').forEach(cell=>cell.hidden=!visible.has(cell.dataset.layoutColumn));
  }else{
    document.querySelectorAll(config.choices).forEach(input=>{
      const column=config.choice?input.dataset[config.choice]:input.value;
      input.checked=visible.has(column);
    });
    config.apply();
  }
  refreshWorkViewState(key);fitTableWrapsToViewport();
}

function universalTableId(table,index=0){
  const raw=table.dataset.layoutKey||table.id||table.tBodies?.[0]?.id||`${table.closest('[id]')?.id||'table'}_${index+1}`;
  return String(raw).replace(/([a-z0-9])([A-Z])/g,'$1_$2').toLowerCase().replace(/[^a-z0-9_]+/g,'_').replace(/^_+|_+$/g,'').slice(0,92)||`table_${index+1}`;
}
function universalHeaderKey(header,index){
  return header.dataset.column||header.dataset.supplyColumn||header.dataset.autoColumn||header.dataset.preorderColumn||
    header.dataset.orderColumn||header.dataset.fulfillmentColumn||header.dataset.receiptColumn||header.dataset.catalogColumn||`column_${index+1}`;
}
function tagUniversalRows(key){
  const current=columnLayouts.tables[key],table=$(workViews[key].table);if(!current||!table)return;
  table.querySelectorAll('tr').forEach(row=>{
    const cells=[...row.children];
    if(cells.length!==current.available.length||cells.some(cell=>Number(cell.colSpan||1)>1))return;
    cells.forEach((cell,index)=>cell.dataset.layoutColumn||=(row.parentElement?.tagName==='THEAD'?universalHeaderKey(cell,index):current.available[index]));
  });
}
function createUniversalBar(key,table){
  const bar=document.createElement('div');bar.className='work-view-bar universal-layout-bar';bar.dataset.workViewBar=key;
  bar.setAttribute('role','group');bar.setAttribute('aria-label','طرح شخصی این جدول');
  bar.innerHTML='<span class="work-view-label">طرح نمایش این جدول</span><span class="work-view-custom" hidden></span><button type="button" class="work-view-hidden-filters" hidden></button>';
  const defaults=table.dataset.defaultColumns?.split(',').filter(column=>columnLayouts.tables[key].available.includes(column));
  if(defaults?.length){
    columnLayouts.tables[key].presetBar=bar;
    columnLayouts.tables[key].defaultVisible=defaults;
    for(const [preset,label,columns] of [['compact','نمای پیگیری',defaults],['all','همه ستون‌ها',columnLayouts.tables[key].available]]){
      const button=document.createElement('button');button.type='button';button.dataset.layoutPreset=preset;button.textContent=label;
      button.setAttribute('aria-pressed',String(preset==='compact'));
      button.addEventListener('click',()=>{layoutVisibility(key,columns);refreshUniversalPresets(key)});bar.append(button);
    }
  }
  const container=table.closest('.table-wrap,.purchase-table-scroll,.sale-price-table-scroll,.contract-item-scroll,.sale-price-item-scroll,.receipt-preview-table-wrap,.pi-table')||table.parentElement;
  container.before(bar);return bar;
}
function refreshUniversalPresets(key){
  const current=columnLayouts.tables[key],bar=current?.presetBar;if(!bar)return;
  const visible=new Set(current.visible||current.available);
  bar.querySelectorAll('[data-layout-preset]').forEach(button=>{
    const expected=button.dataset.layoutPreset==='all'?current.available:current.defaultVisible;
    button.setAttribute('aria-pressed',String(expected.length===visible.size&&expected.every(column=>visible.has(column))));
  });
}
function registerUniversalTable(table,index=0){
  if(!table?.querySelector('thead tr:first-child th')||Object.values(workViews).some(config=>$(config.table)===table))return null;
  const base=universalTableId(table,index);let key=`ui_${base}`,suffix=2;
  if(workViews[key]?.generic&&!$(workViews[key].table)){
    columnLayouts.tables[key]?.panel?.remove();delete columnLayouts.tables[key];delete workViews[key];
  }
  while(workViews[key]&&$(workViews[key].table)!==table)key=`ui_${base}_${suffix++}`;
  table.dataset.layoutTable=key;
  const selector=`[data-layout-table="${key}"]`;
  workViews[key]={table:selector,attribute:'layoutColumn',preference:key,generic:true,views:[]};
  const headers=[...table.querySelectorAll('thead tr:first-child th')];
  preserveDesignedColumnWidths(table);
  headers.forEach((header,column)=>header.dataset.layoutColumn=universalHeaderKey(header,column));
  const available=headers.map(header=>header.dataset.layoutColumn);
  const defaults=table.dataset.defaultColumns?.split(',').filter(column=>available.includes(column));
  columnLayouts.tables[key]={available,order:standardColumnOrder(available),...(defaults?.length?{visible:defaults}:{})};
  tagUniversalRows(key);createUniversalBar(key,table);initializeLayoutPanel(key);applyColumnOrder(key);
  renderLayoutChoices(key);
  const preferred=columnLayouts.saved.find(layout=>layout.table_key===key&&layout.is_default);
  if(preferred)useColumnLayout(key,preferred,false);
  return key;
}
function registerUniversalTables(){document.querySelectorAll('table').forEach(registerUniversalTable)}
function captureLayoutFilters(key){
  const filters={};
  $(workViews[key].table).querySelectorAll('thead input,thead select').forEach(input=>{
    const column=layoutCellKey(key,input.closest('th'));
    if(column&&input.value)filters[column]=input.value;
  });
  return filters;
}
function restoreLayoutFilters(key,filters,notify=true){
  let changed=null;
  $(workViews[key].table).querySelectorAll('thead input,thead select').forEach(input=>{
    const column=layoutCellKey(key,input.closest('th')),value=filters[column]||'';
    if(input.value!==value){input.value=value;changed=input}
  });
  // One existing filter handler refreshes the table, after all values are assigned.
  if(changed&&notify)changed.dispatchEvent(new Event(changed.tagName==='SELECT'?'change':'input',{bubbles:true}));
}
function useColumnLayout(key,layout,notify=true){
  if(columnLayouts.tables[key].available.includes('transfer_supply')&&!layout.column_order.includes('transfer_supply')){
    const order=[...layout.column_order];order.splice(order.indexOf('product_name')+1,0,'transfer_supply');
    layout={...layout,column_order:order,visible_columns:[...layout.visible_columns,'transfer_supply']};
  }
  // Old saved layouts predate this column; new layouts may still hide it deliberately.
  if(columnLayouts.tables[key].available.includes('delivery_date')&&!layout.column_order.includes('delivery_date')){
    layout={...layout,column_order:[...layout.column_order,'delivery_date'],visible_columns:[...layout.visible_columns,'delivery_date']};
  }
  columnLayouts.tables[key].widths=Object.fromEntries(Object.entries(layout.widths||{}).filter(([column,width])=>columnLayouts.tables[key].available.includes(column)&&Number.isInteger(width)&&width>=56&&width<=640));
  applyColumnWidths(key);
  const savedOrder=key==='preview'?upgradePreviewLayoutColumns(layout.column_order):layout.column_order;
  const savedVisible=key==='preview'?upgradePreviewLayoutColumns(layout.visible_columns):layout.visible_columns;
  setColumnOrder(key,savedOrder);
  layoutVisibility(key,savedVisible.filter(column=>columnLayouts.tables[key].available.includes(column)));
  restoreLayoutFilters(key,layout.filters||{},notify);
  const panel=columnLayouts.tables[key].panel;
  panel.querySelector('[data-layout-name]').value=layout.name;
  panel.querySelector('[data-layout-default]').checked=layout.is_default;
  panel.querySelector('[data-layout-select]').value=layout.id;
  renderLayoutColumns(key);
}
function renderLayoutColumns(key){
  const current=columnLayouts.tables[key],headers=layoutHeaders(key);
  const visible=new Set(headers.filter(th=>!th.hidden).map(th=>layoutCellKey(key,th)));
  const labels=Object.fromEntries(headers.map(th=>[layoutCellKey(key,th),th.textContent.trim()]));
  const options=current.order.map((column,index)=>`<option value="${index}">${fa(index+1)} · ${esc(labels[column])}</option>`).join('');
  current.panel.querySelector('[data-layout-columns]').innerHTML=current.order.map(column=>`<div class="layout-column-row" data-layout-row="${esc(column)}"><label><input type="checkbox" data-layout-visible="${esc(column)}" ${visible.has(column)?'checked':''}>${esc(labels[column])}</label><select data-layout-position="${esc(column)}" aria-label="جایگاه ${esc(labels[column])}">${options}</select></div>`).join('');
  current.panel.querySelectorAll('[data-layout-position]').forEach(select=>select.value=String(current.order.indexOf(select.dataset.layoutPosition)));
}
function renderLayoutChoices(key,selected=''){
  const panel=columnLayouts.tables[key].panel;
  panel.querySelector('[data-layout-select]').innerHTML='<option value="">طرح جاری (ذخیره‌نشده)</option>'+columnLayouts.saved.filter(layout=>layout.table_key===layoutTableKey(key))
    .map(layout=>`<option value="${esc(layout.id)}">${layout.is_default?'★ ':''}${esc(layout.name)}</option>`).join('');
  panel.querySelector('[data-layout-select]').value=selected;
  panel.querySelector('[data-layout-save]').disabled=!columnLayouts.available;
  panel.querySelector('[data-layout-status]').textContent=columnLayouts.available?'طرح با همین نام بازنویسی می‌شود. فقط فیلترهای سرستون ذخیره می‌شوند.':'ذخیره روی سرور در دسترس نیست؛ تغییر نمایش فقط برای این بازدید است.';
}
async function saveColumnLayout(key){
  const current=columnLayouts.tables[key],panel=current.panel,button=panel.querySelector('[data-layout-save]');
  const name=panel.querySelector('[data-layout-name]').value.trim();
  if(!name){panel.querySelector('[data-layout-name]').focus();toast('نام طرح را وارد کنید.',true);return}
  const visible=layoutHeaders(key).filter(th=>!th.hidden).map(th=>layoutCellKey(key,th));
  button.disabled=true;
  try{
    const saved=await api(`/warehouse-assistant/api/table-layouts/${layoutTableKey(key)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      name,is_default:panel.querySelector('[data-layout-default]').checked,
      column_order:current.order,visible_columns:visible,filters:captureLayoutFilters(key),widths:current.widths||{}})});
    if(Object.keys(current.widths||{}).length&&!saved.widths)throw new Error('عرض ستون‌ها ذخیره نشد؛ سرویس باید به نسخهٔ جدید راه‌اندازی مجدد شود.');
    // Preserve other tables/users; this response is the authoritative saved order.
    columnLayouts.saved=columnLayouts.saved.filter(layout=>layout.id!==saved.id).map(layout=>saved.is_default&&layout.table_key===saved.table_key?{...layout,is_default:false}:layout);
    columnLayouts.saved.push(saved);renderLayoutChoices(key,saved.id);toast(`طرح «${saved.name}» برای شما ذخیره شد.`);
  }catch(error){toast(error.message,true)}finally{button.disabled=!columnLayouts.available}
}
function initializeLayoutPanel(key){
  const current=columnLayouts.tables[key],bar=document.querySelector(`[data-work-view-bar="${key}"]`);
  const button=document.createElement('button');button.type='button';button.textContent='ذخیره طرح / ستون‌ها ▾';button.dataset.columnManager=key;button.setAttribute('aria-haspopup','dialog');
  const panel=document.createElement('dialog');current.panel=panel;
  panel.className='column-layout-dialog';panel.id=`column-layout-${key}`;panel.setAttribute('aria-labelledby',`${panel.id}-title`);
  panel.innerHTML=`<header><h2 id="${panel.id}-title">ستون‌ها و طرح نمایش</h2><button type="button" data-layout-close aria-label="بستن تنظیمات ستون‌ها">×</button></header><div class="layout-controls"><label>طرح‌های من<select data-layout-select aria-label="انتخاب طرح نمایش"></select></label><label>نام طرح<input data-layout-name maxlength="100" placeholder="مثلاً کنترل موجودی" aria-label="نام طرح نمایش"></label><label class="layout-default"><input type="checkbox" data-layout-default>پیش‌فرض این جدول برای من</label><div class="layout-actions"><button type="button" data-layout-save>ذخیره طرح</button><button type="button" data-layout-standard>ترتیب استاندارد</button></div><small data-layout-status role="status"></small></div><p class="layout-help">ستون‌ها از راست به چپ هستند. جایگاه را از فهرست انتخاب کنید یا سرستون را با موس بکشید.</p><div class="layout-columns" data-layout-columns></div>`;
  document.body.append(panel);bar.append(button);
  button.setAttribute('aria-controls',panel.id);
  button.addEventListener('click',()=>{renderLayoutColumns(key);panel.showModal()});
  panel.querySelector('[data-layout-close]').addEventListener('click',()=>panel.close());
  panel.querySelector('[data-layout-save]').addEventListener('click',()=>saveColumnLayout(key));
  panel.querySelector('[data-layout-standard]').addEventListener('click',()=>{setColumnOrder(key,standardColumnOrder(current.available));renderLayoutColumns(key)});
  panel.querySelector('[data-layout-select]').addEventListener('change',event=>{
    const layout=columnLayouts.saved.find(value=>value.id===event.target.value&&value.table_key===layoutTableKey(key));
    if(layout)useColumnLayout(key,layout);else{panel.querySelector('[data-layout-name]').value='';panel.querySelector('[data-layout-default]').checked=false}
  });
  panel.querySelector('[data-layout-columns]').addEventListener('change',event=>{
    const input=event.target;
    if(input.dataset.layoutPosition){
      const column=input.dataset.layoutPosition;moveColumnTo(key,column,Number(input.value));renderLayoutColumns(key);
      panel.querySelector(`[data-layout-position="${column}"]`).focus();
    }else if(input.dataset.layoutVisible){
      const visible=[...panel.querySelectorAll('[data-layout-visible]:checked')].map(choice=>choice.dataset.layoutVisible);
      if(!visible.length){input.checked=true;toast('حداقل یک ستون باید نمایان باشد.',true);return}
      layoutVisibility(key,visible);
    }
  });
  const table=$(workViews[key].table);
  // Existing preference controls stay reachable in the one column/settings dialog.
  const legacy=key==='inventory'?$('#inventoryDisplayOptions'):table.closest('section')?.querySelector('.column-picker');
  if(legacy){
    legacy.querySelector('summary').textContent=key==='inventory'?'نماهای ذخیره‌شدهٔ قبلی':'انتخاب سریع ستون‌ها';
    panel.append(legacy);
  }
  const scope=table.closest('dialog')||table.closest('section')||table.parentElement;
  const dropZone=document.createElement('div');current.dropZone=dropZone;
  dropZone.className='column-hide-drop-zone';dropZone.hidden=true;dropZone.setAttribute('role','status');
  dropZone.textContent='برای پنهان‌کردن ستون، بیرون ردیف سرستون‌ها رها کنید · داده حذف نمی‌شود';scope.append(dropZone);
  const tray=document.createElement('div');current.hiddenTray=tray;current.hiddenByDrag=[];
  tray.className='column-hidden-tray';tray.hidden=true;tray.dataset.hiddenColumns=key;
  tray.setAttribute('role','group');tray.setAttribute('aria-label','بازگرداندن ستون‌های کنارگذاشته‌شده');bar.append(tray);
  bindColumnDragging(key,table,scope,dropZone);
  bindColumnResizing(key,table);
}
function bindColumnDragging(key,table,scope,dropZone){
  const current=columnLayouts.tables[key];
  layoutHeaders(key).forEach(header=>{header.draggable=false;header.dataset.columnDraggable='true';header.title='برای جابه‌جایی بکشید؛ برای پنهان‌کردن، بیرون ردیف سرستون‌ها رها کنید.'});
  // Pointer events keep dragging consistent in nested scroll containers and dialogs.
  table.addEventListener('pointerdown',event=>{
    if(event.button!==0||event.pointerType==='touch'||event.target.closest('input,select,button,a,[data-column-resize]'))return;
    const header=event.target.closest('thead tr:first-child th'),column=header?layoutCellKey(key,header):'';
    if(!column)return;
    finishColumnDrag();activeColumnDrag={key,column,pointerId:event.pointerId,startX:event.clientX,startY:event.clientY,started:false,header};
    table.setPointerCapture(event.pointerId);event.preventDefault();
  });
  const outside=event=>outsideColumnHeader({x:event.clientX,y:event.clientY},table.querySelector('thead tr').getBoundingClientRect(),scope.getBoundingClientRect());
  document.addEventListener('pointermove',event=>{
    const drag=activeColumnDrag;
    if(drag?.key!==key||drag.pointerId!==event.pointerId)return;
    if(!drag.started&&Math.hypot(event.clientX-drag.startX,event.clientY-drag.startY)<6)return;
    drag.started=true;drag.header.classList.add('column-dragging');event.preventDefault();
    const bounds=table.closest('.table-wrap').getBoundingClientRect();
    dropZone.style.left=`${Math.max(8,bounds.left+12)}px`;
    dropZone.style.top=`${Math.min(window.innerHeight-80,Math.max(12,drag.header.getBoundingClientRect().bottom+12))}px`;
    dropZone.style.width=`${Math.max(150,Math.min(520,bounds.width-24,window.innerWidth-24))}px`;
    dropZone.hidden=false;dropZone.classList.toggle('is-over',outside(event));
  });
  document.addEventListener('pointerup',event=>{
    const drag=activeColumnDrag;
    if(drag?.key!==key||drag.pointerId!==event.pointerId)return;
    const hide=drag.started&&outside(event);
    const header=document.elementFromPoint(event.clientX,event.clientY)?.closest('thead tr:first-child th');
    const target=header&&table.contains(header)?layoutCellKey(key,header):'';
    finishColumnDrag();
    if(!drag.started)return;
    event.preventDefault();
    if(hide)hideDraggedColumn(key,drag.column);
    else if(target)moveColumnTo(key,drag.column,current.order.indexOf(target));
  },true);
  document.addEventListener('pointercancel',event=>{if(activeColumnDrag?.key===key&&activeColumnDrag.pointerId===event.pointerId)finishColumnDrag()});
  table.addEventListener('lostpointercapture',()=>{if(activeColumnDrag?.key===key)finishColumnDrag()});
  window.addEventListener('blur',()=>{if(activeColumnDrag?.key===key)finishColumnDrag()});
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&activeColumnDrag?.key===key){event.preventDefault();finishColumnDrag()}
  });
}
async function initializeColumnLayouts(){
  columnLayouts.saved=[];columnLayouts.available=false;
  registerUniversalTables();
  Object.entries(workViews).forEach(([key,config])=>{
    if(columnLayouts.tables[key])return;
    if(key==='preview')$(config.table).querySelectorAll('thead tr:first-child th').forEach((th,index)=>th.dataset.previewColumn=previewColumnKeys[index]);
    const available=layoutHeaders(key).map(th=>layoutCellKey(key,th));
    columnLayouts.tables[key]={available,order:standardColumnOrder(available)};
    preserveDesignedColumnWidths($(config.table));
    initializeLayoutPanel(key);applyColumnOrder(key);
  });
  try{columnLayouts.saved=(await api('/warehouse-assistant/api/table-layouts')).layouts||[];columnLayouts.available=true}
  catch(error){toast('طرح‌های نمایش بارگیری نشدند؛ ذخیره روی سرور فعلاً در دسترس نیست.',true)}
  Object.keys(columnLayouts.tables).forEach(key=>{
    renderLayoutChoices(key);
    const preferred=columnLayouts.saved.find(layout=>layout.table_key===layoutTableKey(key)&&layout.is_default);
    if(preferred)useColumnLayout(key,preferred,false);
  });
  const observer=new MutationObserver(records=>{
    const tables=new Set();
    records.forEach(record=>{
      const owner=record.target.closest?.('table');if(owner)tables.add(owner);
      record.addedNodes.forEach(node=>{if(node.nodeType!==1)return;if(node.matches?.('table'))tables.add(node);node.querySelectorAll?.('table').forEach(table=>tables.add(table))});
    });
    tables.forEach((table,index)=>{
      const key=table.dataset.layoutTable||Object.keys(workViews).find(value=>$(workViews[value].table)===table)||registerUniversalTable(table,index);
      if(key&&workViews[key]?.generic){
        tagUniversalRows(key);applyColumnOrder(key);
        if(columnLayouts.tables[key].visible)layoutVisibility(key,columnLayouts.tables[key].visible);
      }
    });
  });
  observer.observe(document.body,{childList:true,subtree:true});columnLayouts.observer=observer;
  fitTableWrapsToViewport();
}

function resetColumnLayouts(){
  finishColumnResize(true);
  finishColumnDrag();
  columnLayouts.saved=[];columnLayouts.available=false;
  Object.entries(columnLayouts.tables).forEach(([key,current])=>{
    current.order=standardColumnOrder(current.available);current.visible=null;current.widths={};
    restoreLayoutFilters(key,{},false);
    current.panel.close();
    current.hiddenByDrag=[];current.hiddenTray.replaceChildren();current.hiddenTray.hidden=true;delete current.hiddenTray.dataset.columns;
    current.panel.querySelector('[data-layout-name]').value='';
    current.panel.querySelector('[data-layout-default]').checked=false;
    renderLayoutChoices(key);
    if(workViews[key].generic)layoutVisibility(key,current.available);else applyWorkView(key,workViews[key].views[0][0]);
  });
  applyAllColumnOrders();
}
