"""Native receipt + reservation rehearsal only in the owned loopback clone.

Fixture documents, supplier and policies are rolled back. No production writes.
Native procedures and triggers are never replaced or disabled.
"""
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from uuid import uuid4
import pyodbc

NAME='NeginAI_InterwarehouseBridge_Test'
c=pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=127.0.0.1;DATABASE='+NAME+';Trusted_Connection=yes;TrustServerCertificate=yes;',autocommit=True,timeout=10)
c.timeout=90
assert tuple(c.execute("SELECT DB_NAME(),CONVERT(int,DATABASEPROPERTYEX(DB_NAME(),'IsClone')),(SELECT CONVERT(int,value) FROM sys.extended_properties WHERE class=0 AND name='NeginAI_IsolatedInterwarehouseTest')").fetchone())==(NAME,1,1)
for filename in ['scripts/sql/install_checkbar_receipt_bridge.sql','scripts/sql/install_checkbar_receipt_price_bridge.sql']:
    sql=Path(filename).read_text(encoding='utf-8')
    if filename.endswith('install_checkbar_receipt_bridge.sql'):
        sql=sql.replace("N'NeginAI_CheckbarBridge_Test'","N'NeginAI_CheckbarBridge_Test',N'NeginAI_InterwarehouseBridge_Test'")
    if '--diagnostic' in sys.argv and filename.endswith('install_checkbar_receipt_price_bridge.sql'):
        sql=re.sub(r"ELSE N'[^']*' END;","ELSE ERROR_MESSAGE() END;",sql)
    for batch in re.split(r'^GO\s*$',sql,flags=re.M|re.I):
        if batch.strip():c.execute(batch)

def balances():
    return [tuple(str(v) for v in row) for row in c.execute('SELECT StockDCRef,OnHandQty,ReservedQty FROM gnr.tblStockGoods WHERE GoodsRef=4665 AND AccYear=1405 ORDER BY StockDCRef')]

def call(data,commit,key):
    q=c.cursor();q.execute('EXEC NeginAI.usp_CreateCheckbarReceiptV2 @TransferKey=?,@RequestedBy=?,@PayloadJson=?,@Commit=?',key,'native-isolated-proof',json.dumps(data),commit)
    while True:
        if q.description and 'BridgeStatus' in [r[0] for r in q.description]:return dict(zip([r[0] for r in q.description],q.fetchone()))
        if not q.nextset():raise AssertionError('No bridge result')

def line(mode,qty):
    old=['0','0'] if mode=='unpriced' else ['200','100']
    new=['300','150'] if mode=='changed' else old
    return dict(product_code='364509603',quantity=str(qty),price_mode=mode,item_comment='-'.join(new),
      consumer_price_current=old[0],manufacturer_price_current=old[1],consumer_price_effective=new[0],manufacturer_price_effective=new[1])

