const checkbarState={sequence:0,source:null,lines:[],saved:null,requestId:null,pending:null,submitting:false,editing:null,deletePending:null,includeOrderItems:false};
function checkbarDraftStage(){return !!checkbarState.worksheetWorkflow&&!checkbarState.editing?.worksheet_approved_at&&!checkbarState.editing?.receipt_confirmed}
function checkbarSkipMatching(){return !!checkbarState.skipOrderMatching}
function syncCheckbarMatchingChoice(){
  $('#checkbarMatchingChoice').hidden=!checkbarState.source||(!checkbarState.saved&&checkbarDraftStage());
  $('#checkbarMatchOrders').checked=!checkbarSkipMatching();
  $('#checkbarMatchOrders').disabled=!!checkbarState.saved||checkbarState.submitting||!!checkbarState.pending;
}
let checkbarArchive=[],checkbarArchiveSequence=0,checkbarTableView='count';

function applyCheckbarTableView(view=checkbarTableView){
  const presets={count:[1,2,4,5,6,8,9,10,11,12,17],prices:[1,4,6,11,13,14,15,16]};
  checkbarTableView=view==='all'||presets[view]?view:'count';
  const table=$('#checkbarTable'),visible=presets[checkbarTableView];
  table.dataset.tableView=checkbarTableView;
  table.querySelectorAll('tr').forEach(row=>[...row.children].forEach((cell,index)=>cell.hidden=!!visible&&!visible.includes(index)));
  document.querySelectorAll('[data-checkbar-table-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.checkbarTableView===checkbarTableView)));
  fitFixedTableColumns(table);refreshCheckbarHiddenFilters();
}

function refreshCheckbarHiddenFilters(){
  const filters=[...document.querySelectorAll('#checkbarTable thead th[hidden] input')].filter(input=>input.value.trim());
  $('#checkbarHiddenFilters').hidden=!filters.length;
}

function checkbarRequestId(){
  // LAN HTTP pages expose getRandomValues, but randomUUID requires a secure context.
  return typeof crypto.randomUUID==='function'?crypto.randomUUID():
    Array.from(crypto.getRandomValues(new Uint8Array(16)),byte=>byte.toString(16).padStart(2,'0')).join('');
}

function checkbarNumeric(value,integer=false){
  const text=normalizeSearchText(value??'').replaceAll('٫','.');
  if(!text)return null;
  if(!(integer?/^\d+$/:/^\d+(?:\.\d+)?$/).test(text))throw new Error('تعداد و قیمت را نامنفی وارد کنید؛ کارتن باید عدد صحیح باشد.');
  const number=Number(text);
  if(!Number.isFinite(number))throw new Error('عدد واردشده معتبر نیست.');
  return number;
}

function checkbarActual(line){
  const cartons=checkbarNumeric(line.cartons,true),units=checkbarNumeric(line.units);
  return cartons===null&&units===null?null:(cartons||0)*Number(line.conversion_rate)+(units||0);
}

function checkbarEditable(){return !checkbarState.saved&&!checkbarState.pending}

function checkbarImportPending(){return typeof checkbarImage!=='undefined'&&(checkbarImage.busy||!!checkbarImage.result)}

function checkbarNotice(kind,message,focus=false){
  const element=$('#checkbarNotice');
  element.hidden=!message;element.className=`checkbar-notice ${kind}`;element.textContent=message;
  element.setAttribute('role',kind==='error'?'alert':'status');
  if(focus&&message)element.focus();
}

function validateCheckbarDraft(){
  if(!checkbarState.lines.length)throw new Error('ابتدا حداقل یک کالا به چک‌بار اضافه کنید.');
  checkbarState.lines.forEach((line,index)=>{
    for(const [key,label,integer] of [['cartons','کارتن',true],['units','عدد',false],['manufacturer_price_new','قیمت تولید جدید',false],['consumer_price_new','قیمت مصرف جدید',false]]){
      try{checkbarNumeric(line[key],integer)}catch{throw new Error(`ردیف ${fa(index+1)}، کد ${line.product_code}: «${label}» نامعتبر است؛ مقدار نامنفی${integer?' و صحیح':''} وارد کنید.`)}
    }
  });
}

function checkbarClear(){
  if(typeof resetCheckbarImage==='function')resetCheckbarImage();
  if(typeof resetCheckbarReceipt==='function')resetCheckbarReceipt();
  checkbarState.sequence++;checkbarState.source=null;checkbarState.lines=[];
  checkbarState.saved=null;checkbarState.pending=null;checkbarState.requestId=null;checkbarState.submitting=false;
  checkbarState.editing=null;checkbarState.deletePending=null;
  checkbarState.skipOrderMatching=false;
  checkbarState.worksheetWorkflow=!!state.bootstrap?.checkbar_worksheet_workflow_supported;checkbarState.approvalPending=null;
  $('#checkbarApproveWorksheet').hidden=true;
  checkbarState.remainingOrderId=null;
  checkbarTableView='count';
  for(const id of ['checkbarExtraMetadata','checkbarCountingHelp','checkbarHistoryDetails'])$('#'+id).open=false;
  $('#checkbarHistoryDetails').hidden=true;
  $('#checkbarSplitByBrand').checked=false;$('#checkbarBrandBatch').hidden=true;
  $('#checkbarBrandBatch').innerHTML='';renderCheckbarBrandSplit();
  checkbarState.includeOrderItems=false;$('#checkbarIncludeOrderItems').checked=false;
  $('#checkbarEdit').hidden=true;$('#checkbarDelete').hidden=true;$('#checkbarVersions').innerHTML='';
  checkbarNotice('','');$('#checkbarIssue').textContent='تأیید دریافت و ذخیره چک‌بار';
  $('#checkbarEmptyActions').hidden=true;
  $('#checkbarTitle').textContent='صدور چک‌بار';$('#checkbarSummary').textContent='';
  $('#checkbarEditor').hidden=true;$('#checkbarDownload').hidden=true;$('#checkbarPrint').hidden=true;$('#checkbarIssue').disabled=true;
  $('#checkbarOrderPicker').hidden=false;$('#checkbarReselect').hidden=true;
  $('#checkbarWarehouse').disabled=false;$('#checkbarSupplier').disabled=false;
  $('#checkbarOrders').innerHTML='';$('#checkbarPrepare').disabled=true;
  $('#checkbarManual').hidden=false;
  document.querySelectorAll('[data-checkbar-meta]').forEach(input=>{input.value='';input.disabled=false});
}

async function openCheckbar(){
  if(!has('warehouse.order.draft'))return;
  if(!state.bootstrap?.standalone_checkbar_supported){toast('نسخهٔ مستقل چک‌بار هنوز روی سرویس فعال نشده است؛ پس از فعال‌سازی صفحه را تازه کنید.',true);return}
  checkbarClear();
  $('#checkbarWarehouse').innerHTML=state.bootstrap.warehouses.map(w=>`<option value="${esc(w.code)}">${esc(w.name)}</option>`).join('');
  $('#checkbarDialog').showModal();
  await checkbarLoadContext(true);
}

async function checkbarLoadContext(resetSupplier=false){
  checkbarState.remainingOrderId=null;
  const sequence=++checkbarState.sequence,warehouse=$('#checkbarWarehouse').value;
  if(resetSupplier)$('#checkbarSupplier').innerHTML='<option value="">انتخاب کنید</option>';
  const supplier=$('#checkbarSupplier').value;
  $('#checkbarOrders').innerHTML='';$('#checkbarPrepare').disabled=true;
  $('#checkbarSourceStatus').textContent='در حال خواندن سفارش‌های در راه…';
  try{
    const result=await api(`/warehouse-assistant/api/checkbars/context?warehouse=${encodeURIComponent(warehouse)}&supplier=${encodeURIComponent(supplier)}`);
    if(sequence!==checkbarState.sequence)return;
    if(resetSupplier)$('#checkbarSupplier').innerHTML='<option value="">انتخاب کنید</option>'+result.suppliers.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');
    $('#checkbarOrders').innerHTML=result.orders.map(o=>`<div><strong>${esc(o.preorder_number)}</strong><small>مانده ${fa(o.remaining_cartons)} کارتن · ${fa(o.lines.length)} قلم</small></div>`).join('');
    $('#checkbarSourceStatus').textContent=!result.suppliers.length?'تأمین‌کنندهٔ فعالی برای این انبار تعریف نشده است.':!supplier?'تأمین‌کننده را انتخاب کنید.':result.orders.length?`${fa(result.orders.length)} سفارش در راه این تأمین‌کننده، همگی در همین چک‌بار بررسی می‌شوند؛ تقسیم تعداد از قدیمی‌ترین سفارش است.`:'این تأمین‌کننده سفارش در راه ندارد؛ می‌توانید چک‌بار بدون سفارش صادر کنید.';
    $('#checkbarPrepare').disabled=!supplier;
  }catch(error){if(sequence===checkbarState.sequence)$('#checkbarSourceStatus').textContent=error.message}
}

async function checkbarPrepare(){
  const remainingOrderId=checkbarState.remainingOrderId;
  const order_ids=remainingOrderId?[remainingOrderId]:[];
  if(!$('#checkbarSupplier').value)return;
  const sequence=++checkbarState.sequence;
  const selection={warehouse:$('#checkbarWarehouse').value,supplier:$('#checkbarSupplier').value,order_ids};
  if(remainingOrderId)selection.remaining_order_id=remainingOrderId;
  const includeOrderItems=!!$('#checkbarIncludeOrderItems').checked;
  $('#checkbarPrepare').disabled=true;
  try{
    const source=await api('/warehouse-assistant/api/checkbars/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(selection)});
    if(sequence!==checkbarState.sequence)return;
    checkbarState.source=source;checkbarState.requestId=checkbarRequestId();
    if(source.outstanding_orders?.length)$('#checkbarSourceStatus').textContent=`${fa(source.outstanding_orders.length)} سفارش در راه دارید: ${source.outstanding_orders.map(o=>o.number).join('، ')}. اقلام دستی یا خوانده‌شده از فایل، پیش از تأیید و ذخیره با همهٔ این سفارش‌ها تطبیق داده می‌شوند.`;
    checkbarState.includeOrderItems=includeOrderItems;
    checkbarState.lines=(includeOrderItems?(remainingOrderId?source.lines:(source.aggregate_open_lines||source.lines)):[]).map(line=>({...line,aggregate_open_order:!remainingOrderId&&!!source.aggregate_open_lines,cartons:'',units:'',manufacturer_price_new:'',consumer_price_new:''}));
    if(remainingOrderId)$('#checkbarSourceStatus').textContent='چک‌بار ماندهٔ سفارش انتخاب‌شده؛ تعداد واقعی بار را وارد کنید. تخصیص دریافت فقط به همین سفارش انجام می‌شود.';
    $('#checkbarWarehouse').disabled=true;$('#checkbarSupplier').disabled=true;
    $('#checkbarOrderPicker').hidden=true;$('#checkbarReselect').hidden=false;$('#checkbarEditor').hidden=false;
    $('#checkbarProductSearch').value='';$('#checkbarBrand').value='';$('#checkbarGroup3').value='';renderCheckbarProducts();renderCheckbarLines();
  }catch(error){toast(error.message,true)}finally{if(sequence===checkbarState.sequence)$('#checkbarPrepare').disabled=false}
}

function checkbarOrderContext(product){
  const order=checkbarState.source?.aggregate_open_lines?.find(row=>row.product_code===product.product_code);
  return order?{...product,order_quantity:order.order_quantity,received_qty:order.received_qty,remaining_qty:order.remaining_qty,
    aggregate_open_order:true,preorder_number:'مجموع سفارش‌های در راه'}:product;
}
function checkbarFilteredProducts(query=''){
  const present=new Set(checkbarState.lines.map(l=>l.product_code));
  (checkbarState.source?.lines||[]).forEach(line=>present.add(line.product_code));
  const brand=$('#checkbarBrand').value,group=$('#checkbarGroup3').value;
  return (checkbarState.source?.catalog||[]).filter(p=>!present.has(p.product_code)&&(!brand||p.brand===brand)&&(!group||p.group_level3===group)&&normalizeSearchText([p.product_code,p.product_name,p.barcode,p.manufacturer_product_code,p.brand,p.group_level3].join(' ')).includes(normalizeSearchText(query)));
}
function renderCheckbarProducts(){
  const catalog=checkbarState.source?.catalog||[];
  const options=(id,values,label)=>{const select=$(id),old=select.value;select.innerHTML=`<option value="">${label}</option>`+[...new Set(values.filter(Boolean))].sort().map(value=>`<option value="${esc(value)}">${esc(value)}</option>`).join('');select.value=values.includes(old)?old:''};
  options('#checkbarBrand',catalog.map(p=>p.brand),'همه برندها');
  options('#checkbarGroup3',catalog.filter(p=>!$('#checkbarBrand').value||p.brand===$('#checkbarBrand').value).map(p=>p.group_level3),'همه گروه‌های سطح ۳');
  const products=checkbarFilteredProducts();
  $('#checkbarAdd').disabled=!products.length||!checkbarEditable();
  $('#checkbarCatalogCount').textContent=`${fa(products.length)} کالای قابل افزودن`;
}
function addCheckbarProducts(codes){
  if(!checkbarEditable())return;
  const wanted=new Set(codes),items=checkbarFilteredProducts().filter(p=>wanted.has(p.product_code));
  if(checkbarState.lines.length+items.length>500){toast('حداکثر ۵۰۰ ردیف در چک‌بار مجاز است.',true);return}
  checkbarState.lines.push(...items.map(product=>({...checkbarOrderContext(product),cartons:'',units:'',manufacturer_price_new:'',consumer_price_new:''})));
  renderCheckbarLines();renderCheckbarProducts();
  if($('#checkbarCatalogDialog').open)renderCheckbarCatalog();
  if(items.length)toast(`${fa(items.length)} کالا به چک‌بار اضافه شد.`);
}
function quickAddCheckbar(){
  const code=normalizeSearchText($('#checkbarProductSearch').value);if(!code)return;
  const matches=checkbarFilteredProducts().filter(p=>normalizeSearchText(p.manufacturer_product_code)===code);
  if(matches.length===1){addCheckbarProducts([matches[0].product_code]);$('#checkbarProductSearch').value='';return}
  $('#checkbarCatalogSearch').value=code;renderCheckbarCatalog();$('#checkbarCatalogDialog').showModal();
  toast(matches.length?'این کد به چند کالا مربوط است؛ کالا را از فهرست انتخاب کنید.':'کد دقیق پیدا نشد یا کالا قبلاً اضافه شده است؛ فهرست را بررسی کنید.',!matches.length);
}
function renderCheckbarCatalog(){
  const products=checkbarFilteredProducts($('#checkbarCatalogSearch').value);
  $('#checkbarCatalogRows').innerHTML=products.map(p=>`<tr data-checkbar-catalog-code="${esc(p.product_code)}"><td><input type="checkbox" data-checkbar-pick="${esc(p.product_code)}" aria-label="انتخاب ${esc(p.product_name)}"></td><td>${esc(p.manufacturer_product_code||'—')}</td><td>${esc(p.product_code)}</td><td>${esc(p.barcode||'—')}</td><td>${esc(p.product_name)}</td><td>${esc(p.brand||'—')}</td><td>${esc(p.group_level3||'—')}</td><td>${fa(p.conversion_rate)}</td><td>${fa(p.stock)}</td></tr>`).join('')||'<tr><td colspan="9">کالای قابل افزودنی با این فیلترها پیدا نشد.</td></tr>';
  $('#checkbarAddSelected').disabled=true;
  $('#checkbarPickerStatus').textContent=`${fa(products.length)} کالا · دوبار کلیک یا انتخاب و افزودن`;
}

function checkbarOutstandingSummary(){
  const orders=checkbarState.saved?[]:checkbarState.source?.outstanding_orders||[];
  return orders.length?`${fa(orders.length)} سفارش در راه این تأمین‌کننده: ${orders.map(order=>order.number||order.preorder_number).join('، ')} · همه در تطبیق این بار بررسی می‌شوند.`:'';
}
function checkbarOriginLabel(line){return line.aggregate_open_order?'مجموع سفارش‌های در راه':line.preorder_number||'افزودهٔ دستی'}
function renderCheckbarLines(){
  const outstanding=checkbarOutstandingSummary();$('#checkbarOutstandingSummary').textContent=outstanding;$('#checkbarOutstandingSummary').hidden=!outstanding;
  $('#checkbarEmptyActions').hidden=true;
  const disabled=checkbarEditable()?'':' disabled';
  const input=(line,key)=>`<input type="text" inputmode="decimal" data-checkbar-field="${key}" value="${esc(line[key]??'')}" aria-label="${esc(({cartons:'واقعی کارتن',units:'واقعی عدد',manufacturer_price_new:'تولید جدید',consumer_price_new:'مصرف جدید'})[key])} ${esc(line.product_code)}"${disabled}>`;
  $('#checkbarLines').innerHTML=checkbarState.lines.map((line,index)=>`<tr data-checkbar-index="${index}"><td>${esc(checkbarOriginLabel(line))}</td><td>${esc(line.product_code)}</td><td>${esc(line.manufacturer_product_code||'—')}</td><td>${esc(line.barcode||'—')}</td><td>${esc(line.product_name)}<small>${esc(line.brand||'')}</small></td><td>${fa(line.conversion_rate)}</td><td>${line.order_quantity===null?'—':fa(line.order_quantity)}</td><td>${line.received_qty===null?'—':fa(line.received_qty)}</td><td>${line.remaining_qty===null?'بدون سفارش':receiptQuantityLabel(line.remaining_qty,line)}</td><td>${input(line,'cartons')}</td><td>${input(line,'units')}</td><td data-checkbar-total class="checkbar-total"></td><td data-difference></td><td>${fa(line.manufacturer_price)}</td><td>${fa(line.consumer_price)}</td><td>${input(line,'manufacturer_price_new')}</td><td>${input(line,'consumer_price_new')}</td><td>${line.remaining_qty!==null?`<button data-checkbar-fill type="button" class="secondary-action" title="پر کردن تعداد طبق مانده سفارش"${disabled}>مانده</button>`:''}<button data-checkbar-remove type="button" class="secondary-action" aria-label="حذف ردیف ${esc(line.product_code)}"${disabled}>حذف</button></td><td>${esc(line.group_level3||"—")}</td></tr>`).join('');
  const standalone=!checkbarState.lines.some(line=>line.preorder_id||Number(line.remaining_qty)>0)&&!(checkbarState.source?.order_ids||[]).length;
  const table=$('#checkbarTable');table.classList.toggle('checkbar-standalone',standalone);
  applyCheckbarTableView();
  updateCheckbarTotals();
}

function updateCheckbarTotals(){
  syncCheckbarMatchingChoice();
  renderCheckbarBrandSplit();
  if(typeof invalidateDraftOrderMatching==='function')invalidateDraftOrderMatching();
  let total=0,count=0;
  document.querySelectorAll('#checkbarLines tr').forEach(row=>{
    const line=checkbarState.lines[Number(row.dataset.checkbarIndex)],cell=row.querySelector('[data-difference]');
    try{
      const actual=checkbarActual(line);let over=false;
      row.querySelector('[data-checkbar-total]').textContent=actual===null?'—':fa(actual);
      if(actual!==null){total+=actual;count++;over=line.remaining_qty!==null&&actual>line.remaining_qty}
      cell.textContent=actual===null?'شمارش نشده':line.remaining_qty===null?'بدون مبنای سفارش':fa(Number((actual-line.remaining_qty).toFixed(6)));
      cell.classList.toggle('is-over',over);row.removeAttribute('aria-invalid');
    }catch{cell.textContent='عدد نامعتبر';row.querySelector('[data-checkbar-total]').textContent='نامعتبر';row.setAttribute('aria-invalid','true')}
  });
  $('#checkbarSummary').textContent=`${checkbarState.saved?checkbarState.saved.number+' · ':''}${fa(checkbarState.lines.length)} ردیف · ${fa(count)} ردیف دارای تعداد · جمع تعداد ${fa(total)} عدد`;
  $('#checkbarIssue').disabled=!!checkbarState.saved||checkbarState.submitting||!checkbarState.lines.length||checkbarImportPending();
  if(!checkbarState.saved&&!checkbarState.pending){
    if(checkbarDraftStage()){$('#checkbarIssue').textContent='ذخیره اولیه چک‌بار';checkbarNotice('info','تعداد سفارش کنار اقلام نمایش داده می‌شود. تعدادهای خالی حفظ می‌شوند؛ ذخیره اولیه دریافت کالا را ثبت نمی‌کند.');return}
    if(checkbarImportPending())return;
    if(!checkbarState.lines.length){checkbarNotice('info','برای شروع، فایل حواله را انتخاب و «خواندن حواله» را بزنید، یا کالا را دستی اضافه کنید.');return;}
    try{validateCheckbarDraft();checkbarNotice('info',count<checkbarState.lines.length?`${fa(checkbarState.lines.length-count)} ردیف هنوز شمارش نشده است؛ پیش از ذخیره برای حذف این ردیف‌ها تأیید می‌گیریم. مقدار صفر با خالی متفاوت است. شمارهٔ سند عطف الزامی است؛ سایر مشخصات بار و قیمت جدید اختیاری‌اند.`:'')}
    catch(error){checkbarNotice('error',error.message)}
  }
}

function checkbarBrandGroups(){
  const groups=new Map();
  for(const line of checkbarState.lines){
    const brand=String(line.brand||'').trim();
    groups.set(brand,(groups.get(brand)||0)+1);
  }
  return [...groups].map(([brand,count])=>({brand,count}));
}

function renderCheckbarBrandSplit(){
  $('#checkbarBrandSplitOptions').hidden=!!checkbarState.saved||!!checkbarState.editing;
  $('#checkbarSplitByBrand').disabled=!!checkbarState.pending||checkbarState.submitting;
  const groups=checkbarBrandGroups();
  $('#checkbarBrandSplitSummary').textContent=$('#checkbarSplitByBrand').checked?
    `${fa(groups.length)} چک‌بار جدا: ${groups.map(g=>`${g.brand||'برند نامشخص'} (${fa(g.count)} ردیف)`).join('، ')}. شماره عطف حواله مشترک است؛ انتقال هر چک‌بار به ورانگر جداگانه انجام می‌شود.`:
    'همهٔ اقلام در یک چک‌بار ذخیره می‌شوند.';
}

function renderCheckbarBrandBatch(doc){
  const batch=doc.brand_batch||[];
  $('#checkbarBrandBatch').hidden=!batch.length;
  $('#checkbarBrandBatch').innerHTML=batch.length?'<p>چک‌بارهای صادرشده از این حواله؛ برای انتقال رسید، هر چک‌بار را جدا باز کنید:</p>'+batch.map(d=>
    `<button type="button" class="secondary-action" data-checkbar-view="${Number(d.id)}" ${d.id===doc.id?'disabled':''}>${esc(d.number)} · ${esc(d.brand)}</button>`).join(' '):'';
}

function checkbarIssuePayload(){
  validateCheckbarDraft();
  const reference=normalizeSearchText($('#checkbarReference').value).trim();
  if(!/^[0-9]{1,10}$/.test(reference)||Number(reference)<1||Number(reference)>2147483647)throw new Error('شمارهٔ سند عطف تأمین‌کننده الزامی است؛ عدد صحیح بین ۱ و ۲۱۴۷۴۸۳۶۴۷ وارد کنید.');
  if(!checkbarDraftStage()&&checkbarState.lines.some(line=>checkbarActual(line)===null))throw new Error('ابتدا ردیف‌های بدون تعداد را تکمیل یا حذف کنید؛ مقدار صفر با خالی متفاوت است.');
  const metadata=Object.fromEntries([...document.querySelectorAll('[data-checkbar-meta]')].map(input=>[input.dataset.checkbarMeta,input.value.trim()]));
  metadata.reference_no=reference;
  return {warehouse:checkbarState.source.warehouse,supplier:checkbarState.source.supplier,order_ids:checkbarState.source.order_ids||[],
    ...(checkbarState.source.remaining_order_id?{remaining_order_id:checkbarState.source.remaining_order_id}:{}),
    expected_token:checkbarState.source.expected_token,request_id:checkbarState.requestId,metadata,
    ...(!checkbarState.editing&&checkbarState.worksheetWorkflow?{worksheet_workflow:true}:{}),
    ...(!checkbarState.editing&&$('#checkbarSplitByBrand').checked?{split_by_brand:true}:{}),
    lines:checkbarState.lines.map(line=>({preorder_id:line.preorder_id,product_code:line.product_code,
      cartons:checkbarNumeric(line.cartons,true),units:checkbarNumeric(line.units),
      manufacturer_price_new:checkbarNumeric(line.manufacturer_price_new),consumer_price_new:checkbarNumeric(line.consumer_price_new),tax:line.tax??null})),
    ...(checkbarState.editing?{document_id:checkbarState.editing.id,expected_revision:checkbarState.editing.revision}:{})};
}

async function issueCheckbar(){
  if(!checkbarState.source||checkbarState.saved||checkbarState.submitting)return;
  if(checkbarImportPending()){checkbarNotice('info','ابتدا خواندن حواله و بررسی اقلام را کامل کنید، سپس «وارد کردن اقلام به چک‌بار» را بزنید.',true);return;}
  const requestId=checkbarState.requestId;
  let timer;
  try{
    if(!checkbarState.pending){
      validateCheckbarDraft();
      const reference=normalizeSearchText($('#checkbarReference').value).trim();
      if(!/^[0-9]{1,10}$/.test(reference)||Number(reference)<1||Number(reference)>2147483647){
        throw new Error('شمارهٔ سند عطف تأمین‌کننده الزامی است؛ عدد صحیح بین ۱ و ۲۱۴۷۴۸۳۶۴۷ وارد کنید.');
      }
      const empty=checkbarState.lines.filter(line=>checkbarActual(line)===null).length;
      if(empty&&!checkbarDraftStage()){
        $('#checkbarEmptyActions').hidden=false;
        $('#checkbarRemoveEmpty').disabled=empty===checkbarState.lines.length;
        checkbarNotice('info',empty===checkbarState.lines.length?'هیچ ردیفی تعداد ندارد. ابتدا تعداد حداقل یک کالا را وارد کنید؛ چک‌بار خالی ذخیره نمی‌شود.':`${fa(empty)} ردیف بدون کارتن و عدد است. این ردیف‌ها از این چک‌بار حذف شوند و ${fa(checkbarState.lines.length-empty)} ردیف باقی‌مانده ذخیره شود؟ اطلاعات قیمتِ ردیف‌های حذف‌شده هم در این سند نمی‌آید.`,true);
        return;
      }
      $('#checkbarEmptyActions').hidden=true;
      const payload=checkbarIssuePayload();
      const brands=payload.split_by_brand?checkbarBrandGroups():[];
      if(brands.some(g=>!g.brand))throw new Error('برند برخی اقلام مشخص نیست؛ اطلاعات برند را اصلاح کنید یا تفکیک برند را خاموش کنید.');
      if(!checkbarDraftStage()){
      if(typeof orderMatchingRequest!=='function')throw new Error('بخش تطبیق سفارش‌ها بارگذاری نشده است؛ صفحه را بازخوانی کنید.');
      Object.assign(payload,checkbarSkipMatching()?{skip_order_matching:true}:orderMatchingRequest(true),{confirm_receipt:true});
      if(!checkbarState.worksheetWorkflow&&!checkbarSkipMatching()&&!confirm((brands.length?`${fa(brands.length)} چک‌بار جدا برای ${brands.map(g=>g.brand).join('، ')} صادر شود؟\n`:'')+'تعداد واقعی بار و تقسیم آن بین سفارش‌های در راه تأیید و چک‌بار ذخیره شود؟ مانده سفارش‌ها همین حالا کم می‌شود؛ انتقال به ورانگر مرحله‌ای جداگانه است.'))return;
      }
      checkbarState.pending=checkbarState.editing?{expected_revision:payload.expected_revision,request_id:payload.request_id,metadata:payload.metadata,lines:payload.lines,
        ...(payload.confirm_receipt?{confirm_receipt:true,...(payload.skip_order_matching?{skip_order_matching:true}:{allocations:payload.allocations,allocation_revision:payload.allocation_revision,accept_unallocated:payload.accept_unallocated})}: {})}:payload;
    }
    checkbarState.submitting=true;
    if(typeof renderOrderMatching==='function'&&orderMatchingState.plan)renderOrderMatching(orderMatchingState.plan,true);
    checkbarNotice('info','در حال ذخیره چک‌بار… لطفاً تا مشخص‌شدن نتیجه دوباره ثبت نکنید.');
    $('#checkbarIssue').textContent='در حال ذخیره…';$('#checkbarIssue').disabled=true;
    document.querySelectorAll('[data-checkbar-meta]').forEach(input=>input.disabled=true);
    renderCheckbarLines();renderCheckbarProducts();$('#checkbarIssue').disabled=true;
    const controller=new AbortController();timer=setTimeout(()=>controller.abort(),30000);
    const result=await api(checkbarState.editing?`/warehouse-assistant/api/checkbars/${checkbarState.editing.id}`:'/warehouse-assistant/api/checkbars',
      {method:checkbarState.editing?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(checkbarState.pending),signal:controller.signal});
    if(requestId!==checkbarState.requestId){toast('چک‌بار قبلی ذخیره شد و در فهرست چک‌بارهای صادرشده در دسترس است.');return}
    checkbarState.saved=result.document;showSavedCheckbar(result.document);
    refreshCheckbarVersions(result.document.id);
    loadCheckbarPage();
    if(typeof refreshFulfillmentAfterCheckbar==='function')refreshFulfillmentAfterCheckbar();
    toast(result.document.worksheet_workflow&&!result.document.receipt_confirmed?'برگه اولیه ذخیره شد؛ برای چاپ، برگه را تأیید کنید.':result.document.order_matching?.skipped?'شمارش و قیمت‌ها بدون تطبیق ذخیره شد؛ مانده سفارش‌ها تغییری نکرد.':result.document.brand_batch?`${fa(result.document.brand_batch.length)} چک‌بار جدا صادر شد؛ از فهرست برندهای همین حواله هرکدام را باز کنید.`:'چک‌بار تأیید و ذخیره شد؛ مانده سفارش‌ها به‌روز شد. انتقال به ورانگر جداگانه انجام می‌شود.');
  }catch(error){
    if(requestId!==checkbarState.requestId)return;
    const rejected=error.status>=400&&error.status<500&&![408,429].includes(error.status);
    if(rejected){checkbarState.pending=null;document.querySelectorAll('[data-checkbar-meta]').forEach(input=>input.disabled=false);renderCheckbarLines();renderCheckbarProducts();if(typeof resetOrderMatching==='function')resetOrderMatching()}
    const uncertain=!!checkbarState.pending;
    checkbarNotice('error',uncertain?'پاسخ ذخیره دریافت نشد؛ ممکن است سند ثبت شده باشد. «بررسی و تلاش مجدد» همان درخواست را پیگیری می‌کند و سند تکراری نمی‌سازد.':`${error.message} اطلاعات واردشده حفظ شده‌اند؛ اصلاح کنید و دوباره ذخیره کنید.`,true);
    $('#checkbarIssue').textContent=uncertain?'بررسی و تلاش مجدد':checkbarState.editing?'ذخیره اصلاحات':'تأیید دریافت و ذخیره چک‌بار';
  }finally{
    clearTimeout(timer);
    if(requestId===checkbarState.requestId){checkbarState.submitting=false;$('#checkbarIssue').disabled=!!checkbarState.saved;renderCheckbarBrandSplit();syncCheckbarMatchingChoice()}
  }
}

function showSavedCheckbar(doc){
  checkbarState.skipOrderMatching=!!doc.order_matching?.skipped;
  checkbarState.worksheetWorkflow=!!doc.worksheet_workflow;
  $('#checkbarApproveWorksheet').hidden=!doc.worksheet_workflow||!!doc.worksheet_approved_at||!!doc.deleted;
  $('#checkbarApproveWorksheet').disabled=false;
  $('#checkbarEdit').textContent=doc.worksheet_workflow&&!doc.receipt_confirmed?(doc.worksheet_approved_at?'ثبت شمارش و قیمت انبار':'اصلاح برگه اولیه'):'اصلاح چک‌بار';
  if(typeof resetCheckbarImage==='function'){resetCheckbarImage();$('#checkbarImagePanel').hidden=true;}
  $('#checkbarEmptyActions').hidden=true;
  checkbarState.saved=doc;checkbarState.lines=doc.lines;
  renderCheckbarBrandBatch(doc);renderCheckbarBrandSplit();
  $('#checkbarEdit').hidden=!!doc.deleted;$('#checkbarDelete').hidden=!!doc.deleted;
  $('#checkbarEdit').disabled=false;$('#checkbarDelete').disabled=false;$('#checkbarDelete').textContent='حذف چک‌بار';
  $('#checkbarWarehouse').innerHTML=`<option value="${esc(doc.warehouse)}">${esc(doc.warehouse_name)}</option>`;
  $('#checkbarSupplier').innerHTML=`<option value="${esc(doc.supplier)}">${esc(doc.supplier)}</option>`;
  $('#checkbarTitle').textContent=`چک‌بار ${doc.number} · نسخه ${fa(doc.revision||0)} · ${doc.supplier}${doc.brand?' · '+doc.brand:''}`;
  $('#checkbarEditor').hidden=false;$('#checkbarOrderPicker').hidden=true;$('#checkbarManual').hidden=true;
  $('#checkbarReselect').hidden=true;$('#checkbarWarehouse').disabled=true;$('#checkbarSupplier').disabled=true;
  document.querySelectorAll('[data-checkbar-meta]').forEach(input=>{input.value=doc.metadata[input.dataset.checkbarMeta]||'';input.disabled=true});
  $('#checkbarDownload').href=`/warehouse-assistant/api/checkbars/${doc.id}/document.xlsx`;
  $('#checkbarPrint').href=`/warehouse-assistant/api/checkbars/${doc.id}/print`;
  $('#checkbarPrint').hidden=!!doc.deleted||(doc.worksheet_workflow&&!doc.worksheet_approved_at);
  $('#checkbarDownload').hidden=!!doc.deleted;renderCheckbarLines();
  const uncounted=doc.lines.filter(line=>line.cartons==null&&line.units==null).length;
  $('#checkbarIssue').textContent='ذخیره شد';
  checkbarNotice('success',`چک‌بار ${doc.number} با موفقیت ذخیره شده است. برای دریافت فایل، «دانلود اکسل چک‌بار» را بزنید؛ از سوابق هم قابل مشاهده است. ${uncounted?`${fa(uncounted)} ردیف شمارش‌نشده در سند باقی مانده است. `:''}${doc.receipt_confirmed?'مقدار تأییدشده از مانده سفارش‌ها کم شده است؛ انتقال به ورانگر جداگانه است.':'این سند قدیمی هنوز دریافت تأییدشدهٔ چک‌بار ندارد.'}`,true);
  if(doc.deleted)checkbarNotice('info','این چک‌بار حذف شده است. نسخه‌های نگهداری‌شده از بخش تاریخچه قابل دریافت‌اند؛ دریافت فایل، سند را فعال نمی‌کند.',true);
  else if(doc.order_matching?.skipped)checkbarNotice('success','شمارش و قیمت‌ها بدون تطبیق با سفارش ثبت شد؛ مانده سفارش‌ها تغییری نکرده است. اکنون می‌توانید سند انبار بسازید.',true);
  else if(doc.worksheet_workflow&&!doc.receipt_confirmed)checkbarNotice('success',doc.worksheet_approved_at?'برگه تأیید و برای چاپ آماده است. انباردار پس از کنترل بار، «ثبت شمارش و قیمت انبار» را باز کند. هنوز دریافت یا سند انبار ثبت نشده است.':'برگه اولیه ذخیره شد. اقلام و تعداد سفارش را بررسی کنید و «تأیید برگه برای چاپ» را بزنید؛ مانده سفارش تغییری نکرده است.',true);
  if(typeof refreshCheckbarReceipt==='function')return refreshCheckbarReceipt(doc);
}

async function editSavedCheckbar(){
  if(!checkbarState.saved||checkbarState.saved.deleted||checkbarState.deletePending||checkbarState.submitting)return;
  if(typeof receiptBridge!=='undefined'&&receiptBridge.locked)return;
  if(checkbarState.saved.receipt_confirmed&&typeof receiptBridge!=='undefined'&&receiptBridge.completed){checkbarNotice('error','این چک‌بار به ورانگر منتقل شده است؛ تأیید دوباره یا تغییر تعداد آن مجاز نیست. اصلاح رسید را در ورانگر پیگیری کنید.',true);return;}
  const sequence=++checkbarState.sequence,id=checkbarState.saved.id;
  $('#checkbarEdit').disabled=true;
  try{
    const result=await api(`/warehouse-assistant/api/checkbars/${id}/edit-context`);
    if(sequence!==checkbarState.sequence)return;
    const doc=result.document;
    showSavedCheckbar(doc);
    checkbarState.editing={id:doc.id,revision:doc.revision,worksheet_approved_at:doc.worksheet_approved_at,receipt_confirmed:doc.receipt_confirmed};checkbarState.saved=null;checkbarState.pending=null;
    $('#checkbarBrandBatch').hidden=true;
    if(typeof resetCheckbarReceipt==='function')resetCheckbarReceipt();
    checkbarState.source={...doc,catalog:result.catalog};checkbarState.lines=doc.lines.map(line=>({...line}));
    checkbarState.requestId=checkbarRequestId();
    $('#checkbarTitle').textContent=`اصلاح چک‌بار ${doc.number} · نسخه ${fa(doc.revision)}`;
    $('#checkbarIssue').textContent='ذخیره اصلاحات';$('#checkbarManual').hidden=false;
    $('#checkbarEdit').hidden=true;$('#checkbarDelete').hidden=true;$('#checkbarDownload').hidden=true;$('#checkbarPrint').hidden=true;$('#checkbarApproveWorksheet').hidden=true;
    document.querySelectorAll('[data-checkbar-meta]').forEach(input=>input.disabled=false);
    renderCheckbarProducts();renderCheckbarLines();
  }catch(error){if(sequence===checkbarState.sequence)checkbarNotice('error',error.message,true)}
  finally{if(sequence===checkbarState.sequence)$('#checkbarEdit').disabled=typeof receiptBridge!=='undefined'&&receiptBridge.locked}
}

async function approveCheckbarWorksheet(){
  const doc=checkbarState.saved;if(!doc||doc.deleted||checkbarState.submitting)return;
  if(doc.worksheet_approved_at)return;
  checkbarState.approvalPending||={expected_revision:doc.revision||0,request_id:checkbarRequestId()};
  const sequence=checkbarState.sequence;
  checkbarState.submitting=true;$('#checkbarApproveWorksheet').disabled=true;$('#checkbarEdit').disabled=true;$('#checkbarDelete').disabled=true;
  try{
    const result=await api(`/warehouse-assistant/api/checkbars/${doc.id}/approve-worksheet`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(checkbarState.approvalPending)});
    if(sequence!==checkbarState.sequence)return;
    checkbarState.approvalPending=null;await showSavedCheckbar(result.document);refreshCheckbarVersions(doc.id);loadCheckbarPage();
  }catch(error){
    if(sequence!==checkbarState.sequence)return;
    if(error.status>=400&&error.status<500&&![408,429].includes(error.status))checkbarState.approvalPending=null;
    checkbarNotice('error',checkbarState.approvalPending?'نتیجه تأیید دریافت نشد؛ دوباره همین دکمه را بزنید تا همان درخواست پیگیری شود.':error.message,true);
  }finally{if(sequence===checkbarState.sequence){checkbarState.submitting=false;$('#checkbarApproveWorksheet').disabled=false;$('#checkbarEdit').disabled=false;$('#checkbarDelete').disabled=false}}
}

async function deleteSavedCheckbar(){
  const doc=checkbarState.saved;
  if(!doc||doc.deleted||checkbarState.submitting)return;
  if(typeof receiptBridge!=='undefined'&&receiptBridge.locked)return;
  if(!checkbarState.deletePending){
    if(!confirm(`چک‌بار ${doc.number} حذف شود؟ نسخه‌ها حفظ می‌شوند. ${doc.receipt_confirmed?'اگر به ورانگر منتقل نشده باشد، مقدار آن به مانده سفارش‌ها برمی‌گردد؛ رسید منتقل‌شده تغییر نمی‌کند.':'سفارش‌ها، دریافت‌ها و موجودی تغییر نمی‌کنند.'}`))return;
    checkbarState.deletePending={expected_revision:doc.revision||0,request_id:checkbarRequestId()};
  }
  const sequence=checkbarState.sequence,payload=checkbarState.deletePending;
  checkbarState.submitting=true;$('#checkbarDelete').disabled=true;$('#checkbarEdit').disabled=true;
  let timer;
  try{
    const controller=new AbortController();timer=setTimeout(()=>controller.abort(),30000);
    await api(`/warehouse-assistant/api/checkbars/${doc.id}`,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal});
    loadCheckbarPage();
    if(sequence!==checkbarState.sequence)return;
    checkbarState.deletePending=null;showSavedCheckbar({...doc,deleted:true});
    if(typeof refreshFulfillmentAfterCheckbar==='function')refreshFulfillmentAfterCheckbar();
    refreshCheckbarVersions(doc.id);
  }catch(error){
    if(sequence!==checkbarState.sequence)return;
    if(error.status>=400&&error.status<500&&![408,429].includes(error.status))checkbarState.deletePending=null;
    checkbarNotice('error',checkbarState.deletePending?'نتیجهٔ حذف دریافت نشد؛ «بررسی و تلاش مجدد حذف» همان درخواست را پیگیری می‌کند.':error.message,true);
    $('#checkbarDelete').textContent=checkbarState.deletePending?'بررسی و تلاش مجدد حذف':'حذف چک‌بار';
  }finally{
    clearTimeout(timer);
    if(sequence===checkbarState.sequence){checkbarState.submitting=false;$('#checkbarDelete').disabled=false;$('#checkbarEdit').disabled=!!checkbarState.deletePending}
  }
}

