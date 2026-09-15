const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');

test('transfer stage navigation stays above scrolling content in normal and fullscreen workspaces',()=>{
  const html=readFileSync('app/static/warehouse-assistant.html','utf8');
  const css=readFileSync('app/static/warehouse-operations.css','utf8');
  const navigation=html.match(/<div class="transfer-actions transfer-stage-navigation"[^>]*>(.*?)<\/div>/s)?.[1];
  assert.ok(navigation,'one persistent stage bar must remain outside all stage panels');
  for(const [stage,panel] of [['proposals','balanceProposalPanel'],['requests','balanceRequestPanel'],['documents','balanceDocumentsPanel']]){
    assert.match(navigation,new RegExp(`data-transfer-stage="${stage}"[^>]*aria-controls="${panel}"`));
  }
  assert.match(css,/#transfersView>\.transfer-stage-navigation\{[^}]*position:sticky;[^}]*top:var\(--wa-topbar-height,42px\)/);
  assert.match(css,/#transfersView\.workspace-fullscreen>\.transfer-stage-navigation\{top:0\}/);
});

test('operational stylesheet wins over historical density and feature styles',()=>{
  const html=readFileSync('app/static/warehouse-assistant.html','utf8');
  const sheets=[...html.matchAll(/<link[^>]*href="([^"]+\.css[^\"]*)"/g)].map(x=>x[1]);
  assert.match(sheets.at(-3),/warehouse-operations\.css/);
  assert.match(sheets.at(-2),/warehouse-pages\.css/);
  assert.match(sheets.at(-1),/warehouse-purchase-groups\.css/);
  assert.match(html,/warehouse-operations\.js\?v=5/);
  const css=readFileSync('app/static/warehouse-operations.css','utf8');
  assert.match(css,/\.operation-table\{min-height:410px/);
  assert.match(css,/\.operation-tools :is\(\.work-view-bar,\.table-export-bar\)\{display:contents/);
  assert.match(css,/\.workspace-fullscreen\[hidden\]\{display:none!important/);
  assert.doesNotMatch(css,/zoom:|scale\(/);
});

test('quantity controls stay beside product identity in the default work layout',()=>{
  const context=vm.createContext({document:{addEventListener(){}},window:{addEventListener(){}}});
  vm.runInContext(readFileSync('app/static/warehouse-column-layouts.js','utf8'),context);
  const order=vm.runInContext("standardColumnOrder(['product_code','product_name','consumer_price','transfer_supply','final_order_cartons'])",context);
  assert.deepEqual(Array.from(order),['product_code','product_name','final_order_cartons','transfer_supply','consumer_price']);
});

test('loading saved layouts cannot discard the designed name-column width',()=>{
  const header={dataset:{userColumnWidth:'240'}},table={querySelectorAll:()=>[header]};
  const c=vm.createContext({document:{addEventListener(){}},window:{addEventListener(){}},table});
  vm.runInContext(readFileSync('app/static/warehouse-column-layouts.js','utf8'),c);
  vm.runInContext('preserveDesignedColumnWidths(table)',c);
  assert.equal(header.dataset.defaultColumnWidth,'240');
  header.dataset.userColumnWidth='300';
  vm.runInContext('preserveDesignedColumnWidths(table)',c);
  assert.equal(header.dataset.defaultColumnWidth,'240');
  assert.equal(header.dataset.userColumnWidth,'300');
});

test('secondary action menus retain original controls, disabled state and draft values',()=>{
  const makeNode=(tag='button',attrs=[])=>({tag,attrs,dataset:{},children:[],disabled:false,value:'',
    matches(selector){return selector.split(',').some(s=>s===this.tag||this.attrs.includes(s));},
    append(...nodes){for(const node of nodes){if(node.parentElement){const p=node.parentElement;p.children.splice(p.children.indexOf(node),1);}this.children.push(node);node.parentElement=this;}},
    addEventListener(name,fn){this[name]=fn;}
  });
  const group=makeNode('div'),edit=makeNode('button',['[data-manual-edit]']),approve=makeNode(),revoke=makeNode(),remove=makeNode(),portal=makeNode('button',['[data-order-portal-kind]']);
  portal.disabled=true;edit.value='unsaved draft';group.append(edit,approve,revoke,remove,portal);
  const document={querySelectorAll:()=>[group],createElement:tag=>makeNode(tag),addEventListener(){}};
  const c=vm.createContext({document});vm.runInContext(readFileSync('app/static/warehouse-operations.js','utf8'),c);
  vm.runInContext('compactOrderActions();compactOrderActions()',c);
  assert.equal(group.children.length,2);assert.equal(group.children[0],edit);assert.equal(edit.value,'unsaved draft');
  const menu=group.children[1],content=menu.children[1];
  assert.deepEqual(content.children,[approve,revoke,remove,portal]);assert.equal(portal.disabled,true);
  assert.equal(content.parentElement,menu);assert.equal(menu.parentElement,group);
});

test('table tool registration preserves controls and merges late module toolbars',()=>{
  class Node {
    constructor(className=''){this.className=className;this.childNodes=[];this.dataset={};this.attributes={};this.classList={contains:x=>this.className.split(' ').includes(x),add:x=>{if(!this.classList.contains(x))this.className+=' '+x}};}
    get previousElementSibling(){const p=this.parentElement;return p?.childNodes[p.childNodes.indexOf(this)-1]||null;}
    matches(s){return s.split(',').some(x=>this.classList.contains(x.slice(1)));}
    remove(){if(this.parentElement){const p=this.parentElement;p.childNodes.splice(p.childNodes.indexOf(this),1);this.parentElement=null;}}
    append(...nodes){for(const node of nodes){node.remove();this.childNodes.push(node);node.parentElement=this;}}
    prepend(...nodes){for(const node of [...nodes].reverse()){node.remove();this.childNodes.unshift(node);node.parentElement=this;}}
    before(node){const p=this.parentElement;node.remove();p.childNodes.splice(p.childNodes.indexOf(this),0,node);node.parentElement=p;}
    setAttribute(k,v){this.attributes[k]=v;}
    addEventListener(k,fn){this[k]=fn;}
    querySelectorAll(s){return this.childNodes.flatMap(n=>[...(s==='[data-table-fullscreen]'&&n.dataset.tableFullscreen?[n]:[]),...n.querySelectorAll(s)]);}
    querySelector(s){return this.querySelectorAll(s)[0]||null;}
  }
  const parent=new Node('panel'),wrap=new Node('table-wrap'),exportBar=new Node('table-export-bar'),exportButton=new Node('button');
  exportButton.value='retained';exportBar.append(exportButton);parent.append(exportBar,wrap);
  const table={parentElement:wrap,closest:s=>s==='.panel'?parent:null,querySelectorAll:()=>[]};
  const document={querySelectorAll:()=>[table],createElement:()=>new Node(),addEventListener(){}};
  const context=vm.createContext({document});
  vm.runInContext(readFileSync('app/static/warehouse-operations.js','utf8'),context);
  vm.runInContext('compactTableTools()',context);
  const lateBar=new Node('work-view-bar');wrap.before(lateBar);
  vm.runInContext('compactTableTools();compactTableTools()',context);
  const bars=parent.childNodes.filter(n=>n.classList.contains('operation-tools'));
  assert.equal(bars.length,1);assert.equal(bars[0].querySelectorAll('[data-table-fullscreen]').length,1);
  assert.equal(exportButton.value,'retained');assert.equal(exportButton.parentElement,exportBar);
  assert.equal(exportBar.parentElement,bars[0]);assert.equal(lateBar.parentElement,bars[0]);
});
