const checkbarImage={pages:[],result:null,rows:[],products:[],sequence:0,controller:null,busy:false,source:null};

function showCheckbarImageResult(){
  if(!checkbarImage.result)return;
  $('#checkbarImagePanel').open=true;
  $('#checkbarImageResult').scrollIntoView?.({block:'nearest'});
  $('#checkbarImageResult').focus();
}

function checkbarImageFeedback(message,kind='info'){
  $('#checkbarImageStatus').textContent=message;
  checkbarNotice(kind,message);
  $('#checkbarIssue').disabled=!!checkbarState.saved||checkbarState.submitting||!checkbarState.lines.length||checkbarImportPending();
}

function invalidateCheckbarImage(){
  checkbarImage.sequence++;checkbarImage.controller?.abort();
  Object.assign(checkbarImage,{result:null,rows:[],products:[],controller:null,busy:false,source:null});
  $('#checkbarImageResult').hidden=true;$('#checkbarImageRows').innerHTML='';
  $('#checkbarImageShowResult').hidden=true;
  $('#checkbarIssue').disabled=!!checkbarState.saved||checkbarState.submitting||!checkbarState.lines.length;
}

function resetCheckbarImage(){
  invalidateCheckbarImage();
  checkbarImage.pages.forEach(page=>{if(page.url)URL.revokeObjectURL(page.url)});checkbarImage.pages=[];
  $('#checkbarImagePanel').hidden=false;$('#checkbarImageReview').hidden=true;$('#checkbarImageResult').hidden=true;
  $('#checkbarImagePanel').open=false;
  $('#checkbarImagePages').innerHTML='';
  $('#checkbarImageFile').value='';$('#checkbarImageCamera').value='';$('#checkbarImageRows').innerHTML='';
  $('#checkbarImageStatus').textContent='';$('#checkbarImageRead').disabled=true;
}

function checkbarAttachmentKind(file){
  const extension=(file.name||'').split('.').pop().toLowerCase();
  if(['pdf','xlsx','xls'].includes(extension))return extension;
  return ['image/jpeg','image/png','image/webp'].includes(file.type)?'image':null;
}

function chooseCheckbarImage(files){
  if(!files||!checkbarEditable()||checkbarState.editing)return;
  const additions=Array.isArray(files)?files:[files];
  if(!additions.length)return;
  if(additions.some(file=>!checkbarAttachmentKind(file)||!file.size||file.size>10*1024*1024)){
    $('#checkbarImageStatus').textContent='عکس JPG، PNG، WebP، فایل PDF یا اکسل XLSX و XLS تا حجم ۱۰ مگابایت انتخاب کنید.';return;
  }
  if(checkbarImage.pages.length+additions.length>10){
    $('#checkbarImageStatus').textContent='برای هر حواله حداکثر ۱۰ فایل انتخاب کنید.';return;
  }
  if([...checkbarImage.pages.map(p=>p.file),...additions].reduce((total,file)=>total+file.size,0)>30*1024*1024){
    $('#checkbarImageStatus').textContent='حجم مجموع فایل‌های حواله باید حداکثر ۳۰ مگابایت باشد.';return;
  }
  invalidateCheckbarImage();
  additions.forEach(file=>checkbarImage.pages.push({file,kind:checkbarAttachmentKind(file),url:checkbarAttachmentKind(file)==='image'?URL.createObjectURL(file):null}));
  renderCheckbarImagePages();
}

function renderCheckbarImagePages(){
  const count=checkbarImage.pages.length;
  $('#checkbarImagePages').innerHTML=checkbarImage.pages.map((page,i)=>`<figure class="checkbar-image-page">
    ${page.kind==='image'?`<details><summary aria-label="بزرگ‌نمایی صفحه ${fa(i+1)}"><img src="${esc(page.url)}" alt="صفحه ${fa(i+1)} حواله"><span>بزرگ‌نمایی / کوچک‌نمایی</span></summary></details>`:`<div class="checkbar-file-tile"><strong>${esc(page.kind.toUpperCase())}</strong><span>${page.kind==='pdf'?'همهٔ صفحه‌های PDF خوانده می‌شود.':'سلول‌های همهٔ برگه‌ها خوانده می‌شود.'}</span></div>`}
    <figcaption>فایل ${fa(i+1)} · ${esc(page.file.name||'عکس دوربین')}</figcaption>
    <div class="checkbar-image-actions"><button type="button" data-image-page="${i}" data-page-action="previous" ${i===0?'disabled':''} aria-label="صفحه ${fa(i+1)} به قبل">قبل</button>
    <button type="button" data-image-page="${i}" data-page-action="next" ${i===count-1?'disabled':''} aria-label="صفحه ${fa(i+1)} به بعد">بعد</button>
    <button type="button" data-image-page="${i}" data-page-action="remove" aria-label="حذف فایل ${fa(i+1)}">حذف فایل</button></div></figure>`).join('');
  $('#checkbarImageReview').hidden=!count;$('#checkbarImageRead').disabled=!count;
  checkbarImageFeedback(count?`${fa(count)} فایل آماده است؛ «خواندن حواله» را بزنید. سپس اقلام خوانده‌شده را بررسی و وارد فرم کنید.`:'فایل‌های حواله را اضافه کنید.');
}