async function openCheckbarHistory(id){
  checkbarClear();const sequence=checkbarState.sequence;
  $('#checkbarDialog').showModal();checkbarNotice('info','در حال خواندن سند و نسخه‌ها…');
  try{
    const result=await api(`/warehouse-assistant/api/checkbars/${id}/history`);
    if(sequence!==checkbarState.sequence)return;
    const receiptReady=showSavedCheckbar(result.document);
    renderCheckbarVersions(id,result.versions);
    await receiptReady;
    return sequence===checkbarState.sequence&&checkbarState.saved?.id===id;
  }catch(error){if(sequence===checkbarState.sequence)checkbarNotice('error',error.message,true)}
}

async function openCheckbarArchiveAction(id,action){
  if(!await openCheckbarHistory(id))return;
  if(action==='receipt'){
    $('#checkbarReceiptPanel').hidden=false;
    $('#checkbarReceiptPanel').scrollIntoView?.({block:'nearest'});
    if(typeof receiptActionLabel==='function')receiptActionLabel();
    if(typeof receiptBridge!=='undefined'&&!receiptBridge.locked)$('#checkbarReceiptDate').focus();
    else $('#checkbarReceiptRefresh').focus();
    return;
  }
  // Always check fresh ERP state before acting on a potentially stale archive row.
  if(typeof receiptBridge==='undefined'||receiptBridge.locked)return;
  if(action==='edit')return editSavedCheckbar();
  if(action==='delete')return deleteSavedCheckbar();
}

