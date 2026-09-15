/* Supplier -> dated agreement -> explicit product membership. */
function groupedPurchases(){return purchaseState.catalog.contract_structure==='supplier_contracts'}
function purchaseStockName(stockId){return stockId==null?'همهٔ انبارها':purchaseState.catalog.stocks?.find(s=>s.id===stockId)?.name||`انبار ${fa(stockId)}`}
function purchaseContractInStock(r){return r.stock_id==null||r.stock_id===Number(p$('purchaseStock').value||1)}
function purchaseSupplierRows(){
  const suppliers=new Map(purchaseState.catalog.suppliers.map(s=>[s.id,{...s}]));
  for(const r of purchaseState.contracts)if(!suppliers.has(r.supplier_id))suppliers.set(r.supplier_id,{id:r.supplier_id,name:r.supplier});
  return [...suppliers.values()].map(s=>{
    const today=purchaseState.catalog.today;
    const contracts=purchaseState.contracts.filter(r=>r.supplier_id===s.id&&purchaseContractInStock(r)),active=contracts.filter(r=>r.status==='active'&&r.start_date<=today&&(!r.end_date||today<=r.end_date));
    return {...s,contracts,active:active.length,members:new Set(active.flatMap(r=>r.product_codes||[r.product_code])).size};
  }).sort((a,b)=>Number((b.active_warehouse_count||0)>0)-Number((a.active_warehouse_count||0)>0)||b.active-a.active||a.name.localeCompare(b.name,'fa'));
}
function selectedPurchaseWarehouse(){return purchaseState.catalog.suppliers.find(s=>s.id===Number(p$('purchaseSupplier').value))?.warehouses?.find(w=>w.id===Number(p$('purchaseStock').value))}
function selectPurchaseSupplier(id,stockId=null,coverage=null){
  p$('purchaseSupplier').value=String(id||'');p$('purchaseSearch').value='';
  const supplier=purchaseState.catalog.suppliers.find(s=>s.id===Number(id));
  const chosen=stockId||supplier?.warehouses?.find(w=>w.active&&w.id===Number(p$('purchaseStock').value))?.id||supplier?.warehouses?.find(w=>w.active)?.id||supplier?.warehouses?.[0]?.id||1;
  p$('purchaseStock').value=String(chosen);p$('purchaseCoverage').value=coverage||'covered';
  purchaseSelectTab(coverage?'products':'contracts');p$('purchaseSupplierTitle').focus();
}
function selectPurchaseWarehouse(id){
  p$('purchaseStock').value=String(id);p$('purchaseSearch').value='';
  purchaseSelectTab(purchaseState.tab);
}
function supplierOverviewCard(s){
  const active=(s.warehouses||[]).filter(w=>w.active);
  const status=purchaseState.catalog.supply_scope_known===false?'دامنهٔ تأمین مشخص نشده':`${fa(active.length)} انبار فعال`;
  return `<article class="purchase-supplier-card"><button type="button" class="purchase-supplier-heading" data-purchase-supplier="${s.id}"><strong>${esc(s.name)}</strong><span>${status}</span></button>${active.length?`<div class="purchase-supplier-grid"><span>انبار</span><span>قرارداد معتبر</span><span>فاقد قرارداد</span>${active.map(w=>`<span>${esc(w.name.replace('انبار مرکزی ','').replace('انبار ',''))}</span><span>${fa(w.active_contract_count)}</span><button type="button" class="purchase-uncovered-link ${w.uncovered_product_count?'has-missing':''}" data-purchase-supplier="${s.id}" data-purchase-stock="${w.id}" data-purchase-coverage="uncovered" aria-label="${esc(s.name)} · ${esc(w.name)} · ${fa(w.uncovered_product_count)} کالای فاقد قرارداد">${fa(w.uncovered_product_count)}</button>`).join('')}</div>`:'<small>انبارهای این تأمین‌کننده را در «تأمین مجاز انبار» بررسی کنید.</small>'}</article>`;
}
function renderSupplierContracts(){
  const sid=Number(p$('purchaseSupplier').value),query=normalizeSearchText(p$('purchaseSearch').value),status=p$('purchaseStatus').value;
  const suppliers=purchaseSupplierRows(),selected=suppliers.find(s=>s.id===sid);
  const warehouse=selectedPurchaseWarehouse();
  p$('purchaseSupplierSections').hidden=!!sid;p$('purchaseSupplierTrail').hidden=!sid;
  p$('purchaseContractsPane').hidden=!sid||purchaseState.tab!=='contracts';p$('purchaseNew').disabled=!sid||(selected?.warehouses&&!warehouse?.active);
  p$('purchaseSupplierTitle').textContent=selected?.name||'تأمین‌کنندگان';
  p$('purchaseUncoveredCount').textContent=warehouse?` (${fa(warehouse.uncovered_product_count)})`:'';
  p$('purchaseWarehouseTabs').hidden=!sid;p$('purchaseCoverageLabel').hidden=true;
  p$('purchaseStatusLabel').hidden=!sid||purchaseState.tab!=='contracts';p$('purchaseStockLabel').hidden=true;
  p$('purchaseSupplier').closest?.('label')?.toggleAttribute('hidden',!sid);
  p$('purchaseDateLabel').hidden=true;
  p$('purchaseWarehouseTabs').innerHTML=(selected?.warehouses||[]).map(w=>`<button type="button" data-purchase-warehouse="${w.id}" aria-pressed="${w.id===Number(p$('purchaseStock').value)}"><strong>${esc(w.name)}</strong><span>${w.active?`${fa(w.product_count)} کالا · ${fa(w.uncovered_product_count)} فاقد قرارداد`:'تأمین غیرفعال · مشاهدهٔ سوابق'}</span></button>`).join('');
  p$('purchaseWarehouseNotice').hidden=!sid||!!warehouse?.active;
  p$('purchaseWarehouseNotice').textContent=purchaseState.catalog.supply_scope_known===false?'ابتدا دامنهٔ تأمین را در «تأمین مجاز انبار» مشخص کنید.':'تأمین این انبار برای این تأمین‌کننده فعال نیست؛ قراردادهای قبلی برای مشاهدهٔ سوابق نمایش داده می‌شوند.';
  p$('purchaseDiscover').disabled=!sid;
  document.querySelectorAll('[data-purchase-tab]').forEach(b=>{b.disabled=!sid;b.hidden=!sid});
  if(!sid){
    p$('purchaseProductsPane').hidden=true;
    const visible=suppliers.filter(s=>normalizeSearchText(s.name).includes(query));
    p$('purchaseSupplierSections').innerHTML=visible.map(supplierOverviewCard).join('')||'<p class="purchase-empty">تأمین‌کننده‌ای پیدا نشد.</p>';
    p$('purchaseCount').textContent=`${fa(visible.length)} تأمین‌کننده · پوشش قراردادهای امروز ${purchaseState.catalog.today||''}`;
    p$('purchaseContractRows').innerHTML='';return;
  }
  const rows=purchaseState.contracts.filter(r=>r.supplier_id===sid&&purchaseContractInStock(r)&&(!status||r.status===status)&&normalizeSearchText(`${r.title} ${r.agreement_reference||''} ${(r.product_codes||[]).join(' ')}`).includes(query));
  p$('purchaseContractRows').innerHTML=rows.map(r=>`<tr>
    <td><strong>${esc(r.title)}</strong><small>${esc(purchaseStockName(r.stock_id))} · ${esc(r.agreement_reference||'بدون شماره مرجع')} · نسخه ${fa(r.revision)}</small></td>
    <td><button type="button" class="purchase-member-link" data-purchase-members="${esc(r.id)}">${fa(r.product_codes?.length||1)} کالا · مدیریت</button>${purchaseCanEdit()&&r.status!=='archived'?`<button type="button" data-purchase-add-members="${esc(r.id)}">افزودن کالا</button><button type="button" data-purchase-members="${esc(r.id)}">حذف کالا</button>`:''}</td>
    <td class="purchase-date">${esc(r.start_date)}<small>تا ${esc(r.end_date||'بدون پایان')}</small></td>
    <td>${esc(purchaseBasis[r.basis])}<small>${r.includes_tax?'شامل مالیات':'بدون مالیات'}${Number(r.adjustment_percent)?' · تغییر '+fa(r.adjustment_percent)+'٪':''}</small></td>
    <td>${esc(purchaseDiscountLabel(r))}</td><td>${esc(tailDescription(r))}</td>
    <td><span class="purchase-badge ${r.status}">${purchaseStatus[r.status]}</span></td>
    <td>${purchaseCanEdit()&&r.status!=='archived'?`<button type="button" data-purchase-end="${esc(r.id)}">پایان قرارداد</button>`:''}<button type="button" data-purchase-history="${esc(r.id)}">سابقه قرارداد</button><div class="purchase-actions">${purchaseCanEdit()&&r.status!=='archived'?`<button type="button" data-purchase-edit="${esc(r.id)}">ویرایش قرارداد</button>`:''}${purchaseCanEdit()?`<button type="button" data-purchase-copy="${esc(r.id)}">کپی برای انبار یا دورهٔ دیگر</button>`:''}${purchaseCanEdit()&&r.status!=='archived'?`<button type="button" class="danger-action" data-purchase-archive="${esc(r.id)}">بایگانی</button>`:''}</div></td>
  </tr>`).join('')||'<tr><td colspan="8" class="purchase-empty">قراردادی با این فیلتر نیست؛ برای این تأمین‌کننده قرارداد جدید بسازید.</td></tr>';
  p$('purchaseCount').textContent=`${fa(rows.length)} قرارداد · ${esc(selected?.name||'')}`;
}
function renderPurchaseBulkSelection(){
  const count=purchaseState.selectedUncovered.size;
  p$('purchaseSelectedCount').textContent=count?`${fa(count)} کالا انتخاب شده`:'';
  p$('purchaseCreateSelected').disabled=!count||!purchaseCanEdit();
  for(const id of ['purchaseSelectUncovered','purchaseClearUncovered','purchaseCreateSelected'])p$(id).hidden=!purchaseCanEdit();
  document.querySelectorAll('[data-purchase-uncovered]').forEach(input=>input.checked=purchaseState.selectedUncovered.has(input.dataset.purchaseUncovered));
}
function createPurchaseFromSelection(){
  if(!purchaseState.selectedUncovered.size)return;
  editSupplierContract({supplier_id:Number(p$('purchaseSupplier').value),stock_id:Number(p$('purchaseStock').value),product_codes:[...purchaseState.selectedUncovered]});
}
function showPurchaseMembers(r){return openPurchaseMembers(r,'members')}
document.addEventListener('DOMContentLoaded',()=>{
  p$('purchaseProductRows').addEventListener('change',e=>{const input=e.target.closest('[data-purchase-uncovered]');if(!input)return;input.checked?purchaseState.selectedUncovered.add(input.dataset.purchaseUncovered):purchaseState.selectedUncovered.delete(input.dataset.purchaseUncovered);renderPurchaseBulkSelection()});
  p$('purchaseSelectUncovered').addEventListener('click',()=>{purchaseState.products.filter(i=>!i.contract).forEach(i=>purchaseState.selectedUncovered.add(i.product_code));renderPurchaseBulkSelection()});
  p$('purchaseClearUncovered').addEventListener('click',()=>{purchaseState.selectedUncovered.clear();renderPurchaseBulkSelection()});
  p$('purchaseCreateSelected').addEventListener('click',createPurchaseFromSelection);
  p$('purchaseSupplierSections').addEventListener('click',e=>{const b=e.target.closest('[data-purchase-supplier]');if(b)selectPurchaseSupplier(b.dataset.purchaseSupplier,Number(b.dataset.purchaseStock)||null,b.dataset.purchaseCoverage)});
  p$('purchaseWarehouseTabs').addEventListener('click',e=>{const b=e.target.closest('[data-purchase-warehouse]');if(b)selectPurchaseWarehouse(b.dataset.purchaseWarehouse)});
  p$('purchaseAllSuppliers').addEventListener('click',()=>selectPurchaseSupplier(''));
  p$('purchaseContractRows').addEventListener('click',e=>{const id=e.target.closest('[data-purchase-members]')?.dataset.purchaseMembers;const r=purchaseState.contracts.find(r=>r.id===id);if(r)showPurchaseMembers(r)});
});