function changeCheckbarImagePage(index,action){
  if(!checkbarEditable()||checkbarState.editing||!checkbarImage.pages[index])return;
  const other=action==='previous'?index-1:index+1;
  if(action!=='remove'&&(!['previous','next'].includes(action)||!checkbarImage.pages[other]))return;
  invalidateCheckbarImage();
  if(action==='remove'){const page=checkbarImage.pages.splice(index,1)[0];if(page.url)URL.revokeObjectURL(page.url);}
  else [checkbarImage.pages[index],checkbarImage.pages[other]]=[checkbarImage.pages[other],checkbarImage.pages[index]];
  renderCheckbarImagePages();
}

function checkbarImageProducts(source){
  const products=[...(source.lines||[])],codes=new Set(products.map(p=>p.product_code));
  return products.concat((source.catalog||[]).filter(p=>!codes.has(p.product_code))).map(checkbarOrderContext);
}

async function readCheckbarImage(){
  if(!checkbarImage.pages.length||checkbarImage.busy||!checkbarState.source||!checkbarEditable()||checkbarState.editing)return;
  const sequence=++checkbarImage.sequence,formSequence=checkbarState.sequence,source=checkbarState.source;
  checkbarImage.busy=true;checkbarImage.result=null;checkbarImage.controller=new AbortController();
  $('#checkbarImageRead').disabled=true;$('#checkbarImageResult').hidden=true;
  $('#checkbarImageShowResult').hidden=true;
  checkbarImageFeedback(`در حال خواندن ${fa(checkbarImage.pages.length)} فایل حواله و تطبیق کالاها… لطفاً صبر کنید؛ نتیجه بعد از پایان خواندن نمایش داده می‌شود.`);
  const data=new FormData();checkbarImage.pages.forEach(page=>data.append('file',page.file));
  data.append('selection',JSON.stringify({warehouse:source.warehouse,supplier:source.supplier,order_ids:source.order_ids||[]}));
  data.append('expected_token',source.expected_token);
  const controller=checkbarImage.controller;
  const timer=setTimeout(()=>controller.abort(),175000);
  try{
    const result=await api('/warehouse-assistant/api/checkbars/image-draft',{method:'POST',body:data,signal:controller.signal});
    if(sequence!==checkbarImage.sequence||formSequence!==checkbarState.sequence||source!==checkbarState.source||!checkbarEditable())return;
    if(result.expected_token!==source.expected_token)throw new Error('اطلاعات کالا تغییر کرده؛ فرم را دوباره باز کنید.');
    if((result.file_count??result.page_count??1)!==checkbarImage.pages.length)throw new Error('خواندن همهٔ فایل‌ها تأیید نشد؛ دوباره تلاش کنید.');
    checkbarImage.source=source;checkbarImage.products=checkbarImageProducts(source);checkbarImage.result=result.rows.length?result:null;
    checkbarImage.rows=result.rows.map(row=>({...row,included:true,search:'',selected:row.selected==null?'':String(row.selected)}));
    $('#checkbarImageReference').value=result.metadata.reference_no||'';$('#checkbarImageDate').value=result.metadata.date||'';
    $('#checkbarImageResult').hidden=!result.rows.length;
    $('#checkbarImageShowResult').hidden=!result.rows.length;
    $('#checkbarImageShowResult').textContent=`بررسی ${fa(result.rows.length)} قلم خوانده‌شده`;
    checkbarImageFeedback([result.rows.length?`${fa(result.rows.length)} ردیف خوانده شد. اقلام زیر را بررسی کنید و «وارد کردن اقلام به چک‌بار» را بزنید تا وارد جدول شوند. تأمین‌کنندهٔ خوانده‌شده: ${result.supplier||'ناخوانا'}.`:'ردیف کالای خوانایی پیدا نشد؛ فایل اصلی PDF یا عکس نزدیک و واضح از حواله انتخاب کنید.',...(result.warnings||[])].join('\n'));
    renderCheckbarImageRows();
    if(result.rows.length)showCheckbarImageResult();
  }catch(error){
    if(sequence===checkbarImage.sequence&&formSequence===checkbarState.sequence){
      checkbarImageFeedback(error.name==='AbortError'?'زمان خواندن فایل تمام شد؛ دوباره تلاش کنید.':error.message,'error');
      $('#checkbarImageStatus').scrollIntoView?.({block:'center',behavior:'smooth'});
    }
  }finally{
    clearTimeout(timer);
    if(sequence===checkbarImage.sequence){checkbarImage.busy=false;$('#checkbarImageRead').disabled=false;$('#checkbarIssue').disabled=!!checkbarState.saved||checkbarState.submitting||!checkbarState.lines.length||checkbarImportPending();}
  }
}