function checkbarArchiveStatus(doc){
  if(doc.deleted)return {key:'deleted',label:'چک‌بار حذف‌شده',action:'مشاهده و تاریخچه'};
  if(doc.worksheet_workflow&&!doc.receipt_confirmed)return doc.worksheet_approved_at?{key:'inspection',label:'منتظر شمارش انبار',action:'ثبت شمارش انبار'}:{key:'worksheet',label:'برگه اولیه؛ منتظر تأیید',action:'بررسی و تأیید برگه'};
  if(['not_sent','deleted'].includes(doc.receipt_state))return {key:'ready',label:'آماده ثبت',action:'آماده‌سازی رسید'};
  if(doc.receipt_state==='pending')return {key:'pending',label:'در انتظار نتیجه',action:'پیگیری نتیجه'};
  if(doc.receipt_state==='sent')return {key:'sent',label:'ثبت‌شده',action:'مشاهده سند'};
  return {key:'review',label:'نیازمند بررسی',action:'بررسی وضعیت'};
}

function checkbarArchiveActions(doc){
  const history=`<button type="button" data-checkbar-view="${doc.id}" class="secondary-action">مشاهده و تاریخچه</button>`;
  if(doc.deleted)return history;
  const locked=!['not_sent','deleted'].includes(doc.receipt_state);
  const explanation=locked?'اصلاح و حذف تا تأیید نبودِ سند ورانگر قفل است؛ با اقدام اصلی این ردیف وضعیت را بررسی کنید.':'';
  const button=(action,label)=>`<button type="button" data-checkbar-view="${doc.id}" data-checkbar-action="${action}" class="secondary-action"${action!=='receipt'&&locked?` disabled title="${explanation}"`:''}>${label}</button>`;
  const primary=`<button type="button" data-checkbar-view="${doc.id}" data-checkbar-action="${doc.worksheet_workflow&&!doc.receipt_confirmed?(doc.worksheet_approved_at?'edit':'worksheet'):'receipt'}" data-workflow-primary="true" class="secondary-action checkbar-next-action">${checkbarArchiveStatus(doc).action}</button>`;
  return `<div class="checkbar-archive-actions">${primary}${doc.worksheet_workflow&&!doc.worksheet_approved_at?'':`<a class="secondary-action" href="/warehouse-assistant/api/checkbars/${doc.id}/print" target="_blank" rel="noopener">چاپ</a>`}<details class="operation-row-menu"><summary>سایر عملیات</summary><div>${history}${button('edit','اصلاح')}${button('delete','حذف')}<a href="/warehouse-assistant/api/checkbars/${doc.id}/document.xlsx">اکسل</a>${explanation?`<small>${explanation}</small>`:''}</div></details></div>`;
}