before=balances()
mode=next((v.split('=',1)[1] for v in sys.argv if v.startswith('--mode=')),'changed')
assert mode in ('changed','unchanged','unpriced')
headers=c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]
try:
    c.execute('BEGIN TRANSACTION')
    c.execute("IF NOT EXISTS(SELECT 1 FROM dbo.ContactType WHERE ContactTypeId=1) BEGIN SET IDENTITY_INSERT dbo.ContactType ON; INSERT dbo.ContactType(ContactTypeId,ContactTypeName) VALUES(1,'ISOLATED'); SET IDENTITY_INSERT dbo.ContactType OFF; END; IF NOT EXISTS(SELECT 1 FROM dbo.ContactTitle WHERE ContactTitleId=2) BEGIN SET IDENTITY_INSERT dbo.ContactTitle ON; INSERT dbo.ContactTitle(ContactTitleId,ContactTitleName,ContactTypeId) VALUES(2,'ISOLATED',1); SET IDENTITY_INSERT dbo.ContactTitle OFF; END")
    c.execute("INSERT gnr.tblSupplier(Id,SupplierName,Active) VALUES(900001,'ISOLATED RECEIPT PRICE TEST',1)")
    c.execute('INSERT gnr.tblGoodsSupplier(Id,GoodsRef,SupplierRef) VALUES(900001,4665,900001)')
    c.execute('INSERT NeginAI.ReceiptBridgePolicy VALUES(ORIGINAL_LOGIN(),2,1,1)')
    c.execute('INSERT NeginAI.ReceiptPricePolicy VALUES(ORIGINAL_LOGIN(),2,1)')
    data=dict(price_workflow_version=2,checkbar_number='CB-NATIVE-PRICE-TEST',stock_dc_ref=2,supplier_refs=[900001],
      supplier_name='ISOLATED RECEIPT PRICE TEST',voucher_date='1405/05/31',reference_no='12345',comment='CB-NATIVE-PRICE-TEST',
      lines=[line(mode,12)])
    key=str(uuid4());ready=call(data,False,key)
    print(json.dumps(dict(preview=ready),default=str),flush=True)
    # Preflight intentionally rolls back its read transaction, including an outer
    # fixture transaction. Seed again after that rollback for native commit proof.
    c.execute('BEGIN TRANSACTION')
    c.execute("IF NOT EXISTS(SELECT 1 FROM dbo.ContactType WHERE ContactTypeId=1) BEGIN SET IDENTITY_INSERT dbo.ContactType ON; INSERT dbo.ContactType(ContactTypeId,ContactTypeName) VALUES(1,'ISOLATED'); SET IDENTITY_INSERT dbo.ContactType OFF; END; IF NOT EXISTS(SELECT 1 FROM dbo.ContactTitle WHERE ContactTitleId=2) BEGIN SET IDENTITY_INSERT dbo.ContactTitle ON; INSERT dbo.ContactTitle(ContactTitleId,ContactTitleName,ContactTypeId) VALUES(2,'ISOLATED',1); SET IDENTITY_INSERT dbo.ContactTitle OFF; END")
    c.execute("INSERT gnr.tblSupplier(Id,SupplierName,Active) VALUES(900001,'ISOLATED RECEIPT PRICE TEST',1)")
    c.execute('INSERT gnr.tblGoodsSupplier(Id,GoodsRef,SupplierRef) VALUES(900001,4665,900001)')
    c.execute('INSERT NeginAI.ReceiptBridgePolicy VALUES(ORIGINAL_LOGIN(),2,1,1)')
    c.execute('INSERT NeginAI.ReceiptPricePolicy VALUES(ORIGINAL_LOGIN(),2,1)')
    assert ready['BridgeStatus']=='ready',ready
    data['validation_token']=ready['ValidationToken']
    result=call(data,True,key)
    print(json.dumps(dict(result=result,balances=balances()),default=str),flush=True)
    assert result['BridgeStatus']=='sent',result
    docs=json.loads(result['DocumentsJson']);assert len(docs)==(2 if mode=='changed' else 1)
    after=balances()
    for old,new in zip(before,after):
        assert old[0]==new[0]
        assert int(float(new[1]))==int(float(old[1]))+(12 if old[0]=='2' and mode=='unchanged' else 0)
        assert int(float(new[2]))==int(float(old[2]))+(12 if old[0]=='2' and mode=='changed' else 0)
    assert call(data,True,key)['Replayed'] and balances()==after
    assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==headers+len(docs)
    from app import warehouse_receipt_reflection as reflection
    row=dict(transfer_key=key,payload_json=json.dumps(data),result_json=json.dumps(result))
    evidence=reflection._bundle(c.cursor(),row,reflection._contract(c.cursor()))
    assert evidence['status']==('waiting' if mode=='unpriced' else 'reflected'),evidence['message']
    assert len(evidence['pending_lines'])==(1 if mode=='unpriced' else 0)
    print(json.dumps(dict(native_reflection=evidence['status'],pending_lines=len(evidence['pending_lines']))),flush=True)
finally:
    c.execute('IF @@TRANCOUNT>0 ROLLBACK')
    assert balances()==before
    assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==headers
    assert c.execute('SELECT COUNT(*) FROM NeginAI.ReceiptPricePolicy WHERE Enabled=1').fetchone()[0]==0
    c.close()
    print(json.dumps(dict(native_fixture_rolled_back=True)),flush=True)