function checkbarImageOptions(row){
  let indices=row.suggestions||[];
  if(row.search){
    const query=normalizeSearchText(row.search);
    indices=checkbarImage.products.map((p,i)=>({p,i})).filter(({p})=>normalizeSearchText([p.product_name,p.product_code,p.manufacturer_product_code,p.barcode,p.preorder_number].join(' ')).includes(query)).slice(0,30).map(({i})=>i);
  }
  if(row.selected!=='')indices=[Number(row.selected),...indices];
  return '<option value="">کالا را انتخاب کنید</option>'+[...new Set(indices)].filter(i=>checkbarImage.products[i]).map(i=>{
    const p=checkbarImage.products[i];
    return `<option value="${i}"${String(i)===row.selected?' selected':''}>${esc(p.product_name)} · ${esc(p.manufacturer_product_code||p.product_code)}${p.preorder_number?' · '+esc(p.preorder_number):''}</option>`;
  }).join('');
}

function renderCheckbarImageRows(){
  $('#checkbarImageRows').innerHTML=checkbarImage.rows.map((row,i)=>`<article class="checkbar-image-row" data-image-row="${i}">
    <label><input type="checkbox" data-image-field="included"${row.included?' checked':''}>${esc(row.source_label||'صفحه '+fa(row.source_page??1))} · ردیف ${fa(i+1)}: ${esc(row.description)}</label>
    <small>کد تأمین‌کننده: ${esc(row.supplier_code||'—')} · بارکد: ${esc(row.barcode||'—')} · تعداد روی حواله: ${esc(row.quantity_text||'ناخوانا')}</small>
    <div class="checkbar-image-actions"><label>جستجوی کالا<input data-image-field="search" type="search" value="${esc(row.search)}" placeholder="نام، کد یا بارکد"></label>
    <label>کالای برنامه<select data-image-field="selected">${checkbarImageOptions(row)}</select></label>
    <label>کارتن طبق حواله<input data-image-field="cartons" inputmode="numeric" value="${esc(row.cartons??'')}"></label>
    <label>عدد جزء طبق حواله<input data-image-field="units" inputmode="decimal" value="${esc(row.units??'')}"></label></div>
    <small>${esc(row.match_reason||'')}</small>
    <small>${esc((row.problems||[]).join(' '))}</small></article>`).join('');
}

