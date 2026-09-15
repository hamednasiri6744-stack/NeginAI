const state={bootstrap:null,suggestions:null,inventory:{items:[],total:0,offset:0},inventoryViews:[],inventoryColumns:[],orderingCatalog:[],orderingColumns:[],automaticColumns:[],preorderColumns:[],supplyColumns:[],supplyRows:[],supplyMeta:null,tablePreferences:{},automaticSettings:[],automaticDrafts:{},automaticDefaults:null,automaticPreview:null,automaticPreorders:[],automaticRefreshStatus:null,previewPreorderId:null,filterTimer:null,statusTimer:null};
const $=selector=>document.querySelector(selector);
state.preparedOrderKind='manual';state.manualPreorders=[];
const workspaceViews=["inventory","supply","ordering","automatic","preorders","sent","fulfillment","checkbar","purchase","sale-pricing","unbilled","transfers"];
function requestedWorkspaceView(){const view=location.hash.slice(1).split('/')[0];return workspaceViews.includes(view)?view:"inventory"}
function restoreWorkspaceView(){const view=requestedWorkspaceView();if(view!==state.activeView||view==='preorders')switchView(view,false)}
const fa=value=>new Intl.NumberFormat("fa-IR",{maximumFractionDigits:2}).format(Number(value||0));
const esc=value=>String(value??"").replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
// Normalize only search comparisons; stored codes, quantities and user drafts stay untouched.
function normalizeSearchText(value){
  return String(value??"").replace(/[۰-۹]/g,c=>String(c.charCodeAt(0)-1776))
    .replace(/[٠-٩]/g,c=>String(c.charCodeAt(0)-1632)).replace(/٫/g,".")
    .replace(/([0-9])[,٬](?=[0-9])/g,"$1").replace(/ي/g,'ی').replace(/ك/g,'ک')
    .replace(/[\s\u200c]+/g,' ').trim().toLocaleLowerCase("fa");
}
function groupLevel3Cell(value){
  return String(value??'').trim()?esc(value):'<span title="گروه سطح ۳ در اطلاعات دریافتی این کالا مشخص نشده است.">مشخص نشده</span>';
}

const fixedColumnWidths={group_level3:140,product_name:220,supplier:180,manufacturer:160,brand:120,
  warehouse:115,warehouse_code:115,enabled:72,product_code:110,barcode:135,
  manufacturer_product_code:135,period_out_qty:156,average_daily_out:156,
  contact_email:175,contact_mobile:130,contact_first_name:125,contact_last_name:140,
  contact:140,status:145,actions:200,documents:125,preorder_number:175,
  created_at:150,updated_by:150,evidence:170,order_cycle_status:145};
const previewColumnKeys=["product_code","product_name","brand","physical_procurement_qty","in_transit_qty","pending_receipt_qty","inventory_position_qty",
  "average_daily_out","coverage_days","unadjusted_suggested_cartons","system_suggested_cartons",
  "final_order_cartons","order_quantity","manufacturer_price","consumer_price","approximate_price","estimated_value",
  "manufacturer_product_code","barcode","manufacturer","conversion_rate","group_level3"];
function fixedColumnWidth(key){return key?fixedColumnWidths[key]||112:44}
// Inventory is read-mostly: do not reserve editable-form widths for short labels/numbers.
const inventoryColumnWidths={manufacturer:110,brand:84,warehouse_name:96,product_code:96,
  barcode:116,manufacturer_product_code:132,conversion_rate:60,damaged_qty:64,
  on_hand_qty:88,reserved_qty:88,owned_procurement_qty:88,open_customer_order_qty:88,
  unconfirmed_free_invoice_qty:96,legacy_open_order_qty:88,open_order_qty:88,
  pending_sale_voucher_qty:104,effective_procurement_qty:112,in_transit_qty:96,pending_receipt_qty:156,online_transfer_out_qty:104,
  days_since_last_stock:96,last_in_stock_date:96,sales_window_start:96,sales_window_end:96,
  tax_rate:86,sale_price:104,manufacturer_price:104,consumer_price:104};
function fitFixedTableColumns(table){
  const headers=[...table.querySelectorAll("thead tr:first-child th")];
  const inventory=table.classList.contains("inventory-table");
  let total=0;
  headers.forEach((header,index)=>{
    const key=header.dataset.column||header.dataset.supplyColumn||header.dataset.autoColumn||
      header.dataset.preorderColumn||header.dataset.orderColumn||header.dataset.previewColumn||
      header.dataset.fulfillmentColumn||header.dataset.receiptColumn||header.dataset.catalogColumn||
      (table.classList.contains("preview-lines-table")?previewColumnKeys[index]:"");
    const automaticWidths={warehouse:104,product_count:72,reorder_coverage_days:104,target_days:100,minimum_cartons:104,status:128,actions:104};
    const fulfillmentWidths={number:130,supplier:160,'supplier-confirmation':170,delivery_date:110,viewed:170,notification:150,warehouse:90,sent:150,remaining:120,status:120,actions:196};
    const receiptWidths={code:104,name:248,ordered:96,previous:116,cumulative:100,units:88,complete:108};
    const previewWidths={product_code:96,product_name:220,manufacturer:104,group_level3:104,
      physical_procurement_qty:120,in_transit_qty:92,pending_receipt_qty:128,inventory_position_qty:120,average_daily_out:164,coverage_days:88,
      unadjusted_suggested_cartons:112,system_suggested_cartons:104,final_order_cartons:140};
    const customWidth=Number(header.dataset.userColumnWidth);
    const defaultWidth=Number(header.dataset.defaultColumnWidth);
    const width=Number.isFinite(customWidth)&&customWidth>=56&&customWidth<=640?customWidth:
      Number.isFinite(defaultWidth)&&defaultWidth>=56&&defaultWidth<=640?defaultWidth:
      (inventory?inventoryColumnWidths[key]:table.id==='automaticTable'?automaticWidths[key]:table.id==='fulfillmentTable'?fulfillmentWidths[key]:table.id==='fulfillmentReceiptTable'?receiptWidths[key]:table.classList.contains('preview-lines-table')?previewWidths[key]:table.id==='preorderCatalogTable'?({code:90,manufacturer_code:100,barcode:140,name:220,stock:80,incoming:80,basis:90,daily:90,coverage:90,price:150,cartons:80,action:96})[key]:null)??fixedColumnWidth(key);
    header.style.width=`${width}px`;
    if(!header.hidden)total+=width;
  });
  if(total){table.style.width=`${total}px`;table.classList.add("fixed-columns")}
  if(inventory){
    table.querySelectorAll('tbody td:is([data-column="manufacturer"],[data-column="brand"],[data-column="warehouse_name"],[data-column="product_name"],[data-column="barcode"],[data-column="manufacturer_product_code"])')
      .forEach(cell=>{cell.title=cell.textContent.trim()});
  }
}
class ApiError extends Error{constructor(message,status){super(message);this.status=status}}

// Task-oriented views from Figma Workflow / inventory (20:2). These are display
// presets, NOT saved preferences, filters, calculations or persistence actions.
const workViews={
  inventory:{table:'.inventory-table',choices:'[data-column-choice]',attribute:'column',choice:'columnChoice',apply:()=>applyInventoryColumnVisibility(),views:[
    ['workspace','نمای فشرده',['product_code','product_name','warehouse_name','manufacturer','conversion_rate','on_hand_qty','open_order_qty','in_transit_qty','effective_procurement_qty']],
    ['stock','کنترل موجودی',['product_code','product_name','warehouse_name','manufacturer','group_level3','on_hand_qty','open_order_qty','in_transit_qty','pending_receipt_qty','effective_procurement_qty','period_out_qty','ordering_cycle_active']],
    ['demand','مبنای سفارش',['product_code','product_name','warehouse_name','manufacturer','group_level3','in_transit_qty','pending_receipt_qty','effective_procurement_qty','period_out_qty','online_transfer_out_qty','sales_window_start','sales_window_end','days_since_last_stock','ordering_cycle_active']],
    ['prices','قیمت‌ها',['product_code','product_name','warehouse_name','manufacturer','group_level3','sale_price','manufacturer_price','consumer_price','tax_rate']],
    ['identity','مشخصات کالا',['product_code','product_name','warehouse_name','manufacturer','group_level3','brand','barcode','manufacturer_product_code','conversion_rate']]]},
  automatic:{table:'#automaticTable',choices:'[data-auto-column-choice]',attribute:'autoColumn',preference:'automatic_settings',apply:()=>applyAutomaticColumnVisibility(),views:[
    ['rules','قواعد سفارش',['enabled','warehouse','supplier','product_count','reorder_coverage_days','target_days','minimum_cartons','status','actions']],
    ['contacts','اطلاعات تماس',['enabled','warehouse','supplier','contact_first_name','contact_last_name','contact_email','contact_mobile','status','actions']]]},
  preorders:{table:'#preordersTable',choices:'[data-preorder-column-choice]',attribute:'preorderColumn',preference:'automatic_preorders',apply:()=>applyPreorderColumnVisibility(),views:[
    ['review','بررسی سفارش',['status','warehouse','supplier','item_count','total_cartons','delivery_date','created_at','actions']],
    ['delivery','اطلاعات ارسال',['status','warehouse','supplier','preorder_number','contact','contact_email','delivery_date','documents','actions']]]},
  ordering:{table:'#orderingTable',choices:'[data-order-column-choice]',attribute:'orderColumn',choice:'orderColumnChoice',preference:'ordering',apply:()=>applyOrderingColumnVisibility(),views:[
    ['quantity','تصمیم مقدار',['product_code','product_name','manufacturer','group_level3','effective_procurement_qty','in_transit_qty','pending_receipt_qty','inventory_position_qty','average_daily_out','coverage_days','suggested_quantity','final_order_cartons']]]},
  supply:{table:'#supplyTable',choices:'[data-supply-column-choice]',attribute:'supplyColumn',preference:'supply_scope',apply:()=>applySupplyColumnVisibility(),views:[
    ['scope','تأمین‌کننده و برند',['enabled','warehouse','supplier','brand','product_count','evidence']]]},
  preview:{table:'.preview-lines-table',views:[
    ['quantity','تصمیم مقدار',['product_code','product_name','inventory_position_qty','coverage_days','system_suggested_cartons','final_order_cartons','order_quantity','estimated_value']],
    ['prices','بررسی قیمت',['product_code','product_name','manufacturer','group_level3','final_order_cartons','order_quantity','manufacturer_price','consumer_price','approximate_price','estimated_value']]]}
};
let previewWorkView='quantity';
function workViewColumns(key,viewId,available){
  const config=workViews[key];
  const preset=config?.views.find(([id])=>id===viewId);
  return viewId==='all'?[...available]:available.filter(column=>preset?.[2].includes(column));
}
function applyWorkView(key,viewId){
  const config=workViews[key],table=config&&$(config.table);if(!table)return;
  const wrap=table.closest('.table-wrap');if(wrap)rememberTableScroll(wrap);
  if(key==='preview'){
    previewWorkView=viewId;
    const visible=new Set(workViewColumns(key,viewId,previewColumnKeys));
    table.querySelectorAll('tr').forEach(row=>[...row.children].forEach((cell,index)=>cell.hidden=!visible.has(cell.dataset?.previewColumn||previewColumnKeys[index])));
    if(typeof columnLayouts!=='undefined'&&columnLayouts.tables.preview)columnLayouts.tables.preview.visible=[...visible];
  }else{
    const choices=[...document.querySelectorAll(config.choices)];
    const column=input=>config.choice?input.dataset[config.choice]:input.value;
    const visible=new Set(workViewColumns(key,viewId,choices.map(column)));
    if(!visible.size)return;
    choices.forEach(input=>input.checked=visible.has(column(input)));
    config.apply();
    if(key==='inventory')markInventoryViewEdited();
  }
  refreshWorkViewState(key);
  fitTableWrapsToViewport();
  if(wrap)restoreTableScroll(wrap);
}
function hiddenWorkViewFilters(table){
  return [...table.querySelectorAll('thead input, thead select')]
    .filter(input=>input.closest('th')?.hidden&&normalizeSearchText(input.value));
}
function refreshWorkViewState(key){
  const config=workViews[key],bar=document.querySelector(`[data-work-view-bar="${key}"]`),table=config&&$(config.table);
  if(!bar||!table)return;
  const headers=[...table.querySelectorAll('thead tr:first-child th')];
  const column=(th,index)=>key==='preview'?(th.dataset.previewColumn||previewColumnKeys[index]):th.dataset[config.attribute];
  const available=headers.map(column).filter(Boolean),visible=headers.filter(th=>!th.hidden).map(th=>column(th,headers.indexOf(th))).filter(Boolean);
  const equal=keys=>keys.length===visible.length&&keys.every(key=>visible.includes(key));
  let matched=false;
  bar.querySelectorAll('[data-work-view]').forEach(button=>{
    const selected=equal(workViewColumns(key,button.dataset.workView,available));
    button.setAttribute('aria-pressed',String(selected));matched ||= selected;
  });
  const hint=bar.querySelector('.work-view-custom');hint.hidden=matched;
  const filters=hiddenWorkViewFilters(table),clear=bar.querySelector('.work-view-hidden-filters');
  clear.hidden=!filters.length;
  const label=`پاک‌کردن ${fa(filters.length)} فیلترِ ستون پنهان`;
  if(clear.textContent!==label)clear.textContent=label;
}
function initializeWorkViews(){
  Object.entries(workViews).forEach(([key,config])=>{
    const table=$(config.table);if(!table||document.querySelector(`[data-work-view-bar="${key}"]`))return;
    const bar=document.createElement('div');bar.className='work-view-bar';bar.dataset.workViewBar=key;
    bar.setAttribute('role','group');bar.setAttribute('aria-label','نمای کاری جدول');
    bar.innerHTML=`<span class="work-view-label">نمای کاری</span>${[...config.views,['all','همه ستون‌ها']].map(([id,label])=>`<button type="button" data-work-view="${id}" aria-pressed="false">${label}</button>`).join('')}<span class="work-view-custom">طرح شخصی / سفارشی</span><button type="button" class="work-view-hidden-filters" hidden></button>`;
    table.closest('.table-wrap').before(bar);
    bar.addEventListener('click',event=>{
      const button=event.target.closest('[data-work-view]');if(button){applyWorkView(key,button.dataset.workView);return}
      if(event.target.closest('.work-view-hidden-filters')){
        hiddenWorkViewFilters(table).forEach(input=>{input.value='';input.dispatchEvent(new Event(input.tagName==='SELECT'?'change':'input',{bubbles:true}))});
        refreshWorkViewState(key);
      }
    });
    table.addEventListener('input',()=>refreshWorkViewState(key));
    table.addEventListener('change',()=>refreshWorkViewState(key));
    const hasSaved=key==='inventory'?state.inventoryViews.some(view=>view.is_default):Boolean(state.tablePreferences[config.preference]?.length);
    if(!hasSaved)applyWorkView(key,config.views[0][0]);else refreshWorkViewState(key);
  });
}

function expandableCellText(value,limit=38){
  const text=String(value??'');
  if(text.length<=limit)return esc(text);
  return `<details class="cell-text-details"><summary title="${esc(text)}" aria-label="نمایش متن کامل: ${esc(text)}">${esc(text)}</summary><span>${esc(text)}</span></details>`;
}

const tableScrollStorageKey="warehouse-assistant:table-scroll:v1";
let tableScrollState={};
try{tableScrollState=JSON.parse(sessionStorage.getItem(tableScrollStorageKey)||"{}")||{}}catch{tableScrollState={}}

function rememberTableScroll(wrap){
  if(wrap.dataset.restoringScroll==="true")return;
  const key=wrap.dataset.scrollKey;if(!key)return;
  tableScrollState[key]={left:wrap.scrollLeft,top:wrap.scrollTop};
  try{sessionStorage.setItem(tableScrollStorageKey,JSON.stringify(tableScrollState))}catch{}
}

function restoreTableScroll(wrap){
  const saved=tableScrollState[wrap.dataset.scrollKey];if(!saved)return;
  wrap.dataset.restoringScroll="true";
  requestAnimationFrame(()=>{
    wrap.scrollLeft=Number(saved.left)||0;
    wrap.scrollTop=Math.min(Number(saved.top)||0,Math.max(0,wrap.scrollHeight-wrap.clientHeight));
    requestAnimationFrame(()=>{delete wrap.dataset.restoringScroll;rememberTableScroll(wrap)});
  });
}

function replaceTableRows(container,markup){
  const wrap=container.closest(".table-wrap[data-scroll-key]");
  const saved=wrap?{left:wrap.scrollLeft,top:wrap.scrollTop}:null;
  container.innerHTML=markup;
  if(!wrap||!saved)return;
  tableScrollState[wrap.dataset.scrollKey]=saved;
  restoreTableScroll(wrap);
}