function updateCheckbarArchiveReceipt(id,data){
  const doc=checkbarArchive.find(row=>row.id===id);
  if(!doc)return;
  doc.receipt_state=data.receipt?.state==='exists'?'sent':data.receipt?.state||data.status||'unknown';
  doc.receipt_number=data.receipt?.number||data.result?.VocherNo||doc.receipt_number;
  renderCheckbarArchive();
}

function renderCheckbarVersions(id,versions){
  $('#checkbarHistoryDetails').hidden=!versions.length;
  $('#checkbarVersions').innerHTML='<p>تاریخچه؛ دریافت نسخه‌های پیشین (حتی پس از حذف)</p>'+versions.map(v=>
    `<p>نسخه ${fa(v.revision)} · ${esc(({issue:'صدور',edit:'اصلاح',delete:'حذف'})[v.operation])} · ${esc(v.created_by)} · ${esc(formatRefreshDate(v.created_at))} <a href="/warehouse-assistant/api/checkbars/${id}/revisions/${v.revision}/document.xlsx">دریافت اکسل این نسخه</a></p>`).join('');
}

async function refreshCheckbarVersions(id){
  const sequence=checkbarState.sequence;
  try{
    const result=await api(`/warehouse-assistant/api/checkbars/${id}/history`);
    if(sequence===checkbarState.sequence&&checkbarState.saved?.id===id)renderCheckbarVersions(id,result.versions);
  }catch{if(sequence===checkbarState.sequence)$('#checkbarVersions').textContent='تاریخچه خوانده نشد؛ سند را از فهرست سوابق دوباره باز کنید.'}
}

