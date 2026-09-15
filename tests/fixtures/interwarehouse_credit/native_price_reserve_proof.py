"""Native clone proof: price reserve is separate from healthy transfer stock.

Creates one explicit native type76 reservation fixture ONLY in the retained,
owned loopback clone, then one type65 credit. Never releases reserve/type41,
never changes ERP global settings, and always disables local test policies.
"""
import json
from pathlib import Path
import re
from uuid import UUID,uuid5
import pyodbc

NAME='NeginAI_InterwarehouseBridge_Test'
c=pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=127.0.0.1;DATABASE=NeginAI_InterwarehouseBridge_Test;Trusted_Connection=yes;TrustServerCertificate=yes;',autocommit=True,timeout=10)
c.timeout=90
assert tuple(c.execute("SELECT DB_NAME(),CONVERT(int,DATABASEPROPERTYEX(DB_NAME(),'IsClone')),(SELECT CONVERT(int,value) FROM sys.extended_properties WHERE class=0 AND name='NeginAI_IsolatedInterwarehouseTest')").fetchone())==(NAME,1,1)
assert c.execute('SELECT COUNT(*) FROM NeginAI.InterwarehouseCreditPolicy WHERE Enabled=1 OR IsolatedValidationComplete=1').fetchone()[0]==0
sql=Path('scripts/sql/install_interwarehouse_credit_bridge.sql').read_text(encoding='utf-8')
assert sql.count('USE [NeginPakhsh];')==1
for batch in re.split(r'^GO\s*$',sql.replace('USE [NeginPakhsh];',f'USE [{NAME}];'),flags=re.M|re.I):
    if batch.strip():c.execute(batch)

NAMESPACE=UUID('2e5f1819-6057-4463-89c9-c5803f73fbb5')
reserve_key=str(uuid5(NAMESPACE,'native-price-reserve-fixture'))
assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr WHERE UniqueId=?',reserve_key).fetchone()[0]==0,'Fixture already executed; inspect retained proof'
def balances():
    return {int(r[0]):[int(r[1]),int(r[2])] for r in c.execute('SELECT StockDCRef,OnHandQty,ReservedQty FROM gnr.tblStockGoods WHERE AccYear=1405 AND GoodsRef=4665 ORDER BY StockDCRef')}

def footprint():
    return dict(balances=balances(),headers=c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0],
        items=c.execute('SELECT COUNT(*) FROM inv.tblVocherItm').fetchone()[0],
        audit=c.execute('SELECT COUNT(*) FROM NeginAI.InterwarehouseCreditAudit').fetchone()[0],
        counters=[tuple(r) for r in c.execute('SELECT VocherType,StockDCRef,AccYear,VocherNo FROM dbo.tblVocherNo ORDER BY VocherType,StockDCRef,AccYear')])

def result_row(q,column):
    while True:
        if q.description and column in [x[0] for x in q.description]:
            return dict(zip([x[0] for x in q.description],q.fetchone()))
        if not q.nextset():raise AssertionError('Missing result')

def bridge(data,commit,key):
    q=c.cursor();q.execute('EXEC NeginAI.usp_CreateInterwarehouseCredit @TransferKey=?,@RequestedBy=?,@PayloadJson=?,@Commit=?',
                         key,'isolated-price-reserve-test',json.dumps(data),commit)
    return result_row(q,'BridgeStatus')

def payload(number,source=2,qty=1):
    return dict(version=1,document_number=number,source_stock_ref=source,destination_stock_ref=1 if source==2 else 2,
                voucher_date='1405/05/31',lines=[dict(product_code='364509603',quantity=qty)])

