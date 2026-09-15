// Exports the currently rendered table state. It never writes to Varanegar/ERP.
function warehouseExportVisible(element){
  return !element.hidden&&window.getComputedStyle(element).display!=='none'&&window.getComputedStyle(element).visibility!=='hidden';
}

function warehouseExportControlValue(control){
  if(control.matches('select'))return control.selectedOptions[0]?.textContent.trim()||'';
  if(control.matches('input[type="checkbox"],input[type="radio"]'))return control.checked?'بله':'خیر';
  return control.value??'';
}

function warehouseExportCellValue(cell){
  const explicit=cell.getAttribute('data-export-value')||cell.querySelector('[data-export-value]')?.getAttribute('data-export-value');
  if(explicit!==null&&explicit!==undefined)return explicit.trim();
  const controls=[...cell.querySelectorAll('input,select,textarea')];
  if(controls.length===1&&controls[0].matches('input[type="number"]')){
    const numeric=Number(normalizeSearchText(controls[0].value));
    if(Number.isFinite(numeric)&&controls[0].value.trim()!=='')return numeric;
  }
  const clone=cell.cloneNode(true),cloneControls=[...clone.querySelectorAll('input,select,textarea')];
  cloneControls.forEach((control,index)=>control.replaceWith(document.createTextNode(warehouseExportControlValue(controls[index]))));
  clone.querySelectorAll('button,script,style,[data-export-ignore]').forEach(node=>node.remove());
  return (clone.innerText||clone.textContent||'').replace(/\s+/g,' ').trim();
}

function warehouseExportTitle(table){
  const explicit=table.getAttribute('aria-label')||table.dataset.exportTitle;
  if(explicit)return explicit.trim();
  const scope=table.closest('dialog,section,.panel');
  const heading=scope?.querySelector('h2,h3');
  return heading?.textContent.trim()||table.id||'جدول دستیار انبار';
}

function warehouseExportPayload(table){
  const headerRow=table.tHead?.rows[0];
  if(!headerRow)throw new Error('عنوان ستون‌های این جدول مشخص نیست.');
  const headers=[...headerRow.cells];
  const indexes=headers.map((header,index)=>({header,index})).filter(({header})=>{
    const label=(header.innerText||header.textContent||'').replace(/\s+/g,' ').trim();
    return warehouseExportVisible(header)&&header.dataset.exportIgnore!=='true'&&
      header.dataset.filterable!=='false'&&!/^(عملیات|انتخاب)$/.test(label);
  });
  const columns=indexes.map(({header})=>(header.innerText||header.textContent||'').replace(/\s+/g,' ').trim());
  const rows=[...table.tBodies].flatMap(body=>[...body.rows]).filter(row=>warehouseExportVisible(row)&&
    row.cells.length>1&&![...row.cells].some(cell=>cell.colSpan>1)).map(row=>indexes.map(({index})=>{
      const cell=row.cells[index];return cell?warehouseExportCellValue(cell):'';
    }));
  if(!columns.length)throw new Error('ستون قابل خروجی در این جدول وجود ندارد.');
  if(!rows.length)throw new Error('ردیفی در جدول فعلی برای خروجی وجود ندارد.');
  return {title:warehouseExportTitle(table),columns,rows};
}

function warehouseExportFilename(response,title){
  const value=response.headers.get('Content-Disposition')||'';
  const match=value.match(/filename\*=UTF-8''([^;]+)/i);
  if(match){try{return decodeURIComponent(match[1])}catch(_error){}}
  return `warehouse-${title}.xlsx`;
}

async function warehouseExportTable(table,button){
  let payload;
  try{payload=warehouseExportPayload(table)}catch(error){toast(error.message,true);return}
  const previous=button.textContent;button.disabled=true;button.textContent='در حال ساخت اکسل…';
  try{
    const response=await fetch('/warehouse-assistant/api/table-export.xlsx',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Warehouse-Export':'1'},body:JSON.stringify(payload)});
    if(!response.ok){let message='ساخت خروجی اکسل انجام نشد.';try{message=(await response.json()).detail||message}catch(_error){}throw new Error(message)}
    const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download=warehouseExportFilename(response,payload.title);document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
    toast(`خروجی اکسل «${payload.title}» آماده شد.`);
  }catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent=previous}
}

function initializeWarehouseTableExports(root=document){
  root.querySelectorAll?.('table:not([data-excel-export-ready])').forEach(table=>{
    table.dataset.excelExportReady='true';
    const wrapper=table.parentElement;if(!wrapper)return;
    const bar=document.createElement('div');bar.className='table-export-bar';bar.dataset.exportFor=table.id||'table';
    const button=document.createElement('button');button.type='button';button.className='table-export-button';button.textContent='خروجی اکسل همین جدول';
    button.setAttribute('aria-label',`دریافت خروجی اکسل ${warehouseExportTitle(table)}`);
    button.addEventListener('click',()=>warehouseExportTable(table,button));bar.appendChild(button);wrapper.before(bar);
  });
}

document.addEventListener('DOMContentLoaded',()=>{
  initializeWarehouseTableExports();
  let scheduled=false;
  new MutationObserver(records=>{
    if(scheduled||!records.some(record=>record.addedNodes.length))return;scheduled=true;
    requestAnimationFrame(()=>{scheduled=false;initializeWarehouseTableExports()});
  }).observe(document.body,{childList:true,subtree:true});
});
