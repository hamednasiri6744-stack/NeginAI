"""Positive native confirmation proof for all six routes in the retained clone.

Requires native_six_route_openings.ps1 once. This script only connects to the
owned clone on loopback. All policies it enables are disabled in finally.
Outputs JSON evidence; it never writes production SQL or an application config.
"""
import hashlib
import json
from uuid import UUID,uuid5
import pyodbc

NAME='NeginAI_InterwarehouseBridge_Test'
ROUTES=[(2,1),(2,9),(1,2),(1,9),(9,2),(9,1)]
NAMESPACE=UUID('a8a5d498-e312-4e4a-a489-a265f9de0508')
c=pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=127.0.0.1;DATABASE=NeginAI_InterwarehouseBridge_Test;Trusted_Connection=yes;TrustServerCertificate=yes;',autocommit=True,timeout=10)
c.timeout=90
assert tuple(c.execute("SELECT DB_NAME(),CONVERT(int,DATABASEPROPERTYEX(DB_NAME(),'IsClone')),(SELECT CONVERT(int,value) FROM sys.extended_properties WHERE class=0 AND name='NeginAI_IsolatedInterwarehouseTest')").fetchone())==(NAME,1,1)
assert c.execute('SELECT COUNT(*) FROM NeginAI.InterwarehouseCreditPolicy WHERE Enabled=1 OR IsolatedValidationComplete=1').fetchone()[0]==0

def stock():
    return {int(r[0]):int(r[1]) for r in c.execute('SELECT StockDCRef,OnHandQty FROM gnr.tblStockGoods WHERE GoodsRef=4665 AND AccYear=1405 ORDER BY StockDCRef')}

def config_hash():
    parts=[]
    for table in ['gnr.tblGeneralConfig','gnr.tblServerConfig']:
        parts.extend((table,str(r[0]),str(r[1])) for r in c.execute(f'SELECT KeyName,KeyValue FROM {table} ORDER BY KeyName,KeyValue'))
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()

def call(key,data,commit):
    q=c.cursor()
    q.execute('EXEC NeginAI.usp_CreateInterwarehouseCredit @TransferKey=?,@RequestedBy=?,@PayloadJson=?,@Commit=?',
              key,'isolated-six-route-test',json.dumps(data),commit)
    while True:
        if q.description and 'BridgeStatus' in [x[0] for x in q.description]:
            return dict(zip([x[0] for x in q.description],q.fetchone()))
        if not q.nextset():raise AssertionError('No wrapper result')

evidence=[]
initial_stock=stock()
initial_config=config_hash()
initial_debits=c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr WHERE VocherTypeCode=15').fetchone()[0]
initial_disabled=[r[0] for r in c.execute('SELECT name FROM sys.triggers WHERE is_disabled=1 ORDER BY name')]
try:
    for source,destination in ROUTES:
        c.execute("""IF EXISTS(SELECT 1 FROM NeginAI.InterwarehouseCreditPolicy WHERE LoginName=ORIGINAL_LOGIN() AND SourceStockDCRef=? AND DestinationStockDCRef=?)
          UPDATE NeginAI.InterwarehouseCreditPolicy SET AppUserId=1,Enabled=1,IsolatedValidationComplete=1
          WHERE LoginName=ORIGINAL_LOGIN() AND SourceStockDCRef=? AND DestinationStockDCRef=?;
          ELSE INSERT NeginAI.InterwarehouseCreditPolicy VALUES(ORIGINAL_LOGIN(),?,?,1,1,1)""",source,destination,source,destination,source,destination)
        number=f'TR-NATIVE-SIX-{source}-{destination}'
        key=str(uuid5(NAMESPACE,number))
        data=dict(version=1,document_number=number,source_stock_ref=source,destination_stock_ref=destination,
                  voucher_date='1405/05/31',lines=[dict(product_code='364509603',quantity=1)])
        assert c.execute('SELECT COUNT(*) FROM NeginAI.InterwarehouseCreditAudit WHERE TransferKey=?',key).fetchone()[0]==0,'This proof already ran; inspect retained evidence instead of creating new keys'
        before=stock()
        ready=call(key,data,False)
        assert ready['BridgeStatus']=='ready',(source,destination,ready)
        assert stock()==before,'Preflight changed stock'
        data['validation_token']=ready['ValidationToken']
        result=call(key,data,True)
        assert result['BridgeStatus']=='sent' and result['Confirmed'] and not result['Replayed'],(source,destination,result)
        expected=dict(before);expected[source]-=1
        after=stock()
        assert after==expected,(source,destination,before,after)
        assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr WHERE VocherTypeCode=15').fetchone()[0]==initial_debits
        header=tuple(c.execute('SELECT VocherTypeCode,HealthCodeType,HealthCode,StockDCRef,TStockDCRef,ConfirmedBy,AccYear FROM inv.tblVocherHdr WHERE ID=?',result['VocherId']).fetchone())
        assert header==(65,1047,1,source,destination,1,1405),header
        replay=call(key,data,True)
        assert replay['BridgeStatus']=='sent' and replay['Replayed'] and replay['VocherId']==result['VocherId']
        assert stock()==after
        entry=dict(source_stock_ref=source,destination_stock_ref=destination,quantity=1,document_number=number,
                   transfer_key=key,vocher_id=result['VocherId'],vocher_no=result['VocherNo'],confirmed=True,
                   before=before,after=after,source_only_delta=True,created_type15_count=0,exact_retry_stock_unchanged=True)
        evidence.append(entry)
        print(json.dumps(entry,sort_keys=True),flush=True)
    assert config_hash()==initial_config,'Global ERP configuration changed'
    assert [r[0] for r in c.execute('SELECT name FROM sys.triggers WHERE is_disabled=1 ORDER BY name')]==initial_disabled
    assert sum(initial_stock.values())-sum(stock().values())==6
finally:
    for source,destination in ROUTES:
        c.execute('UPDATE NeginAI.InterwarehouseCreditPolicy SET Enabled=0,IsolatedValidationComplete=0 WHERE LoginName=ORIGINAL_LOGIN() AND SourceStockDCRef=? AND DestinationStockDCRef=?',source,destination)
    policies=[tuple(r) for r in c.execute('SELECT SourceStockDCRef,DestinationStockDCRef,Enabled,IsolatedValidationComplete FROM NeginAI.InterwarehouseCreditPolicy ORDER BY SourceStockDCRef,DestinationStockDCRef')]
    assert all(not row[2] and not row[3] for row in policies),policies
    print(json.dumps(dict(completed_routes=len(evidence),policies_disabled=True,configuration_unchanged=config_hash()==initial_config,stock_final=stock(),debit_count=c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr WHERE VocherTypeCode=15').fetchone()[0]),sort_keys=True),flush=True)
    c.close()
