// Presentation only: retain the original controls, event handlers and draft nodes.
function compactTableTools(root=document){
  root.querySelectorAll('table').forEach(table=>{
    if(table.closest('.column-layout-dialog'))return;
    const wrap=table.parentElement;
    if(!wrap||!wrap.matches('.table-wrap,.supplier-review-table,.purchase-table-scroll,.sale-price-table-scroll,.contract-item-scroll,.sale-price-item-scroll,.receipt-preview-table-wrap,.pi-table,.unbilled-table-scroll'))return;
    let tools=wrap.previousElementSibling;
    if(!tools?.classList.contains('operation-tools')){
      tools=document.createElement('div');tools.className='operation-tools';
      tools.setAttribute('role','group');tools.setAttribute('aria-label','ابزار جدول');
      wrap.before(tools);
    }
    // Each module can register its bar later. Move, never clone, its controls.
    let previous=tools.previousElementSibling;
    while(previous?.matches('.table-export-bar,.work-view-bar,.operation-tools')){
      const next=previous.previousElementSibling;
      if(previous.classList.contains('operation-tools')){
        previous.querySelectorAll('[data-table-fullscreen]').forEach(button=>button.remove());
        tools.prepend(...previous.childNodes);previous.remove();
      }else tools.prepend(previous);
      previous=next;
    }
    wrap.classList.add('operation-table');
    table.querySelectorAll('thead tr:first-child th').forEach(header=>{
      if(!header.title)header.title=header.textContent.replace(/[↔↕]/g,'').trim();
    });
    if(!tools.querySelector('[data-table-fullscreen]')){
      const surface=table.closest('dialog')||table.closest('.panel')||table.closest('section');
      if(!surface)return;
      const button=document.createElement('button');button.type='button';button.className='secondary-action';
      button.dataset.tableFullscreen='true';button.textContent='تمام‌صفحه';
      button.setAttribute('aria-label',`تمام‌صفحه ${typeof warehouseExportTitle==='function'?warehouseExportTitle(table):'جدول'}`);
      button.setAttribute('aria-pressed','false');tools.append(button);
      button.addEventListener('click',()=>setWorkspaceFullscreen(surface,!surface.classList.contains('workspace-fullscreen')));
    }
  });
}

function initializeOperationsLayout(){
  compactTableTools();compactOrderActions();
  const navigationToggle=document.getElementById('workspaceNavigationToggle');
  navigationToggle?.addEventListener('click',()=>{
    const collapsed=document.body.classList.toggle('workspace-navigation-collapsed');
    navigationToggle.setAttribute('aria-expanded',String(!collapsed));
    const label=collapsed?'باز کردن منوی اصلی':'جمع کردن منوی اصلی';
    navigationToggle.setAttribute('aria-label',label);navigationToggle.title=label;
    if(typeof fitTableWrapsToViewport==='function')fitTableWrapsToViewport();
  });
  let scheduled=false;
  new MutationObserver(records=>{
    if(scheduled||!records.some(record=>record.addedNodes.length))return;
    scheduled=true;requestAnimationFrame(()=>{scheduled=false;compactTableTools();compactOrderActions()});
  }).observe(document.body,{childList:true,subtree:true});
}
function compactOrderActions(root=document){
  root.querySelectorAll('.preorder-actions:not(.fulfillment-work-actions),.manual-order-actions,#purchaseView tbody .purchase-actions').forEach(group=>{
    if(group.dataset.compactActions)return;
    group.dataset.compactActions='true';
    const controls=[...group.children].filter(node=>node.matches('button,a'));
    if(controls.length<4)return;
    // The workflow renderer chooses the next action; this module only lays it out.
    const primary=controls.find(node=>node.matches('[data-workflow-primary="true"]')&&!node.disabled)||
      controls.find(node=>!node.disabled)||controls[0];
    const menu=document.createElement('details');menu.className='operation-row-menu';
    const summary=document.createElement('summary');summary.textContent='سایر عملیات';
    const content=document.createElement('div');
    menu.append(summary,content);group.append(menu);
    controls.filter(node=>node!==primary).forEach(node=>content.append(node));
    // The original delegation chain is retained: menu stays inside its order row.
    content.addEventListener('click',event=>{if(event.target.closest('button:not(:disabled),a'))menu.open=false});
  });
}
document.addEventListener('DOMContentLoaded',initializeOperationsLayout);
