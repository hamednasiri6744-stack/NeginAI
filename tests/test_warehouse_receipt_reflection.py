"""Synthetic SQL responses and isolated SQLite; no live ERP/API calls."""
import hashlib
import json
import sqlite3
from datetime import datetime

import pytest

from app import warehouse_receipt_reflection as reflection
from app.warehouse_assistant_service import WarehouseAssistantError


@pytest.fixture
def case(monkeypatch):
    definitions = {'trg_tblVocherHdr_UpdateStockGoods': 'synthetic header', 'trg_tblVocherItm_UpdateStockGoods': 'synthetic item'}
    monkeypatch.setattr(reflection, 'TRIGGER_HASHES', {name: hashlib.sha256(text.encode()).hexdigest() for name, text in definitions.items()})
    payload = dict(order_matching={'version': 1}, stock_dc_ref=1, supplier_refs=[7], supplier_name='supplier',
                   voucher_date='1405/06/15', reference_no='2222', comment='CB-1 / v0',
                   lines=[dict(product_code='00123', quantity='120', item_comment='200-100')])
    conn = sqlite3.connect(':memory:')
    from app.warehouse_receipt_lifecycle import init_schema
    init_schema(conn)
    conn.executescript('''CREATE TABLE warehouse_checkbars(id INTEGER PRIMARY KEY,warehouse_code TEXT);
        CREATE TABLE warehouse_checkbar_transfers(document_id INTEGER PRIMARY KEY,status TEXT,
          transfer_key TEXT,payload_json TEXT,result_json TEXT);
        CREATE TABLE warehouse_snapshots(id INTEGER PRIMARY KEY,source_kind TEXT,period_end TEXT);
        CREATE TABLE warehouse_receipt_stock_state(document_id INTEGER PRIMARY KEY,warehouse_code TEXT,
          status TEXT,snapshot_id INTEGER,evidence_json TEXT,updated_at TEXT);
        INSERT INTO warehouse_checkbars VALUES(1,'karaj');
        INSERT INTO warehouse_snapshots VALUES(1,'varanegar','1405/06/16');''')
    conn.execute('INSERT INTO warehouse_checkbar_transfers VALUES(?,?,?,?,?)', (1,'sent',
                 '12345678-1234-1234-1234-123456789abc',json.dumps(payload),json.dumps(dict(VocherId=501,VocherNo=71,AccYear=1405))))
    source = dict(config=[{'KeyValue': '1'}], effects=[dict(CardexType=1, EffectOnHandQty=True, EffectType=1)],
        triggers=[dict(name=name,is_disabled=False,definition=text) for name,text in definitions.items()],
        headers=[dict(ID=501,UniqueId='12345678-1234-1234-1234-123456789abc',VocherNo=71,StockDCRef=1,AccYear=1405,
            VocherTypeCode=20,HealthCodeType=12,HealthCode=1,SupplierRef=7,SupplierName='supplier',
            VocherDate='1405/06/15',TVocherNo=2222,ConfirmDate=None,ConfirmedBy=None,Comment='CB-1 / v0',ChangeTimeStamp=b'123')],
        items=[dict(GoodsRef=100,GoodsCode='00123',UnitRef=1,BasicUnitRef=1,UnitCapacity=1,UnitQty=120,TotalQty=120,Comment='200-100')],
        years=[dict(AccYear=1405)],suppliers=[dict(Id=7)])
    yield conn,source
    conn.close()


class Cursor:
    def __init__(self, source):
        self.source, self.calls, self.description, self.data = source, [], [], []

    def execute(self, sql):
        self.calls.append(sql)
        assert sql.lstrip().upper().startswith('SELECT')
        if 'GNR.tblGeneralConfig' in sql: key='config'
        elif 'inv.tblCardexType' in sql: key='effects'
        elif 'sys.triggers' in sql: key='triggers'
        elif 'FROM inv.tblVocherHdr H' in sql: key='headers'
        elif 'FROM inv.tblVocherItm I' in sql: key='items'
        elif 'FROM gnr.tblAccYear' in sql: key='years'
        elif 'FROM gnr.tblSupplier S' in sql: key='suppliers'
        else: raise AssertionError(sql)
        rows = self.source[key]
        if isinstance(rows, Exception): raise rows
        keys = list(rows[0]) if rows else []
        self.description = [(key,) for key in keys]
        self.data = [tuple(row[key] for key in keys) for row in rows]

    def fetchall(self): return self.data


