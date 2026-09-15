// Maximize the existing form within the browser. Never recreate inputs or drafts.
function setWorkspaceFullscreen(surface,enabled){
  const positions=[...surface.querySelectorAll('.table-wrap,.checkbar-body')].map(el=>[el,el.scrollTop,el.scrollLeft]);
  surface.classList.toggle('workspace-fullscreen',enabled);
  surface.querySelectorAll('[data-workspace-fullscreen],[data-table-fullscreen]').forEach(button=>{
    button.textContent=enabled?'خروج از تمام‌صفحه':'تمام‌صفحه';
    button.setAttribute('aria-pressed',String(enabled));
    button.setAttribute('aria-label',enabled?'خروج از تمام‌صفحه':'نمایش تمام‌صفحه');
  });
  if(!surface.dataset?.fullscreenEventsBound&&surface.addEventListener){
    surface.dataset.fullscreenEventsBound='true';
    surface.addEventListener('cancel',event=>{if(surface.classList.contains('workspace-fullscreen')){event.preventDefault();setWorkspaceFullscreen(surface,false)}});
    surface.addEventListener('close',()=>setWorkspaceFullscreen(surface,false));
  }
  requestAnimationFrame(()=>{
    surface.querySelectorAll('table').forEach(fitFixedTableColumns);
    positions.forEach(([el,top,left])=>{el.scrollTop=top;el.scrollLeft=left});
  });
}
document.addEventListener('DOMContentLoaded',()=>{
  const ids=['checkbarDialog','checkbarCatalogDialog','preorderPreviewDialog','preorderCatalogDialog','fulfillmentReceiptDialog','transferDocumentDialog','orderingView'];
  ids.forEach(id=>{
    const surface=document.getElementById(id),head=surface?.querySelector('.preview-dialog-head,.panel-head');
    if(!head)return;
    const button=document.createElement('button');button.type='button';button.className='secondary-action workspace-fullscreen-button';
    button.dataset.workspaceFullscreen=id;head.insertBefore(button,head.lastElementChild);
    setWorkspaceFullscreen(surface,false);
    button.addEventListener('click',()=>setWorkspaceFullscreen(surface,!surface.classList.contains('workspace-fullscreen')));
  });
  // Views and their nested panels share this mode. Leaving a view must not
  // reopen it fullscreen later, or leave an invisible target ahead of Escape.
  new MutationObserver(()=>{
    document.querySelectorAll('.workspace-fullscreen').forEach(surface=>{
      if(surface.closest('[hidden]'))setWorkspaceFullscreen(surface,false);
    });
  }).observe(document.body,{attributes:true,attributeFilter:['hidden'],subtree:true});
  document.addEventListener('keydown',event=>{
    if(event.defaultPrevented||event.key!=='Escape'||document.querySelector('dialog[open]'))return;
    const surface=[...document.querySelectorAll('.workspace-fullscreen')].find(surface=>!surface.closest('[hidden]'));
    if(surface){event.preventDefault();setWorkspaceFullscreen(surface,false)}
  });
});
