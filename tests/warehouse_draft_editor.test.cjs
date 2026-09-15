const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');

function setup(kind){
  const nodes={},handlers={},calls=[];
  function node(){return {value:'',disabled:false,open:true,textContent:'',dataset:{},
    close(){this.open=false},showModal(){this.open=true},
    addEventListener(name,fn){(this.events??={})[name]=fn},setAttribute(){},removeAttribute(){},querySelectorAll:()=>[date,...inputs]};}
  const date=node();date.value='1405/06/25';
  const inputs=[node(),node()];inputs.forEach((input,i)=>{input.value=String(i+1);input.dataset.manualCartons='T'+i;input.closest=()=>({dataset:{productCode:'T'+i}})});
  const docEvents={};
  const c=vm.createContext({console,Map,JSON,document:{addEventListener:(event,fn)=>docEvents[event]=fn,querySelectorAll:selector=>selector.includes('cartons')?inputs:[]},
    window:{addEventListener:(event,fn)=>handlers[event]=fn},$:selector=>nodes[selector]??=(selector.includes('DeliveryDate')?date:node()),
    normalizeSearchText:s=>String(s).trim().replace(/[۰-۹]/g,ch=>String(ch.charCodeAt(0)-1776)),
    state:{bootstrap:{draft_editor_atomic_supported:true},previewExpectedToken:'token'},confirm:()=>false,
    api:async(url,options)=>{calls.push([url,JSON.parse(options.body),options.method]);return {id:1,email_send_token:'new-token'}}});
  vm.runInContext(fs.readFileSync('app/static/warehouse-order-workflow.js','utf8'),c);
  const run=s=>vm.runInContext(s,c);run(`beginDraftEditor('${kind}')`);
  return {c,run,date,inputs,nodes,calls,handlers,docEvents};
}

for(const kind of ['supplier_order','automatic_preorder']){
  test(`${kind}: one request saves date and quantities, then marks clean`,async()=>{
    const s=setup(kind);s.date.value='۱۴۰۵/۰۶/۲۸';s.inputs[0].value='4';
    assert.equal(s.run(`draftEditorDirty('${kind}')`),true);
    await s.run(`saveDraftEditor('${kind}',{id:1,email_send_token:'token'})`);
    assert.equal(s.calls.length,1);assert.equal(s.calls[0][1].delivery_date,'1405/06/28');
    assert.equal(s.calls[0][1].lines[0].cartons,4);assert.equal(s.calls[0][1].expected_token,'token');
    assert.equal(s.calls[0][2],kind==='supplier_order'?'POST':'PUT');
    assert.equal(s.run(`draftEditorDirty('${kind}')`),false);
  });
  test(`${kind}: failure preserves draft and exiting can be declined`,async()=>{
    const s=setup(kind);s.date.value='1405/06/28';s.inputs[0].value='4';
    s.c.api=async()=>{throw Error('network failure')};
    await assert.rejects(s.run(`saveDraftEditor('${kind}',{id:1,email_send_token:'token'})`),/network failure/);
    assert.equal(s.run(`draftEditorDirty('${kind}')`),true);
    assert.equal(s.run(`canCloseDraftEditor('${kind}')`),false);
    assert.equal(s.inputs[0].value,'4');assert.equal(s.date.value,'1405/06/28');assert.equal(s.date.disabled,false);
    s.run(`beginDraftEditor('${kind}')`);assert.equal(s.run(`canCloseDraftEditor('${kind}')`),true);
  });
  test(`${kind}: no second save or close while first request is pending`,async()=>{
    const s=setup(kind);let finish;s.c.api=()=>new Promise(resolve=>finish=resolve);
    const first=s.run(`saveDraftEditor('${kind}',{id:1,email_send_token:'token'})`);
    assert.equal(s.run(`canCloseDraftEditor('${kind}')`),false);assert.equal(s.date.disabled,true);
    await assert.rejects(s.run(`saveDraftEditor('${kind}',{id:1,email_send_token:'token'})`));
    finish({id:1});await first;assert.equal(s.date.disabled,false);
  });
  test(`${kind}: old backend cannot silently discard delivery date`,async()=>{
    const s=setup(kind);s.c.state.bootstrap={};s.date.value='1405/06/28';
    await assert.rejects(s.run(`saveDraftEditor('${kind}',{id:1,email_send_token:'token'})`),/فعال نیست/);
    assert.equal(s.calls.length,0);assert.equal(s.run(`draftEditorDirty('${kind}')`),true);
  });
  test(`${kind}: invalid dates and quantities stay local`,async()=>{
    const s=setup(kind);s.date.value='bad';
    await assert.rejects(s.run(`saveDraftEditor('${kind}',{id:1,email_send_token:'token'})`));
    s.date.value='1405/06/28';s.inputs[0].value='1.5';
    await assert.rejects(s.run(`saveDraftEditor('${kind}',{id:1,email_send_token:'token'})`));
    assert.equal(s.calls.length,0);
  });
  test(`${kind}: internal exit choices keep, discard or save exactly once`,async()=>{
    const s=setup(kind);s.date.value='1405/06/28';let closed=0;s.c.closeEditor=()=>closed++;
    s.c.currentPreviewPreorder=()=>({can_edit:true});
    s.c.saveManualEdit=s.c.savePreorderPreview=()=>s.run(`saveDraftEditor('${kind}',{id:1,email_send_token:'token'})`);
    s.run(`requestDraftEditorClose('${kind}',closeEditor)`);
    await s.run("resolveDraftEditorExit('keep')");assert.equal(closed,0);assert.equal(s.run(`draftEditorDirty('${kind}')`),true);
    s.run(`requestDraftEditorClose('${kind}',closeEditor)`);
    await s.run("resolveDraftEditorExit('discard')");assert.equal(closed,1);assert.equal(s.calls.length,0);
    s.run(`requestDraftEditorClose('${kind}',closeEditor)`);
    await s.run("resolveDraftEditorExit('save')");assert.equal(closed,2);assert.equal(s.calls.length,1);
  });
  test(`${kind}: unsuccessful save-and-exit keeps both dialogs and draft`,async()=>{
    const s=setup(kind);s.date.value='1405/06/28';let closed=0;s.c.closeEditor=()=>closed++;
    s.c.currentPreviewPreorder=()=>({can_edit:true});s.c.saveManualEdit=s.c.savePreorderPreview=async()=>{};
    s.run(`requestDraftEditorClose('${kind}',closeEditor)`);
    await s.run("resolveDraftEditorExit('save')");assert.equal(closed,0);assert.equal(s.run(`draftEditorDirty('${kind}')`),true);
    assert.match(s.nodes['#draftExitError'].textContent,/ذخیره کامل نشد/);
  });
}

test('closing preview delegates to the shared dirty guard',()=>{
  const source=fs.readFileSync('app/static/warehouse-assistant.js','utf8');
  const close=source.match(/function closePreorderPreview\(\)\{[^\n]+/)[0];
  const dialog={open:true,close(){this.open=false}},state={previewPreorderId:1};
  const c=vm.createContext({$:()=>dialog,state,requestDraftEditorClose:()=>{}});
  vm.runInContext(close,c);vm.runInContext('closePreorderPreview()',c);
  assert.equal(dialog.open,true);assert.equal(state.previewPreorderId,1);
  c.requestDraftEditorClose=(_kind,close)=>close();vm.runInContext('closePreorderPreview()',c);assert.equal(dialog.open,false);
});
