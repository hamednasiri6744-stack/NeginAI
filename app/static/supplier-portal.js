const $ = (s) => document.querySelector(s),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>'"]/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          "'": "&#39;",
          '"': "&quot;",
        })[c],
    ),
  norm = (v) =>
    String(v ?? "")
      .trim()
      .replace(/[يى]/g, "ی")
      .replace(/ك/g, "ک")
      .toLocaleLowerCase("fa-IR");
const labels = {
  awaiting_supplier: "منتظر تأیید شما",
  draft: "پیش‌نویس تغییرات",
  submitted: "در انتظار تأیید نگین پخش برای ارسال",
  changes_requested: "نیازمند اصلاح",
  accepted: "تأییدشده برای ارسال",
  rejected: "ردشده",
  cancelled: "لغوشده",
};
let profile = null,
  orders = [],
  active = null;
let selectedOrderStage='action',orderDetailRequest=0;
let loadingOrderId=null,orderDetailController=null;
function cancelOrderDetail(){
  orderDetailRequest++;
  orderDetailController?.abort();
  orderDetailController=null;loadingOrderId=null;
  $('#orderDetail').setAttribute('aria-busy','false');
}
const orderStageLabels={action:'سفارش‌های در انتظار اقدام',negin:'در انتظار تأیید نگین پخش برای ارسال',approved:'سفارش‌های تأییدشده برای ارسال',history:'سوابق رد یا لغو'};
function supplierOrderStage(order){
  if(['awaiting_supplier','draft','changes_requested'].includes(order.status))return 'action';
  if(order.status==='submitted')return 'negin';
  if(order.status==='accepted')return 'approved';
  return 'history';
}
function orderMatchesCartableFilters(order){
  const supplier=$('#cartableSupplierFilter')?.value,warehouse=$('#cartableWarehouseFilter')?.value;
  return (!supplier||order.document.supplier===supplier)&&(!warehouse||order.document.warehouse_name===warehouse);
}
function renderOrderStageNav(){
  const filtered=orders.filter(orderMatchesCartableFilters);
  $('#orderStageNav').innerHTML=Object.entries(orderStageLabels).filter(([stage])=>stage!=='history'||filtered.some(o=>supplierOrderStage(o)==='history')||selectedOrderStage==='history').map(([stage,label])=>{
    const count=filtered.filter(order=>supplierOrderStage(order)===stage).length;
    return `<button type="button" data-order-stage="${stage}" aria-pressed="${stage===selectedOrderStage}" class="sp-stage-button${stage==='history'?' sp-stage-history':''}"><span>${label}</span><b>${count.toLocaleString('fa-IR')}</b></button>`;
  }).join('');
  $('#orderStageNav').querySelectorAll('[data-order-stage]').forEach(button=>button.onclick=()=>{
    selectOrderStage(button.dataset.orderStage);
    $('#orderStageNav').querySelector(`[data-order-stage="${selectedOrderStage}"]`)?.focus();
  });
}
function supplierResponseIsDirty(){
  if(!active||!['awaiting_supplier','draft','changes_requested'].includes(active.status))return false;
  return ($('#proposedDate')&&$('#proposedDate').value!==(active.proposed_delivery_date||active.requested_delivery_date))||
    ($('#supplierComment')&&$('#supplierComment').value!==(active.supplier_comment||''))||
    [...($('#responseForm')?.querySelectorAll('.line-cartons')||[])].some((input,index)=>Number(input.value)!==Number(active.lines[index].proposed_cartons));
}
function selectOrderStage(stage){
  if(!Object.hasOwn(orderStageLabels,stage)||stage===selectedOrderStage)return;
  if(supplierResponseIsDirty()&&!confirm('تغییرات این پاسخ هنوز ارسال نشده است. بدون ذخیره به بخش دیگر بروید؟'))return;
  selectedOrderStage=stage;active=null;cancelOrderDetail();
  $('#orderDetail').innerHTML='<div class="sp-empty">یک سفارش از این بخش را برای بررسی انتخاب کنید.</div>';
  renderOrderList();
}
async function api(url, options = {}) {
  const r = await fetch(url, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  let body = {};
  try {
    body = await r.json();
  } catch {}
  if (!r.ok) {
    const e = new Error(body.detail || "خطا در ارتباط با سامانه");
    e.status = r.status;
    throw e;
  }
  return body;
}
function show(id) {
  ["loginView", "passwordView", "portalView"].forEach((x) =>
    $("#" + x).classList.toggle("hidden", x !== id),
  );
  $("#logoutButton").classList.toggle("hidden", id === "loginView"); $("#changePasswordButton").classList.toggle("hidden",id!=="portalView");
}
function err(el, message = "") {
  el.textContent = message;
  el.classList.toggle("hidden", !message);
}
$('#changePasswordButton').addEventListener('click',()=>show('passwordView'));
$('#cancelPasswordChange').addEventListener('click',()=>show('portalView'));
async function boot() {
  try {
    profile = await api("/supplier-portal/api/me");
    $("#supplierBadge").textContent = profile.access?.cartable_name || profile.supplier_name;
    show("portalView");
    await loadOrders();
  } catch {
    show("loginView");
  }
}
$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  err($("#loginError"));
  const b = e.submitter;
  b.disabled = true;
  try {
    profile = await api("/supplier-portal/api/login", {
      method: "POST",
      body: JSON.stringify({
        username: $("#username").value,
        password: $("#password").value,
      }),
    });
    $("#supplierBadge").textContent = profile.access?.cartable_name || profile.supplier_name;
    show("portalView");
    await loadOrders();
  } catch (x) {
    err($("#loginError"), x.message);
  } finally {
    b.disabled = false;
  }
});
$("#passwordForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  err($("#passwordError"));
  if ($("#newPassword").value !== $("#newPasswordAgain").value)
    return err($("#passwordError"), "تکرار رمز جدید یکسان نیست.");
  const b = e.submitter;
  b.disabled = true;
  try {
    await api("/supplier-portal/api/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: $("#currentPassword").value,
        new_password: $("#newPassword").value,
      }),
    });
    profile.must_change_password = false;
    show("portalView");
    await loadOrders();
  } catch (x) {
    err($("#passwordError"), x.message);
  } finally {
    b.disabled = false;
  }
});
$("#logoutButton").addEventListener("click", async () => {
  cancelOrderDetail();active=null;
  try {
    await api("/supplier-portal/api/logout", { method: "POST" });
  } finally {
    location.reload();
  }
});
function status(s) {
  return `<span class="sp-status ${esc(s)}">${esc(labels[s] || s)}</span>`;
}
async function loadOrders() {
  if(!$('#cartableFilters')){
    const controls=document.createElement('div');controls.id='cartableFilters';controls.className='sp-form section-gap';
    controls.innerHTML='<details class="sp-cartable-filters"><summary>فیلتر تأمین‌کننده و انبار</summary><label class="field"><span>تأمین‌کننده سفارش</span><select id="cartableSupplierFilter"></select></label><label class="field"><span>انبار سفارش</span><select id="cartableWarehouseFilter"></select></label></details><button id="cartableRefresh" type="button" class="btn btn-secondary">بازخوانی سفارش‌ها</button><p id="cartableFeedback" role="status"></p>';
    $('#orderStats').after(controls);
    $('#cartableSupplierFilter').onchange=renderOrderList;
    $('#cartableWarehouseFilter').onchange=renderOrderList;
    $('#cartableRefresh').onclick=loadOrders;
  }
  const feedback=$('#cartableFeedback'),button=$('#cartableRefresh');
  button.disabled=true;
  feedback.className='hint';
  feedback.textContent='در حال دریافت سفارش‌های کارتابل…';
  $('#orderList').setAttribute('aria-busy','true');
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),20000);
  try {
  const data=await api('/supplier-portal/api/orders',{signal:controller.signal,cache:'no-store'});
  if(!Array.isArray(data.orders))throw new Error('پاسخ فهرست سفارش‌ها معتبر نیست. دوباره بازخوانی کنید.');
  orders=data.orders;
  const refreshedActive=active&&orders.find(order=>order.id===active.id);
  if(refreshedActive)selectedOrderStage=supplierOrderStage(refreshedActive);
  for(const [id,field,label] of [['cartableSupplierFilter','supplier','همه تأمین‌کنندگان مجاز'],['cartableWarehouseFilter','warehouse_name','همه انبارهای مجاز']]){
    const select=$('#'+id),old=select.value,values=[...new Set(orders.map(o=>o.document[field]).filter(Boolean))];
    select.innerHTML=`<option value="">${label}</option>`+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');
    select.value=values.includes(old)?old:'';
  }
  const pending = orders.filter((o) =>
    ["awaiting_supplier", "draft", "changes_requested"].includes(o.status),
  ).length;
  $("#orderStats").innerHTML =
    `<div class="sp-stat"><strong>${orders.length.toLocaleString("fa-IR")}</strong><span>کل سفارش‌ها</span></div><div class="sp-stat"><strong>${pending.toLocaleString("fa-IR")}</strong><span>نیازمند اقدام</span></div>`;
  renderOrderList();
  feedback.textContent=orders.length ? `${orders.length.toLocaleString('fa-IR')} سفارش دریافت شد.` : 'سفارشی در محدودهٔ مسئولیت شما قرار ندارد.';
  if (active) {
    const fresh = orders.find((o) => o.id === active.id);
    if (fresh) await openOrder(fresh.id,{refresh:true}); else {active=null;cancelOrderDetail();$("#orderDetail").innerHTML='<div class="sp-empty">این سفارش دیگر در محدودهٔ دسترسی یا کارتابل شما نیست.</div>'}
  }
  return true;
  } catch(e) {
    // A successful login must not hide subsequent list errors in the login form.
    orders=[];active=null;cancelOrderDetail();
    $('#orderStats').innerHTML='';$('#orderList').innerHTML='';
    renderOrderStageNav();$('#orderSectionSummary').textContent='فهرست دریافت نشده است.';
    $('#orderDetail').innerHTML='<div class="sp-empty">فهرست سفارش‌ها دریافت نشد؛ «بازخوانی سفارش‌ها» را بزنید.</div>';
    feedback.className='error';
    feedback.textContent=controller.signal.aborted ? 'دریافت سفارش‌ها طول کشید. دوباره بازخوانی کنید.' : `دریافت سفارش‌ها انجام نشد: ${e.message}`;
    if(e.status===401){show('loginView');err($('#loginError'),'نشست شما پایان یافته؛ دوباره وارد شوید.');}
    return false;
  } finally {
    clearTimeout(timeout);button.disabled=false;
    $('#orderList').setAttribute('aria-busy','false');
  }
}
function renderOrderList(){
  renderOrderStageNav();
  const visible=orders.filter(o=>supplierOrderStage(o)===selectedOrderStage&&orderMatchesCartableFilters(o));
  $('#orderSectionSummary').textContent=`${orderStageLabels[selectedOrderStage]} · ${visible.length.toLocaleString('fa-IR')} سفارش`;
  $("#orderList").innerHTML = visible.length
    ? visible
        .map(
          (o) =>
            `<button class="sp-order ${(loadingOrderId??active?.id) === o.id ? "is-active" : ""}" data-id="${o.id}" aria-busy="${loadingOrderId===o.id}" ${loadingOrderId===o.id?'disabled':''}><strong><span dir="ltr">${esc(o.document.number)}</span>${status(o.status)}</strong><small>${esc(o.document.supplier)} · ${esc(o.document.warehouse_name)} · تحویل ${esc(o.delivery_date||(o.status==="accepted"?(o.proposed_delivery_date||o.requested_delivery_date):o.requested_delivery_date))}</small>${loadingOrderId===o.id?'<small class="sp-order-loading">در حال بازکردن سفارش…</small>':''}</button>`,
        )
        .join("")
    : '<div class="sp-empty">سفارشی در این محدوده و فیلتر وجود ندارد.</div>';
  $("#orderList")
    .querySelectorAll("[data-id]")
    .forEach((b) => (b.onclick = () => openOrder(+b.dataset.id)));
}
async function openOrder(id,{refresh=false}={}) {
  if(loadingOrderId===id||(!refresh&&active?.id===id))return;
  if(active?.id!==id&&supplierResponseIsDirty()&&!confirm('تغییرات این پاسخ هنوز ارسال نشده است. بدون ذخیره به سفارش دیگر بروید؟'))return;
  cancelOrderDetail();
  const request=orderDetailRequest,controller=new AbortController();
  orderDetailController=controller;loadingOrderId=id;active=null;
  const detail=$('#orderDetail'),summary=orders.find(row=>row.id===id);
  detail.setAttribute('aria-busy','true');
  detail.innerHTML=`<div class="sp-detail-state" role="status" aria-live="polite"><span class="sp-spinner" aria-hidden="true"></span><strong>در حال دریافت اقلام سفارش…</strong><span dir="ltr">${esc(summary?.document.number||'')}</span></div>`;
  renderOrderList();
  const timeout=setTimeout(()=>controller.abort(),20000);
  try {
    const order=await api(`/supplier-portal/api/orders/${id}`,{signal:controller.signal,cache:'no-store'});
    if(request!==orderDetailRequest)return;
    if(order.id!==id||!order.document||!Array.isArray(order.lines)||!Array.isArray(order.comments))throw new Error('پاسخ جزئیات سفارش معتبر نیست.');
    active=order;selectedOrderStage=supplierOrderStage(order);
    orders=orders.map(row=>row.id===order.id?{...row,status:order.status,delivery_date:order.delivery_date}:row);
    renderOrder(active);
  } catch(e){
    if(request!==orderDetailRequest)return;
    active=null;
    const message=controller.signal.aborted?'دریافت سفارش طول کشید. اتصال را بررسی کنید و دوباره تلاش کنید.':e.message;
    detail.innerHTML=`<div class="sp-detail-state"><div class="error" role="alert">${esc(message)}</div><button id="retryOrderDetail" type="button" class="btn btn-secondary">تلاش مجدد برای دریافت سفارش</button></div>`;
    $('#retryOrderDetail').onclick=()=>openOrder(id);
    if(e.status===401){show('loginView');err($('#loginError'),'نشست شما پایان یافته؛ دوباره وارد شوید.');}
  } finally {
    clearTimeout(timeout);
    if(request===orderDetailRequest){
      orderDetailController=null;loadingOrderId=null;
      detail.setAttribute('aria-busy','false');renderOrderList();
    }
  }
}
function renderOrder(o) {
  const locked = ["accepted", "rejected", "cancelled", "submitted"].includes(
    o.status,
  );
  const brands = [
    ...new Set(o.lines.map((line) => line.brand).filter(Boolean)),
  ].sort((a, b) => a.localeCompare(b, "fa"));
  $("#orderDetail").innerHTML =
    `<div class="sp-card-head"><div><h1>سفارش <span dir="ltr">${esc(o.document.number)}</span></h1><p>${esc(o.supplier_name)} · ${esc(o.document.warehouse_name)}</p></div><div class="sp-toolbar">${status(o.status)}<a class="btn btn-secondary" href="/supplier-portal/api/orders/${o.id}/document.xlsx">خروجی اکسل</a></div></div><div class="sp-card-body"><div id="orderError" class="error hidden" role="alert"></div>${o.status === "changes_requested" && o.manager_comment ? `<div class="review-banner"><b>درخواست اصلاح نگین پخش:</b> ${esc(o.manager_comment)}</div>` : ""}<div class="sp-meta"><div><span>تاریخ تحویل درخواستی</span><strong>${esc(o.requested_delivery_date)}</strong></div><div><span>${o.status==="accepted"?"تاریخ تحویل تأییدشده":"پیشنهاد تأمین‌کننده (نیازمند تأیید نگین)"}</span><strong>${esc(o.proposed_delivery_date || "هنوز ثبت نشده")}</strong></div><div><span>تعداد اقلام</span><strong>${o.lines.length.toLocaleString("fa-IR")}</strong></div><div><span>وضعیت</span><strong>${esc(labels[o.status] || o.status)}</strong></div></div><form id="responseForm"><div class="sp-form two"><label class="field"><span>تاریخ تحویل قابل تعهد</span><input id="proposedDate" data-original-date="${esc(o.requested_delivery_date)}" value="${esc(o.proposed_delivery_date || o.requested_delivery_date)}" ${locked ? "disabled" : ""} required dir="ltr"></label><label class="field"><span>توضیح کلی تغییرات</span><input id="supplierComment" value="${esc(o.supplier_comment)}" ${locked ? "disabled" : ""} maxlength="1000" placeholder="در صورت تغییر تعداد یا تاریخ توضیح دهید"></label></div><fieldset class="line-filters section-gap"><legend>فیلتر اقلام سفارش</legend><label><span>کد تولیدکننده</span><input id="makerCodeFilter" type="search" autocomplete="off"></label><label><span>بارکد</span><input id="barcodeFilter" type="search" inputmode="numeric" autocomplete="off"></label><label><span>تعداد در کارتن</span><input id="packFilter" type="search" inputmode="decimal" autocomplete="off"></label><label><span>برند</span><select id="brandFilter"><option value="">همه برندها</option>${brands.map((brand) => `<option value="${esc(brand)}">${esc(brand)}</option>`).join("")}</select></label><span id="lineFilterCount" class="filter-count" role="status"></span></fieldset><div class="table-wrap compact-order-table"><table><thead><tr><th>کد کالا</th><th>کد تولیدکننده</th><th>بارکد</th><th>نام کالا</th><th>برند</th><th>گروه</th><th>تعداد در کارتن</th><th>کارتن سفارش</th><th>کارتن قابل ارسال</th></tr></thead><tbody>${o.lines.map((l, i) => `<tr data-line="${i}" data-original="${l.original_cartons}" data-maker="${esc(l.manufacturer_product_code || "")}" data-barcode="${esc(l.barcode || "")}" data-pack="${esc(l.conversion_rate)}" data-brand="${esc(l.brand || "")}" class="${Number(l.proposed_cartons) !== Number(l.original_cartons) ? "changed-row" : ""}"><td class="ltr">${esc(l.product_code)}</td><td class="ltr">${esc(l.manufacturer_product_code || "—")}</td><td class="ltr">${esc(l.barcode || "—")}</td><td><strong>${esc(l.product_name)}</strong></td><td>${esc(l.brand || "—")}</td><td>${esc(l.group_level3 || "—")}</td><td class="qty">${Number(l.conversion_rate).toLocaleString("fa-IR")}</td><td class="qty">${Number(l.original_cartons).toLocaleString("fa-IR")}</td><td><input class="line-control line-cartons" aria-label="کارتن قابل ارسال ${esc(l.product_name)}" type="number" min="0" max="1000000" value="${l.proposed_cartons}" ${locked ? "disabled" : ""}></td><input type="hidden" class="line-code" value="${esc(l.product_code)}"></tr>`).join("")}</tbody></table></div>${locked ? "" : `<div class="sp-toolbar response-actions section-gap"><button id="confirmWholeOrder" class="btn btn-primary" type="submit" data-mode="confirm">تأیید کامل سفارش</button><button id="requestOrderChange" class="btn btn-secondary" type="submit" data-mode="request_change">ارسال تغییر تعداد یا تاریخ</button><span id="changeStateHint" class="hint" aria-live="polite">بدون تغییر؛ سفارش آماده تأیید کامل است.</span></div>`}</form><div class="section-gap conversation-section"><h3>گفت‌وگوی سفارش</h3><div class="conversation">${o.comments.length ? o.comments.map((c) => `<div class="message ${c.author_kind}"><small>${esc(c.author_name)} · ${esc(new Date(c.created_at).toLocaleString("fa-IR"))}</small>${esc(c.body)}</div>`).join("") : '<div class="hint">هنوز پیامی ثبت نشده است.</div>'}</div><form id="commentForm" class="comment-row"><input id="commentBody" maxlength="1000" placeholder="پیام یا توضیح برای واحد خرید…" required><button class="btn btn-secondary" type="submit">ارسال پیام</button></form></div></div>`;
  $("#responseForm")
    ?.querySelectorAll(".line-cartons")
    .forEach((input) =>
      input.addEventListener("input", () => {
        input
          .closest("tr")
          .classList.toggle(
            "changed-row",
            Number(input.value) !==
              Number(input.closest("tr").dataset.original),
          );
        updateResponseActions();
      }),
    );
  $("#proposedDate")?.addEventListener("input", updateResponseActions);
  ["makerCodeFilter", "barcodeFilter", "packFilter", "brandFilter"].forEach(
    (id) =>
      $("#" + id)?.addEventListener(
        id === "brandFilter" ? "change" : "input",
        applyLineFilters,
      ),
  );
  $("#responseForm")?.addEventListener("submit", saveResponse);
  $("#commentForm").addEventListener("submit", sendComment);
  setupConversationPanel(o.comments.length);
  applyLineFilters();
  updateResponseActions();
}
function setupConversationPanel(commentCount) {
  const section = $(".conversation-section"),
    toolbar = $("#orderDetail > .sp-card-head .sp-toolbar");
  if (!section || !toolbar) return;
  section.id = "conversationPanel";
  section.classList.add("is-collapsed");
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "btn btn-secondary conversation-toggle";
  toggle.setAttribute("aria-controls", "conversationPanel");
  toggle.setAttribute("aria-expanded", "false");
  const label = `گفت‌وگو (${Number(commentCount).toLocaleString("fa-IR")})`;
  toggle.textContent = label;
  toggle.addEventListener("click", () => {
    const collapsed = section.classList.toggle("is-collapsed");
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.textContent = collapsed ? label : "بستن گفت‌وگو";
  });
  toolbar.append(toggle);
}
function responseHasChanges() {
  const form = $("#responseForm");
  if (!form) return false;
  const date = $("#proposedDate");
  if (date && date.value.trim() !== date.dataset.originalDate) return true;
  return [...form.querySelectorAll("[data-line]")].some(
    (tr) =>
      Number(tr.querySelector(".line-cartons").value) !==
      Number(tr.dataset.original),
  );
}
function updateResponseActions() {
  const changed = responseHasChanges(),
    confirm = $("#confirmWholeOrder"),
    request = $("#requestOrderChange"),
    hint = $("#changeStateHint");
  if (!confirm || !request) return;
  confirm.disabled = changed;
  confirm.setAttribute("aria-disabled", String(changed));
  request.disabled = !changed;
  request.setAttribute("aria-disabled", String(!changed));
  hint.textContent = changed
    ? "تغییر ثبت شده؛ تأیید کامل غیرفعال است و درخواست باید برای نگین پخش ارسال شود."
    : "بدون تغییر؛ سفارش آماده تأیید کامل است.";
}
function applyLineFilters() {
  const maker = norm($("#makerCodeFilter")?.value),
    barcode = norm($("#barcodeFilter")?.value),
    pack = norm($("#packFilter")?.value),
    brand = norm($("#brandFilter")?.value);
  let visible = 0;
  document.querySelectorAll("#responseForm [data-line]").forEach((row) => {
    const matches =
      (!maker || norm(row.dataset.maker).includes(maker)) &&
      (!barcode || norm(row.dataset.barcode).includes(barcode)) &&
      (!pack || norm(row.dataset.pack).includes(pack)) &&
      (!brand || norm(row.dataset.brand) === brand);
    row.hidden = !matches;
    if (matches) visible++;
  });
  const count = $("#lineFilterCount");
  if (count)
    count.textContent = `نمایش ${visible.toLocaleString("fa-IR")} از ${active.lines.length.toLocaleString("fa-IR")} قلم`;
}
async function saveResponse(e) {
  e.preventDefault();
  const mode = e.submitter.dataset.mode;
  if (
    !confirm(
      mode === "confirm"
        ? "کل سفارش با همین تعداد و تاریخ تأیید شود؟"
        : "درخواست تغییر تعداد یا تاریخ برای تأیید نگین پخش ارسال شود؟",
    )
  )
    return;
  const b = e.submitter;
  b.disabled = true;
  const lines = [...e.currentTarget.querySelectorAll("[data-line]")].map(
    (tr) => {
      const cartons = +tr.querySelector(".line-cartons").value,
        original = +tr.dataset.original;
      return {
        product_code: tr.querySelector(".line-code").value,
        proposed_cartons: cartons,
        line_status:
          cartons === 0
            ? "unavailable"
            : cartons === original
              ? "confirmed"
              : "changed",
        supplier_note: "",
      };
    },
  );
  try {
    active = await api(`/supplier-portal/api/orders/${active.id}/response`, {
      method: "PUT",
      body: JSON.stringify({
        expected_revision: active.revision,
        proposed_delivery_date: $("#proposedDate").value,
        supplier_comment: $("#supplierComment").value,
        submit: true,
        confirmation_mode: mode,
        lines,
      }),
    });
    renderOrder(active);
    await loadOrders();
  } catch (x) {
    err($("#orderError"), x.message);
    updateResponseActions();
  }
}
async function sendComment(e) {
  e.preventDefault();
  const b = e.submitter;
  b.disabled = true;
  try {
    await api(`/supplier-portal/api/orders/${active.id}/comments`, {
      method: "POST",
      body: JSON.stringify({ body: $("#commentBody").value }),
    });
    await openOrder(active.id,{refresh:true});
  } catch (x) {
    err($("#orderError"), x.message);
  } finally {
    b.disabled = false;
  }
}
boot();