def import_state(case):
    conn,source=case
    captured=reflection.capture(conn)
    evidence=reflection.source_queries(Cursor(source),captured)
    reflection.apply(conn,captured,evidence,1)
    return conn.execute('SELECT status,evidence_json FROM warehouse_receipt_stock_state').fetchone()


def test_waiting_confirmation_and_unconfirmation_recomputed(case):
    assert import_state(case)[0]=='waiting'
    header=case[1]['headers'][0]
    header.update(ConfirmDate=datetime(2026,9,7),ConfirmedBy=2)
    assert import_state(case)[0]=='reflected'
    header.update(ConfirmDate=None,ConfirmedBy=None)
    assert import_state(case)[0]=='waiting'


def archive_fixture(conn, receipt_id=501):
    row=conn.execute('SELECT transfer_key,payload_json,result_json FROM warehouse_checkbar_transfers').fetchone()
    result=json.loads(row[2]);result['VocherId']=receipt_id
    conn.execute('INSERT INTO warehouse_checkbar_transfer_history VALUES(?,1,0,?,?,?,?,?)',
        (row[0],'worker',row[1],json.dumps(result),'test','test'))


def test_archived_receipt_absence_requires_both_header_and_items_in_fresh_snapshot(case):
    conn,source=case;archive_fixture(conn)
    conn.execute('DELETE FROM warehouse_checkbar_transfers')
    assert reflection.capture(conn)[0]['deleted_generation']
    source['headers']=[]
    assert import_state(case)[0]=='review'  # Orphan details remain.
    source['items']=[]
    assert import_state(case)[0]=='waiting'


def test_restored_older_generation_blocks_stock_even_with_valid_new_receipt(case):
    conn,source=case;archive_fixture(conn,500)
    class GenerationCursor(Cursor):
        restored=False
        def execute(self,sql):
            if 'WHERE H.ID=500' in sql or 'WHERE I.HdrRef=500' in sql:
                self.description=[('ID',)] if self.restored else []
                self.data=[(500,)] if self.restored else []
            else:super().execute(sql)
    captured=reflection.capture(conn);cursor=GenerationCursor(source)
    assert reflection.source_queries(cursor,captured)['1']['status']=='waiting'
    cursor.restored=True
    assert reflection.source_queries(cursor,captured)['1']['status']=='review'


@pytest.mark.parametrize('change', ['deleted','qty','code','comment','unit','capacity','pack_qty','identity','number','warehouse','year','date','reference','supplier','mixed_confirmation'])
def test_deleted_or_changed_receipt_requires_review(case,change):
    _,s=case; h=s['headers'][0]; i=s['items'][0]
    if change=='deleted':s['headers']=[]
    elif change=='qty':i['TotalQty']=121;i['UnitQty']=121
    elif change=='code':i['GoodsCode']='different'
    elif change=='comment':i['Comment']='999-100'
    elif change=='unit':i['UnitRef']=2
    elif change=='capacity':i['UnitCapacity']=12
    elif change=='pack_qty':i['UnitQty']=10
    elif change=='identity':h['UniqueId']='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    elif change=='number':h['VocherNo']=72
    elif change=='warehouse':h['StockDCRef']=2
    elif change=='year':h['AccYear']=1404
    elif change=='date':h['VocherDate']='1405/06/14'
    elif change=='reference':h['TVocherNo']=999
    elif change=='supplier':h['SupplierRef']=8
    else:h['ConfirmedBy']=2
    assert import_state(case)[0]=='review'


@pytest.mark.parametrize('change',['configuration','disabled_trigger','changed_trigger','hidden_definition','wrong_effect','ambiguous_supplier','ambiguous_year'])
def test_unverifiable_effect_contract_requires_review(case,change):
    s=case[1]
    if change=='configuration':s['config'][0]['KeyValue']='0'
    elif change=='disabled_trigger':s['triggers'][0]['is_disabled']=True
    elif change=='changed_trigger':s['triggers'][0]['definition']='different'
    elif change=='hidden_definition':s['triggers'][0]['definition']=None
    elif change=='wrong_effect':s['effects'][0]['EffectType']=-1
    elif change=='ambiguous_supplier':s['suppliers'].append(dict(Id=8))
    else:s['years'].append(dict(AccYear=1404))
    assert import_state(case)[0]=='review'