function applyCheckbarImage(){
  if(!checkbarImage.result||checkbarImage.busy||!checkbarEditable()||checkbarState.editing||checkbarImage.source!==checkbarState.source)return;
  try{
    const lines=[],seen=new Set();
    for(const [index,row] of checkbarImage.rows.entries()){
      if(!row.included)continue;
      const product=row.selected===''?null:checkbarImage.products[Number(row.selected)];
      if(!product)throw new Error(`کالای ردیف ${fa(index+1)} را انتخاب کنید یا تیک آن ردیف را بردارید.`);
      const key=JSON.stringify([product.preorder_id??null,product.product_code]);
      if(seen.has(key))throw new Error('یک کالا از یک مبنا چند بار انتخاب شده؛ ردیف‌های تکراری را بررسی کنید.');
      seen.add(key);
      const cartons=checkbarNumeric(row.cartons,true),units=checkbarNumeric(row.units);
      if(row.total_base_units!=null&&!row.quantityEdited){
        const actual=(cartons||0)*Number(product.conversion_rate)+(units||0);
        if(!Number.isFinite(actual)||Math.abs(actual-Number(row.total_base_units))>1e-6)
          throw new Error(`تعداد ردیف ${fa(index+1)} با مقدار کل حواله برابر نیست؛ ضریب کارتنِ کالای انتخاب‌شده را بررسی و تعداد را صریحاً اصلاح کنید.`);
      }
      if(cartons>1000000||units>1e9||(cartons||0)*Number(product.conversion_rate)+(units||0)>1e9)
        throw new Error(`تعداد ردیف ${fa(index+1)} بیش از حد مجاز است.`);
      lines.push({...product,cartons:cartons??'',units:units??'',manufacturer_price_new:'',consumer_price_new:''});
    }
    if(!lines.length)throw new Error('حداقل یک ردیف برای پر کردن فرم انتخاب کنید.');
    if(checkbarState.includeOrderItems){
      const incoming=new Map(lines.map(line=>[JSON.stringify([line.preorder_id??null,line.product_code]),line]));
      const hasCount=checkbarState.lines.some(line=>incoming.has(JSON.stringify([line.preorder_id??null,line.product_code]))&&checkbarActual(line)!==null);
      if(hasCount&&!confirm('تعدادهای قبلی اقلام موجود در حواله با تعداد خوانده‌شده جایگزین شوند؟ سایر ردیف‌ها حفظ می‌شوند.'))return;
      const merged=checkbarState.lines.map(line=>{
        const key=JSON.stringify([line.preorder_id??null,line.product_code]),read=incoming.get(key);
        if(!read)return line;
        incoming.delete(key);return {...line,cartons:read.cartons,units:read.units};
      });
      merged.push(...incoming.values());
      if(merged.length>500)throw new Error('حداکثر ۵۰۰ ردیف در چک‌بار مجاز است.');
      checkbarState.lines=merged;
    }else{
      if(checkbarState.lines.length&&!confirm('اقلام و مشخصات خوانده‌شده جایگزین اقلام فعلی این فرم شوند؟'))return;
      checkbarState.lines=lines;
    }
    $('#checkbarReference').value=$('#checkbarImageReference').value.trim();
    const metadata={date:$('#checkbarImageDate').value.trim(),note:'پیش‌نویس از فایل حواله؛ تعدادها اعلامی تأمین‌کننده و نیازمند شمارش انبار است.'};
    document.querySelectorAll('[data-checkbar-meta]').forEach(input=>{
      const key=input.dataset.checkbarMeta;
      if(key==='date'&&metadata.date)input.value=metadata.date;
      if(key==='note')input.value=(metadata.note+(input.value?'\n'+input.value:'')).slice(0,500);
    });
    checkbarImage.result=null;$('#checkbarImageResult').hidden=true;
    $('#checkbarImageShowResult').hidden=true;
    $('#checkbarImagePanel').open=false;
    renderCheckbarLines();renderCheckbarProducts();
    $('#checkbarImageStatus').textContent='فرم پر شد. تعدادها طبق حواله‌اند؛ ماندهٔ سفارش در راه جداگانه نمایش داده می‌شود. '+(checkbarState.includeOrderItems?'اقلامی که در حواله نبودند با تعداد قبلی یا خالی حفظ شدند. ':'')+'شمارش و تأیید انبار هنوز انجام نشده و چک‌بار ذخیره نشده است.';
    checkbarNotice('info','اطلاعات حواله وارد فرم شد؛ تعدادها را در انبار بررسی کنید و سپس ذخیره کنید.',true);
  }catch(error){checkbarImageFeedback(error.message,'error');}
}

document.addEventListener('DOMContentLoaded',()=>{
  for(const id of ['checkbarImageFile','checkbarImageCamera'])$('#'+id).addEventListener('change',event=>{
    chooseCheckbarImage(Array.from(event.target.files||[]));event.target.value='';
  });
  $('#checkbarImagePages').addEventListener('click',event=>{
    const button=event.target.closest('[data-page-action]');
    if(button)changeCheckbarImagePage(Number(button.dataset.imagePage),button.dataset.pageAction);
  });
  $('#checkbarImageRead').addEventListener('click',readCheckbarImage);
  $('#checkbarImageShowResult').addEventListener('click',showCheckbarImageResult);
  $('#checkbarImageApply').addEventListener('click',applyCheckbarImage);
  $('#checkbarImageRows').addEventListener('input',event=>{
    const key=event.target.dataset.imageField,element=event.target.closest('[data-image-row]');
    if(!key||!element)return;
    const row=checkbarImage.rows[Number(element.dataset.imageRow)];
    row[key]=key==='included'?event.target.checked:event.target.value;
    if(key==='cartons'||key==='units')row.quantityEdited=true;
    if(key==='search')element.querySelector('select').innerHTML=checkbarImageOptions(row);
  });
});
