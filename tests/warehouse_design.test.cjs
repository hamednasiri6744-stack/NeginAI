const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');

function setup(){
  const handlers={};
  let focused=false;
  const panel={id:'checkbarImagePanel',open:true,contains:()=>false,querySelector:()=>({focus:()=>{focused=true}})};
  const editor={open:true,querySelectorAll:()=>panel.open?[panel]:[],addEventListener:(name,fn)=>{handlers[name]=fn}};
  vm.runInNewContext(readFileSync('app/static/warehouse-design.js','utf8'),{document:{getElementById:()=>editor}});
  return {panel,editor,dispatch:(type,event)=>handlers[type]?.(event),focused:()=>focused};
}

test('scrollbar clicks and focus outside the import panel keep the review open',()=>{
  const {panel,editor,dispatch}=setup();
  // Native scrollbar interaction can target the dialog or move focus to it.
  dispatch('click',{target:editor});
  assert.equal(panel.open,true);
  dispatch('focusin',{target:editor});
  assert.equal(panel.open,true);
  dispatch('click',{target:{closest:()=>null}});
  assert.equal(panel.open,true);
});

test('review shortcut leaves the import panel open',()=>{
  const {panel,dispatch}=setup();
  const shortcut={closest:()=>shortcut};
  dispatch('click',{target:shortcut});
  dispatch('focusin',{target:shortcut});
  assert.equal(panel.open,true);
});

test('Escape closes the open tool and restores focus without closing the editor',()=>{
  const {panel,editor,dispatch,focused}=setup();
  let prevented=false,stopped=false;
  dispatch('keydown',{key:'Escape',preventDefault:()=>{prevented=true},stopPropagation:()=>{stopped=true}});
  assert.equal(panel.open,false);
  assert.equal(editor.open,true);
  assert.equal(focused(),true);
  assert.equal(prevented,true);
  assert.equal(stopped,true);
});

test('Escape with no open tool is left to the editor',()=>{
  const {panel,dispatch}=setup();panel.open=false;
  dispatch('keydown',{key:'Escape',preventDefault:()=>assert.fail('Unexpected prevention'),stopPropagation:()=>assert.fail('Unexpected interception')});
});
