const state={bootstrap:null,suggestions:null};
const $=selector=>document.querySelector(selector);
const fa=value=>new Intl.NumberFormat("fa-IR",{maximumFractionDigits:2}).format(Number(value||0));
const esc=value=>String(value??"").replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
class ApiError extends Error{constructor(message,status){super(message);this.status=status}}

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
  $("#loginButton").hidden=true;$("#logoutButton").hidden=false;
  $("#userBadge").hidden=false;$("#userBadge").textContent=data.username;
  $("#accessMessage").hidden=true;
  $("#warehouseSelect").innerHTML=data.warehouses.map(item=>`<option value="${esc(item.code)}">${esc(item.name)}</option>`).join("");
  const snapshot=data.latest_snapshot;
  $("#snapshotDate").textContent=snapshot?new Date(snapshot.imported_at).toLocaleString("fa-IR"):"—";
  $("#snapshotFile").textContent=snapshot?`${snapshot.source_filename}${snapshot.period_start?` · ${snapshot.period_start} تا ${snapshot.period_end}`:""} · توسط ${snapshot.imported_by}`:"هنوز داده‌ای دریافت نشده است";
  $("#productCount").textContent=snapshot?fa(snapshot.product_count):"۰";
  $("#snapshotForm").hidden=!has("warehouse.data.refresh");
  $("#varanegarSyncForm").hidden=!has("warehouse.data.refresh");
  if(snapshot?.period_days){$("#periodDays").value=snapshot.period_days;$("#syncPeriodDays").value=snapshot.period_days}
  $("#calculateButton").disabled=!snapshot||!has("warehouse.order.suggest");
  $("#createOrderButton").hidden=!has("warehouse.order.draft");
  $("#refreshOrdersButton").hidden=!has("warehouse.order.draft");
}

async function start(){
  try{
    renderBootstrap(await api("/warehouse-assistant/api/bootstrap"));
    if(has("warehouse.order.draft"))await loadOrders();
  }catch(error){
    if(error.status===401){showLogin();return}
    const notice=$("#accessMessage");notice.hidden=false;notice.textContent=error.message;
    if(error.status===403){$("#loginButton").hidden=true;$("#logoutButton").hidden=false}
    toast(error.message,true);
  }
}

function showLogin(){
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
  await fetch("/auth/logout",{method:"POST",credentials:"same-origin"});
  state.bootstrap=null;state.suggestions=null;showLogin();
}

async function syncVaranegar(event){
  event.preventDefault();const periodDays=Number($("#syncPeriodDays").value);const button=$("#syncButton");
  button.disabled=true;button.textContent="در حال خواندن ورانگر...";
  try{
    const result=await api("/warehouse-assistant/api/sync/varanegar",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({period_days:periodDays})});
    toast(result.duplicate?"داده ورانگر تغییری نکرده است.":"موجودی و روند خروج از ورانگر دریافت شد.");
    state.suggestions=null;renderBootstrap(await api("/warehouse-assistant/api/bootstrap"));
  }catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent="دریافت موجودی و خروج از ورانگر"}
}

async function importSnapshot(event){
  event.preventDefault();const input=$("#snapshotFileInput");if(!input.files.length)return;
  const button=$("#importButton");button.disabled=true;button.textContent="در حال خواندن فایل...";
  const form=new FormData();form.append("file",input.files[0]);
  try{
    const result=await api("/warehouse-assistant/api/snapshots/import",{method:"POST",body:form});
    toast(result.duplicate?"این Snapshot قبلاً وارد شده بود.":"Snapshot انبار با موفقیت وارد شد.");
    input.value="";state.suggestions=null;renderBootstrap(await api("/warehouse-assistant/api/bootstrap"));
  }catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent="ورود فایل پشتیبان"}
}

