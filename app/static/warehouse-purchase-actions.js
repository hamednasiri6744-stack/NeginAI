const purchaseEndState={contract:null,busy:false};
function renderPurchaseCoverageTabs(counts=null){
  const coverage=p$('purchaseCoverage').value,warehouse=selectedPurchaseWarehouse();
  const numbers=counts||{covered:warehouse?.covered_product_count,uncovered:warehouse?.uncovered_product_count};
  document.querySelectorAll('[data-purchase-coverage-tab]').forEach(b=>{
    const key=b.dataset.purchaseCoverageTab;
    b.setAttribute('aria-pressed',String(key===coverage));
    b.textContent=(key==='covered'?'دارای قرارداد فعال جاری':'فاقد قرارداد فعال جاری')+(numbers[key]==null?'':` (${fa(numbers[key])})`);
  });
  p$('purchaseProductSelectionControls').hidden=coverage!=='uncovered'||!purchaseCanEdit();
}
function openPurchaseEnd(r){
  if(!purchaseCanEdit()||r.status==='archived'||purchaseEndState.busy)return;
  purchaseEndState.contract=r;
  p$('purchaseEndTitle').textContent='پایان قرارداد · '+r.title;
  p$('purchaseEndSummary').textContent=`${r.supplier} · ${purchaseStockName(r.stock_id)} · ${fa(r.product_codes?.length||1)} کالا${r.stock_id==null?' · قرارداد مشترک است؛ پایان برای همهٔ انبارها اعمال می‌شود.':''}`;
  p$('purchaseEndDate').value=r.end_date||'';p$('purchaseEndError').textContent='';
  p$('purchaseEndDialog').showModal();p$('purchaseEndDate').focus?.();
}
async function savePurchaseEnd(event){
  event.preventDefault();if(purchaseEndState.busy||!purchaseCanEdit())return;
  const r=purchaseEndState.contract;if(!r)return;
  purchaseEndState.busy=true;p$('purchaseEndSave').disabled=true;p$('purchaseEndClose').disabled=true;p$('purchaseEndDate').disabled=true;
  p$('purchaseEndError').textContent='';
  try{
    await api('/warehouse-assistant/api/purchase-contracts/'+encodeURIComponent(r.id)+'/end',{method:'PUT',headers:purchaseHeaders(),body:JSON.stringify({expected_revision:r.revision,end_date:p$('purchaseEndDate').value})});
    p$('purchaseEndDialog').close();await loadPurchaseContracts();toast('پایان قرارداد با حفظ سابقه ثبت شد.');
  }catch(error){p$('purchaseEndError').textContent=error.message}
  finally{purchaseEndState.busy=false;p$('purchaseEndSave').disabled=false;p$('purchaseEndClose').disabled=false;p$('purchaseEndDate').disabled=false}
}
document.addEventListener('DOMContentLoaded',()=>{
  p$('purchaseCoverageTabs').addEventListener('click',e=>{
    const b=e.target.closest('[data-purchase-coverage-tab]');if(!b)return;
    p$('purchaseCoverage').value=b.dataset.purchaseCoverageTab;renderPurchaseCoverageTabs();loadPurchaseProducts(true);
  });
  p$('purchaseEndClose').addEventListener('click',()=>{if(!purchaseEndState.busy)p$('purchaseEndDialog').close()});
  p$('purchaseEndDialog').addEventListener('cancel',e=>{if(purchaseEndState.busy)e.preventDefault()});
  p$('purchaseEndForm').addEventListener('submit',savePurchaseEnd);
});
