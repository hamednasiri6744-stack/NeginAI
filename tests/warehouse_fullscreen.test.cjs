const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
test('fullscreen toggles existing form without losing draft or scroll',()=>{
  const classes=new Set(),button={setAttribute(k,v){this[k]=v}},scroll={scrollTop:140,scrollLeft:-90},draft={value:'۲۰'};
  const surface={classList:{toggle:(k,on)=>on?classes.add(k):classes.delete(k)},querySelector:()=>button,querySelectorAll:s=>s==='table'?[{}]:s.startsWith('[data-workspace')?[button]:[scroll],draft};
  const c=vm.createContext({document:{addEventListener(){}},requestAnimationFrame:fn=>fn(),fitFixedTableColumns:()=>{scroll.scrollTop=0;scroll.scrollLeft=0},surface});
  vm.runInContext(readFileSync('app/static/warehouse-fullscreen.js','utf8'),c);
  for(const enabled of [true,false]){
    vm.runInContext(`setWorkspaceFullscreen(surface,${enabled})`,c);
    assert.equal(classes.has('workspace-fullscreen'),enabled);assert.equal(button['aria-pressed'],String(enabled));
    assert.equal(surface.draft,draft);assert.equal(draft.value,'۲۰');assert.equal(scroll.scrollTop,140);assert.equal(scroll.scrollLeft,-90);
  }
});

function fullscreenWorkspace(){
  const listeners=new Map(),observers=[],surfaces=[];
  const document={body:{},activeElement:null,
    addEventListener(type,listener){const handlers=listeners.get(type)||[];handlers.push(listener);listeners.set(type,handlers)},
    getElementById(){return null},
    querySelectorAll(selector){return surfaces.filter(surface=>selector==='.workspace-fullscreen'&&surface.classList.contains('workspace-fullscreen'))},
    querySelector(selector){return selector==='dialog[open]'?surfaces.find(surface=>surface.tagName==='DIALOG'&&surface.open):this.querySelectorAll(selector)[0]}
  };
  const context=vm.createContext({document,requestAnimationFrame:fn=>fn(),fitFixedTableColumns(){},
    MutationObserver:class{constructor(callback){observers.push(callback)}observe(){}}
  });
  vm.runInContext(readFileSync('app/static/warehouse-fullscreen.js','utf8'),context);
  const emit=(type,event={})=>{event.preventDefault=()=>{event.defaultPrevented=true};for(const listener of listeners.get(type)||[])listener(event);return event};
  emit('DOMContentLoaded');
  function surface(parentElement=null,tagName='SECTION'){
    const classes=new Set(),handlers=new Map(),draft={value:'۲۰'},scroll={scrollTop:140,scrollLeft:-90};
    const button={setAttribute(key,value){this[key]=value},focus(){document.activeElement=this}};
    const node={parentElement,tagName,dataset:{},hidden:false,open:tagName==='DIALOG',draft,button,
      classList:{contains:key=>classes.has(key),toggle:(key,on)=>on?classes.add(key):classes.delete(key)},
      closest(selector){if(selector==='[hidden]')return this.hidden?this:this.parentElement?.closest(selector)||null;if(selector==='dialog')return this.tagName==='DIALOG'?this:null;return null},
      querySelectorAll(selector){return selector==='table'?[]:selector.startsWith('[data-workspace')?[button]:[scroll]},
      addEventListener(type,listener){const list=handlers.get(type)||[];list.push(listener);handlers.set(type,list)},
      dispatch(type){const event={defaultPrevented:false,preventDefault(){this.defaultPrevented=true}};for(const listener of handlers.get(type)||[])listener(event);return event}
    };
    surfaces.push(node);return node;
  }
  return {document,surface,emit,set:(node,enabled)=>context.setWorkspaceFullscreen(node,enabled),flushHidden:()=>observers.forEach(callback=>callback([{type:'attributes',attributeName:'hidden'}]))};
}

test('Escape exits the visible fullscreen workspace even when an older view is hidden',()=>{
  const app=fullscreenWorkspace(),oldView=app.surface(),currentView=app.surface();
  app.set(oldView,true);oldView.hidden=true;app.set(currentView,true);
  const event=app.emit('keydown',{key:'Escape'});
  assert.equal(event.defaultPrevented,true);
  assert.equal(currentView.classList.contains('workspace-fullscreen'),false);
});

test('switching away clears fullscreen on the view and nested panels while retaining drafts',()=>{
  const app=fullscreenWorkspace(),view=app.surface(),panel=app.surface(view);
  app.set(view,true);app.set(panel,true);view.hidden=true;app.flushHidden();
  for(const surface of [view,panel]){
    assert.equal(surface.classList.contains('workspace-fullscreen'),false);
    assert.equal(surface.button['aria-pressed'],'false');
    assert.equal(surface.draft.value,'۲۰');
  }
  view.hidden=false;
  assert.equal(panel.classList.contains('workspace-fullscreen'),false);
});

test('Escape first exits modal fullscreen and then delegates to the dirty-draft close guard',()=>{
  const app=fullscreenWorkspace(),dialog=app.surface(null,'DIALOG');let closeRequests=0;
  dialog.addEventListener('cancel',event=>{
    if(event.defaultPrevented||dialog.classList.contains('workspace-fullscreen'))return;
    event.preventDefault();closeRequests++;
  });
  app.set(dialog,true);app.document.activeElement=dialog.draft;
  assert.equal(dialog.dispatch('cancel').defaultPrevented,true);
  assert.equal(dialog.classList.contains('workspace-fullscreen'),false);
  assert.equal(dialog.open,true);assert.equal(closeRequests,0);
  assert.equal(app.document.activeElement,dialog.draft);assert.equal(dialog.draft.value,'۲۰');
  assert.equal(dialog.dispatch('cancel').defaultPrevented,true);
  assert.equal(closeRequests,1);
});
