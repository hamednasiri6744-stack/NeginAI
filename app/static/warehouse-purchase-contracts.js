/* Purchase rules belong to a dated supplier/item context; previews never post. */
const purchaseState={contracts:[],catalog:{suppliers:[]},tab:'contracts',editing:null,products:[],selectedUncovered:new Set(),offset:0,total:0,busy:false,request:0,catalogRequest:0,discovery:null};
const purchaseScope={supplier:'همهٔ کالاهای تأمین‌کننده',brand:'برند',item:'کالا',collection:'قرارداد خرید'};
const purchaseBasis={manufacturer:'قیمت تولید',consumer:'قیمت مصرف',announcement:'اعلامیهٔ خرید'};
const purchaseStatus={draft:'پیش‌نویس',active:'فعال',archived:'بایگانی'};
const purchaseSourceMode={manual:'تنظیم دستی',discovered:'پیشنهاد از سابقه',migrated:'انتقال از تنظیمات قبلی'};
const p$=id=>document.getElementById(id);
function resetPurchaseContracts(){
  purchaseState.request++;purchaseState.catalogRequest++;if(typeof purchaseEditor!=='undefined')purchaseEditor.request++;purchaseState.contracts=[];purchaseState.products=[];purchaseState.editing=null;
  for(const id of ['purchaseContractDialog','purchaseHistoryDialog'])if(p$(id)?.open)p$(id).close();
}
function purchaseTaxLabel(item){return item.tax_status==='known'&&item.tax_rate!==null?`${fa(item.tax_rate)}٪${Number(item.tax_rate)===0?' · معاف':''}`:item.tax_status==='conflict'?'گروه ناسازگار':'نامشخص'}
function purchaseItemPriceCheck(item){
  const check=item.price_validation;if(!check)return '';
  const valid=['available','valid','ok','known'].includes(check.status);
  return `<small class="${valid?'purchase-price-ok':'purchase-missing'}">${esc(check.message||item.source_price_status||'')}${valid&&check.price!=null?' · '+fa(check.price):''}</small>`;
}
function purchaseRuleScope(r){return r.scope==='collection'?`${fa(r.product_codes.length)} کالای عضو قرارداد`:r.scope==='item'?`${r.product_code} · ${r.product_name}`:r.scope==='brand'?r.brand:'همهٔ کالاها'}
function purchaseDiscountLabel(r){return (r.discount_steps||[{percent:r.discount_percent}]).map(s=>fa(s.percent)+'٪').join(' سپس ')}
function purchaseHeaders(){return {'Content-Type':'application/json','X-Warehouse-Settings':'1'}}
function purchaseError(error){p$('purchaseMessage').textContent=error.message;p$('purchaseMessage').hidden=false}
function purchaseMessage(message){p$('purchaseMessage').textContent=message;p$('purchaseMessage').hidden=!message}
function purchaseCanEdit(){return has('warehouse.order.draft')}
function purchaseFillSuppliers(select,first){
  const value=select.value;
  select.innerHTML=`<option value="">${first}</option>`+purchaseState.catalog.suppliers.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join('');
  select.value=value;
}
async function loadPurchaseContracts(){
  const request=++purchaseState.catalogRequest,stock=p$('purchaseStock').value||'1';purchaseState.request++;
  if(purchaseState.catalog.stock_id!=null&&purchaseState.catalog.stock_id!==Number(stock)){
    p$('purchaseSupplierSections').innerHTML='';p$('purchaseContractRows').innerHTML='';p$('purchaseProductRows').innerHTML='';
    p$('purchaseUncoveredCount').textContent='';p$('purchaseCount').textContent='در حال دریافت قراردادهای انبار انتخاب‌شده…';
  }
  try{
    const result=await api('/warehouse-assistant/api/purchase-contracts?'+new URLSearchParams({stock_id:stock}));
    if(request!==purchaseState.catalogRequest)return;
    purchaseState.contracts=result.contracts.filter(r=>!r.materialized);purchaseState.legacyContracts=Object.fromEntries(result.contracts.filter(r=>r.materialized).map(r=>[r.id,r]));purchaseState.catalog=result.catalog;
    const knownSuppliers=new Set(result.catalog.suppliers.map(s=>s.id));
    for(const r of purchaseState.contracts)if(!knownSuppliers.has(r.supplier_id)){result.catalog.suppliers.push({id:r.supplier_id,name:r.supplier});knownSuppliers.add(r.supplier_id)}
    purchaseFillSuppliers(p$('purchaseSupplier'),'همهٔ تأمین‌کنندگان');
    purchaseFillSuppliers(p$('contractSupplier'),'انتخاب تأمین‌کننده');
    p$('purchaseDate').value||=result.catalog.today;
    p$('purchaseCatalogStatus').textContent=result.catalog.updated_at?`مالیات و فهرست کالا: ${new Date(result.catalog.updated_at).toLocaleString('fa-IR')}`:'برای شروع، «دریافت فهرست و مالیات» را بزنید.';
    p$('purchaseRefresh').hidden=!has('warehouse.data.refresh');
    p$('purchaseDiscover').hidden=!has('warehouse.data.refresh');
    p$('purchaseDiscover').disabled=!p$('purchaseSupplier').value;
    p$('purchaseNew').hidden=!purchaseCanEdit();p$('purchaseNew').disabled=!result.catalog.suppliers.length;
    await purchaseSelectTab(purchaseState.tab);
  }catch(error){if(request===purchaseState.catalogRequest)purchaseError(error)}
}
async function refreshPurchaseCatalog(button){
  button.disabled=true;purchaseMessage('در حال دریافت فهرست تأمین‌کنندگان، برندها و مالیات کالاها…');
  try{
    const result=await api('/warehouse-assistant/api/purchase-contracts/catalog/refresh',{method:'POST',headers:purchaseHeaders(),body:'{}'});
    await loadPurchaseContracts();
    purchaseMessage(`${fa(result.products)} کالا به‌روز شد؛ ${fa(result.unknown)} کالا مالیات نامشخص یا ناسازگار دارند.`);
    if(state.bootstrap?.latest_snapshot)await loadInventory(true);
    toast('مالیات و فهرست خرید به‌روز شد.');
  }catch(error){purchaseError(error);toast(error.message,true)}finally{button.disabled=false}
}
function renderPurchaseContracts(){
  if(purchaseState.catalog.contract_structure==='supplier_contracts'){renderSupplierContracts();return}
  const supplier=Number(p$('purchaseSupplier').value),query=normalizeSearchText(p$('purchaseSearch').value),status=p$('purchaseStatus').value;
  const rows=purchaseState.contracts.filter(r=>(!supplier||r.supplier_id===supplier)&&(!status||r.status===status)&&normalizeSearchText(`${r.title} ${r.supplier} ${r.brand} ${r.product_name} ${r.product_code}`).includes(query));
  const shownBatches=new Set();
  p$('purchaseContractRows').innerHTML=rows.length?rows.map(r=>`<tr>
    <td><strong>${esc(r.supplier)}</strong><small>${esc(r.manufacturer||'')}</small></td><td><strong>${r.product_code?esc(r.product_code)+' · '+esc(r.product_name):esc(purchaseRuleScope(r))}</strong><small>${esc(r.brand||'')} · ${esc(r.group_name||'')}</small><small>${esc(r.title)}${r.agreement_reference?' · مرجع '+esc(r.agreement_reference):''} · ${purchaseSourceMode[r.source_mode]||purchaseSourceMode.manual}</small></td>
    <td class="purchase-date">${esc(r.start_date)}<small>تا ${esc(r.end_date||'بدون پایان')}</small></td>
    <td>${esc(purchaseBasis[r.basis])}<small>${r.includes_tax?'شامل مالیات':'بدون مالیات'}${Number(r.adjustment_percent)?` · تغییر ${fa(r.adjustment_percent)}٪`:''}</small></td>
    <td>${esc(purchaseDiscountLabel(r))}</td><td>${esc(tailDescription(r))}</td><td><span class="purchase-badge ${r.status}">${purchaseStatus[r.status]}</span></td>
    <td><div class="purchase-actions">${purchaseCanEdit()&&r.batch_id&&!shownBatches.has(r.batch_id)&&r.status!=='archived'?(shownBatches.add(r.batch_id),`<button type="button" data-purchase-batch="${esc(r.batch_id)}">ویرایش مشترک مجموعه</button>`):''}${purchaseCanEdit()&&r.status!=='archived'?`<button type="button" data-purchase-edit="${esc(r.id)}">ویرایش</button>`:''}${purchaseCanEdit()?`<button type="button" data-purchase-copy="${esc(r.id)}">قرارداد جدید از این</button>`:''}<button type="button" data-purchase-history="${esc(r.id)}">سابقه</button>${purchaseCanEdit()&&r.status!=='archived'?`<button type="button" class="danger-action" data-purchase-archive="${esc(r.id)}">بایگانی</button>`:''}</div></td></tr>`).join(''):'<tr><td colspan="8" class="purchase-empty">قراردادی با این فیلتر وجود ندارد.</td></tr>';
  p$('purchaseCount').textContent=`${fa(rows.length)} قرارداد کالا · نسخه‌ها و شرایط هر کالا مستقل است`;
  p$('purchaseDiscover').disabled=!p$('purchaseSupplier').value;
}
function purchaseSelectTab(tab){
  if(tab==='uncovered'){tab='products';p$('purchaseCoverage').value='uncovered'}
  if(purchaseState.catalog.contract_structure==='supplier_contracts'&&!p$('purchaseSupplier').value)tab='contracts';
  if(tab==='products'&&!['covered','uncovered'].includes(p$('purchaseCoverage').value))p$('purchaseCoverage').value='covered';
  purchaseState.tab=tab;purchaseState.request++;
  if(groupedPurchases())renderSupplierContracts();
  p$('purchaseContractsPane').hidden=tab!=='contracts'||(groupedPurchases()&&!p$('purchaseSupplier').value);p$('purchaseProductsPane').hidden=tab==='contracts';
  document.querySelectorAll('[data-purchase-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.purchaseTab===tab)));
  p$('purchaseDateLabel').hidden=groupedPurchases()||tab!=='products';p$('purchaseStatusLabel').hidden=tab!=='contracts'||!p$('purchaseSupplier').value;
  if(p$('purchaseSupplierSections'))p$('purchaseSupplierSections').hidden=!!p$('purchaseSupplier').value;
  renderPurchaseCoverageTabs();
  if(tab!=='contracts')return loadPurchaseProducts(true);
  renderPurchaseContracts();
}
async function loadPurchaseProducts(reset=false){
  const request=++purchaseState.request;
  purchaseState.selectedUncovered.clear();renderPurchaseBulkSelection();
  if(reset)purchaseState.offset=0;
  if(reset){purchaseState.products=[];p$('purchaseProductRows').innerHTML='<tr><td colspan="12" class="purchase-empty">در حال بررسی قواعد…</td></tr>';p$('purchaseMore').hidden=true}
  const supplier=p$('purchaseSupplier').value;
  if(!supplier){p$('purchaseProductRows').innerHTML='<tr><td colspan="12" class="purchase-empty">تأمین‌کننده را انتخاب کنید تا قاعدهٔ هر کالا در تاریخ انتخاب‌شده نمایش داده شود.</td></tr>';p$('purchaseMore').hidden=true;return}
  const uncovered=p$('purchaseCoverage').value==='uncovered';
  const query=new URLSearchParams({supplier_id:supplier,on_date:purchaseState.catalog.today||p$('purchaseDate').value,search:p$('purchaseSearch').value,offset:0,limit:500,coverage:p$('purchaseCoverage').value||'all',supply_only:'true'});
  if(uncovered)query.set('without_contract','true');
  const stock=p$('purchaseStock')?.value||'1';query.set('stock_id',stock);
  try{
    const result=await api('/warehouse-assistant/api/purchase-contracts/products?'+query);
    if(request!==purchaseState.request)return;
    // Header filters and sorting must cover every matching item, not only the first page.
    const items=[...result.items];
    if(result.total>20000)throw new Error('برای نمایش همهٔ قواعد، جست‌وجوی کالا را محدودتر کنید.');
    while(items.length<result.total){
      query.set('offset',String(items.length));const page=await api('/warehouse-assistant/api/purchase-contracts/products?'+query);
      if(request!==purchaseState.request)return;
      if(!page.items.length||page.total!==result.total||(page.on_date&&page.on_date!==result.on_date))throw new Error('فهرست کالا هنگام دریافت تغییر کرد؛ دوباره بازخوانی کنید.');
      items.push(...page.items);
    }
    purchaseState.products=items;purchaseState.total=result.total;
    const warehouse=selectedPurchaseWarehouse();
    if(warehouse&&result.coverage_counts){warehouse.uncovered_product_count=result.coverage_counts.uncovered;warehouse.covered_product_count=result.coverage_counts.covered;warehouse.product_count=result.coverage_counts.all}
    renderPurchaseCoverageTabs(result.coverage_counts);
    const missing=result.coverage_counts?.uncovered??result.uncovered_product_count;
    p$('purchaseUncoveredCount').textContent=missing==null?'':` (${fa(missing)} فاقد قرارداد)`;
    p$('purchaseProductRows').innerHTML=purchaseState.products.map(item=>{
      const r=item.contract;
      return `<tr><td>${!r&&purchaseCanEdit()?`<input type="checkbox" data-purchase-uncovered="${esc(item.product_code)}" aria-label="انتخاب ${esc(item.product_code)} برای قرارداد">`:"—"}</td><td>${esc(item.product_code)}</td><td>${esc(item.manufacturer_product_code||'—')}</td><td>${esc(item.barcode||'—')}</td><td><strong>${esc(item.product_name)}</strong></td><td>${esc(item.brand||'—')}</td><td>${esc(item.group_level3||item.group_name||'—')}</td><td>${purchaseTaxLabel(item)}</td><td>${r?`${esc(purchaseScope[r.scope])}<small>${esc(r.title)} · نسخه ${fa(r.revision)}</small>`:'<span class="purchase-missing">بدون قرارداد معتبر</span>'}</td><td>${r?esc(purchaseBasis[r.basis]):'—'}${purchaseItemPriceCheck(item)}</td><td>${r?`${esc(purchaseDiscountLabel(r))} / ${esc(tailDescription(r))}`:'—'}</td><td>${purchaseCanEdit()?`<button type="button" data-purchase-item="${esc(item.product_code)}">${r?.scope==='collection'?'ویرایش قرارداد':r?.scope==='item'?'ویرایش قاعدهٔ کالا':purchaseState.catalog.contract_structure==='supplier_contracts'?'قرارداد جدید برای کالا':'قاعدهٔ اختصاصی'}</button>`:''}${r?`<button type="button" data-purchase-product-history="${esc(r.id)}">سابقه قرارداد</button>${purchaseCanEdit()?`<button type="button" data-purchase-product-end="${esc(r.id)}">پایان قرارداد</button>`:''}`:''}</td></tr>`;
    }).join('')||`<tr><td colspan="12" class="purchase-empty">${uncovered&&!p$('purchaseSearch').value?'این تأمین‌کننده در فهرست فعلی کالای فاقد قرارداد معتبر برای امروز ندارد.':'کالایی پیدا نشد.'}</td></tr>`;
    p$('purchaseCount').textContent=uncovered?`${fa(result.total)} کالای فاقد قرارداد${p$('purchaseSearch').value?' مطابق جست‌وجو':''} · امروز ${result.on_date}`:`${fa(purchaseState.products.length)} از ${fa(result.total)} کالا · تاریخ مبنا ${result.on_date}`;
    p$('purchaseCount').textContent+=` · ${purchaseStockName(Number(stock))}`;
    p$('purchaseMore').hidden=purchaseState.products.length>=result.total;
  }catch(error){if(request===purchaseState.request){purchaseError(error);purchaseState.products=[];p$('purchaseProductRows').innerHTML='<tr><td colspan="12" class="purchase-empty">دریافت قواعد کامل نشد؛ دوباره بازخوانی کنید.</td></tr>';p$('purchaseMore').hidden=true}}
}
async function purchaseArchive(r){
  if(!window.confirm(`قرارداد «${r.title}» بایگانی شود؟ سابقه حفظ می‌شود و این قرارداد دیگر برای خرید کالاهای عضو استفاده نمی‌شود.`))return;
  try{await api(`/warehouse-assistant/api/purchase-contracts/${encodeURIComponent(r.id)}/archive`,{method:'POST',headers:purchaseHeaders(),body:JSON.stringify({expected_revision:r.revision,confirmed:true})});await loadPurchaseContracts();toast('قرارداد بایگانی شد؛ سابقه محفوظ است.')}catch(error){purchaseError(error)}
}
async function purchaseHistory(r){
  try{
    const result=await api(`/warehouse-assistant/api/purchase-contracts/${encodeURIComponent(r.id)}/history`);
    p$('purchaseHistoryTitle').textContent='سابقهٔ '+r.title;
    p$('purchaseHistoryBody').innerHTML=result.history.map(h=>{const c=h.contract;return `<article><strong>نسخه ${fa(c.revision)} · ${purchaseStatus[c.status]} · ${esc(c.title)}</strong><p>${esc(c.supplier)} · ${esc(purchaseStockName(c.stock_id))} · ${esc(purchaseRuleScope(c))}</p><p>${esc(c.start_date)} تا ${esc(c.end_date||'بدون پایان')} · ${esc(purchaseBasis[c.basis])} · ${c.includes_tax?'قیمت شامل مالیات':'قیمت بدون مالیات'} · تغییر تجاری ${fa(c.adjustment_percent)}٪ · تخفیف ستون ${esc(purchaseDiscountLabel(c))} · انتهایی ${esc(tailDescription(c))}</p><p>${purchaseSourceMode[c.source_mode]||purchaseSourceMode.manual}${c.agreement_reference?' · مرجع '+esc(c.agreement_reference):''}</p><p>${esc(c.note)}</p>${c.scope==='collection'?`<details><summary>کالاهای این نسخه (${fa(c.product_codes.length)})</summary><p>${c.product_codes.map(code=>esc(code)+(c.product_end_dates?.[code]?' · پایان '+esc(c.product_end_dates[code]):'')).join('، ')}</p></details>`:''}<small>${esc(h.actor)} · ${new Date(h.saved_at).toLocaleString('fa-IR')}</small></article>`}).join('');
    p$('purchaseHistoryDialog').showModal();
    if(r.scope==='collection'){
      p$('purchaseHistoryBody').insertAdjacentHTML('beforeend',`<details><summary>کد کالاهای نسخهٔ فعلی (${fa(r.product_codes.length)})</summary><p>${r.product_codes.map(esc).join('، ')}</p></details>`);
      if(r.legacy_contract_ids?.length)p$('purchaseHistoryBody').insertAdjacentHTML('beforeend',`<details><summary>سوابق کالایی قبل از انتقال ساختار</summary>${r.legacy_contract_ids.map((id,index)=>`<button type="button" data-purchase-legacy="${esc(id)}">کالای ${esc(purchaseState.legacyContracts?.[id]?.product_code||fa(index+1))}</button>`).join('')}</details>`);
    }
  }catch(error){purchaseError(error)}
}
function discoveryConfidence(value){return value==='high'?'اطمینان بالا':value==='medium'?'نیازمند کنترل':'نیازمند بررسی دقیق'}
function renderPurchaseDiscovery(result){
  const proposals=result.proposals||[],rejections=Object.entries(result.rejections||{}).map(([reason,count])=>`${fa(count)} مورد: ${esc(reason)}`).join(' · ');
  p$('purchaseDiscoveryTitle').textContent=`کشف قرارداد اولیهٔ ${result.supplier||''}`;
  p$('purchaseDiscoveryBody').innerHTML=`<div class="purchase-discovery-summary"><span>${fa(result.rows_read)} قلم خوانده شد</span><span>${fa(result.eligible_count)} شاهد قابل محاسبه</span><span>${fa(result.rejected_count)} مورد نیازمند بررسی</span><span>سال ${fa(result.from_year)} تا ${fa(result.to_year)}</span></div>
    ${proposals.map((proposal,index)=>`<article class="purchase-discovery-proposal"><div><strong>${esc(proposal.label)} <span class="purchase-discovery-confidence ${proposal.confidence}">${discoveryConfidence(proposal.confidence)}</span></strong><small>${fa(proposal.evidence_count)} شاهد در ${fa(proposal.invoice_count)} فاکتور و ${fa(proposal.product_count)} کالا · پوشش ${fa(proposal.coverage_percent)}٪</small></div><button type="button" data-discovery-proposal="${index}">بازکردن در تنظیمات دستی</button></article>`).join('')||'<p class="purchase-empty">الگوی قابل اتکایی پیدا نشد؛ قرارداد را دستی و با فاکتور نمونه تنظیم کنید.</p>'}
    ${rejections?`<p class="purchase-discovery-warning">موارد کنارگذاشته‌شده: ${rejections}</p>`:''}
    ${(result.warnings||[]).map(value=>`<p class="purchase-discovery-warning">${esc(value)}</p>`).join('')}`;
}
async function discoverPurchaseContract(){
  const supplierId=Number(p$('purchaseSupplier').value);
  if(!supplierId){purchaseMessage('ابتدا یک تأمین‌کننده انتخاب کنید.');return}
  p$('purchaseDiscoveryTitle').textContent='کشف قرارداد اولیه';p$('purchaseDiscoveryBody').setAttribute('aria-busy','true');p$('purchaseDiscoveryBody').textContent='در حال خواندن سابقهٔ تأییدشده و بازسازی قواعد…';p$('purchaseDiscoveryDialog').showModal();p$('purchaseDiscover').disabled=true;
  try{
    const result=await api('/warehouse-assistant/api/purchase-contracts/discovery',{method:'POST',headers:purchaseHeaders(),body:JSON.stringify({supplier_id:supplierId})});
    purchaseState.discovery=result;renderPurchaseDiscovery(result);
  }catch(error){p$('purchaseDiscoveryBody').innerHTML=`<p class="purchase-discovery-warning" role="alert">${esc(error.message)}</p><button type="button" data-discovery-retry>تلاش دوباره</button>`}finally{p$('purchaseDiscoveryBody').removeAttribute('aria-busy');p$('purchaseDiscover').disabled=!p$('purchaseSupplier').value}
}
function applyDiscoveryProposal(index){
  const result=purchaseState.discovery,proposal=result?.proposals?.[index];if(!proposal)return;
  const supplier=purchaseState.catalog.suppliers.find(item=>item.id===result.supplier_id);
  const manufacturer=purchaseState.catalog.manufacturers?.find(item=>normalizeSearchText(item.name)===normalizeSearchText(supplier?.name));
  p$('purchaseDiscoveryDialog').close();
  editPurchaseContract({...proposal,supplier_id:result.supplier_id,manufacturer_id:manufacturer?.id||'',title:`قرارداد خرید ${result.supplier}`,
    start_date:purchaseState.catalog.today,status:'draft',source_mode:'discovered',evidence_run_id:result.run_id,
    note:`پیشنهاد از ${proposal.evidence_count} شاهد تاریخی؛ پیش از فعال‌سازی با نمونه‌های واقعی بازبینی شود.`},false);
}
document.addEventListener('DOMContentLoaded',()=>{
  if(!p$('purchaseView'))return;
  p$('purchaseRefresh').addEventListener('click',e=>refreshPurchaseCatalog(e.currentTarget));
  p$('purchaseDiscover').addEventListener('click',discoverPurchaseContract);
  p$('inventoryTaxRefresh').addEventListener('click',e=>refreshPurchaseCatalog(e.currentTarget));
  p$('purchaseNew').addEventListener('click',()=>editPurchaseContract());
  document.querySelectorAll('[data-purchase-tab]').forEach(b=>b.addEventListener('click',()=>purchaseSelectTab(b.dataset.purchaseTab)));
  const filter=()=>{if(!p$('purchaseSupplier').value&&purchaseState.catalog.contract_structure==='supplier_contracts'){purchaseSelectTab('contracts');return}p$('purchaseProductsPane').hidden?renderPurchaseContracts():loadPurchaseProducts(true)};
  p$('purchaseSupplier').addEventListener('change',()=>selectPurchaseSupplier(p$('purchaseSupplier').value));p$('purchaseStatus').addEventListener('change',filter);p$('purchaseDate').addEventListener('change',filter);
  p$('purchaseCoverage').addEventListener('change',()=>loadPurchaseProducts(true));
  p$('purchaseStock')?.addEventListener('change',()=>loadPurchaseContracts());
  let timer;p$('purchaseSearch').addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(filter,300)});
  p$('purchaseMore').addEventListener('click',()=>{purchaseState.offset=purchaseState.products.length;loadPurchaseProducts()});
  p$('purchaseContractRows').addEventListener('click',e=>{
    const batch=e.target.closest('[data-purchase-batch]')?.dataset.purchaseBatch;
    if(batch){const group=purchaseState.contracts.filter(r=>r.batch_id===batch&&r.status!=='archived');if(group.length)editPurchaseContract(group[0],false,group);return}
    for(const [key,action] of [['purchaseEdit',r=>editPurchaseContract(r)],['purchaseCopy',r=>editPurchaseContract(r,true)],['purchaseArchive',purchaseArchive],['purchaseHistory',purchaseHistory],['purchaseEnd',openPurchaseEnd]]){
      const b=e.target.closest('button');if(b?.dataset[key]){const r=purchaseState.contracts.find(x=>x.id===b.dataset[key]);if(r)action(r);break}
    }
  });
  p$('purchaseProductRows').addEventListener('click',e=>{
    const action=e.target.closest('[data-purchase-product-history],[data-purchase-product-end]');if(action){const r=purchaseState.contracts.find(r=>r.id===(action.dataset.purchaseProductHistory||action.dataset.purchaseProductEnd));if(r)(action.dataset.purchaseProductHistory?purchaseHistory:openPurchaseEnd)(r);return}
    const code=e.target.closest('[data-purchase-item]')?.dataset.purchaseItem;if(!code)return;
    const item=purchaseState.products.find(i=>i.product_code===code);
    if(item.contract?.scope==='collection'){editPurchaseContract(purchaseState.contracts.find(r=>r.id===item.contract.id)||item.contract);return}
    if(purchaseState.catalog.contract_structure==='supplier_contracts'){editPurchaseContract({supplier_id:item.supplier_id,product_codes:[code],title:'خرید '+item.product_name,status:'draft'});return}
    if(item.contract?.scope==='item'){editPurchaseContract(item.contract);return}
    editPurchaseContract({...item.contract,id:undefined,revision:undefined,supplier_id:item.supplier_id,manufacturer_id:item.manufacturer_id,scope:'item',brand_id:null,product_code:code,title:'خرید '+item.product_name,status:'draft'},true);
  });
  p$('purchaseHistoryClose').addEventListener('click',()=>p$('purchaseHistoryDialog').close());
  p$('purchaseHistoryBody').addEventListener('click',e=>{const id=e.target.closest('[data-purchase-legacy]')?.dataset.purchaseLegacy;if(id)purchaseHistory({id,title:'کالا قبل از انتقال ساختار'})});
  p$('purchaseDiscoveryClose').addEventListener('click',()=>p$('purchaseDiscoveryDialog').close());
  p$('purchaseDiscoveryBody').addEventListener('click',event=>{if(event.target.closest('[data-discovery-retry]')){discoverPurchaseContract();return}const index=event.target.closest('[data-discovery-proposal]')?.dataset.discoveryProposal;if(index!==undefined)applyDiscoveryProposal(Number(index))});
});
