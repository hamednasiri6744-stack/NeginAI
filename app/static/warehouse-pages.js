// Fit every main-page table, including nested tabs and module-owned wrappers.
// No rows, form values, saved layouts or business controls are replaced.
function initializeWarehousePages(){
  const content=document.querySelector('.app-content');
  if(!content)return;
  let frame=0;
  const fit=()=>{
    frame=0;
    const summary=document.getElementById('orderingConditionsSummary');
    if(summary){
      const value=id=>document.getElementById(id)?.value||'—';
      const date=value('orderingDeliveryDate');
      const text=`حد شروع ${value('reorderCoverageDays')} روز · هدف ${value('targetDays')} روز · فروش ${value('periodDays')} روز · ${document.getElementById('onlyNeeded')?.checked?'فقط اقلام نیازمند':'همه اقلام'}${date!=='—'?' · تحویل '+date:''}`;
      if(summary.textContent!==text)summary.textContent=text;
    }
    content.querySelectorAll('.operation-table').forEach(wrap=>{
      const tools=wrap.previousElementSibling;
      if(tools?.classList.contains('operation-tools')&&tools.hidden!==wrap.hidden)tools.hidden=wrap.hidden;
      if(!wrap.getClientRects().length||wrap.closest('dialog'))return;
      wrap.dataset.pageGrid='true';
      const panel=wrap.closest('.panel');
      const footer=panel?.querySelector('.unbilled-footer,.inventory-more,.fulfillment-footnote');
      const footerHeight=footer?.getClientRects().length?footer.getBoundingClientRect().height:0;
      const available=Math.max(220,Math.floor(window.innerHeight-wrap.getBoundingClientRect().top-footerHeight-10));
      const height=`${available}px`;
      if(wrap.style.getPropertyValue('--page-table-height')!==height)wrap.style.setProperty('--page-table-height',height);
    });
  };
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(fit)};
  const resize=new ResizeObserver(schedule);
  resize.observe(content);
  content.querySelectorAll('.panel-head,form,.operation-tools').forEach(element=>resize.observe(element));
  new MutationObserver(schedule).observe(content,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden','open']});
  content.addEventListener('toggle',schedule,true);
  content.addEventListener('input',schedule);
  content.addEventListener('change',schedule);
  content.addEventListener('invalid',event=>{
    const conditions=event.target.closest('.ordering-advanced');
    if(conditions)conditions.open=true;
  },true);
  window.addEventListener('resize',schedule);
  document.getElementById('workspaceNavigationToggle')?.addEventListener('click',schedule);
  schedule();
}
document.addEventListener('DOMContentLoaded',initializeWarehousePages);