def test_physical_total_including_overage_and_same_code_price_groups(case):
    conn,s=case
    payload=json.loads(conn.execute('SELECT payload_json FROM warehouse_checkbar_transfers').fetchone()[0])
    payload['order_matching']['allocations']=[dict(quantity=100)]
    payload['lines'].append(dict(product_code='00123',quantity='5',item_comment='300-150'))
    conn.execute('UPDATE warehouse_checkbar_transfers SET payload_json=?',(json.dumps(payload),))
    s['items'][0]['TotalQty']=70;s['items'][0]['UnitQty']=70
    s['items'].append({**s['items'][0],'TotalQty':50,'UnitQty':50})
    s['items'].append({**s['items'][0],'TotalQty':5,'UnitQty':5,'Comment':'300-150'})
    assert import_state(case)[0]=='waiting'
    s['items'].pop()
    assert import_state(case)[0]=='review'


@pytest.mark.parametrize('mutation',['new_sent','changed_payload','removed_sent','changed_result'])
def test_transfer_race_aborts_before_publish(case,mutation):
    conn,s=case;captured=reflection.capture(conn);evidence=reflection.source_queries(Cursor(s),captured)
    if mutation=='new_sent':
        conn.execute("INSERT INTO warehouse_checkbars VALUES(2,'karaj')")
        conn.execute('INSERT INTO warehouse_checkbar_transfers SELECT 2,status,transfer_key,payload_json,result_json FROM warehouse_checkbar_transfers WHERE document_id=1')
    elif mutation=='changed_payload':
        p=json.loads(captured[0]['payload_json']);p['comment']='changed'
        conn.execute('UPDATE warehouse_checkbar_transfers SET payload_json=?',(json.dumps(p),))
    elif mutation=='removed_sent':conn.execute("UPDATE warehouse_checkbar_transfers SET status='pending'")
    else:conn.execute("UPDATE warehouse_checkbar_transfers SET result_json='{}'")
    with pytest.raises(WarehouseAssistantError,match='هم‌زمان'):
        reflection.apply(conn,captured,evidence,1)
    assert conn.execute('SELECT COUNT(*) FROM warehouse_receipt_stock_state').fetchone()[0]==0


def test_capture_excludes_legacy_and_includes_without_prior_state(case):
    conn,_=case
    assert len(reflection.capture(conn))==1
    conn.execute("UPDATE warehouse_checkbar_transfers SET payload_json='{}'")
    assert reflection.capture(conn)==[]
    cursor=Cursor({})
    assert reflection.source_queries(cursor,[])=={} and not cursor.calls


def test_source_failure_aborts_preserving_previous_state(case):
    conn,s=case
    assert import_state(case)[0]=='waiting'
    s['items']=RuntimeError('SELECT denied')
    with pytest.raises(WarehouseAssistantError,match='خواندن وضعیت'):
        reflection.source_queries(Cursor(s),reflection.capture(conn))
    assert conn.execute('SELECT status FROM warehouse_receipt_stock_state').fetchone()[0]=='waiting'


def test_incomplete_evidence_cannot_publish(case):
    conn,_=case
    with pytest.raises(WarehouseAssistantError,match='کامل نیست'):
        reflection.apply(conn,reflection.capture(conn),{},1)


def test_different_snapshot_year_requires_review(case):
    conn,s=case;s['headers'][0].update(ConfirmDate=datetime(2026,9,7),ConfirmedBy=2)
    conn.execute("UPDATE warehouse_snapshots SET period_end='1406/01/10'")
    assert import_state(case)[0]=='review'


def test_excel_snapshot_cannot_assert_reflection(case):
    conn,s=case;captured=reflection.capture(conn);evidence=reflection.source_queries(Cursor(s),captured)
    conn.execute("UPDATE warehouse_snapshots SET source_kind='excel'")
    with pytest.raises(WarehouseAssistantError,match='زنده'):
        reflection.apply(conn,captured,evidence,1)
