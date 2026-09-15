"""Run only the owned native diagnostic clone, never production.

This leaves the small diagnostic clone available for inspection. --install
installs the staged wrapper and explicitly enables only the local test policy.
Normal attempts retain the result and pre/post stock counts, never customer data.
"""
import argparse
import json
from pathlib import Path
import re
from uuid import UUID
import pyodbc

parser=argparse.ArgumentParser()
parser.add_argument('--install',action='store_true')
parser.add_argument('--commit',action='store_true')
parser.add_argument('--diagnostic',action='store_true',help='Print native error in isolated clone only; no behavior changes')
parser.add_argument('--replay',action='store_true',help='Read immutable local test audit and retry exact bytes')
args=parser.parse_args()
c=pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=127.0.0.1;DATABASE=NeginAI_InterwarehouseBridge_Test;Trusted_Connection=yes;TrustServerCertificate=yes;',autocommit=True,timeout=10)
c.timeout=60
assert tuple(c.execute("SELECT DB_NAME(),CONVERT(int,DATABASEPROPERTYEX(DB_NAME(),'IsClone')),(SELECT CONVERT(int,value) FROM sys.extended_properties WHERE class=0 AND name='NeginAI_IsolatedInterwarehouseTest')").fetchone())==('NeginAI_InterwarehouseBridge_Test',1,1)
if args.install:
    sql=Path('scripts/sql/install_interwarehouse_credit_bridge.sql').read_text(encoding='utf-8')
    assert sql.count('USE [NeginPakhsh];')==1
    sql=sql.replace('USE [NeginPakhsh];','USE [NeginAI_InterwarehouseBridge_Test];')
    if args.diagnostic:
        sql=sql.replace("IF NULLIF(LTRIM(RTRIM(REPLACE", "PRINT @Err; IF NULLIF(LTRIM(RTRIM(REPLACE")
    for batch in re.split(r'^GO\s*$',sql,flags=re.M|re.I):
        if batch.strip():c.execute(batch)
    c.execute("IF NOT EXISTS(SELECT 1 FROM NeginAI.InterwarehouseCreditPolicy) INSERT NeginAI.InterwarehouseCreditPolicy VALUES(ORIGINAL_LOGIN(),2,1,1,1,1)")
data=dict(version=1,document_number='TR-NATIVE-TEST-000001',source_stock_ref=2,destination_stock_ref=1,voucher_date='1405/05/31',lines=[dict(product_code='364509603',quantity=1)])
key=str(UUID('d050d658-f4d1-45a4-8578-fa19938c0500'))
def call(commit):
    q=c.cursor();q.execute('EXEC NeginAI.usp_CreateInterwarehouseCredit @TransferKey=?,@RequestedBy=?,@PayloadJson=?,@Commit=?',key,'isolated-test',json.dumps(data),commit)
    while True:
        if q.description and 'BridgeStatus' in [x[0] for x in q.description]:
            if args.diagnostic:print('native_messages',ascii(q.messages))
            return dict(zip([x[0] for x in q.description],q.fetchone()))
        if not q.nextset():raise AssertionError('No bridge result')
if args.replay:
    stored=c.execute('SELECT PayloadJson FROM NeginAI.InterwarehouseCreditAudit WHERE TransferKey=?',key).fetchone()
    assert stored is not None
    data=json.loads(stored[0])
    before=[tuple(r) for r in c.execute('SELECT StockDCRef,OnHandQty FROM gnr.tblStockGoods WHERE GoodsRef=4665 ORDER BY StockDCRef')]
    result=call(True)
    assert result['BridgeStatus']=='sent' and result['Replayed'] and result['Confirmed'],result
    after=[tuple(r) for r in c.execute('SELECT StockDCRef,OnHandQty FROM gnr.tblStockGoods WHERE GoodsRef=4665 ORDER BY StockDCRef')]
    assert before==after
    print('native_exact_retry',json.dumps(result,default=str),'stock_unchanged',before==after)
    c.close()
    raise SystemExit(0)
result=call(False)
print(json.dumps(result,ensure_ascii=True,default=str))
if args.commit and result['BridgeStatus']=='ready':
    data['validation_token']=result['ValidationToken']
    result=call(True)
    print(json.dumps(result,ensure_ascii=True,default=str))
    print('stock', [tuple(r) for r in c.execute('SELECT StockDCRef,OnHandQty FROM gnr.tblStockGoods WHERE GoodsRef=4665 ORDER BY StockDCRef')])
    print('vouchers', [tuple(r) for r in c.execute('SELECT VocherTypeCode,COUNT(*) FROM inv.tblVocherHdr GROUP BY VocherTypeCode')])
    assert result['BridgeStatus']=='sent',result
c.close()