function initializeTableScrollPersistence(){
  document.querySelectorAll(".table-wrap[data-scroll-key]").forEach(wrap=>{
    if(wrap.dataset.scrollTracking)return;
    wrap.dataset.scrollTracking="true";
    wrap.addEventListener("scroll",()=>rememberTableScroll(wrap),{passive:true});
    restoreTableScroll(wrap);
  });
  window.addEventListener("pagehide",()=>document.querySelectorAll(".table-wrap[data-scroll-key]").forEach(rememberTableScroll),{once:true});
}

function toast(message,error=false){const element=$("#toast");element.textContent=message;element.className=`toast show${error?" error":""}`;clearTimeout(element.timer);element.timer=setTimeout(()=>element.className="toast",3500)}

async function api(path,options={}){
  const response=await fetch(path,{credentials:"same-origin",...options});
  let body=null;try{body=await response.json()}catch{body={detail:"پاسخ نامعتبر از سرویس دریافت شد."}}
  if(!response.ok)throw new ApiError(typeof body?.detail==="string"?body.detail:"ارتباط با سرویس انجام نشد.",response.status);
  return body;
}

function has(permission){return state.bootstrap?.capabilities?.includes(permission)}

function renderBootstrap(data){
  state.bootstrap=data;
  if($('#warehouseVersionNotice'))$('#warehouseVersionNotice').hidden=data.order_workflow_api_version>=1&&data.inventory_cycle_manual_exclusion_supported===true;
  if($('#smsSettingsButton'))$('#smsSettingsButton').hidden=!data.sms_settings_admin;
  $("#loginButton").hidden=true;$("#logoutButton").hidden=false;
  $("#userBadge").hidden=false;$("#userBadge").textContent=data.username;
  $("#accessMessage").hidden=true;
  const selectedOrderingWarehouse=$("#warehouseSelect").value;
  $("#warehouseSelect").innerHTML=data.warehouses.map(item=>`<option value="${esc(item.code)}">${esc(item.name)}</option>`).join("");
  if(data.warehouses.some(item=>item.code===selectedOrderingWarehouse))$("#warehouseSelect").value=selectedOrderingWarehouse;
  const automaticWarehouse=$("#automaticWarehouseSelect");
  const selectedAutomaticWarehouse=automaticWarehouse.value;
  automaticWarehouse.innerHTML='<option value="">همه انبارها</option>'+data.warehouses.map(item=>`<option value="${esc(item.code)}">${esc(item.name)}</option>`).join("");
  if(data.warehouses.some(item=>item.code===selectedAutomaticWarehouse))automaticWarehouse.value=selectedAutomaticWarehouse;
  const supplyWarehouse=$("#supplyWarehouseSelect");
  const selectedSupplyWarehouse=supplyWarehouse.value;
  supplyWarehouse.innerHTML=data.warehouses.map(item=>`<option value="${esc(item.code)}">${esc(item.name)}</option>`).join("");
  if(data.warehouses.some(item=>item.code===selectedSupplyWarehouse))supplyWarehouse.value=selectedSupplyWarehouse;
  const inventoryWarehouse=$("#inventoryWarehouseSelect");
  const selectedInventoryWarehouse=inventoryWarehouse.value;
  inventoryWarehouse.innerHTML='<option value="">همه</option>'+data.warehouses.map(item=>`<option value="${esc(item.name)}">${esc(item.name)}</option>`).join("");
  inventoryWarehouse.value=selectedInventoryWarehouse;
  const preorderWarehouse=$("#preorderWarehouseFilter");
  const selectedPreorderWarehouse=preorderWarehouse.value;
  preorderWarehouse.innerHTML='<option value="">همه انبارها</option>'+data.warehouses.map(item=>`<option value="${esc(item.code)}">${esc(item.name)}</option>`).join("");
  if(data.warehouses.some(item=>item.code===selectedPreorderWarehouse))preorderWarehouse.value=selectedPreorderWarehouse;
  const snapshot=data.latest_snapshot;
  $("#snapshotDate").textContent=snapshot?new Date(snapshot.imported_at).toLocaleString("fa-IR"):"—";
  $("#snapshotFile").textContent=snapshot?`${snapshot.source_filename}${snapshot.period_start?` · ${snapshot.period_start} تا ${snapshot.period_end}`:""} · توسط ${snapshot.imported_by}`:"هنوز داده‌ای دریافت نشده است";
  $("#productCount").textContent=snapshot?fa(snapshot.product_count):"۰";
  $("#snapshotForm").hidden=!has("warehouse.data.refresh");
  $("#inventoryDataTools").hidden=!has("warehouse.data.refresh");
  if($("#inventoryTaxRefresh"))$("#inventoryTaxRefresh").hidden=!has("warehouse.data.refresh");
  $("#varanegarSyncForm").hidden=!has("warehouse.data.refresh");
  if(snapshot?.period_days){$("#periodDays").value=snapshot.period_days;$("#syncPeriodDays").value=snapshot.period_days}
  $("#calculateButton").disabled=!snapshot||!has("warehouse.order.suggest");
  $("#previewAutomaticButton").disabled=!snapshot||!has("warehouse.order.suggest");
  $("#prepareAutomaticButton").disabled=!snapshot||!has("warehouse.order.draft");
  $("#manualRefreshPreordersButton").disabled=!snapshot||!has("warehouse.order.draft");
  $("#manualRefreshPreordersButton").hidden=!has("warehouse.order.draft");
  $("#refreshAutomaticPreordersButton").hidden=!has("warehouse.order.draft");
  $("#createOrderButton").hidden=!has("warehouse.order.draft");
  $("#orderFromInventoryButton").hidden=!has("warehouse.order.suggest");
  $("#refreshOrdersButton").hidden=!has("warehouse.order.draft");
  $("#refreshSupplyScopeButton").hidden=!has("warehouse.data.refresh");
}

async function start(){
  try{
    renderBootstrap(await api("/warehouse-assistant/api/bootstrap"));
    initializeInventoryColumns();
    initializeOrderingColumns();
    initializeAutomaticColumns();
    initializePreorderColumns();
    initializeSupplyColumns();
    await Promise.all([loadInventoryViews(true),loadTablePreferences()]);
    initializeWorkViews();
    if(typeof initializeColumnLayouts==='function')await initializeColumnLayouts();
    switchView(requestedWorkspaceView(),false);
    if(state.bootstrap.latest_snapshot){await Promise.all([loadInventory(true),loadOrderingCatalog(),loadAutomaticSettings(),loadSupplyScope()])}
    if(has("warehouse.order.draft")){
      await Promise.all([loadOrders(),loadAutomaticPreorders(),loadAutomaticRefreshStatus()]);
    }
    clearInterval(state.statusTimer);state.statusTimer=setInterval(()=>{if(!state.bootstrap)return;const tasks=[loadAutomaticRefreshStatus()];if(has("warehouse.order.draft"))tasks.push(loadOrders(),loadAutomaticPreorders());Promise.all(tasks)},60000);
  }catch(error){
    if(error.status===401){showLogin();return}
    const notice=$("#accessMessage");notice.hidden=false;notice.textContent=error.message;
    if(error.status===403){$("#loginButton").hidden=true;$("#logoutButton").hidden=false}
    toast(error.message,true);
  }
}

function showLogin(){
  state.inventoryRequest=(state.inventoryRequest||0)+1;
  if(typeof resetUnbilledReceipts==='function')resetUnbilledReceipts();
  if(typeof resetPurchaseInvoice==='function')resetPurchaseInvoice();
  if(typeof resetPurchaseContracts==='function')resetPurchaseContracts();
  if($('#smsSettingsButton'))$('#smsSettingsButton').hidden=true;
  if($('#smsSettingsDialog')?.open)$('#smsSettingsDialog').close();
  $("#loginButton").hidden=false;$("#logoutButton").hidden=true;$("#userBadge").hidden=true;
  if(!$("#loginDialog").open)$("#loginDialog").showModal();
  requestAnimationFrame(()=>$("#loginUsername").focus());
}

async function login(event){
  event.preventDefault();const errorElement=$("#loginError");errorElement.textContent="";
  const button=event.submitter||event.currentTarget.querySelector("button[type=submit]");button.disabled=true;
  try{
    const profile=await api("/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:$("#loginUsername").value.trim(),password:$("#loginPassword").value})});
    if(profile.must_change_password){errorElement.textContent="برای ادامه ابتدا رمز موقت را در دستیار اصلی تغییر دهید.";return}
    $("#loginPassword").value="";$("#loginDialog").close();await start();
  }catch(error){errorElement.textContent=error.message}finally{button.disabled=false}
}

async function logout(){
  invalidateOrderingSuggestions();
  await fetch("/auth/logout",{method:"POST",credentials:"same-origin"});
  if(typeof resetColumnLayouts==='function')resetColumnLayouts();
  clearInterval(state.statusTimer);state.statusTimer=null;state.bootstrap=null;state.suggestions=null;state.supplyRows=[];state.supplyMeta=null;state.automaticSettings=[];state.automaticPreview=null;state.automaticPreorders=[];state.automaticRefreshStatus=null;showLogin();
}

async function reloadWarehouseDataViews(){
  invalidateOrderingSuggestions();
  const tasks=[loadInventory(true),loadOrderingCatalog(),loadAutomaticSettings(),loadSupplyScope()];
  if(has("warehouse.order.draft"))tasks.push(loadAutomaticPreorders());
  tasks.push(loadAutomaticRefreshStatus());
  await Promise.all(tasks);
}

async function syncVaranegar(event){
  event.preventDefault();const periodDays=Number($("#syncPeriodDays").value);const button=$("#syncButton");
  button.disabled=true;button.textContent="در حال خواندن ورانگر...";
  try{
    const result=await api("/warehouse-assistant/api/sync/varanegar",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({period_days:periodDays})});
    toast(result.duplicate?"داده ورانگر تغییری نکرده است.":"موجودی و روند خروج از ورانگر دریافت شد.");
    invalidateOrderingSuggestions();state.automaticPreview=null;renderBootstrap(await api("/warehouse-assistant/api/bootstrap"));await reloadWarehouseDataViews();
  }catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent="دریافت موجودی و خروج از ورانگر"}
}

async function importSnapshot(event){
  event.preventDefault();const input=$("#snapshotFileInput");if(!input.files.length)return;
  const button=$("#importButton");button.disabled=true;button.textContent="در حال خواندن فایل...";
  const form=new FormData();form.append("file",input.files[0]);
  try{
    const result=await api("/warehouse-assistant/api/snapshots/import",{method:"POST",body:form});
    toast(result.duplicate?"این اطلاعات انبار قبلاً وارد شده بود.":"اطلاعات انبار با موفقیت وارد شد.");
    input.value="";invalidateOrderingSuggestions();state.automaticPreview=null;renderBootstrap(await api("/warehouse-assistant/api/bootstrap"));await reloadWarehouseDataViews();
  }catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent="ورود فایل پشتیبان"}
}

function renderOrderingBrands(){
  const manufacturer=$("#manufacturerFilter").value;
  const current=$("#brandFilter").value;
  let brands=[];
  if(manufacturer){
    brands=state.orderingCatalog.find(item=>item.name===manufacturer)?.brands||[];
  }else{
    const totals=new Map();
    state.orderingCatalog.forEach(item=>item.brands.forEach(brand=>totals.set(brand.name,(totals.get(brand.name)||0)+brand.product_count)));
    brands=[...totals].map(([name,product_count])=>({name,product_count})).sort((a,b)=>a.name.localeCompare(b.name,"fa"));
  }
  const select=$("#brandFilter");
  select.innerHTML='<option value="">همه نام‌های تجاری</option>'+brands.map(item=>`<option value="${esc(item.name)}">${esc(item.name)} (${fa(item.product_count)} کالا)</option>`).join("");
  select.disabled=!brands.length;
  if(brands.some(item=>item.name===current))select.value=current;
}

async function loadOrderingCatalog(){
  const warehouse=$("#warehouseSelect").value;
  const requestId=state.orderingCatalogRequest=(state.orderingCatalogRequest||0)+1;
  const result=await api(`/warehouse-assistant/api/catalog?warehouse=${encodeURIComponent(warehouse)}`);
  if(requestId!==state.orderingCatalogRequest||warehouse!==$("#warehouseSelect").value)return;
  state.orderingCatalog=result.manufacturers||[];
  const select=$("#manufacturerFilter");const current=select.value;
  select.innerHTML='<option value="">همه تولیدکننده‌ها</option>'+state.orderingCatalog.map(item=>`<option value="${esc(item.name)}">${esc(item.name)} (${fa(item.product_count)} کالا)</option>`).join("");
  if(state.orderingCatalog.some(item=>item.name===current))select.value=current;
  renderOrderingBrands();
}

async function loadTablePreferences(){
  const result=await api("/warehouse-assistant/api/table-preferences");
  state.tablePreferences=result.preferences||{};
  applySavedColumnPreference("ordering","[data-order-column-choice]");
  applySavedColumnPreference("automatic_settings","[data-auto-column-choice]");
  applySavedColumnPreference("automatic_preorders","[data-preorder-column-choice]");
  applySavedColumnPreference("supply_scope","[data-supply-column-choice]");
  applyOrderingColumnVisibility();applyAutomaticColumnVisibility();applyPreorderColumnVisibility();applySupplyColumnVisibility();
}

function applySavedColumnPreference(tableKey,selector){
  const saved=state.tablePreferences[tableKey];if(!saved?.length)return;
  const visible=new Set(saved);document.querySelectorAll(selector).forEach(input=>input.checked=visible.has(input.value));
}