function saveCheckbarWithoutEmpty(){
  if(!checkbarEditable())return;
  try{
    validateCheckbarDraft();
    const counted=checkbarState.lines.filter(line=>checkbarActual(line)!==null);
    if(!counted.length){checkbarNotice('error','تعداد حداقل یک کالا را وارد کنید؛ چک‌بار خالی ذخیره نمی‌شود.',true);return}
    checkbarState.lines=counted;$('#checkbarEmptyActions').hidden=true;
    renderCheckbarLines();renderCheckbarProducts();return issueCheckbar();
  }catch(error){checkbarNotice('error',error.message,true)}
}

function renderCheckbarArchive(){
  const query=normalizeSearchText($('#checkbarArchiveSearch').value);
  const warehouse=$('#checkbarArchiveWarehouse').value,status=$('#checkbarArchiveState').value;
  const warehouses=[...new Set([...checkbarArchive.map(d=>d.warehouse_name),warehouse].filter(Boolean))].sort((a,b)=>a.localeCompare(b,'fa'));
  const options='<option value="">همه انبارها</option>'+warehouses.map(name=>`<option value="${esc(name)}">${esc(name)}</option>`).join('');
  if($('#checkbarArchiveWarehouse').innerHTML!==options){$('#checkbarArchiveWarehouse').innerHTML=options;$('#checkbarArchiveWarehouse').value=warehouse}
  const rows=checkbarArchive.filter(d=>(!warehouse||d.warehouse_name===warehouse)&&(!status||checkbarArchiveStatus(d).key===status)&&normalizeSearchText([d.number,d.supplier,d.brand,d.warehouse_name,d.receipt_number].join(' ')).includes(query));
  $('#checkbarHistoryRows').innerHTML=rows.map(d=>`<tr><td>${esc(d.number)}${d.deleted?' · حذف‌شده':''}${d.receipt_number?`<small>سند ورانگر ${fa(d.receipt_number)} · ${esc(({deleted:'حذف‌شده',pending:'در حال پیگیری',sent:'ثبت‌شده',unknown:'وضعیت نامشخص',review:'نیازمند بررسی'})[d.receipt_state]||'نیازمند بررسی')}</small>`:''}</td><td>${esc(d.warehouse_name)}</td><td>${esc(d.supplier)}${d.brand?`<small>${esc(d.brand)}</small>`:""}</td><td>${esc(formatRefreshDate(d.created_at))}</td><td><span class="checkbar-receipt-status" data-checkbar-status="${checkbarArchiveStatus(d).key}">${checkbarArchiveStatus(d).label}</span></td><td>${checkbarArchiveActions(d)}</td></tr>`).join('')||`<tr><td colspan="6" class="empty-cell">${query||warehouse||status?'چک‌باری مطابق فیلترها پیدا نشد؛ فیلترها را پاک کنید.':'هنوز چک‌باری صادر نشده است. برای شروع «صدور چک‌بار جدید» را بزنید؛ داشتن سفارش قبلی لازم نیست.'}</td></tr>`;
  $('#checkbarArchiveStatus').textContent=`${fa(rows.length)} از ${fa(checkbarArchive.length)} سند دریافتی · فقط ۱۰۰ سند اخیر · وضعیت ثبت‌شده در سامانه؛ پیش از عملیات استعلام می‌شود`;
}

