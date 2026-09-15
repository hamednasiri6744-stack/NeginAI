const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
function setup(){
  const nodes={},rows=[{dataset:{productCode:'001'}}];
  const context=vm.createContext({
    document:{addEventListener(){},querySelectorAll(){return rows}},
    $:key=>nodes[key]??={value:'',innerHTML:'',textContent:'',open:false,close(){this.open=false}},
    normalizeSearchText:value=>String(value).replace(/[۰-۹]/g,c=>c.charCodeAt(0)-1776).toLowerCase(),
    esc:value=>String(value??'').replaceAll('<','&lt;').replaceAll('"','&quot;'),fa:String,
    state:{bootstrap:{preorder_catalog_supported:true}},toast(){},
  });
  vm.runInContext(readFileSync('app/static/warehouse-preorder-catalog.js','utf8'),context);
  context.items=[{product_code:'001',product_name:'existing',can_add:true},
    {product_code:'002',product_name:'<unsafe>',can_add:true,barcode:'000123',conversion_rate:6},
    {product_code:'003',product_name:'blocked',can_add:false}];
  vm.runInContext('preorderCatalog.items=items',context);
  return {context,nodes,rows};
}
test('picker escapes names and disables existing or blocked products',()=>{
  const {context,nodes}=setup();vm.runInContext('renderPreorderCatalog()',context);
  const html=nodes['#preorderCatalogRows'].innerHTML;
  assert.match(html,/&lt;unsafe>/);assert.doesNotMatch(html,/<unsafe>/);
  assert.match(html,/data-catalog-add="001" disabled/);
  assert.match(html,/data-catalog-add="003" disabled/);
  assert.match(html,/data-catalog-add="002" >/);
});
test('localized search matches barcode without converting stored identity',()=>{
  const {context,nodes}=setup();context.$('#preorderCatalogSearch').value='۱۲۳';
  vm.runInContext('renderPreorderCatalog()',context);
  assert.match(nodes['#preorderCatalogRows'].innerHTML,/000123/);
  assert.doesNotMatch(nodes['#preorderCatalogRows'].innerHTML,/data-catalog-add="001"/);
});
test('reset invalidates pending requests and hides additions for approved orders',()=>{
  const {context,nodes}=setup();
  vm.runInContext("resetPreorderCatalog({id:2,email_send_token:'original',status:'approved'})",context);
  assert.equal(nodes['#addPreorderProductsButton'].hidden,true);
  assert.equal(vm.runInContext('preorderCatalog.request',context),1);
  assert.equal(vm.runInContext('preorderCatalog.token',context),'original');
});