async function persistColumnPreference(tableKey,visibleColumns){
  fitTableWrapsToViewport();
  try{
    const result=await api(`/warehouse-assistant/api/table-preferences/${tableKey}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({visible_columns:visibleColumns})});
    state.tablePreferences[tableKey]=result.visible_columns;
  }catch(error){toast(error.message,true)}
}

function initializeSupplyColumns(){
  if(state.supplyColumns.length)return;
  state.supplyColumns=[...document.querySelectorAll(".supply-heading-row th[data-supply-column]")].map(th=>({key:th.dataset.supplyColumn,title:th.textContent.trim()}));
  $("#supplyColumnChoices").innerHTML=state.supplyColumns.map(column=>`<label><input type="checkbox" data-supply-column-choice value="${esc(column.key)}" checked> ${esc(column.title)}</label>`).join("");
  document.querySelectorAll("[data-supply-column-choice]").forEach(input=>input.addEventListener("change",()=>{applySupplyColumnVisibility();persistColumnPreference("supply_scope",visibleSupplyColumns())}));
}

function visibleSupplyColumns(){const checked=[...document.querySelectorAll("[data-supply-column-choice]:checked")].map(input=>input.value);return checked.length?checked:state.supplyColumns.map(column=>column.key)}
function applySupplyColumnVisibility(){const visible=new Set(visibleSupplyColumns());document.querySelectorAll("#supplyTable [data-supply-column]").forEach(cell=>cell.hidden=!visible.has(cell.dataset.supplyColumn));const empty=$("#supplyRows .empty-cell");if(empty)empty.colSpan=Math.max(1,visible.size)}

function supplyFilterMatches(item){
  const sourceNames=(item.source_supplier_names||[]).join(" ");
  const global=normalizeSearchText($("#supplySearch").value);
  const haystack=normalizeSearchText(`${item.supplier} ${item.brand} ${sourceNames}`);
  if(global&&!haystack.includes(global))return false;
  const status=$("#supplyStatusFilter").value;
  if(status==="enabled"&&!item.enabled)return false;
  if(status==="disabled"&&item.enabled)return false;
  if(status==="observed"&&!item.observed_in_recent_receipts)return false;
  if(status==="manual"&&!item.is_user_override)return false;
  const evidence=item.observed_in_recent_receipts?"رسید ورانگر":"فاقد رسید اخیر";
  const values={supplier:item.supplier,brand:item.brand,product_count:item.product_count,receipt_count:item.receipt_count,receipt_quantity:item.receipt_quantity,last_receipt_date:item.last_receipt_date||"",evidence,updated_by:item.updated_by};
  return [...document.querySelectorAll("[data-supply-filter]")].every(input=>normalizeSearchText(values[input.dataset.supplyFilter]).includes(normalizeSearchText(input.value)));
}

function supplyBrandRow(item){
  const canEdit=has("warehouse.order.draft");
  const evidence=item.observed_in_recent_receipts?'<span class="scope-evidence observed">رسید تأییدشده ۹۰ روز</span>':'<span class="scope-evidence missing">بدون رسید اخیر</span>';
  const override=item.is_user_override?'<small class="manual-override">تنظیم دستی محفوظ</small>':"";
  const sourceNames=(item.source_supplier_names||[]).join("، ")||"—";
  return `<tr class="supply-brand-row"><td data-supply-column="enabled"><input class="supply-brand-toggle" data-supply-id="${item.id}" type="checkbox" ${item.enabled?"checked":""} ${canEdit?"":"disabled"} aria-label="فعال بودن برند ${esc(item.brand||"بدون برند")}"></td><td data-supply-column="warehouse"><span class="warehouse-chip">${esc(item.warehouse_name)}</span></td><td data-supply-column="supplier"><span class="supplier-indent">↳ ${esc(item.supplier)}</span></td><td data-supply-column="brand"><strong>${esc(item.brand||"بدون برند")}</strong></td><td data-supply-column="product_count">${fa(item.product_count)}</td><td data-supply-column="receipt_count">${fa(item.receipt_count)}</td><td data-supply-column="receipt_quantity">${fa(item.receipt_quantity)}</td><td data-supply-column="last_receipt_date" class="ltr-value">${esc(item.last_receipt_date||"—")}</td><td data-supply-column="evidence">${evidence}<small>${esc(sourceNames)}</small>${override}</td><td data-supply-column="updated_by">${esc(item.updated_by)}<small>${esc(new Date(item.updated_at).toLocaleString("fa-IR"))}</small></td></tr>`;
}

function renderSupplyScope(){
  const warehouse=$("#supplyWarehouseSelect").value;
  const rows=state.supplyRows.filter(item=>item.warehouse_code===warehouse);
  const visible=rows.filter(supplyFilterMatches);
  const groups=new Map();visible.forEach(item=>{if(!groups.has(item.supplier))groups.set(item.supplier,[]);groups.get(item.supplier).push(item)});
  const canEdit=has("warehouse.order.draft");
  const html=[...groups].map(([supplier,brands])=>{
    const allEnabled=brands.every(item=>item.enabled);const someEnabled=brands.some(item=>item.enabled);
    const supplierRow=`<tr class="supply-supplier-row"><td data-supply-column="enabled"><input class="supply-supplier-toggle" data-supply-supplier="${esc(supplier)}" type="checkbox" ${allEnabled?"checked":""} ${canEdit?"":"disabled"} aria-label="فعال بودن همه برندهای ${esc(supplier)}"></td><td data-supply-column="warehouse"><span class="warehouse-chip">${esc(brands[0].warehouse_name)}</span></td><td data-supply-column="supplier"><strong>${esc(supplier)}</strong><small>${fa(brands.length)} برند · ${someEnabled?fa(brands.filter(item=>item.enabled).length)+" فعال":"همه غیرفعال"}</small></td><td data-supply-column="brand"><span class="all-brands">همه برندها</span></td><td data-supply-column="product_count">${fa(brands.reduce((sum,item)=>sum+item.product_count,0))}</td><td data-supply-column="receipt_count">${fa(brands.reduce((sum,item)=>sum+item.receipt_count,0))}</td><td data-supply-column="receipt_quantity">${fa(brands.reduce((sum,item)=>sum+Number(item.receipt_quantity||0),0))}</td><td data-supply-column="last_receipt_date" class="ltr-value">${esc(brands.map(item=>item.last_receipt_date).filter(Boolean).sort().at(-1)||"—")}</td><td data-supply-column="evidence"><span class="scope-evidence group">کنترل یکجای تأمین‌کننده</span></td><td data-supply-column="updated_by">—</td></tr>`;
    return supplierRow+brands.map(supplyBrandRow).join("");
  }).join("");
  replaceTableRows($("#supplyRows"),html||'<tr><td colspan="10" class="empty-cell">ترکیبی با این فیلتر پیدا نشد.</td></tr>');
  document.querySelectorAll(".supply-supplier-toggle").forEach(input=>{const brands=visible.filter(item=>item.supplier===input.dataset.supplySupplier);input.indeterminate=brands.some(item=>item.enabled)&&!brands.every(item=>item.enabled)});
  applySupplyColumnVisibility();
  const activeRows=rows.filter(item=>item.enabled);const activeSuppliers=new Set(activeRows.map(item=>item.supplier));
  const meta=state.supplyMeta||{};
  $("#supplySummary").className="result-summary";
  $("#supplySummary").innerHTML=`<span>تأمین‌کننده فعال: <strong>${fa(activeSuppliers.size)}</strong></span><span>برند فعال: <strong>${fa(activeRows.length)}</strong></span><span>دارای رسید اخیر: <strong>${fa(rows.filter(item=>item.observed_in_recent_receipts).length)}</strong></span><span>تغییر دستی: <strong>${fa(rows.filter(item=>item.is_user_override).length)}</strong></span><span>بازه شاهد: <strong>${esc(meta.evidence_window_start||"—")} تا ${esc(meta.evidence_window_end||"—")}</strong></span>`;
}

async function loadSupplyScope(){
  const result=await api("/warehouse-assistant/api/supply-scope");
  state.supplyRows=result.rows||[];state.supplyMeta=result;renderSupplyScope();
}

async function refreshSupplyScope(){
  const button=$("#refreshSupplyScopeButton");button.disabled=true;button.textContent="در حال خواندن رسیدها...";
  try{const result=await api("/warehouse-assistant/api/supply-scope/refresh",{method:"POST"});invalidateOrderingSuggestions();await Promise.all([loadSupplyScope(),loadOrderingCatalog(),loadAutomaticSettings()]);toast(`${fa(result.observed_pairs)} ترکیب انبار، تأمین‌کننده و برند از رسیدهای اخیر شناسایی شد.`)}catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent="بازخوانی رسیدهای ۹۰ روز"}
}

async function saveSupplyScopeToggle(input){
  input.disabled=true;
  try{
    if(input.classList.contains("supply-supplier-toggle"))await api("/warehouse-assistant/api/supply-scope/supplier",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({warehouse:$("#supplyWarehouseSelect").value,supplier:input.dataset.supplySupplier,enabled:input.checked})});
    else await api(`/warehouse-assistant/api/supply-scope/${input.dataset.supplyId}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({enabled:input.checked})});
    invalidateOrderingSuggestions();await Promise.all([loadSupplyScope(),loadOrderingCatalog(),loadAutomaticSettings(),loadAutomaticPreorders()]);toast("دامنه تأمین ذخیره شد و سفارش‌های آماده قبلیِ مرتبط برای بازبینی باطل شدند.");
  }catch(error){toast(error.message,true);await loadSupplyScope()}
}

function automaticStatus(setting){
  const preview=state.automaticPreview?.suppliers?.find(item=>item.id===setting.id);
  if(!setting.enabled)return '<span class="auto-status is-disabled">غیرفعال</span>';
  if(!preview)return '<span class="auto-status">محاسبه نشده</span>';
  if(preview.readiness_status==="ready")return `<span class="auto-status is-ready">آماده فایل · ${fa(preview.suggested_cartons)} کارتن</span>`;
  if(preview.readiness_status==="below_minimum")return `<span class="auto-status is-waiting">${fa(preview.suggested_cartons)} کارتن · ${fa(preview.minimum_shortfall_cartons)} کارتن تا حداقل</span>`;
  return '<span class="auto-status">فعلاً نیاز به سفارش ندارد</span>';
}

function automaticRow(setting){
  const canEdit=has("warehouse.order.draft");
  const draft=state.automaticDrafts[setting.id];const values=draft?{...setting,...draft}:setting;
  return `<tr data-auto-id="${setting.id}" class="${draft?"auto-dirty":""}"><td data-auto-column="enabled"><input class="auto-enabled" type="checkbox" ${values.enabled?"checked":""} ${canEdit?"":"disabled"} aria-label="فعال بودن سفارش اتوماتیک ${esc(setting.supplier)}"></td><td data-auto-column="warehouse"><span class="warehouse-chip">${esc(setting.warehouse_name)}</span></td><td data-auto-column="supplier" class="auto-supplier"><div class="cell-name">${expandableCellText(setting.supplier)}</div><small>${draft?"تغییر ذخیره‌نشده":"آخرین تغییر: "+esc(setting.updated_by)}</small></td><td data-auto-column="product_count">${fa(setting.product_count)}</td><td data-auto-column="reorder_coverage_days"><span class="number-with-unit"><input class="auto-reorder" type="number" min="0" max="180" step="1" value="${values.reorder_coverage_days}" ${canEdit?"":"disabled"}><small>روز</small></span></td><td data-auto-column="target_days"><span class="number-with-unit"><input class="auto-target" type="number" min="1" max="180" step="1" value="${values.target_days}" ${canEdit?"":"disabled"}><small>روز</small></span></td><td data-auto-column="minimum_cartons"><span class="number-with-unit"><input class="auto-minimum" type="number" min="0" max="1000000" step="1" value="${values.minimum_cartons}" ${canEdit?"":"disabled"}><small>کارتن</small></span></td><td data-auto-column="contact_first_name"><input class="auto-first-name" maxlength="80" value="${esc(values.contact_first_name)}" placeholder="نام" ${canEdit?"":"disabled"}></td><td data-auto-column="contact_last_name"><input class="auto-last-name" maxlength="100" value="${esc(values.contact_last_name)}" placeholder="نام خانوادگی" ${canEdit?"":"disabled"}></td><td data-auto-column="contact_email"><input class="auto-email ltr-input" type="email" maxlength="254" value="${esc(values.contact_email)}" placeholder="name@company.com" ${canEdit?"":"disabled"}></td><td data-auto-column="contact_mobile"><input class="auto-mobile ltr-input" maxlength="30" value="${esc(values.contact_mobile)}" placeholder="09..." ${canEdit?"":"disabled"}></td><td data-auto-column="status">${draft?'<span class="auto-status is-waiting">ذخیره نشده</span>':automaticStatus(setting)}</td><td data-auto-column="actions"><button class="secondary-action auto-save" type="button" data-auto-save="${setting.id}" ${canEdit?"":"disabled"}>${draft?"ذخیره این ردیف":"ذخیره"}</button></td></tr>`;
}

function automaticFilterMatches(setting){
  setting={...setting,...(state.automaticDrafts[setting.id]||{})};
  const preview=state.automaticPreview?.suppliers?.find(item=>item.id===setting.id);
  const values={enabled:setting.enabled?"فعال":"غیرفعال",warehouse:setting.warehouse_name,supplier:setting.supplier,product_count:setting.product_count,reorder_coverage_days:setting.reorder_coverage_days,target_days:setting.target_days,minimum_cartons:setting.minimum_cartons,contact_first_name:setting.contact_first_name,contact_last_name:setting.contact_last_name,contact_email:setting.contact_email,contact_mobile:setting.contact_mobile,status:preview?.readiness_status||"محاسبه نشده"};
  return [...document.querySelectorAll("[data-auto-filter]")].every(input=>normalizeSearchText(values[input.dataset.autoFilter]).includes(normalizeSearchText(input.value)));
}

function renderAutomaticSettings(){
  const rows=$("#automaticRows");
  const selectedWarehouse=$("#automaticWarehouseSelect").value;
  const visibleSettings=state.automaticSettings.filter(item=>(!selectedWarehouse||item.warehouse_code===selectedWarehouse)&&automaticFilterMatches(item));
  replaceTableRows(rows,visibleSettings.length?visibleSettings.map(automaticRow).join(""):'<tr><td colspan="13" class="empty-cell">تنظیماتی با این فیلترها پیدا نشد.</td></tr>');
  applyAutomaticColumnVisibility();
  updateAutomaticSaveState();
  const dirtyCount=Object.keys(state.automaticDrafts).length;
  if(dirtyCount){
    $("#automaticSummary").className="result-summary unsaved-settings-notice";
    $("#automaticSummary").innerHTML=`<span><b>${fa(dirtyCount)} تغییر ذخیره‌نشده</b>؛ ابتدا «ذخیره تنظیمات» را بزنید، سپس پیش‌سفارش‌ها را بازسازی کنید.</span>`;
    return;
  }
  if(!state.automaticPreview){
    const defaults=state.automaticDefaults||{reorder_coverage_days:10,target_days:20};
    $("#automaticSummary").className="result-summary";
    $("#automaticSummary").innerHTML=`<span>تنظیمات نمایش‌داده‌شده: <strong>${fa(visibleSettings.length)}</strong></span><span>کل تنظیمات انبارها: <strong>${fa(state.automaticSettings.length)}</strong></span><span>پیش‌فرض شروع: <strong>زیر ${fa(defaults.reorder_coverage_days)} روز</strong></span><span>پیش‌فرض هدف: <strong>${fa(defaults.target_days)} روز</strong></span><span>حداقل پیش‌فرض: <strong>بدون محدودیت</strong></span>`;
    return;
  }
  const preview=state.automaticPreview;
  $("#automaticSummary").className="result-summary";
  $("#automaticSummary").innerHTML=`<span>انبار: <strong>${esc(preview.warehouse.name)}</strong></span><span>آماده عبور از حداقل: <strong>${fa(preview.ready_suppliers)}</strong></span><span>تأمین‌کننده فعال: <strong>${fa(preview.suppliers.filter(item=>item.enabled).length)}</strong></span><span>سند ساخته‌شده: <strong>خیر؛ فقط پیش‌نمایش</strong></span>`;
}

async function loadAutomaticSettings(){
  const result=await api("/warehouse-assistant/api/automatic-settings");
  state.automaticSettings=result.settings||[];
  state.automaticDrafts={};
  state.automaticDefaults=result.defaults||null;
  state.automaticPreview=null;
  renderAutomaticSettings();
}

function automaticPayload(row){
  return{
    enabled:row.querySelector(".auto-enabled").checked,
    reorder_coverage_days:Number(row.querySelector(".auto-reorder").value),
    target_days:Number(row.querySelector(".auto-target").value),
    minimum_cartons:Number(row.querySelector(".auto-minimum").value),
    contact_first_name:row.querySelector(".auto-first-name").value.trim(),
    contact_last_name:row.querySelector(".auto-last-name").value.trim(),
    contact_email:row.querySelector(".auto-email").value.trim(),
    contact_mobile:row.querySelector(".auto-mobile").value.trim()
  };
}

function automaticPayloadIsUnchanged(payload,setting){
  return ["enabled","reorder_coverage_days","target_days","minimum_cartons","contact_first_name","contact_last_name","contact_email","contact_mobile"].every(key=>payload[key]===setting[key]);
}

function updateAutomaticSaveState(){
  const count=Object.keys(state.automaticDrafts).length;const button=$("#saveAutomaticSettingsButton");
  if(button){button.disabled=!count||!has("warehouse.order.draft");button.textContent=count?`ذخیره تنظیمات (${fa(count)})`:"ذخیره تنظیمات"}
  const unavailable=!state.bootstrap?.latest_snapshot||!has("warehouse.order.draft");
  $("#prepareAutomaticButton").disabled=unavailable||count>0;$("#manualRefreshPreordersButton").disabled=unavailable||count>0;
  $("#previewAutomaticButton").disabled=!state.bootstrap?.latest_snapshot||!has("warehouse.order.suggest")||count>0;
}

function captureAutomaticDraft(row){
  const id=Number(row.dataset.autoId);const setting=state.automaticSettings.find(item=>item.id===id);if(!setting)return;
  const payload=automaticPayload(row);
  if(automaticPayloadIsUnchanged(payload,setting))delete state.automaticDrafts[id];else state.automaticDrafts[id]=payload;
  const dirty=Boolean(state.automaticDrafts[id]);state.automaticPreview=null;row.classList.toggle("auto-dirty",dirty);
  row.querySelector(".auto-supplier small").textContent=dirty?"تغییر ذخیره‌نشده":`آخرین تغییر: ${setting.updated_by}`;
  row.querySelector('[data-auto-column="status"]').innerHTML=dirty?'<span class="auto-status is-waiting">ذخیره نشده</span>':automaticStatus(setting);
  row.querySelector(".auto-save").textContent=dirty?"ذخیره این ردیف":"ذخیره";updateAutomaticSaveState();
  const dirtyCount=Object.keys(state.automaticDrafts).length;
  if(dirtyCount){$("#automaticSummary").className="result-summary unsaved-settings-notice";$("#automaticSummary").innerHTML=`<span><b>${fa(dirtyCount)} تغییر ذخیره‌نشده</b>؛ اطلاعات تماس بلافاصله پس از ذخیره اعمال می‌شود؛ تغییر شرایط سفارش نیازمند بازسازی است.</span>`}
  else renderAutomaticSettings();
}