before_reserve=balances()
assert before_reserve[2]==[287,0],before_reserve
temp=re.search(r'CREATE TABLE #apiVocher \(.*?\n  \);',sql,re.S).group(0)
c.execute(temp)
native="""SET XACT_ABORT ON; SET NOCOUNT ON;
DECLARE @Id int,@No int,@Err nvarchar(max),@Result varchar(max);
BEGIN TRY
 BEGIN TRANSACTION;
 INSERT #apiVocher(StockDCRef,VocherTypeCode,HealthCodeType,HealthCode,VocherDate,UserRef,AccYear,DCRef,Comment,UniqueId,GoodsRef,RowOrder,UnitRef,UnitCapacity,UnitQty,TotalQty)
 VALUES(2,76,1009,1,'1405/05/31',1,1405,1,'ISOLATED PRICE RESERVE FIXTURE',?,4665,1,3,1,200,200);
 EXEC dbo.usp_DBApi_CreateInvVocher @AppUserId=1,@AccYear=1405,@DCRef=1,@VocherId=@Id OUTPUT,@VocherNo=@No OUTPUT,@DontChangeUnitQty=1;
 SET @Err=N'';SET @Result='';
 EXEC FRU.usp_VocherConfirmation @AccYear=1405,@DCRef=1,@UserRef=1,@VocherHdrRef=@Id,@IsConfirm=1,@ErrMsg=@Err OUTPUT,@ResultMsg=@Result OUTPUT;
 IF NULLIF(LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(@Err,CHAR(13),N''),CHAR(10),N''),CHAR(9),N''))),N'') IS NOT NULL THROW 51570,@Err,1;
 IF NOT EXISTS(SELECT 1 FROM inv.tblVocherHdr WHERE ID=@Id AND VocherTypeCode=76 AND ConfirmedBy=1 AND ConfirmDate IS NOT NULL) THROW 51570,'Native reservation not confirmed.',1;
 IF NOT EXISTS(SELECT 1 FROM gnr.tblStockGoods WHERE GoodsRef=4665 AND StockDCRef=2 AND AccYear=1405 AND OnHandQty=87 AND ReservedQty=200) THROW 51570,'Unexpected fixture stock effect.',1;
 COMMIT;
 SELECT @Id AS ReserveVocherId,@No AS ReserveVocherNo;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK;
 THROW;
END CATCH;"""
reserve=result_row(c.cursor().execute(native,reserve_key),'ReserveVocherId')
c.execute('DROP TABLE #apiVocher')
assert balances()==dict(before_reserve)|{2:[87,200]}
print(json.dumps(dict(native_reserve_fixture=reserve,before=before_reserve,after=balances())),flush=True)
cases=[]
try:
    c.execute('UPDATE NeginAI.InterwarehouseCreditPolicy SET Enabled=1,IsolatedValidationComplete=1 WHERE LoginName=ORIGINAL_LOGIN() AND (SourceStockDCRef=2 AND DestinationStockDCRef=1 OR SourceStockDCRef=1 AND DestinationStockDCRef=2)')
    data=payload('TR-NATIVE-PRICE-RESERVE-SUFFICIENT')
    key=str(uuid5(NAMESPACE,data['document_number']))
    before=footprint();ready=bridge(data,False,key)
    assert ready['BridgeStatus']=='ready',ready
    assert footprint()==before
    data['validation_token']=ready['ValidationToken']
    sent=bridge(data,True,key)
    assert sent['BridgeStatus']=='sent' and sent['Confirmed'],sent
    after=balances();assert after==dict(before['balances'])|{2:[86,200]},after
    replay=bridge(data,True,key);assert replay['BridgeStatus']=='sent' and replay['Replayed'] and balances()==after
    print(json.dumps(dict(sufficient_native=sent,source_before=[87,200],source_after=[86,200],reserved_unchanged=True)),flush=True)
    for source in [2,1]:
        for commit in [False,True]:
            before=footprint();healthy,reserved=before['balances'][source]
            data=payload(f'TR-NATIVE-PRICE-SHORT-{source}-{int(commit)}',source,healthy+1)
            response=bridge(data,commit,str(uuid5(NAMESPACE,data['document_number'])))
            assert response['BridgeStatus']=='rejected' and response['ErrorCode']==51515,response
            issues=json.loads(response['StockIssuesJson'])
            assert issues==[dict(ProductCode='364509603',RequestedQuantity=healthy+1,OnHandQuantity=healthy,ReservedQuantity=reserved,ShortageQuantity=1)],issues
            assert footprint()==before,'Rejected shortage changed stock, ledger, audit or counter'
            case=dict(source=source,commit=commit,issues=issues,no_side_effects=True)
            cases.append(case);print(json.dumps(case),flush=True)
    assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr WHERE VocherTypeCode IN(15,41)').fetchone()[0]==0
finally:
    c.execute('UPDATE NeginAI.InterwarehouseCreditPolicy SET Enabled=0,IsolatedValidationComplete=0 WHERE LoginName=ORIGINAL_LOGIN()')
    assert c.execute('SELECT COUNT(*) FROM NeginAI.InterwarehouseCreditPolicy WHERE Enabled=1 OR IsolatedValidationComplete=1').fetchone()[0]==0
    print(json.dumps(dict(policies_disabled=True,shortage_cases=len(cases),balances_final=balances(),release_or_destination_debit_count=c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr WHERE VocherTypeCode IN(15,41)').fetchone()[0])),flush=True)
    c.close()
