(() => {
  const root=document.querySelector('#cartableAccessPanel');
  if(!root)return;
  const accountHelp=document.querySelector('#accountForm')?.closest('article')?.querySelector('.sp-card-head p');
  if(accountHelp)accountHelp.textContent='برای هر مسئول یک حساب با شماره خودش بسازید؛ دسترسی کارتابل مشترک را پایین همین صفحه تعیین کنید.';
  const base='/warehouse-assistant/api/supplier-portal';
  let catalog,accounts;
  const selected=(items,value,label)=>items.map(x=>`<option value="${esc(value(x))}">${esc(label(x))}</option>`).join('');
  async function refresh(){
    try{
      [catalog,{accounts}]=await Promise.all([api(base+'/cartables'),api(base+'/accounts')]);
      render();
    }catch(e){root.innerHTML=`<div class="error" role="alert">${esc(e.message)}؛ اگر نسخه تازه فعال شده، صفحه را بازخوانی کنید.</div>`;}
  }
  function render(){
    const assigned=new Set(catalog.cartables.flatMap(g=>g.suppliers.map(s=>s.supplier_key)));
    root.innerHTML=`<div id="accessFeedback" role="status" aria-live="polite"></div>
      <div class="sp-form two"><form id="cartableCreateForm" class="sp-form">
      <h3>ایجاد کارتابل مشترک</h3><label class="field"><span>نام کارتابل</span><input name="name" required maxlength="200"></label>
      <fieldset><legend>تأمین‌کنندگان این کارتابل</legend><div class="sp-form two">${catalog.suppliers.filter(s=>!assigned.has(s.supplier_key)).map(s=>`<label><input type="checkbox" name="supplier" value="${esc(s.supplier_name)}"> ${esc(s.supplier_name)}</label>`).join('')}</div></fieldset>
      <label class="field"><span>حساب مسئول کل (یکی از همین تأمین‌کنندگان)</span><select name="manager" required><option value="">انتخاب حساب</option>${selected(accounts.filter(a=>a.active&&!a.access),a=>a.id,a=>a.supplier_name+' · '+a.username)}</select></label>
      <label><input type="checkbox" name="confirm" required> مسئول کل تمام سفارش‌های تأمین‌کنندگان انتخاب‌شده در همه انبارها را ببیند.</label>
      <button class="btn btn-primary">ساخت کارتابل مشترک</button></form>
      <form id="accountAccessForm" class="sp-form"><h3>دسترسی مسئول تأمین</h3>
      <p class="hint">ابتدا حساب مسئول را از بخش ایجاد حساب بسازید. حساب جدیدِ کارتابل مشترک تا تعیین دسترسی، هیچ سفارشی نمی‌بیند.</p>
      <label class="field"><span>حساب مسئول</span><select id="accessAccount" required><option value="">انتخاب حساب</option>${selected(accounts,a=>a.id,a=>a.supplier_name+' · '+a.username)}</select></label>
      <label class="field"><span>کارتابل مشترک</span><select id="accessCartable" required><option value="">انتخاب کارتابل</option>${selected(catalog.cartables,g=>g.id,g=>g.name)}</select></label>
      <label class="field"><span>نوع دسترسی</span><select id="accessMode"><option value="limited">فقط ترکیب‌های انتخاب‌شده</option><option value="all">مسئول کل: همه سفارش‌های این کارتابل</option></select></label>
      <fieldset id="accessScopes"><legend>تأمین‌کننده و انبار مجاز</legend><div id="scopeChoices"></div></fieldset>
      <p id="scopeSummary" class="hint" role="status"></p>
      <label><input type="checkbox" id="accessConfirmed" required> محدودهٔ انتخاب‌شده را بررسی و تأیید می‌کنم.</label>
      <button class="btn btn-primary">ذخیره دسترسی مسئول</button></form></div>
      <h3 class="section-gap">کارتابل‌های تعریف‌شده</h3>${catalog.cartables.map(g=>`<p><strong>${esc(g.name)}</strong> · ${g.suppliers.map(s=>esc(s.supplier_name)).join('، ')}</p>`).join('')||'<p>هنوز کارتابل مشترکی تعریف نشده است.</p>'}
      <h3>دسترسی فعلی حساب‌ها</h3>${accounts.map(a=>`<p><strong>${esc(a.username)}</strong> · ${a.access?esc(a.access.cartable_name)+' · '+(a.access.all_orders?'مسئول کل':a.access.scopes.map(s=>esc(s.supplier_name)+' / '+esc(s.warehouse_code==='*'?'همه انبارها':catalog.warehouses.find(w=>w.warehouse_code===s.warehouse_code)?.warehouse_name||s.warehouse_code)).join('، ')||'بدون دسترسی به سفارش'):esc(a.supplier_name)+' · حساب مستقل'}</p>`).join('')}`;
    root.querySelector('#cartableCreateForm').onsubmit=create;
    root.querySelector('#accountAccessForm').onsubmit=save;
    root.querySelector('#accessAccount').onchange=()=>{
      const a=accounts.find(a=>a.id===Number(root.querySelector('#accessAccount').value));
      root.querySelector('#accessCartable').value=a?.access?.cartable_id||'';
      root.querySelector('#accessMode').value=a?.access?.all_orders?'all':'limited';
      scopes(a?.access?.scopes||[]);
    };
    root.querySelector('#accessCartable').onchange=()=>scopes([]);
    root.querySelector('#accessMode').onchange=summary;
    scopes([]);
  }
  function scopes(current){
    const g=catalog.cartables.find(g=>g.id===Number(root.querySelector('#accessCartable').value));
    root.querySelector('#scopeChoices').innerHTML=(g?.suppliers||[]).map(s=>`<fieldset><legend>${esc(s.supplier_name)}</legend><div class="sp-form two">${[{warehouse_code:'*',warehouse_name:'همه انبارها'},...catalog.warehouses].map(w=>`<label><input type="checkbox" data-scope data-supplier="${esc(s.supplier_name)}" value="${esc(w.warehouse_code)}" ${current.some(c=>c.supplier_key===s.supplier_key&&c.warehouse_code===w.warehouse_code)?'checked':''}> ${esc(s.supplier_name)} · ${esc(w.warehouse_name)}</label>`).join('')}</div></fieldset>`).join('');
    root.querySelectorAll('[data-scope]').forEach(e=>e.onchange=summary);
    summary();
  }
  function summary(){
    const all=root.querySelector('#accessMode').value==='all';
    root.querySelector('#accessScopes').disabled=all;
    const n=root.querySelectorAll('[data-scope]:checked').length;
    root.querySelector('#scopeSummary').textContent=all?'همه سفارش‌های همین کارتابل در همه انبارها قابل مشاهده است.':n?`${n} ترکیب مجاز انتخاب شده؛ سایر سفارش‌ها نمایش داده نمی‌شوند.`:'هیچ ترکیبی انتخاب نشده؛ این حساب هیچ سفارشی نخواهد دید.';
    root.querySelector('#accessConfirmed').checked=false;
  }
  async function submit(event,operation){
    event.preventDefault();const button=event.submitter;button.disabled=true;
    const feedback=root.querySelector('#accessFeedback');feedback.className='hint';feedback.textContent='در حال ذخیره…';
    try{await operation();await refresh();root.querySelector('#accessFeedback').textContent='ذخیره شد؛ دسترسی در درخواست بعدی مسئول اعمال می‌شود.';}
    catch(e){feedback.className='error';feedback.textContent=e.message;}
    finally{button.disabled=false;}
  }
  function create(event){return submit(event,async()=>{
    const form=event.target;
    const names=[...form.querySelectorAll('[name=supplier]:checked')].map(e=>e.value);
    if(!names.length)throw new Error('حداقل یک تأمین‌کننده انتخاب کنید.');
    await api(base+'/cartables',{method:'POST',body:JSON.stringify({name:form.elements.name.value,supplier_names:names,manager_account_id:Number(form.elements.manager.value)})});
  });}
  function save(event){return submit(event,async()=>{
    const id=Number(root.querySelector('#accessAccount').value),a=accounts.find(a=>a.id===id);
    const all=root.querySelector('#accessMode').value==='all';
    const rules=all?[]:[...root.querySelectorAll('[data-scope]:checked')].map(e=>({supplier_name:e.dataset.supplier,warehouse_code:e.value}));
    await api(`${base}/accounts/${id}/access`,{method:'PUT',body:JSON.stringify({cartable_id:Number(root.querySelector('#accessCartable').value),all_orders:all,scopes:rules,expected_revision:a?.access?.revision||0})});
  });}
  window.addEventListener('portal-accounts-updated',refresh);
  refresh();
})();