function validateAutomaticPayload(payload){
  if(!Number.isInteger(payload.reorder_coverage_days)||!Number.isInteger(payload.target_days)||payload.target_days<=payload.reorder_coverage_days){toast("پوشش هدف باید عدد صحیح و بیشتر از کاوریج شروع سفارش باشد.",true);return}
  if(!Number.isInteger(payload.minimum_cartons)||payload.minimum_cartons<0){toast("حداقل سفارش باید تعداد صحیح و صفر یا بیشتر باشد.",true);return}
  return true;
}

async function saveAutomaticSettings(ids=null,sourceButton=null){
  const targetIds=(ids||Object.keys(state.automaticDrafts)).map(Number).filter(id=>state.automaticDrafts[id]);
  if(!targetIds.length){toast("تغییری برای ذخیره وجود ندارد.");return}
  if(targetIds.some(id=>!validateAutomaticPayload(state.automaticDrafts[id])))return;
  const button=sourceButton||$("#saveAutomaticSettingsButton");button.disabled=true;button.textContent="در حال ذخیره...";
  let savedCount=0;
  try{
    for(const id of targetIds){
      const saved=await api(`/warehouse-assistant/api/automatic-settings/${id}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(state.automaticDrafts[id])});
      state.automaticSettings=state.automaticSettings.map(item=>item.id===id?saved:item);delete state.automaticDrafts[id];savedCount+=1;
      // Refresh contacts/tokens only; never recalculate order quantities here.
      await loadAutomaticPreorders({strict:true});
    }
    state.automaticPreview=null;renderAutomaticSettings();toast(`${fa(savedCount)} تنظیم ذخیره شد؛ اطلاعات تماس سفارش‌های ارسال‌نشده به‌روز است. فقط تغییر شرایط سفارش نیازمند بازسازی است.`);
  }catch(error){renderAutomaticSettings();toast(savedCount?`${fa(savedCount)} مورد ذخیره شد؛ ادامه ذخیره متوقف شد: ${error.message}`:error.message,true)}
}

async function saveAutomaticSetting(button){
  const row=button.closest("tr");captureAutomaticDraft(row);await saveAutomaticSettings([Number(button.dataset.autoSave)],button);
}

async function previewAutomaticOrders(){
  if(Object.keys(state.automaticDrafts).length){toast("ابتدا تغییرات تنظیمات را ذخیره کنید، سپس وضعیت سفارش‌ها را محاسبه کنید.",true);return}
  const warehouseSelect=$("#automaticWarehouseSelect");
  const selectedWarehouse=warehouseSelect.value;
  const warehouses=selectedWarehouse?[selectedWarehouse]:(state.bootstrap?.warehouses||[]).map(item=>item.code);
  warehouseSelect.disabled=true;
  const button=$("#previewAutomaticButton");button.disabled=true;button.textContent="در حال محاسبه...";
  try{
    const previews=await Promise.all(warehouses.map(code=>api(`/warehouse-assistant/api/automatic-settings/preview/${encodeURIComponent(code)}`)));
    state.automaticPreview=selectedWarehouse?previews[0]:{
      warehouse:{code:"",name:"همه انبارها"},
      suppliers:previews.flatMap(preview=>preview.suppliers),
      ready_suppliers:previews.reduce((sum,preview)=>sum+preview.ready_suppliers,0),
      documents_created:false,varanegar_write:false
    };
    renderAutomaticSettings();toast("وضعیت سفارش اتوماتیک تأمین‌کننده‌ها محاسبه شد.");
  }
  catch(error){toast(error.message,true)}finally{warehouseSelect.disabled=false;button.textContent="محاسبه وضعیت سفارش‌ها";updateAutomaticSaveState()}
}

function preorderStatus(preorder){
  const portal=preorder.supplier_portal;
  if(portal){
    const workflow=portal.workflow_status||portal.status;
    const portalLabels={awaiting_link:"آمادهٔ قرار دادن در کارتابل",awaiting_supplier:"در انتظار واکنش تأمین‌کننده",draft:"در حال تکمیل پاسخ تأمین‌کننده",supplier_confirmed:"تأییدشده با تأمین‌کننده",awaiting_negin:"منتظر تأیید نگین",changes_requested:"در انتظار اصلاح تأمین‌کننده",awaiting_delivery:"در انتظار تحویل سفارش",rejected:"پاسخ تأمین‌کننده رد شد",cancelled:"لغوشده"};
    const cls=["supplier_confirmed","awaiting_delivery"].includes(workflow)?"approved":"waiting";
    return `<span class="preorder-status ${cls}" title="تحویل درخواستی: ${esc(portal.requested_delivery_date||'—')} · پیشنهاد تأمین‌کننده: ${esc(portal.proposed_delivery_date||'—')}">${esc(portalLabels[workflow]||workflow)}</span>`;
  }
  if(preorder.status==="awaiting_approval")return '<span class="preorder-status waiting">منتظر تأیید کاربر</span>';
  const delivery=preorder.email_delivery;
  if(delivery){
    const labels={sent:"ایمیل ارسال شد",failed:"ارسال ناموفق · تلاش مجدد",sending:"ارسال در جریان · در توقف طولانی بررسی شود",unknown:"نتیجه ارسال نامشخص · نیازمند بررسی"};
    return `<span class="preorder-status ${delivery.status==="sent"?"approved":"waiting"}" title="${esc([delivery.recipient,delivery.completed_at||delivery.started_at,delivery.error].filter(Boolean).join(' · '))}">${esc(labels[delivery.status]||delivery.status)}</span>`;
  }
  if(preorder.status==="approved")return '<span class="preorder-status approved">آمادهٔ قرار دادن در کارتابل</span>';
  return '<span class="preorder-status requested">دستور ارسال ثبت شده</span>';
}

function renderAutomaticPreorders(preorders=state.automaticPreorders){
  preorders=preorders.filter(order=>!order.order_stage||order.order_stage==='draft');
  state.automaticPreorders=preorders;
  const container=$("#automaticPreordersList");
  const warehouse=$("#preorderWarehouseFilter").value;const status=$("#preorderStatusFilter").value;
  const filters={};document.querySelectorAll("[data-preorder-filter]").forEach(input=>filters[input.dataset.preorderFilter]=normalizeSearchText(input.value));
  const visible=preorders.filter(preorder=>{
    if(warehouse&&preorder.warehouse_code!==warehouse)return false;if(status&&preorder.status!==status)return false;
    const values={delivery_date:preorder.delivery_date||preorder.requested_delivery_date,supplier:preorder.supplier,preorder_number:preorder.preorder_number,item_count:preorder.item_count,total_cartons:preorder.total_cartons,reorder_coverage_days:preorder.reorder_coverage_days,target_days:preorder.target_days,contact:preorder.contact_full_name,contact_email:preorder.contact_email,created_at:formatRefreshDate(preorder.last_refreshed_at||preorder.created_at)};
    return Object.entries(filters).every(([key,value])=>!value||normalizeSearchText(values[key]).includes(value));
  });
  const awaiting=preorders.filter(item=>item.status==="awaiting_approval").length;
  updatePreparedOrderCounts();
  $("#preordersSummary").className="result-summary";$("#preordersSummary").innerHTML=`<span>کل صف فعال: <strong>${fa(preorders.length)}</strong></span><span>منتظر تأیید: <strong>${fa(awaiting)}</strong></span><span>نمایش با فیلتر فعلی: <strong>${fa(visible.length)}</strong></span>`;
  if(!visible.length){replaceTableRows(container,'<tr><td colspan="14" class="empty-cell">با این فیلتر پیش‌سفارشی وجود ندارد.</td></tr>');applyPreorderColumnVisibility();return}
  replaceTableRows(container,visible.map(preorder=>{
    const contact=preorder.contact_full_name||"مسئول ثبت نشده";
    
    
    return `<tr><td data-preorder-column="status">${preorderStatus(preorder)}</td><td data-preorder-column="warehouse"><span class="warehouse-chip">${esc(preorder.warehouse_name)}</span></td><td data-preorder-column="supplier" class="preorder-supplier"><div class="cell-name">${expandableCellText(preorder.supplier)}</div><small>${esc(preorder.contact_mobile||"")}</small></td><td data-preorder-column="preorder_number" class="ltr-value">${esc(preorder.preorder_number)}</td><td data-preorder-column="item_count">${fa(preorder.item_count)}</td><td data-preorder-column="total_cartons" class="quantity">${fa(preorder.total_cartons)}</td><td data-preorder-column="reorder_coverage_days">زیر ${fa(preorder.reorder_coverage_days)} روز</td><td data-preorder-column="target_days">${fa(preorder.target_days)} روز</td><td data-preorder-column="contact">${esc(contact)}</td><td data-preorder-column="contact_email" class="ltr-value">${esc(preorder.contact_email||"ثبت نشده")}</td><td data-preorder-column="created_at">${esc(formatRefreshDate(preorder.last_refreshed_at||preorder.created_at))}</td><td data-preorder-column="delivery_date">${orderDeliveryDateCell(preorder)}</td><td data-preorder-column="documents"><div class="preorder-documents"><a href="/warehouse-assistant/api/automatic-preorders/${preorder.id}/document.xlsx">Excel</a><a href="/warehouse-assistant/api/automatic-preorders/${preorder.id}/document.txt">متن</a></div></td><td data-preorder-column="actions"><div class="preorder-actions"><button class="secondary-action preorder-preview-button" type="button" data-preorder-action="preview" data-preorder-id="${preorder.id}">مشاهده اقلام</button>${draftOrderActions(preorder,"automatic_preorder")}</div></td></tr>`;
  }).join(""));applyPreorderColumnVisibility();
}

function currentPreviewPreorder(){return state.automaticPreorders.find(item=>item.id===state.previewPreorderId)}

function previewDataValue(value,unit,emptyLabel="داده موجود نیست"){
  if(value===null||value===undefined)return `<span class="preview-data-value is-empty">—<small>${emptyLabel}</small></span>`;
  return `<span class="preview-data-value">${fa(value)}<small>${unit}</small></span>`;
}

function demandAuditNote(item,{inventory=false}={}){
  const exceptional=Number(item.exceptional_period_out_qty??item.exceptional_period_out??0);
  const amiran=Number(item.amiran_period_out_qty??item.amiran_period_out??0);
  const onlineTransfer=Number(item.online_transfer_out_qty??item.online_transfer_out??0);
  const raw=Number(item.raw_period_out_qty??item.raw_period_out??0);
  const adjusted=Number(item.period_out_qty??item.adjusted_period_out??item.period_out??0);
  const anomalyDays=Number(item.demand_anomaly_days||0);
  const recurring=Boolean(item.demand_recurring_pattern);
  const recurringDays=Number(item.demand_recurring_pattern_days||0);
  const days=Number(item.sales_rate_days||0);
  const sales=raw||Number(item.gross_out_qty??item.gross_out??adjusted??0);
  const notes=[`${fa(days)} روز موجود · فروش ${fa(sales)} عدد`];
  const adjustment=[];
  if(exceptional>0)adjustment.push(`حذف هیجانی ${fa(exceptional)} عدد${anomalyDays>0?` (${fa(anomalyDays)} روز هیجانی)`:''}`);
  adjustment.push(`مبنای محاسبه ${fa(adjusted)} عدد`);
  notes.push(adjustment.join(' · '));
  if(recurring)notes.push(`${fa(recurringDays)} روز پرتکرار؛ الگوی عادی کالا محسوب شد`);
  if(amiran>0)notes.push(`امیران ${fa(amiran)} کامل لحاظ شد`);
  if(onlineTransfer>0)notes.push(`انتقال آنلاین ${fa(onlineTransfer)} کامل لحاظ شد`);
  if(inventory&&Number(item.period_return_qty||0)>0)notes.push(`برگشت فروش ${fa(item.period_return_qty)} عدد`);
  const classes=`demand-audit-note${exceptional>0?" has-adjustment":""}${amiran>0?" has-amiran":""}${recurring?" is-recurring":""}`;
  return `<details class="demand-audit-details"><summary aria-label="خلاصه محاسبه خروج روزانه">${exceptional>0?'تعدیل فروش':'محاسبه'}</summary><span class="${classes}" data-export-value="${esc(demandAuditExportValue(item,item.average_daily_out??null))}">${notes.map(note=>`<span>${note}</span>`).join('')}</span></details>`;
}

function demandAuditExportValue(item,dailyOut=null){
  const days=Number(item.sales_rate_days||0);
  const raw=Number(item.raw_period_out_qty??item.raw_period_out??item.gross_out_qty??item.gross_out??item.period_out_qty??item.adjusted_period_out??item.period_out??0);
  const adjusted=Number(item.period_out_qty??item.adjusted_period_out??item.period_out??raw);
  const exceptional=Number(item.exceptional_period_out_qty??item.exceptional_period_out??0);
  const values=[];
  if(dailyOut!==null&&dailyOut!==undefined)values.push(`روزانه ${fa(dailyOut)} عدد`);
  values.push(`${fa(days)} روز موجود`,`فروش ${fa(raw)} عدد`);
  if(exceptional>0)values.push(`حذف هیجانی ${fa(exceptional)} عدد`);
  values.push(`مبنا ${fa(adjusted)} عدد`);
  return values.join('؛ ');
}

function previewPreorderLine(line,editable){
  let columnIndex=0;
  const remove=editable?`<button type="button" class="preview-remove-line secondary-action danger-action" data-preview-remove aria-label="حذف ${esc(line.product_name)} از سفارش">حذف قلم</button>`:"";
  return `<tr data-product-code="${esc(line.product_code)}" data-conversion="${Number(line.conversion_rate)}" data-approximate-price="${Number(line.approximate_price)}" data-original-cartons="${Number(line.cartons)}"><td class="product-code">${esc(line.product_code)}</td><td><div class="product-cell"><div class="cell-name">${expandableCellText(line.product_name)}</div></div></td><td>${esc(line.brand||"—")}</td><td>${previewDataValue(line.physical_procurement_qty,"عدد")}</td><td>${previewDataValue(line.in_transit_qty,"عدد")}</td><td>${previewDataValue(line.pending_receipt_qty,"عدد")}</td><td>${previewDataValue(line.inventory_position_qty,"عدد")}</td><td data-export-value="${esc(demandAuditExportValue(line,line.average_daily_out))}">${previewDataValue(line.average_daily_out,"عدد/روز")}${demandAuditNote(line)}</td><td>${previewDataValue(line.coverage_days,"روز","خروج روزانه ثبت نشده")}</td><td><span class="system-suggestion unadjusted-suggestion">${fa(line.unadjusted_suggested_cartons??line.system_suggested_cartons??line.cartons)} کارتن</span></td><td><span class="system-suggestion">${fa(line.system_suggested_cartons??line.cartons)} کارتن</span></td><td><div class="quantity-editor"><input title="تعداد نهایی به کارتن؛ صفر یعنی حذف" class="preview-cartons" type="number" min="0" max="1000000" step="1" value="${Number(line.cartons)}" ${editable?"":"disabled"} aria-label="تعداد نهایی کارتن ${esc(line.product_name)}">${remove}</div></td><td class="preview-quantity">${fa(line.order_quantity)}</td><td>${fa(line.manufacturer_price)}</td><td>${fa(line.consumer_price)}</td><td>${fa(line.approximate_price)}</td><td class="preview-value">${fa(line.estimated_value)}</td><td>${esc(line.manufacturer_product_code||'—')}</td><td>${esc(line.barcode||'—')}</td><td>${expandableCellText(line.manufacturer||'—')}</td><td>${fa(line.conversion_rate)}</td><td>${groupLevel3Cell(line.group_level3)}</td></tr>`.replace(/<td(?=[ >])/g,()=>`<td data-preview-column="${previewColumnKeys[columnIndex++]}"`);
}

function updatePreviewTotals(){
  const preorder=currentPreviewPreorder();if(!preorder)return;
  let totalCartons=0,totalQuantity=0,totalValue=0;
  document.querySelectorAll("#previewPreorderLines tr").forEach(row=>{
    const input=row.querySelector(".preview-cartons");const cartons=Math.max(0,Number(input.value)||0);const conversion=Number(row.dataset.conversion)||1;const approximatePrice=Number(row.dataset.approximatePrice)||0;const quantity=cartons*conversion;const value=quantity*approximatePrice;
    totalCartons+=cartons;totalQuantity+=quantity;totalValue+=value;row.querySelector(".preview-quantity").textContent=fa(quantity);row.querySelector(".preview-value").textContent=fa(value);row.classList.toggle("preview-row-changed",cartons!==Number(row.dataset.originalCartons));row.classList.toggle("preview-row-removed",cartons===0);
  });
  const suggested=preorder.lines.reduce((sum,line)=>sum+Number(line.system_suggested_cartons??line.cartons),0);
  const unadjusted=preorder.lines.reduce((sum,line)=>sum+Number(line.unadjusted_suggested_cartons??line.system_suggested_cartons??line.cartons),0);
  $("#previewPreorderSummary").innerHTML=`<span>اقلام<strong>${fa(document.querySelectorAll("#previewPreorderLines tr").length)}</strong></span><span>بدون تعدیل هیجان<strong>${fa(unadjusted)} کارتن</strong></span><span>پیشنهاد سیستم<strong>${fa(suggested)} کارتن</strong></span><span>جمع نهایی<strong>${fa(totalCartons)} کارتن · ${fa(totalQuantity)} عدد</strong></span><span>ارزش تخمینی<strong>${fa(totalValue)}</strong></span>`;
  $("#savePreorderPreviewButton").disabled=preorder.status!=="awaiting_approval"||totalCartons<1||[...document.querySelectorAll(".preview-cartons")].some(input=>!Number.isInteger(Number(input.value))||Number(input.value)<0);
}

function openPreorderPreview(id){
  const preorder=state.automaticPreorders.find(item=>item.id===id);if(!preorder)return;
  state.previewPreorderId=id;const editable=preorder.can_edit&&preorder.status==="awaiting_approval";
  state.previewExpectedToken=preorder.email_send_token;
  if($('#previewDeliveryDate')){$('#previewDeliveryDate').value=preorder.delivery_date||'';$('#previewDeliveryDate').disabled=!preorder.can_edit_delivery_date;$('#previewDeliverySave').disabled=!preorder.can_edit_delivery_date;$('#previewDeliverySave').hidden=Boolean(editable)||!preorder.can_edit_delivery_date}
  if(typeof resetPreorderCatalog==='function')resetPreorderCatalog(preorder);
  $("#previewPreorderTitle").textContent=preorder.supplier;$("#previewPreorderSubtitle").textContent=`${preorder.warehouse_name} · ${preorder.preorder_number}`;
  replaceTableRows($("#previewPreorderLines"),preorder.lines.map(line=>previewPreorderLine(line,editable)).join(""));
  $("#savePreorderPreviewButton").hidden=!editable;$("#previewEditAudit").textContent=editable?"قبل از تأیید می‌توانید تعدادها را اصلاح کنید.":`این سفارش ${preorder.status==="approved"?"تأیید شده":"در صف ارسال است"} و ویرایش آن قفل شده است.`;
  updatePreviewTotals();if(!$("#preorderPreviewDialog").open)$("#preorderPreviewDialog").showModal();fitTableWrapsToViewport();
  if(previewWorkView==='custom'&&typeof applyColumnOrder==='function')applyColumnOrder('preview');else applyWorkView('preview',previewWorkView);
  beginDraftEditor('automatic_preorder',{dateOnly:!editable});
}

function closePreorderPreview(){requestDraftEditorClose('automatic_preorder',()=>{if($("#preorderPreviewDialog").open)$("#preorderPreviewDialog").close();state.previewPreorderId=null})}

async function savePreorderPreview(){
  const preorder=currentPreviewPreorder();if(!preorder)return;
  const lines=[...document.querySelectorAll("#previewPreorderLines tr")].map(row=>({product_code:row.dataset.productCode,cartons:Number(row.querySelector(".preview-cartons").value)}));
  if(lines.some(line=>!Number.isInteger(line.cartons)||line.cartons<0)||!lines.some(line=>line.cartons>0)){toast("تعداد باید عدد صحیح و صفر یا بیشتر باشد؛ حداقل یک قلم باید در سفارش باقی بماند.",true);return}
  const button=$("#savePreorderPreviewButton");button.disabled=true;button.textContent="در حال ذخیره...";
  try{
    const updated=await saveDraftEditor('automatic_preorder',preorder);
    state.automaticPreorders=state.automaticPreorders.map(item=>item.id===preorder.id?updated:item);renderAutomaticPreorders();openPreorderPreview(preorder.id);$('#previewDeliveryFeedback').textContent='تاریخ و تعدادها ذخیره شد.';toast("تاریخ و تعدادهای نهایی ذخیره شد.");
  }catch(error){$('#previewDeliveryFeedback').textContent=error.message;toast(error.message,true)}finally{button.textContent="ذخیره تغییرات";button.disabled=false}
}

async function loadAutomaticPreorders({strict=false}={}){
  try{const result=await api("/warehouse-assistant/api/automatic-preorders");renderAutomaticPreorders(result.preorders||[]);await loadFulfillmentOrders()}
  catch(error){if(strict)throw error;toast(error.message,true)}
}

function formatRefreshDate(value){const date=new Date(value);return value&&Number.isFinite(date.getTime())?date.toLocaleString("fa-IR"):"—"}

function renderAutomaticRefreshStatus(){
  const status=state.automaticRefreshStatus;const box=$("#automaticRefreshStatus");if(!status){box.textContent="وضعیت اجرای ساعتی در دسترس نیست.";return}
  const lastResult=status.last_result||{};
  if(status.running){box.className="automatic-refresh-status is-running";box.innerHTML='<b>در حال به‌روزرسانی خودکار سفارش‌ها…</b><span>موجودی ورانگر و همه شرایط تأمین‌کننده‌ها دوباره محاسبه می‌شوند.</span>';return}
  box.className=`automatic-refresh-status${status.last_error?" has-error":""}`;
  box.innerHTML=`<span><b>اجرای خودکار:</b> هر یک ساعت</span><span><b>آخرین اجرای موفق:</b> ${esc(formatRefreshDate(status.last_success_at))}</span><span><b>اجرای بعدی:</b> ${esc(formatRefreshDate(status.next_run_at))}</span><span><b>نتیجه آخر:</b> ${fa(lastResult.created_count||0)} جدید · ${fa(lastResult.updated_count||0)} به‌روزشده · ${fa(lastResult.removed_count||0)} حذف‌شده از صف</span>${status.last_error?`<span class="refresh-error"><b>خطای آخر:</b> ${esc(status.last_error)}</span>`:""}`;
}

async function loadAutomaticRefreshStatus(){
  try{state.automaticRefreshStatus=await api("/warehouse-assistant/api/automatic-preorders/refresh-status");renderAutomaticRefreshStatus()}catch(error){if(error.status!==403)toast(error.message,true)}
}

async function prepareAutomaticPreorders(quiet=false,sourceButton=null){
  if(Object.keys(state.automaticDrafts).length){switchView("automatic");toast("ابتدا تغییرات تنظیمات را ذخیره کنید، سپس پیش‌سفارش‌ها را بازسازی کنید.",true);return}
  const buttons=[$("#prepareAutomaticButton"),$("#manualRefreshPreordersButton")].filter(Boolean);
  const button=sourceButton||$("#prepareAutomaticButton");
  buttons.forEach(item=>item.disabled=true);
  if(!quiet)button.textContent="در حال به‌روزرسانی همه سفارش‌ها...";
  try{
    const result=await api("/warehouse-assistant/api/automatic-preorders/run",{method:"POST"});
    if(result.skipped){if(!quiet)toast("یک به‌روزرسانی دیگر در حال اجراست؛ پس از پایان، صف تازه می‌شود.");return}
    renderAutomaticPreorders(result.preorders||[]);state.automaticRefreshStatus=result.refresh_status;renderAutomaticRefreshStatus();
    if(!quiet)toast(`${fa(result.created_count)} جدید، ${fa(result.updated_count)} به‌روزشده و ${fa(result.removed_count)} پیشنهاد بدون نیاز از صف حذف شد.`);
  }catch(error){if(!quiet)toast(error.message,true);await loadAutomaticRefreshStatus()}finally{
    const disabled=!state.bootstrap?.latest_snapshot||!has("warehouse.order.draft");
    buttons.forEach(item=>item.disabled=disabled);
    $("#prepareAutomaticButton").textContent="بازسازی دستی همه پیش‌سفارش‌ها";
    $("#manualRefreshPreordersButton").textContent="به‌روزرسانی دستی سفارش‌های اتوماتیک";
    updateAutomaticSaveState();
  }
}

async function automaticPreorderAction(button){
  const id=Number(button.dataset.preorderId);const action=button.dataset.preorderAction;
  button.disabled=true;
  try{
    let preorder=state.automaticPreorders.find(item=>item.id===id);
    if(action==='approve'&&!window.confirm('این پیش‌سفارش تأیید شود؟ قرار دادن در کارتابل مرحله‌ای جداگانه است؛ اکنون پیامکی یا ایمیلی ارسال نمی‌شود.')){button.disabled=false;return}
    if(action==="send-email"){
      const fresh=await api(`/warehouse-assistant/api/automatic-preorders/${id}`);
      preorder=fresh.preorder;
      state.automaticPreorders=state.automaticPreorders.map(item=>item.id===id?preorder:item);
      if(!window.confirm(`فایل اکسل سفارش ${preorder.preorder_number}\nتأمین‌کننده: ${preorder.supplier}\nگیرنده: ${preorder.contact_email}\nتلفن: ${preorder.contact_mobile||"ثبت نشده"}\nجمع: ${fa(preorder.total_cartons)} کارتن\n\nهم‌اکنون ایمیل ارسال شود؟`)){button.disabled=false;renderAutomaticPreorders();return}
    }
    if(action==="revoke-approval"&&!window.confirm(`تأیید سفارش ${preorder.preorder_number} لغو شود؟\nاقلام حفظ می‌شوند و سفارش دوباره قابل ویرایش خواهد بود.`)){button.disabled=false;return}
    if(action==="delete"&&!window.confirm(`سفارش ${preorder.preorder_number} از صف آماده حذف شود؟\nسابقه حفظ می‌شود؛ بازسازی بعدی می‌تواند دوباره آن را آماده کند.`)){button.disabled=false;return}
    const result=await api(`/warehouse-assistant/api/automatic-preorders/${id}/${action}`,{method:"POST",...(action==="send-email"?{headers:{"Content-Type":"application/json"},body:JSON.stringify({expected_token:preorder.email_send_token})}:{})});
    state.automaticPreorders=state.automaticPreorders.map(item=>item.id===id?result.preorder:item);
    if(action==='delete'||result.send_status==='sent')state.automaticPreorders=state.automaticPreorders.filter(item=>item.id!==id);
    renderAutomaticPreorders();
    if(state.previewPreorderId===id){if(action==='delete'||result.send_status==='sent')closePreorderPreview();else openPreorderPreview(id)}
    if(action==='delete'){toast('از صف آماده حذف شد؛ در بازسازی بعدی دوباره قابل آماده‌سازی است.');return}
    if(result.send_status==='sent')await loadFulfillmentOrders();
    if(action==="revoke-approval"){toast("تأیید لغو شد؛ سفارش قابل ویرایش است و پیش از ارسال باید دوباره تأیید شود.");return}
    toast(action==="approve"?"پیش‌سفارش تأیید شد؛ اکنون می‌توانید آن را در کارتابل تأمین‌کننده قرار دهید.":result.send_status==="sent"?(result.already_sent?"این سفارش قبلاً ایمیل شده؛ دوباره ارسال نشد.":"ایمیل و فایل اکسل به سرور ارسال تحویل شد؛ دریافت توسط تأمین‌کننده هنوز تأیید نشده است."):(result.preorder?.email_delivery?.error||"نتیجه ارسال نیازمند بررسی است."),action==="send-email"&&result.send_status!=="sent");
  }catch(error){
    toast(action==="send-email"?`${error.message} قبل از تلاش مجدد، صف را بازخوانی کنید.`:error.message,true);
    if(action!=="send-email")button.disabled=false;
  }
}

function initializeOrderingColumns(){
  if(state.orderingColumns.length)return;
  state.orderingColumns=[...document.querySelectorAll(".ordering-heading-row th[data-order-column]")].map(th=>({key:th.dataset.orderColumn,title:th.textContent.trim()}));
  $("#orderingColumnChoices").innerHTML=state.orderingColumns.map(column=>`<label><input type="checkbox" data-order-column-choice="${esc(column.key)}" checked> ${esc(column.title)}</label>`).join("");
  document.querySelectorAll("[data-order-column-choice]").forEach(input=>input.addEventListener("change",()=>{applyOrderingColumnVisibility();persistColumnPreference("ordering",visibleOrderingColumns())}));
}

function initializeAutomaticColumns(){
  if(state.automaticColumns.length)return;state.automaticColumns=[...document.querySelectorAll(".automatic-heading-row th[data-auto-column]")].map(th=>({key:th.dataset.autoColumn,title:th.textContent.trim()}));
  $("#automaticColumnChoices").innerHTML=state.automaticColumns.map(column=>`<label><input type="checkbox" data-auto-column-choice value="${esc(column.key)}" checked> ${esc(column.title)}</label>`).join("");
  document.querySelectorAll("[data-auto-column-choice]").forEach(input=>input.addEventListener("change",()=>{applyAutomaticColumnVisibility();persistColumnPreference("automatic_settings",visibleAutomaticColumns())}));
}
function visibleAutomaticColumns(){const checked=[...document.querySelectorAll("[data-auto-column-choice]:checked")].map(input=>input.value);return checked.length?checked:state.automaticColumns.map(column=>column.key)}
function applyAutomaticColumnVisibility(){const visible=new Set(visibleAutomaticColumns());document.querySelectorAll("#automaticTable [data-auto-column]").forEach(cell=>cell.hidden=!visible.has(cell.dataset.autoColumn));const empty=$("#automaticRows .empty-cell");if(empty)empty.colSpan=Math.max(1,visible.size)}

function initializePreorderColumns(){
  if(state.preorderColumns.length)return;state.preorderColumns=[...document.querySelectorAll(".preorder-heading-row th[data-preorder-column]")].map(th=>({key:th.dataset.preorderColumn,title:th.textContent.trim()}));
  $("#preorderColumnChoices").innerHTML=state.preorderColumns.map(column=>`<label><input type="checkbox" data-preorder-column-choice value="${esc(column.key)}" checked> ${esc(column.title)}</label>`).join("");
  document.querySelectorAll("[data-preorder-column-choice]").forEach(input=>input.addEventListener("change",()=>{applyPreorderColumnVisibility();persistColumnPreference("automatic_preorders",visiblePreorderColumns())}));
}
function visiblePreorderColumns(){const checked=[...document.querySelectorAll("[data-preorder-column-choice]:checked")].map(input=>input.value);return checked.length?checked:state.preorderColumns.map(column=>column.key)}
function applyPreorderColumnVisibility(){const visible=new Set(visiblePreorderColumns());document.querySelectorAll("#preordersTable [data-preorder-column]").forEach(cell=>cell.hidden=!visible.has(cell.dataset.preorderColumn));const empty=$("#automaticPreordersList .empty-cell");if(empty)empty.colSpan=Math.max(1,visible.size)}

function visibleOrderingColumns(){
  const checked=[...document.querySelectorAll("[data-order-column-choice]:checked")].map(input=>input.dataset.orderColumnChoice);
  return checked.length?checked:state.orderingColumns.map(column=>column.key);
}

function applyOrderingColumnVisibility(){
  const visible=new Set(visibleOrderingColumns());
  document.querySelectorAll("#orderingTable [data-order-column]").forEach(cell=>cell.hidden=!visible.has(cell.dataset.orderColumn));
  const empty=$("#suggestionRows .empty-cell");if(empty)empty.colSpan=Math.max(1,visible.size+1);
}

function filterOrderingRows(){
  const filters=[...document.querySelectorAll("[data-order-filter]")].map(input=>({key:input.dataset.orderFilter,value:normalizeSearchText(input.value)})).filter(item=>item.value);
  let visibleCount=0;document.querySelectorAll("#suggestionRows tr[data-index]").forEach(row=>{const matches=filters.every(filter=>normalizeSearchText(row.querySelector(`[data-order-column="${filter.key}"]`)?.textContent).includes(filter.value));row.hidden=!matches;if(matches)visibleCount+=1});
  if(state.suggestions&&filters.length)$("#resultSummary").dataset.filteredCount=String(visibleCount);
}

function renderSuggestions(data){
  state.suggestions=data;
  const summary=data.summary;const snapshot=data.snapshot;
  const anchored=snapshot.demand_basis==="net_sales_last_stock_window";
  $("#resultSummary").className="result-summary";
  const demandLabel=anchored?"فروش خالص + انتقال آنلاین، در ۶۰ روز منتهی به آخرین موجودی":snapshot.demand_basis==="net_sales_stockout_adjusted"?"فروش خالص تعدیل‌شده با ناموجودی":"خروج دوره فایل";
  const adjustmentSummary=Number(summary.exceptional_period_out||0)>0?`<span class="summary-adjustment">فروش هیجانی تعدیل‌شده: <strong>${fa(summary.exceptional_period_out)}</strong> در ${fa(summary.demand_anomaly_items)} کالا</span>`:"";
  const recurringSummary=Number(summary.demand_recurring_pattern_items||0)>0?`<span class="summary-recurring">الگوی فروش پرتکرار و عادی: <strong>${fa(summary.demand_recurring_pattern_items)} کالا</strong></span>`:"";
  const amiranSummary=Number(summary.amiran_period_out||0)>0?`<span class="summary-amiran">فروش امیرانِ لحاظ‌شده کامل: <strong>${fa(summary.amiran_period_out)}</strong></span>`:"";
  const onlineTransferSummary=Number(summary.online_transfer_out||0)>0?`<span class="summary-amiran">انتقال آنلاینِ لحاظ‌شده: <strong>${fa(summary.online_transfer_out)}</strong></span>`:"";
  $("#resultSummary").innerHTML=`<span>منبع: <strong>${esc(snapshot.source_filename)}</strong></span><span>مبنای تقاضا: <strong>${demandLabel}</strong></span><span>قاعده کاوریج: <strong>زیر ${fa(data.parameters.reorder_coverage_days)} روز ← تا ${fa(data.parameters.target_days)} روز</strong></span><span>بازه مبنا: <strong>${fa(data.parameters.period_days)} روز قبل از آخرین موجودی</strong></span>${adjustmentSummary}${recurringSummary}${amiranSummary}${onlineTransferSummary}${anchored?`<span>خارج از چرخه بیش از ${fa(data.parameters.stale_after_days)} روز: <strong>${fa(summary.excluded_stale_items)}</strong></span>`:""}<span>اقلام نیازمند: <strong>${fa(summary.matched_items)}</strong></span><span>مقدار پیشنهادی: <strong>${fa(summary.suggested_quantity)}</strong></span><span>خروجی: <strong>سند تأمین‌کننده</strong></span>`;
  replaceTableRows($("#suggestionRows"),data.items.length?data.items.map((item,index)=>`<tr data-index="${index}"><td><input class="order-select" type="checkbox" aria-label="انتخاب ${esc(item.product_name||item.product_code)}" ${item.suggested_quantity>0?"checked":""}></td><td data-order-column="product_code" class="product-code">${esc(item.product_code)}</td><td data-order-column="manufacturer_product_code" class="ltr-value">${esc(item.manufacturer_product_code||"—")}</td><td data-order-column="barcode" class="ltr-value">${esc(item.barcode||"—")}</td><td data-order-column="product_name"><div class="product-cell"><div class="cell-name">${expandableCellText(item.product_name||"بدون نام")}</div></div></td><td data-order-column="conversion_rate">${fa(item.conversion_rate)}</td><td data-order-column="manufacturer">${esc(item.manufacturer||"تولیدکننده نامشخص")}</td><td data-order-column="group_level3">${groupLevel3Cell(item.group_level3)}</td><td data-order-column="brand">${expandableCellText(item.brand||"—",18)}</td><td data-order-column="on_hand_qty">${fa(item.stock)}</td><td data-order-column="reserved_qty">${fa(item.reserved)}</td><td data-order-column="open_order_qty">${fa(item.open_order_qty)}</td><td data-order-column="effective_procurement_qty" class="effective-stock">${fa(item.effective_procurement_qty)}</td><td data-order-column="in_transit_qty">${fa(item.in_transit_qty)}</td><td data-order-column="pending_receipt_qty">${fa(item.pending_receipt_qty)}${item.receipt_review_required?'<small>رسید نیازمند تطبیق؛ سفارش جدید متوقف است</small>':''}</td><td data-order-column="inventory_position_qty">${fa(item.inventory_position_qty)}</td><td data-order-column="effective_cartons">${fa(item.effective_cartons)}</td><td data-order-column="average_daily_out">${fa(item.average_daily_out)}${demandAuditNote(item)}</td><td data-order-column="period_out_qty">${fa(item.period_out)}</td><td data-order-column="online_transfer_out_qty">${fa(item.online_transfer_out_qty)}</td><td data-order-column="gross_sales_qty">${fa(item.gross_out)}</td><td data-order-column="sales_return_qty">${fa(item.period_return)}</td><td data-order-column="excluded_seller_qty">${fa(item.excluded_seller_qty)}</td><td data-order-column="sales_rate_days">${fa(item.sales_rate_days)}</td><td data-order-column="stockout_days">${fa(item.stockout_days)}</td><td data-order-column="last_in_stock_date" class="ltr-value">${esc(item.last_in_stock_date||"—")}</td><td data-order-column="days_since_last_stock">${item.days_since_last_stock===null?"—":fa(item.days_since_last_stock)+" روز"}</td><td data-order-column="sales_window_start" class="ltr-value">${esc(item.sales_window_start||"—")}</td><td data-order-column="sales_window_end" class="ltr-value">${esc(item.sales_window_end||"—")}</td><td data-order-column="coverage_days">${item.coverage_days===null?"—":fa(item.coverage_days)+" روز"}</td><td data-order-column="suggested_quantity" class="quantity">${fa(item.suggested_quantity)}<small class="applied-note">${fa(item.suggested_cartons)} کارتن</small></td><td data-order-column="final_order_cartons" class="quantity"><input class="order-cartons" type="number" min="0" step="1" value="${Number(item.suggested_cartons||0)}" aria-label="سفارش نهایی کارتن ${esc(item.product_name||item.product_code)}"><small class="applied-note">هر کارتن ${fa(item.conversion_rate)} عدد</small></td></tr>`).join(""):`<tr><td colspan="${visibleOrderingColumns().length+1}" class="empty-cell">با این فیلتر، کالای نیازمند سفارشی پیدا نشد.</td></tr>`);
  applyOrderingColumnVisibility();
  filterOrderingRows();
  if(summary.excluded_manual_items)$("#resultSummary").innerHTML+=`<span>خارج از چرخه دستی: <strong>${fa(summary.excluded_manual_items)} کالا</strong></span>`;
  $("#createOrderButton").disabled=!data.items.length||!has("warehouse.order.draft");
}

function orderingParameters(){
  return new URLSearchParams({warehouse:$("#warehouseSelect").value,manufacturer:$("#manufacturerFilter").value.trim(),brand:$("#brandFilter").value.trim(),search:$("#productSearch").value.trim(),reorder_coverage_days:$("#reorderCoverageDays").value,target_days:$("#targetDays").value,safety_days:"0",period_days:$("#periodDays").value,only_needed:$("#onlyNeeded").checked?"true":"false"});
}
async function orderFromInventory(){
  if(!has("warehouse.order.suggest")||state.orderingSubmitting)return;
  const selectedName=$("#inventoryWarehouseSelect").value;
  const matches=(state.bootstrap?.warehouses||[]).filter(item=>item.name===selectedName);
  if(!selectedName||matches.length!==1){toast("ابتدا یک انبار مشخص را در فیلتر ستون «انبار» انتخاب کنید.",true);return}
  const warehouse=matches[0];
  if($("#warehouseSelect").value!==warehouse.code){
    if(state.suggestions&&!confirm("انبار سفارش تغییر کند؟ جدول و تعدادهای قبلی برای مراجعه باقی می‌مانند، اما برای این انبار باید دوباره محاسبه کنید."))return;
    $("#warehouseSelect").value=warehouse.code;$("#manufacturerFilter").value="";$("#brandFilter").value="";
    invalidateOrderingSuggestions();
    loadOrderingCatalog().catch(error=>toast(error.message,true));
  }
  switchView("ordering");
  toast(`انبار «${warehouse.name}» انتخاب شد؛ فیلترهای کالا و روزهای پوشش را در همین صفحه بررسی کنید. هنوز سفارشی ساخته نشده است.`);
}
function orderingProposalIsCurrent(){
  return !!state.suggestions&&!state.orderingCalculating&&state.orderingSignature===orderingParameters().toString();
}
function updateOrderingAvailability(message){
  $("#createOrderButton").disabled=!!state.orderingSubmitting||!orderingProposalIsCurrent()||!state.suggestions.items.length||!has("warehouse.order.draft");
  if(message!==undefined){const notice=$("#orderingStatus");notice.textContent=message;notice.hidden=!message}
}
function invalidateOrderingSuggestions(){
  // Keep editable rows for reference, but never submit them as a current calculation.
  state.orderingRevision=(state.orderingRevision||0)+1;
  state.orderingSignature=null;
  updateOrderingAvailability(state.suggestions||state.orderingCalculating?"انبار، فیلترها یا اطلاعات مبنا تغییر کرده است؛ جدول قبلی قابل آماده‌سازی نیست. دوباره محاسبه کنید.":"");
}
async function calculate(){
  if(state.orderingSubmitting||!$("#filterForm").reportValidity())return;
  const params=orderingParameters(),signature=params.toString(),revision=state.orderingRevision||0;
  const requestId=state.orderingRequest=(state.orderingRequest||0)+1;
  state.orderingSignature=null;state.orderingCalculating=true;
  updateOrderingAvailability("در حال محاسبه؛ تا آماده‌شدن نتیجه امکان ساخت سفارش وجود ندارد.");
  const button=$("#calculateButton");button.disabled=true;button.textContent="در حال محاسبه...";
  try{
    const data=await api(`/warehouse-assistant/api/suggestions?${params}`);
    if(requestId!==state.orderingRequest)return;
    if(revision!==(state.orderingRevision||0)||signature!==orderingParameters().toString()){
      updateOrderingAvailability("انبار، فیلترها یا اطلاعات مبنا تغییر کرده است؛ دوباره محاسبه کنید.");return;
    }
    if(data.warehouse?.code!==params.get("warehouse"))throw new Error("انبار نتیجه با انبار انتخاب‌شده مطابقت ندارد؛ دوباره محاسبه کنید.");
    renderSuggestions(data);state.orderingSignature=signature;
    updateOrderingAvailability("تعدادها را بررسی کنید؛ آماده‌سازی، سفارش را برای تأیید به «سفارش‌های آماده» می‌برد و چیزی ارسال نمی‌کند.");
  }catch(error){
    if(requestId===state.orderingRequest){updateOrderingAvailability("محاسبه انجام نشد؛ جدول قبلی قابل آماده‌سازی نیست. دوباره محاسبه کنید.");toast(error.message,true)}
  }finally{
    if(requestId===state.orderingRequest){state.orderingCalculating=false;button.disabled=false;button.textContent="محاسبه پیشنهاد";updateOrderingAvailability()}
  }
}

function selectedLines(){
  if(!state.suggestions)return[];
  return [...document.querySelectorAll("#suggestionRows tr[data-index]")].filter(row=>row.querySelector(".order-select").checked).map(row=>{
    const item=state.suggestions.items[Number(row.dataset.index)];
    const cartons=Number(row.querySelector(".order-cartons").value);
    return{product_code:item.product_code,cartons,quantity:cartons*Number(item.conversion_rate)};
  });
}

async function createSupplierDocuments(){
  if(state.orderingSubmitting)return;
  if($('#orderingDeliveryDate')?.value.trim()&&state.bootstrap?.order_delivery_date_supported!==true){toast('برای ثبت تاریخ تحویل، ابتدا نسخه جدید سرویس انبار باید فعال شود.',true);return}
  if(!orderingProposalIsCurrent()){invalidateOrderingSuggestions();toast("ابتدا پیشنهاد سفارش را با انبار و فیلترهای فعلی دوباره محاسبه کنید.",true);return}
  const lines=selectedLines();
  if(!lines.length){toast("حداقل یک قلم را برای سفارش انتخاب کنید.",true);return}
  if(lines.some(line=>!Number.isInteger(line.cartons)||line.cartons<=0)){toast("سفارش نهایی باید تعداد صحیح و بیشتر از صفرِ کارتن باشد.",true);return}
  const proposal=state.suggestions;
  state.orderingSubmitting=true;
  const button=$("#createOrderButton");button.disabled=true;button.textContent="در حال ساخت سند...";
  try{
    const result=await api("/warehouse-assistant/api/supplier-orders",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({snapshot_id:proposal.snapshot.id,warehouse:proposal.warehouse.code,delivery_date:$('#orderingDeliveryDate')?.value.trim()||'',lines:lines.map(line=>({product_code:line.product_code,quantity:line.quantity}))})});
    state.orderingSignature=null;
    updateOrderingAvailability("سفارش آماده شد و هنوز ارسال نشده است. برای ساخت سفارش دیگری، ابتدا دوباره محاسبه کنید.");
    toast(`${fa(result.orders.length)} پیش‌سفارش دستی آماده شد؛ برای تأیید و ارسال در بخش پیش‌سفارش بررسی کنید.`);await loadOrders();selectPreparedOrderKind('manual');
  }catch(error){toast(error.message,true)}finally{state.orderingSubmitting=false;updateOrderingAvailability();button.textContent="آماده‌سازی سفارش تأمین‌کننده"}
}

function renderPreparedOrderKind(){
  const kind=state.preparedOrderKind==='system'?'system':'manual';
  if($('#manualPreparedPanel'))$('#manualPreparedPanel').hidden=kind!=='manual';
  if($('#systemPreparedPanel'))$('#systemPreparedPanel').hidden=kind!=='system';
  document.querySelectorAll('[data-prepared-kind]').forEach(button=>{
    const selected=button.dataset.preparedKind===kind;
    button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;
  });
}
function selectPreparedOrderKind(kind){state.preparedOrderKind=kind==='system'?'system':'manual';switchView('preorders')}
function preparedOrderTabKey(event){
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();
  const kind=event.key==='Home'?'manual':event.key==='End'?'system':state.preparedOrderKind==='manual'?'system':'manual';
  selectPreparedOrderKind(kind);document.querySelector(`[data-prepared-kind="${kind}"]`)?.focus();
}
function updatePreparedOrderCounts(){
  const isDraft=order=>!order.deleted&&(!order.order_stage||order.order_stage==='draft');
  const manual=(state.manualPreorders||[]).filter(isDraft).length,system=(state.automaticPreorders||[]).filter(isDraft).length;
  const badge=$('#preorderMenuBadge');if(badge){badge.textContent=fa(manual+system);badge.title=`${fa(manual)} دستی و ${fa(system)} سیستمی؛ منتظر تأیید و ارسال`}
  if($('#manualPreparedCount'))$('#manualPreparedCount').textContent=fa(manual);
  if($('#systemPreparedCount'))$('#systemPreparedCount').textContent=fa(system);
}

function orderDeliveryDateCell(order){
  const portal=order.supplier_portal||{};
  const requested=order.requested_delivery_date||portal.requested_delivery_date||'';
  const effective=order.delivery_date||(portal.status==='accepted'?(portal.proposed_delivery_date||requested):requested);
  const pending=order.pending_delivery_date||(portal.status==='submitted'&&portal.proposed_delivery_date!==requested?portal.proposed_delivery_date:'');
  return `<span class="order-delivery-date" dir="ltr">${esc(effective||'—')}</span>${pending?`<small class="order-delivery-pending">پیشنهاد تأمین‌کننده: <bdi>${esc(pending)}</bdi> · منتظر تأیید شما</small>`:''}`;
}

function renderOrders(orders){
  orders=orders.filter(order=>!order.order_stage||order.order_stage==="draft");
  state.manualPreorders=orders;updatePreparedOrderCounts();
  const headings=[['number','شماره سفارش',150],['supplier','تأمین‌کننده / برند',175],['warehouse','انبار',100],['date','زمان / ثبت‌کننده',130],['count','اقلام',50],['quantity','تعداد (عدد)',75],['delivery_date','تاریخ تحویل',170],['status','وضعیت',105],['actions','عملیات',215]];
  $('#ordersList').innerHTML=orders.length?`<div class="table-wrap manual-orders-table-wrap"><table id="manualOrdersTable"><thead><tr>${headings.map(([key,label,width])=>`<th data-column="${key}" data-user-column-width="${width}">${label}</th>`).join('')}</tr></thead><tbody>${orders.map(order=>{const sent=order.email_delivery?.status==='sent';const workflow=order.supplier_portal?.workflow_status||order.supplier_portal?.status;const portalLabel={awaiting_link:'آمادهٔ قرار دادن در کارتابل',awaiting_supplier:'در انتظار واکنش تأمین‌کننده',draft:'در حال تکمیل پاسخ تأمین‌کننده',supplier_confirmed:'تأییدشده با تأمین‌کننده',awaiting_negin:'منتظر تأیید نگین',changes_requested:'در انتظار اصلاح تأمین‌کننده',awaiting_delivery:'در انتظار تحویل سفارش',rejected:'پاسخ تأمین‌کننده رد شد',cancelled:'لغوشده'}[workflow];const status=order.deleted?'حذف‌شده':portalLabel||(sent?'ایمیل ارسال شد':order.is_approved?'آمادهٔ قرار دادن در کارتابل':'تأییدنشده');return `<tr><td dir="ltr">${esc(order.order_number)}</td><td><strong>${esc(order.supplier)}</strong><small>${esc([...new Set(order.lines.map(l=>l.brand).filter(Boolean))].join('، '))}</small></td><td>${esc(order.warehouse_name)}</td><td>${esc(formatRefreshDate(order.created_at))}<small>${esc(order.created_by)}</small></td><td>${fa(order.lines.length)}</td><td>${fa(order.total_quantity)}</td><td>${orderDeliveryDateCell(order)}</td><td>${esc(status)}</td><td><div class="manual-order-actions"><button type="button" data-manual-details="${order.id}" aria-expanded="false" aria-controls="manual-order-details-${order.id}" class="secondary-action">اقلام سفارش</button><a href="/warehouse-assistant/api/supplier-orders/${order.id}/document.xlsx">اکسل</a><a href="/warehouse-assistant/api/supplier-orders/${order.id}/document.txt">متن</a>${draftOrderActions(order,"supplier_order")}</div></td></tr><tr id="manual-order-details-${order.id}" hidden><td colspan="9"><div class="manual-order-lines">${order.lines.map(l=>`<div><span dir="ltr">${esc(l.product_code)}</span><span>${esc(l.product_name)}<small>${esc(l.brand||'')}</small></span><span>${fa(l.order_quantity)} عدد</span></div>`).join('')}</div>${order.note?`<p>${esc(order.note)}</p>`:''}</td></tr>`}).join('')}</tbody></table></div>`:'<div class="empty-cell">سفارش دستی برای نمایش وجود ندارد.</div>';
  fitTableWrapsToViewport();
}

async function manualOrderAction(button){
  const id=Number(button.dataset.manualId),action=button.dataset.manualAction;
  const order=await api(`/warehouse-assistant/api/supplier-orders/${id}`);
  if(!order)return toast('سفارش پیدا نشد؛ فهرست را بازخوانی کنید.',true);
  const prompt=action==='approve'?'این پیش‌سفارش تأیید شود؟ قرار دادن در کارتابل مرحله‌ای جداگانه است؛ اکنون پیامکی یا ایمیلی ارسال نمی‌شود.':action==='revoke-approval'?'تأیید این سفارش لغو شود؟':`فایل اکسل سفارش به ${order.contact_email||'ایمیل ثبت‌نشده'} ارسال شود؟`;
  if(!confirm(prompt))return;
  button.disabled=true;
  try{
    const options={method:'POST'};
    if(action==='send-email'){options.headers={'Content-Type':'application/json'};options.body=JSON.stringify({expected_token:order.email_send_token})}
    const result=await api(`/warehouse-assistant/api/supplier-orders/${id}/${action}`,options);
    await loadOrders();
    toast(action==='approve'?'پیش‌سفارش تأیید شد؛ اکنون می‌توانید آن را در کارتابل تأمین‌کننده قرار دهید.':action==='revoke-approval'?'تأیید سفارش لغو شد؛ پیش از ارسال باید دوباره تأیید شود.':result.already_sent?'این سفارش قبلاً ایمیل شده است.':'ایمیل و فایل اکسل سفارش ارسال شد.');
  }catch(error){toast(error.message,true);button.disabled=false}
}

async function deleteManualOrder(button){
  if(button.disabled||!confirm(`سفارش دستی ${button.dataset.manualNumber} حذف شود؟ اقلام و فایل سفارش در سابقه حفظ می‌شوند.`))return;
  button.disabled=true;
  try{await api(`/warehouse-assistant/api/supplier-orders/${Number(button.dataset.manualDelete)}`,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed:true})});await loadOrders();toast('سفارش دستی حذف شد؛ از «نمایش حذف‌شده‌ها» قابل مشاهده است.')}
  catch(error){toast(error.message,true);button.disabled=false}
}

async function loadOrders(){
  const button=$("#refreshOrdersButton");if(button)button.disabled=true;
  try{const result=await api(`/warehouse-assistant/api/supplier-orders?stage=draft&limit=200&include_deleted=${!!$('#manualOrdersIncludeDeleted')?.checked}`);renderOrders(result.orders)}catch(error){toast(error.message,true)}finally{if(button)button.disabled=false}
}

function switchView(view,updateHash=true){
  const selected=workspaceViews.includes(view)?view:"inventory";
  if(selected==='preorders'){
    if(!updateHash){const kind=location.hash.split('/')[1];state.preparedOrderKind=kind==='system'?'system':'manual'}
    renderPreparedOrderKind();
  }
  if(typeof prepareFulfillmentNavigation==='function')prepareFulfillmentNavigation(state.activeView,selected);
  state.activeView=selected;
  $("#inventoryView").hidden=selected!=="inventory";
  if($("#purchaseView"))$("#purchaseView").hidden=selected!=="purchase";
  if($("#salePriceView"))$("#salePriceView").hidden=selected!=="sale-pricing";
  if($("#unbilledView"))$("#unbilledView").hidden=selected!=="unbilled";
  if(selected==="unbilled"&&state.bootstrap&&typeof loadUnbilledReceipts==="function")loadUnbilledReceipts();
  if(selected==="purchase"&&state.bootstrap&&typeof loadPurchaseContracts==="function")loadPurchaseContracts();
  if(selected==="sale-pricing"&&state.bootstrap&&typeof loadSalePriceContracts==="function")loadSalePriceContracts();
  $("#supplyView").hidden=selected!=="supply";
  $("#orderingView").hidden=selected!=="ordering";
  $("#automaticView").hidden=selected!=="automatic";
  $("#preordersView").hidden=selected!=="preorders";
  if($("#fulfillmentView"))$("#fulfillmentView").hidden=!["sent","fulfillment"].includes(selected);
  if($("#checkbarView"))$("#checkbarView").hidden=selected!=="checkbar";
  if($('#transfersView'))$('#transfersView').hidden=selected!=='transfers';
  if(selected==='transfers'&&state.bootstrap&&typeof loadTransferRequests==='function')loadTransferRequests();
  document.querySelectorAll(".page-tabs [data-view]").forEach(button=>{
    const active=button.dataset.view===selected;
    button.classList.toggle("is-active",active);
    if(active)button.setAttribute("aria-current","page");else button.removeAttribute("aria-current");
  });
  const targetHash=selected==='preorders'?`#preorders/${state.preparedOrderKind}`:`#${selected}`;
  if(updateHash&&location.hash!==targetHash)history.pushState(null,"",targetHash);
  // Navigation preserves the loaded result window; refresh/filter actions explicitly reload it.
  if(selected==='inventory'&&updateHash&&!state.inventory.loaded&&state.bootstrap?.latest_snapshot&&has('warehouse.inventory.view'))loadInventory(true).catch(error=>toast(error.message,true));
  if(selected==="preorders"&&state.bootstrap&&has("warehouse.order.draft")){loadOrders();loadAutomaticPreorders()}
  if(['sent','fulfillment'].includes(selected)&&state.bootstrap&&has('warehouse.order.draft')){renderFulfillmentOrders();loadFulfillmentOrders().catch(error=>toast(error.message,true))}
  if(selected==='checkbar'&&state.bootstrap&&has('warehouse.order.draft'))loadCheckbarPage();
  fitTableWrapsToViewport();
}

let tableFitFrame=0;
function initializeWorkspaceChrome(){
  const topbar=document.querySelector('.topbar');
  const summary=document.querySelector('.summary-grid');
  if(topbar&&summary)topbar.append(summary);
  // Keep secondary guidance available without consuming permanent table height.
  document.querySelectorAll(".rules-disclosure[data-guide]").forEach(guide=>{
    const head=guide.closest(".panel")?.querySelector(".panel-head");
    if(!head)return;
    let actions=head.querySelector(".panel-actions");
    if(!actions){
      actions=document.createElement("div");actions.className="panel-actions";
      [...head.children].filter(child=>child.matches("button")).forEach(child=>actions.append(child));
      head.append(actions);
    }
    actions.append(guide);
  });
  const inventoryHead=$('#inventoryView .panel-head .panel-actions');
  if(inventoryHead){
    inventoryHead.append($('#inventoryDataTools'),$('#inventoryTotals'));
    const guide=$('#inventoryView .rules-disclosure > div');
    if(guide){
      const description=$('#inventoryView .panel-head p');
      if(description)guide.append(description);
      guide.append($('#inventoryGroupHelp'));
    }
  }
  document.querySelectorAll('.app-content .panel-head').forEach(head=>{
    if(head.closest('#inventoryDataTools'))return;
    const description=head.querySelector(':scope > div > p');
    if(!description)return;
    const guide=document.createElement('details');guide.className='page-purpose';
    const label=document.createElement('summary');label.textContent='راهنمای این بخش';
    guide.append(label,description);head.append(guide);
  });
  document.querySelectorAll('.app-content > section .panel-head').forEach((head,index)=>{
    head.querySelectorAll(':scope > details,:scope > .panel-actions > details').forEach(details=>details.name=`workspace-tools-${index}`);
  });
  document.querySelectorAll("details").forEach(details=>details.addEventListener("toggle",fitTableWrapsToViewport));
  document.addEventListener("click",event=>{
    document.querySelectorAll(".workspace-options[open],.rules-disclosure[open],.column-picker[open]").forEach(details=>{
      if(!details.contains(event.target))details.open=false;
    });
  });
  document.addEventListener("keydown",event=>{
    if(event.key!=="Escape")return;
    const details=event.target.closest("details[open]");
    if(!details)return;
    // Close the focused menu, not the order preview behind it.
    event.preventDefault();details.open=false;details.querySelector("summary")?.focus();
  });
}

function fitTableWrapsToViewport(){
  cancelAnimationFrame(tableFitFrame);
  tableFitFrame=requestAnimationFrame(()=>{
    if(typeof applyAllColumnOrders==='function')applyAllColumnOrders();
    document.querySelectorAll(".table-wrap table").forEach(fitFixedTableColumns);
    document.querySelectorAll('.table-wrap table').forEach(table=>{
      const headings=[...table.querySelectorAll('thead tr:first-child th')];
      table.querySelectorAll('input,select').forEach(input=>{
        if(input.hasAttribute('aria-label'))return;
        const cell=input.closest('th,td'),heading=headings[cell?.cellIndex];
        if(heading?.textContent.trim())input.setAttribute('aria-label',`${cell.tagName==='TH'?'فیلتر ':''}${heading.textContent.trim()}`);
      });
    });
    Object.keys(workViews).forEach(refreshWorkViewState);
    const minimumHeight=window.matchMedia("(max-width:650px)").matches?150:170;
    document.querySelectorAll(".table-wrap").forEach(wrap=>{
      if(wrap.offsetParent===null)return;
      const top=Math.max(0,wrap.getBoundingClientRect().top);
      const dialog=wrap.closest("dialog[open]");
      const dialogFooter=dialog?.querySelector(".preview-dialog-footer");
      const inventoryFooter=!dialog&&wrap.closest('#inventoryView')
        ?wrap.parentElement.querySelector('.inventory-more')?.offsetHeight||0:0;
      const viewportBottom=dialog
        ?dialog.getBoundingClientRect().bottom-(dialogFooter?.offsetHeight||0)-2
        :window.innerHeight-10-inventoryFooter;
      const available=Math.floor(viewportBottom-top);
      wrap.style.maxHeight=`${Math.max(minimumHeight,available)}px`;
      wrap.style.setProperty('--workspace-table-height',`${Math.max(minimumHeight,available)}px`);
      wrap.classList.add("viewport-fitted");
      restoreTableScroll(wrap);
    });
  });
}

function inventoryRow(item){
  const effectiveClass=Number(item.effective_procurement_qty)<0?"is-negative":"";
  const forced=Boolean(item.order_cycle_forced_active);
  const excluded=Boolean(item.order_cycle_forced_inactive);
  const systemLabel=item.system_ordering_cycle_active?"فعال (سیستم)":"خارج از چرخه (سیستم)";
  const exclusionSupported=state.bootstrap?.inventory_cycle_manual_exclusion_supported===true;
  const inactiveOption=`<option value="force_inactive" ${excluded?"selected":""}${exclusionSupported?"":" disabled"}>خارج از چرخه دستی${exclusionSupported?"":" · نیازمند به‌روزرسانی سرویس"}</option>`;
  const cycleControl=state.bootstrap?.inventory_cycle_override_supported?`<select class="inventory-cycle-select" data-warehouse="${esc(item.warehouse)}" data-product-code="${esc(item.product_code)}" aria-label="وضعیت چرخه سفارش ${esc(item.product_code)}" title="تغییر فقط برای این کالا در همین انبار است؛ موجودی و سوابق حذف نمی‌شوند." ${has("warehouse.order.draft")?"":"disabled"}><option value="system" ${forced||excluded?"":"selected"}>${systemLabel}</option><option value="force_active" ${forced&&!excluded?"selected":""}>فعال‌شده دستی</option>${inactiveOption}</select>`:(item.ordering_cycle_active?"فعال":"خارج از چرخه");
  return `<tr><td data-column="product_code" class="product-code">${esc(item.product_code)}</td><td data-column="product_name"><div class="product-cell"><div class="cell-name">${expandableCellText(item.product_name||"بدون نام")}</div>${item.purchase_price_validation?.message?`<small class="purchase-missing">${esc(item.purchase_price_validation.message)}</small>`:""}</div></td><td data-column="warehouse_name">${esc(item.warehouse_name)}</td><td data-column="manufacturer">${expandableCellText(item.manufacturer||"—",20)}</td><td data-column="group_level3">${groupLevel3Cell(item.group_level3)}</td><td data-column="brand">${expandableCellText(item.brand||"—",18)}</td><td data-column="tax_rate" title="${esc(item.tax_updated_at?'منبع: گروه پویا؛ به‌روز شده '+new Date(item.tax_updated_at).toLocaleString('fa-IR'):'ابتدا به‌روزرسانی مالیات را بزنید')}">${item.tax_status==='known'&&item.tax_rate!==null?fa(item.tax_rate)+'٪':item.tax_status==='conflict'?'ناسازگار':'نامشخص'}</td><td data-column="barcode" class="ltr-value">${esc(item.barcode||"—")}</td><td data-column="manufacturer_product_code" class="ltr-value">${esc(item.manufacturer_product_code||"—")}</td><td data-column="conversion_rate">${fa(item.conversion_rate)}</td><td data-column="on_hand_qty">${fa(item.on_hand_qty)}</td><td data-column="reserved_qty">${fa(item.reserved_qty)}</td><td data-column="owned_procurement_qty">${fa(item.owned_procurement_qty)}</td><td data-column="open_customer_order_qty">${fa(item.open_customer_order_qty)}</td><td data-column="unconfirmed_free_invoice_qty">${fa(item.unconfirmed_free_invoice_qty)}</td><td data-column="legacy_open_order_qty">${fa(item.legacy_open_order_qty)}</td><td data-column="open_order_qty">${fa(item.open_order_qty)}</td><td data-column="pending_sale_voucher_qty">${fa(item.pending_sale_voucher_qty)}<small class="applied-note">اعمال‌شده در موجودی عملیاتی</small></td><td data-column="in_transit_qty">${fa(item.in_transit_qty)}</td><td data-column="pending_receipt_qty">${fa(item.pending_receipt_qty)}${item.receipt_review_required?'<small>رسید نیازمند تطبیق؛ سفارش جدید متوقف است</small>':''}</td><td data-column="effective_procurement_qty" class="effective-stock ${effectiveClass}">${fa(item.effective_procurement_qty)}</td><td data-column="damaged_qty">${fa(item.damaged_qty)}</td><td data-column="period_out_qty">${fa(item.period_out_qty)}${demandAuditNote(item,{inventory:true})}</td><td data-column="online_transfer_out_qty">${fa(item.online_transfer_out_qty)}</td><td data-column="last_in_stock_date" class="ltr-value">${esc(item.last_in_stock_date||"—")}</td><td data-column="days_since_last_stock">${item.days_since_last_stock===null?"بیش از ۹۰ روز":fa(item.days_since_last_stock)+" روز"}</td><td data-column="sales_window_start" class="ltr-value">${esc(item.sales_window_start||"—")}</td><td data-column="sales_window_end" class="ltr-value">${esc(item.sales_window_end||"—")}</td><td data-column="sale_price" class="price-cell">${fa(item.sale_price)}</td><td data-column="manufacturer_price" class="price-cell">${fa(item.manufacturer_price)}</td><td data-column="consumer_price" class="price-cell">${fa(item.consumer_price)}</td><td data-column="ordering_cycle_active">${cycleControl}</td></tr>`;
}

async function saveInventoryCycleOverride(select){
  if(!has("warehouse.order.draft"))return;
  select.disabled=true;
  try{
    const result=await api("/warehouse-assistant/api/inventory/order-cycle",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({warehouse:select.dataset.warehouse,product_code:select.dataset.productCode,mode:select.value})});
    invalidateOrderingSuggestions();
    await loadInventory(true);
    toast(result.order_cycle_forced_inactive?"کالا در این انبار از چرخه سفارش خارج شد؛ موجودی و سوابق آن باقی می‌ماند.":result.order_cycle_forced_active?"کالا به‌صورت دستی به چرخه سفارش برگشت.":"وضعیت چرخه کالا به تشخیص سیستم برگردانده شد.");
  }catch(error){await loadInventory(true);toast(error.message,true)}
}

function renderInventory(data,append=false){
  state.inventory.loaded=true;
  state.inventory.items=append?[...state.inventory.items,...data.items]:data.items;
  state.inventory.total=data.summary.total_items;
  state.inventory.offset=state.inventory.items.length;
  const summary=data.summary;
  $("#inventorySummary").className="result-summary";
  $("#inventorySummary").innerHTML=`<span>ردیف‌ها: <strong>${fa(summary.total_items)}</strong></span><span>موجودی عملیاتی: <strong>${fa(summary.on_hand_qty)}</strong></span><span>رزرو قیمت: <strong>${fa(summary.reserved_qty)}</strong></span><span>تعهد باز: <strong>${fa(summary.open_order_qty)}</strong></span><span>حواله بدون فاکتور: <strong>${fa(summary.pending_sale_voucher_qty)}</strong></span><span>انتقال به آنلاین در بازه: <strong>${fa(summary.online_transfer_out_qty)}</strong></span><span>موجودی در راه: <strong>${fa(summary.in_transit_qty)}</strong></span><span>مبنای سفارش با در راه: <strong>${fa(summary.effective_procurement_qty)}</strong></span><span>خارج از چرخه سفارش: <strong>${fa(summary.out_of_cycle_items)}</strong></span>`;
  replaceTableRows($("#inventoryRows"),state.inventory.items.length?state.inventory.items.map(inventoryRow).join(""):`<tr><td colspan="${visibleInventoryColumns().length}" class="empty-cell">با این فیلتر کالایی پیدا نشد.</td></tr>`);
  applyInventoryColumnVisibility();
  $("#loadMoreInventoryButton").hidden=!data.pagination.has_more;
}

async function loadInventory(reset=true){
  if(!state.bootstrap?.latest_snapshot)return;
  const button=reset?$("#refreshInventoryButton"):$("#loadMoreInventoryButton");
  button.disabled=true;
  const offset=reset?0:state.inventory.offset;
  const params=new URLSearchParams({search:normalizeSearchText($("#inventorySearch").value),filters:JSON.stringify(collectInventoryFilters()),limit:"250",offset:String(offset)});
  const table=document.querySelector('.inventory-table');
  if(typeof registerSharedTableAdapter==='function')registerSharedTableAdapter(table,()=>loadInventory(true));
  const query=typeof getSharedTableQuery==='function'?getSharedTableQuery(table):null;
  if(query?.sort){params.set('sort_by',query.sort.key.replace(/^column:/,''));params.set('sort_direction',query.sort.direction)}
  const request=(state.inventoryRequest||0)+1;state.inventoryRequest=request;
  try{const result=await api(`/warehouse-assistant/api/inventory?${params}`);if(request===state.inventoryRequest)renderInventory(result,!reset)}catch(error){if(request===state.inventoryRequest)toast(error.message,true)}finally{if(request===state.inventoryRequest){$("#refreshInventoryButton").disabled=false;$("#loadMoreInventoryButton").disabled=false}}
}

function initializeInventoryColumns(){
  if(state.inventoryColumns.length)return;
  state.inventoryColumns=[...document.querySelectorAll(".inventory-heading-row th[data-column]")].map(th=>({key:th.dataset.column,title:th.textContent.trim()}));
  const priceColumns=new Set(["sale_price","manufacturer_price","consumer_price"]);
  $("#inventoryColumnChoices").innerHTML=state.inventoryColumns.map(column=>`<label><input type="checkbox" data-column-choice="${esc(column.key)}" ${state.bootstrap?.inventory_prices_supported||!priceColumns.has(column.key)?"checked":""}> ${esc(column.title)}</label>`).join("");
  document.querySelectorAll("[data-column-choice]").forEach(input=>input.addEventListener("change",()=>{applyInventoryColumnVisibility();markInventoryViewEdited()}));
  applyInventoryColumnVisibility();
}

function visibleInventoryColumns(){
  const checked=[...document.querySelectorAll("[data-column-choice]:checked")].map(input=>input.dataset.columnChoice);
  if(checked.length&&typeof columnLayouts!=='undefined'&&columnLayouts.tables.inventory)return columnLayouts.tables.inventory.order.filter(key=>checked.includes(key));
  return checked.length?checked:state.inventoryColumns.map(column=>column.key);
}

function applyInventoryColumnVisibility(){
  fitTableWrapsToViewport();
  const visible=new Set(visibleInventoryColumns());
  document.querySelectorAll(".inventory-table [data-column]").forEach(cell=>cell.hidden=!visible.has(cell.dataset.column));
  const empty=$("#inventoryRows .empty-cell");if(empty)empty.colSpan=Math.max(1,visible.size);
}

function collectInventoryFilters(){
  const filters={};
  document.querySelectorAll(".inventory-filter-row [data-filter]").forEach(input=>{const value=normalizeSearchText(input.value);if(value)filters[input.dataset.filter]=value});
  return filters;
}

function applyInventoryFilters(filters={}){
  document.querySelectorAll(".inventory-filter-row [data-filter]").forEach(input=>{input.value=filters[input.dataset.filter]||""});
}

function markInventoryViewEdited(){
  const selected=$("#inventoryViewSelect").value;
  if(selected)$("#inventoryViewSelect").dataset.edited="true";
}

function renderInventoryViews(selectedId=""){
  const select=$("#inventoryViewSelect");
  select.innerHTML='<option value="">طرح جاری (ذخیره‌نشده)</option>'+state.inventoryViews.map(view=>`<option value="${esc(view.id)}">${view.is_default?"★ ":""}${esc(view.name)}</option>`).join("");
  select.value=selectedId;
  $("#deleteInventoryViewButton").disabled=!selectedId;
}

function applyInventoryView(view,load=true){
  if(load&&typeof setColumnOrder==='function'&&columnLayouts.tables.inventory)setColumnOrder('inventory',view.visible_columns||[]);
  applyInventoryFilters(view.filters||{});
  const visible=new Set(view.visible_columns||[]);
  document.querySelectorAll("[data-column-choice]").forEach(input=>input.checked=visible.has(input.dataset.columnChoice));
  $("#inventoryViewName").value=view.name;
  $("#inventoryViewDefault").checked=Boolean(view.is_default);
  $("#inventoryViewSelect").value=view.id;
  $("#inventoryViewSelect").dataset.edited="false";
  $("#deleteInventoryViewButton").disabled=false;
  applyInventoryColumnVisibility();
  if(load&&state.bootstrap?.latest_snapshot)loadInventory(true);
}

async function loadInventoryViews(applyDefault=false,selectedId=""){
  const result=await api("/warehouse-assistant/api/inventory/views");
  state.inventoryViews=result.views||[];
  renderInventoryViews(selectedId);
  if(applyDefault){const preferred=state.inventoryViews.find(view=>view.is_default);if(preferred)applyInventoryView(preferred,false)}
}

async function saveInventoryView(){
  const name=$("#inventoryViewName").value.trim();
  if(!name){toast("برای طرح یک نام وارد کنید.",true);$("#inventoryViewName").focus();return}
  const button=$("#saveInventoryViewButton");button.disabled=true;
  try{
    const view=await api("/warehouse-assistant/api/inventory/views",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,is_default:$("#inventoryViewDefault").checked,visible_columns:visibleInventoryColumns(),filters:collectInventoryFilters()})});
    await loadInventoryViews(false,view.id);applyInventoryView(view,false);toast(`طرح «${view.name}» برای شما ذخیره شد.`);
  }catch(error){toast(error.message,true)}finally{button.disabled=false}
}