async function loadCheckbarPage(){
  if(!has('warehouse.order.draft'))return;
  const sequence=++checkbarArchiveSequence;
  $('#checkbarArchiveStatus').textContent='در حال خواندن سوابق…';
  try{
    const data=await api(`/warehouse-assistant/api/checkbars?include_deleted=${!!$('#checkbarIncludeDeleted').checked}`);
    if(sequence!==checkbarArchiveSequence)return;
    checkbarArchive=data.documents;renderCheckbarArchive();
  }catch(error){if(sequence===checkbarArchiveSequence)$('#checkbarArchiveStatus').textContent=error.message}
}

document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('[data-checkbar-table-view]').forEach(button=>button.addEventListener('click',()=>applyCheckbarTableView(button.dataset.checkbarTableView)));
  $('#checkbarHiddenFilters').addEventListener('click',()=>applyCheckbarTableView('all'));
  $('#checkbarTable').addEventListener('input',refreshCheckbarHiddenFilters);
  $('#checkbarSplitByBrand').addEventListener('change',()=>{renderCheckbarBrandSplit();if(typeof invalidateDraftOrderMatching==='function')invalidateDraftOrderMatching()});
  $('#checkbarBrandBatch').addEventListener('click',event=>{const button=event.target.closest('[data-checkbar-view]');if(button)openCheckbarHistory(Number(button.dataset.checkbarView))});
  $('#openCheckbarButton').addEventListener('click',openCheckbar);
  $('#checkbarIncludeDeleted').addEventListener('change',()=>{
    if(!$('#checkbarIncludeDeleted').checked&&$('#checkbarArchiveState').value==='deleted')$('#checkbarArchiveState').value='';
    return loadCheckbarPage();
  });
  $('#checkbarEdit').addEventListener('click',editSavedCheckbar);
  $('#checkbarDelete').addEventListener('click',deleteSavedCheckbar);
  $('#refreshCheckbarPage').addEventListener('click',loadCheckbarPage);
  $('#checkbarArchiveSearch').addEventListener('input',renderCheckbarArchive);
  $('#checkbarArchiveWarehouse').addEventListener('change',renderCheckbarArchive);
  $('#checkbarArchiveState').addEventListener('change',()=>{
    if($('#checkbarArchiveState').value==='deleted'&&!$('#checkbarIncludeDeleted').checked){$('#checkbarIncludeDeleted').checked=true;return loadCheckbarPage()}
    renderCheckbarArchive();
  });
  $('#checkbarArchiveClear').addEventListener('click',()=>{
    for(const id of ['checkbarArchiveSearch','checkbarArchiveWarehouse','checkbarArchiveState'])$('#'+id).value='';
    renderCheckbarArchive();
  });
  $('#closeCheckbar').addEventListener('click',()=>{if(typeof requestCheckbarClose==='function')requestCheckbarClose();else{checkbarState.sequence++;$('#checkbarDialog').close()}});
  $('#checkbarDialog').addEventListener('cancel',event=>{
    if(event.defaultPrevented||$('#checkbarDialog').classList.contains('workspace-fullscreen'))return;
    if(typeof requestCheckbarClose==='function'){event.preventDefault();requestCheckbarClose()}else checkbarState.sequence++;
  });
  $('#checkbarWarehouse').addEventListener('change',()=>checkbarLoadContext(true));
  $('#checkbarSupplier').addEventListener('change',()=>checkbarLoadContext());
  $('#checkbarOrders').addEventListener('change',()=>$('#checkbarPrepare').disabled=!$('#checkbarSupplier').value);
  $('#checkbarPrepare').addEventListener('click',checkbarPrepare);
  $('#checkbarReselect').addEventListener('click',()=>{if(confirm('تغییرات ذخیره‌نشدهٔ این فرم کنار گذاشته شود؟')){checkbarClear();checkbarLoadContext()}});
  $('#checkbarBrand').addEventListener('change',()=>{$('#checkbarGroup3').value='';renderCheckbarProducts()});
  $('#checkbarGroup3').addEventListener('change',renderCheckbarProducts);
  $('#checkbarProductSearch').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();quickAddCheckbar()}});
  $('#checkbarAdd').addEventListener('click',()=>{if(!checkbarEditable())return;$('#checkbarCatalogSearch').value='';renderCheckbarCatalog();$('#checkbarCatalogDialog').showModal()});
  $('#closeCheckbarCatalog').addEventListener('click',()=>$('#checkbarCatalogDialog').close());
  $('#checkbarCatalogSearch').addEventListener('input',renderCheckbarCatalog);
  $('#checkbarCatalogRows').addEventListener('change',()=>$('#checkbarAddSelected').disabled=!document.querySelector('[data-checkbar-pick]:checked'));
  $('#checkbarCatalogRows').addEventListener('dblclick',event=>{const row=event.target.closest('[data-checkbar-catalog-code]');if(row)addCheckbarProducts([row.dataset.checkbarCatalogCode])});
  $('#checkbarAddSelected').addEventListener('click',()=>addCheckbarProducts([...document.querySelectorAll('[data-checkbar-pick]:checked')].map(input=>input.dataset.checkbarPick)));
  $('#checkbarLines').addEventListener('input',event=>{
    if(!checkbarEditable()||!event.target.dataset.checkbarField)return;
    $('#checkbarEmptyActions').hidden=true;
    const line=checkbarState.lines[Number(event.target.closest('tr').dataset.checkbarIndex)];
    line[event.target.dataset.checkbarField]=event.target.value;updateCheckbarTotals();
  });
  $('#checkbarLines').addEventListener('click',event=>{
    if(!checkbarEditable())return;
    const row=event.target.closest('[data-checkbar-index]');if(!row)return;
    const index=Number(row.dataset.checkbarIndex),line=checkbarState.lines[index];
    if(event.target.closest('[data-checkbar-fill]')){Object.assign(line,receiptParts(line.remaining_qty,line));renderCheckbarLines()}
    if(event.target.closest('[data-checkbar-remove]')){checkbarState.lines.splice(index,1);renderCheckbarLines();renderCheckbarProducts()}
  });
  document.querySelectorAll('[data-checkbar-meta]').forEach(input=>input.addEventListener('input',()=>{if(typeof invalidateDraftOrderMatching==='function')invalidateDraftOrderMatching()}));
  $('#checkbarIssue').addEventListener('click',issueCheckbar);
  $('#checkbarMatchOrders').addEventListener('change',()=>{
    if(checkbarState.saved||checkbarState.submitting||checkbarState.pending){syncCheckbarMatchingChoice();return}
    checkbarState.skipOrderMatching=!$('#checkbarMatchOrders').checked;
    resetOrderMatching();updateCheckbarTotals();
  });
  $('#checkbarApproveWorksheet').addEventListener('click',approveCheckbarWorksheet);
  $('#checkbarRemoveEmpty').addEventListener('click',saveCheckbarWithoutEmpty);
  $('#checkbarCompleteEmpty').addEventListener('click',()=>{$('#checkbarEmptyActions').hidden=true;checkbarNotice('info','تعداد ردیف‌های خالی را تکمیل کنید، سپس دریافت را تأیید و چک‌بار را ذخیره کنید.');});
  $('#checkbarHistoryRows').addEventListener('click',async event=>{
    if(event.target.closest('a'))event.target.closest('details')?.removeAttribute('open');
    const button=event.target.closest('[data-checkbar-view]');if(!button||button.disabled)return;
    button.closest('details')?.removeAttribute('open');
    if(button.dataset.checkbarAction)await openCheckbarArchiveAction(Number(button.dataset.checkbarView),button.dataset.checkbarAction);
    else await openCheckbarHistory(Number(button.dataset.checkbarView));
  });
});