function renderSuggestions(data){
  state.suggestions=data;
  const summary=data.summary;const snapshot=data.snapshot;
  $("#resultSummary").className="result-summary";
  $("#resultSummary").innerHTML=`<span>منبع: <strong>${esc(snapshot.source_filename)}</strong></span><span>بازه خروج: <strong>${fa(data.parameters.period_days)} روز</strong></span><span>اقلام نیازمند: <strong>${fa(summary.matched_items)}</strong></span><span>مقدار پیشنهادی: <strong>${fa(summary.suggested_quantity)}</strong></span><span>خروجی: <strong>سند تأمین‌کننده</strong></span>`;
  $("#suggestionRows").innerHTML=data.items.length?data.items.map((item,index)=>`<tr data-index="${index}"><td><input class="order-select" type="checkbox" aria-label="انتخاب ${esc(item.product_name||item.product_code)}" ${item.suggested_quantity>0?"checked":""}></td><td><div class="product-cell"><strong>${esc(item.product_name||"بدون نام")}</strong><small>کد ${esc(item.product_code)}</small></div></td><td><div class="maker-cell"><span>${esc(item.manufacturer||"تأمین‌کننده نامشخص")}</span><small>${esc(item.brand||"—")}</small></div></td><td>${fa(item.stock)}</td><td>${fa(item.reserved)}</td><td>${fa(item.available_quantity)}</td><td>${fa(item.period_out)}<br><small>خروج ${fa(item.gross_out)} · برگشت ${fa(item.period_return)}</small></td><td>${item.coverage_days===null?"—":fa(item.coverage_days)+" روز"}</td><td>${fa(item.conversion_rate)}</td><td class="quantity"><input class="order-quantity" type="number" min="0.01" step="0.01" value="${Number(item.suggested_quantity||0)}" aria-label="تعداد سفارش ${esc(item.product_name||item.product_code)}"><br><small>${fa(item.suggested_cartons)} کارتن پیشنهادی</small></td><td>${fa(item.estimated_value)}</td></tr>`).join(""):'<tr><td colspan="11" class="empty-cell">با این فیلتر، کالای نیازمند سفارشی پیدا نشد.</td></tr>';
  $("#createOrderButton").disabled=!data.items.length||!has("warehouse.order.draft");
}

async function calculate(){
  const params=new URLSearchParams({warehouse:$("#warehouseSelect").value,manufacturer:$("#manufacturerFilter").value.trim(),brand:$("#brandFilter").value.trim(),search:$("#productSearch").value.trim(),target_days:$("#targetDays").value,safety_days:$("#safetyDays").value,period_days:$("#periodDays").value,only_needed:$("#onlyNeeded").checked?"true":"false"});
  const button=$("#calculateButton");button.disabled=true;button.textContent="در حال محاسبه...";
  try{renderSuggestions(await api(`/warehouse-assistant/api/suggestions?${params}`))}catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent="محاسبه پیشنهاد"}
}

function selectedLines(){
  if(!state.suggestions)return[];
  return [...document.querySelectorAll("#suggestionRows tr[data-index]")].filter(row=>row.querySelector(".order-select").checked).map(row=>{
    const item=state.suggestions.items[Number(row.dataset.index)];
    return{product_code:item.product_code,quantity:Number(row.querySelector(".order-quantity").value)};
  });
}

async function createSupplierDocuments(){
  const lines=selectedLines();
  if(!lines.length){toast("حداقل یک قلم را برای سفارش انتخاب کنید.",true);return}
  if(lines.some(line=>!Number.isFinite(line.quantity)||line.quantity<=0)){toast("تعداد همه اقلام انتخاب‌شده باید بیشتر از صفر باشد.",true);return}
  const button=$("#createOrderButton");button.disabled=true;button.textContent="در حال ساخت سند...";
  try{
    const result=await api("/warehouse-assistant/api/supplier-orders",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({snapshot_id:state.suggestions.snapshot.id,warehouse:$("#warehouseSelect").value,lines})});
    toast(`${fa(result.orders.length)} سند تأمین‌کننده آماده شد.`);await loadOrders();
  }catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent="ساخت سند تأمین‌کننده"}
}

function renderOrders(orders){
  $("#ordersList").innerHTML=orders.length?orders.map(order=>`<article class="order-card"><div class="order-card-head"><div><h3>${esc(order.supplier)}</h3><small>${esc(order.warehouse_name)} · ${esc(order.created_by)}</small></div><span class="order-number">${esc(order.order_number)}</span></div><div class="order-meta"><span>اقلام<strong>${fa(order.lines.length)}</strong></span><span>جمع تعداد<strong>${fa(order.total_quantity)}</strong></span><span>ارزش تخمینی<strong>${fa(order.estimated_value)}</strong></span></div><div class="order-links"><a href="/warehouse-assistant/api/supplier-orders/${order.id}/document.xlsx">دریافت Excel</a><a href="/warehouse-assistant/api/supplier-orders/${order.id}/document.txt">دریافت متن</a></div></article>`).join(""):'<div class="empty-cell">هنوز سندی آماده نشده است.</div>';
}

async function loadOrders(){
  const button=$("#refreshOrdersButton");if(button)button.disabled=true;
  try{const result=await api("/warehouse-assistant/api/supplier-orders");renderOrders(result.orders)}catch(error){toast(error.message,true)}finally{if(button)button.disabled=false}
}

document.addEventListener("DOMContentLoaded",()=>{
  $("#loginForm").addEventListener("submit",login);
  $("#loginButton").addEventListener("click",showLogin);
  $("#logoutButton").addEventListener("click",logout);
  $("#varanegarSyncForm").addEventListener("submit",syncVaranegar);
  $("#snapshotForm").addEventListener("submit",importSnapshot);
  $("#calculateButton").addEventListener("click",calculate);
  $("#createOrderButton").addEventListener("click",createSupplierDocuments);
  $("#refreshOrdersButton").addEventListener("click",loadOrders);
  start();
});