async function deleteInventoryView(){
  const id=$("#inventoryViewSelect").value;if(!id)return;
  const view=state.inventoryViews.find(item=>item.id===id);if(!view)return;
  if(!window.confirm(`طرح «${view.name}» حذف شود؟`))return;
  try{
    await api(`/warehouse-assistant/api/inventory/views/${encodeURIComponent(id)}`,{method:"DELETE"});
    applyInventoryFilters({});document.querySelectorAll("[data-column-choice]").forEach(input=>input.checked=true);applyInventoryColumnVisibility();
    $("#inventoryViewName").value="";$("#inventoryViewDefault").checked=false;await loadInventoryViews(false);await loadInventory(true);toast("طرح حذف شد.");
  }catch(error){toast(error.message,true)}
}

function clearInventoryFilters(){
  $("#inventorySearch").value="";applyInventoryFilters({});$("#inventoryViewSelect").value="";$("#deleteInventoryViewButton").disabled=true;loadInventory(true);
}

function scheduleInventoryFilter(){
  markInventoryViewEdited();clearTimeout(state.filterTimer);state.filterTimer=setTimeout(()=>loadInventory(true),450);
}

document.addEventListener("DOMContentLoaded",()=>{
  window.addEventListener("hashchange",restoreWorkspaceView);
  initializeWorkspaceChrome();
  $("#loginForm").addEventListener("submit",login);
  $("#loginButton").addEventListener("click",showLogin);
  $("#logoutButton").addEventListener("click",logout);
  $("#varanegarSyncForm").addEventListener("submit",syncVaranegar);
  $("#snapshotForm").addEventListener("submit",importSnapshot);
  $("#filterForm").addEventListener("submit",event=>{event.preventDefault();calculate()});
  $("#filterForm").addEventListener("input",invalidateOrderingSuggestions);
  $("#filterForm").addEventListener("change",invalidateOrderingSuggestions);
  $("#warehouseSelect").addEventListener("change",()=>{$("#manufacturerFilter").value="";$("#brandFilter").value="";loadOrderingCatalog().catch(error=>toast(error.message,true))});
  $("#manufacturerFilter").addEventListener("change",()=>{$("#brandFilter").value="";renderOrderingBrands()});
  $("#createOrderButton").addEventListener("click",createSupplierDocuments);
  $("#orderFromInventoryButton").addEventListener("click",orderFromInventory);
  $("#refreshOrdersButton").addEventListener("click",loadOrders);
  $('#manualOrdersIncludeDeleted').addEventListener('change',loadOrders);
  document.querySelectorAll('[data-prepared-kind]').forEach(button=>{button.addEventListener('click',()=>selectPreparedOrderKind(button.dataset.preparedKind));button.addEventListener('keydown',preparedOrderTabKey)});
  $('#ordersList').addEventListener('click',event=>{
    const remove=event.target.closest('[data-manual-delete]');if(remove){deleteManualOrder(remove);return}
    const action=event.target.closest('[data-manual-action]');if(action){manualOrderAction(action);return}
    const button=event.target.closest('[data-manual-details]');if(!button)return;
    const row=$('#manual-order-details-'+Number(button.dataset.manualDetails));row.hidden=!row.hidden;
    button.textContent=row.hidden?'اقلام سفارش':'بستن اقلام';button.setAttribute('aria-expanded',String(!row.hidden));fitTableWrapsToViewport();
  });
  $("#inventoryFilterForm").addEventListener("submit",event=>{event.preventDefault();loadInventory(true)});
  $("#clearInventoryFiltersButton").addEventListener("click",clearInventoryFilters);
  $("#saveInventoryViewButton").addEventListener("click",saveInventoryView);
  $("#deleteInventoryViewButton").addEventListener("click",deleteInventoryView);
  $("#inventoryViewSelect").addEventListener("change",event=>{const view=state.inventoryViews.find(item=>item.id===event.target.value);if(view)applyInventoryView(view);else{$("#deleteInventoryViewButton").disabled=true}});
  document.querySelectorAll(".inventory-filter-row input[data-filter]").forEach(input=>{input.addEventListener("input",scheduleInventoryFilter);input.addEventListener("keydown",event=>{if(event.key==="Enter"){event.preventDefault();clearTimeout(state.filterTimer);loadInventory(true)}})});
  $("#inventoryWarehouseSelect").addEventListener("change",scheduleInventoryFilter);
  $("#inventoryTaxFilter").addEventListener("change",scheduleInventoryFilter);
  $("#refreshInventoryButton").addEventListener("click",()=>loadInventory(true));
  $("#loadMoreInventoryButton").addEventListener("click",()=>loadInventory(false));
  $("#inventoryRows").addEventListener("change",event=>{const select=event.target.closest(".inventory-cycle-select");if(select)saveInventoryCycleOverride(select)});
  $("#refreshSupplyScopeButton").addEventListener("click",refreshSupplyScope);
  $("#supplyWarehouseSelect").addEventListener("change",renderSupplyScope);
  $("#supplySearch").addEventListener("input",renderSupplyScope);
  $("#supplyStatusFilter").addEventListener("change",renderSupplyScope);
  document.querySelectorAll("[data-supply-filter]").forEach(input=>input.addEventListener("input",renderSupplyScope));
  $("#supplyRows").addEventListener("change",event=>{const input=event.target.closest(".supply-brand-toggle,.supply-supplier-toggle");if(input)saveSupplyScopeToggle(input)});
  $("#previewAutomaticButton").addEventListener("click",previewAutomaticOrders);
  $("#prepareAutomaticButton").addEventListener("click",()=>prepareAutomaticPreorders(false));
  $("#manualRefreshPreordersButton").addEventListener("click",event=>prepareAutomaticPreorders(false,event.currentTarget));
  $("#refreshAutomaticPreordersButton").addEventListener("click",loadAutomaticPreorders);
  $("#automaticWarehouseSelect").addEventListener("change",()=>{state.automaticPreview=null;renderAutomaticSettings()});
  document.querySelectorAll("[data-auto-filter]").forEach(input=>input.addEventListener(input.tagName==="SELECT"?"change":"input",renderAutomaticSettings));
  $("#automaticRows").addEventListener("click",event=>{const button=event.target.closest("[data-auto-save]");if(button)saveAutomaticSetting(button)});
  $("#saveAutomaticSettingsButton").addEventListener("click",event=>saveAutomaticSettings(null,event.currentTarget));
  $("#automaticRows").addEventListener("input",event=>{const row=event.target.closest("tr[data-auto-id]");if(row)captureAutomaticDraft(row)});
  $("#automaticPreordersList").addEventListener("click",event=>{const button=event.target.closest("[data-preorder-action]");if(!button)return;if(button.dataset.preorderAction==="preview")openPreorderPreview(Number(button.dataset.preorderId));else automaticPreorderAction(button)});
  $("#previewPreorderLines").addEventListener("input",event=>{if(event.target.matches(".preview-cartons"))updatePreviewTotals()});
  $("#previewPreorderLines").addEventListener("click",event=>{
    const remove=event.target.closest("[data-preview-remove]");if(!remove)return;
    const input=remove.closest("tr").querySelector(".preview-cartons");input.value="0";updatePreviewTotals();
    updateDraftEditorStatus('automatic_preorder');
    toast("قلم برای حذف علامت خورد؛ برای اعمال، «ذخیره تغییرات» را بزنید.");
  });
  $("#savePreorderPreviewButton").addEventListener("click",savePreorderPreview);
  $("#closePreorderPreviewButton").addEventListener("click",closePreorderPreview);
  $("#cancelPreorderPreviewButton").addEventListener("click",closePreorderPreview);
  $("#preorderWarehouseFilter").addEventListener("change",()=>renderAutomaticPreorders());
  $("#preorderStatusFilter").addEventListener("change",()=>renderAutomaticPreorders());
  document.querySelectorAll("[data-preorder-filter]").forEach(input=>input.addEventListener("input",()=>renderAutomaticPreorders()));
  document.querySelectorAll("[data-order-filter]").forEach(input=>input.addEventListener("input",filterOrderingRows));
  document.querySelectorAll(".page-tabs [data-view]").forEach(button=>button.addEventListener("click",()=>switchView(button.dataset.view)));
  window.addEventListener("resize",fitTableWrapsToViewport,{passive:true});
  window.addEventListener("load",fitTableWrapsToViewport,{once:true});
  initializeTableScrollPersistence();
  new MutationObserver(fitTableWrapsToViewport).observe($("#warehouseAssistantApp"),{childList:true,subtree:true});
  fitTableWrapsToViewport();
  start();
});
