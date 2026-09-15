import json

import pytest
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_transfer_bridge import credit, request
from app import warehouse_assistant_service as service
from app import warehouse_rebalancing as ledger
from app import warehouse_transfer_bridge as bridge
from app import warehouse_transfer_documents as documents


def shortage(code='00123', requested=12, on_hand=2, reserved=20):
    return dict(ProductCode=code, RequestedQuantity=requested, OnHandQuantity=on_hand,
                ReservedQuantity=reserved, ShortageQuantity=requested-on_hand)


def rejected(*issues):
    return dict(BridgeStatus='rejected', ErrorCode=51515, Message='موجودی کافی نیست',
                StockIssuesJson=json.dumps(list(issues)))


def add_good_line(b, doc, ident):
    with service.warehouse_connection(b.settings) as c:
        row=dict(c.execute('SELECT * FROM warehouse_rebalance_requests WHERE id=?', (ident,)).fetchone())
        row.pop('id'); row.update(product_code='GOOD', product_name='کالای موجود')
        new_id=c.execute(f'INSERT INTO warehouse_rebalance_requests ({",".join(row)}) VALUES ({",".join("?" for _ in row)})', tuple(row.values())).lastrowid
        c.execute('INSERT INTO warehouse_transfer_document_lines VALUES(?,?,100,?,?)', (new_id,doc,'سازنده','برند'))
    return new_id


def test_reserved_shortage_returns_only_affected_line_to_staging(credit):
    b,doc,ident,remote=credit
    good=add_good_line(b,doc,ident)
    remote.return_value=rejected(shortage())
    result=bridge.preview(b.settings,'test-user',doc)
    assert result['status']=='stock_excluded'
    assert result['remaining_item_count']==1 and result['document_deleted'] is False
    assert result['excluded_items'][0]['product_code']=='00123'
    assert result['excluded_items'][0]['shortage_quantity']==10
    assert 'آزادسازی' in result['message']
    assert 'preview_token' not in result
    rows={r['id']:r for r in ledger.list_requests(b.settings,'test-user')}
    assert rows[ident]['issued_document_id'] is None
    assert rows[good]['issued_document_id']==doc
    with service.warehouse_connection(b.settings) as c:
        assert ledger.reservations(c,'karaj')[0]=={'00123':12,'GOOD':12}
        assert c.execute('SELECT COUNT(*) FROM warehouse_transfer_document_line_history').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM warehouse_transfer_stock_exclusions').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM warehouse_transfer_bridge_intents').fetchone()[0]==0
    assert bridge.status(b.settings,'test-user',doc)['stock_exclusions'][0]['product_code']=='00123'
    assert remote.call_count==1 and remote.call_args.args[-1] is False


def test_all_reserved_shortages_archive_empty_document_and_keep_requests(credit):
    b,doc,ident,remote=credit;remote.return_value=rejected(shortage())
    result=bridge.preview(b.settings,'test-user',doc)
    assert result['document_deleted'] and result['remaining_item_count']==0
    assert ledger.list_requests(b.settings,'test-user')[0]['issued_document_id'] is None
    with service.warehouse_connection(b.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM warehouse_transfer_document_deletions').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM warehouse_rebalance_deletions').fetchone()[0]==0
    # After official release, a fresh document may contain the unchanged request.
    new=documents.create_documents(b.settings,'test-user',[ident],request_id='after-release')['documents'][0]['id']
    remote.return_value=dict(BridgeStatus='ready',ValidationToken='fresh')
    assert bridge.preview(b.settings,'test-user',new)['payload']['lines'][0]['quantity']=='12.0'


def test_commit_stock_change_rolls_back_then_excludes_without_resubmitting(credit):
    b,doc,ident,remote=credit;req=request(credit);remote.return_value=rejected(shortage())
    result=bridge.submit(b.settings,'test-user',doc,req)
    assert result['status']=='rejected' and result['document_deleted']
    assert result['excluded_items'][0]['product_code']=='00123'
    assert remote.call_count==2  # preflight and one rejected commit; no automatic repost
    with service.warehouse_connection(b.settings) as c:
        assert c.execute('SELECT status FROM warehouse_transfer_bridge_intents').fetchone()[0]=='rejected'
        assert c.execute('SELECT COUNT(*) FROM warehouse_transfer_stock_exclusions').fetchone()[0]==1


@pytest.mark.parametrize('response',[
    rejected(shortage(reserved=0)),
    rejected(shortage(code='OUTSIDE')),
    rejected(shortage(requested=13)),
    rejected(dict(shortage(), ShortageQuantity=99)),
    rejected(dict(shortage(), ReservedQuantity=float('nan'))),
    dict(rejected(shortage()), BridgeStatus='blocked'),
    dict(BridgeStatus='rejected',ErrorCode=51515,Message='old bridge'),
])
def test_unverified_or_nonreserved_shortage_never_removes_lines(credit,response):
    b,doc,ident,remote=credit;remote.return_value=response
    with pytest.raises(service.WarehouseAssistantError):bridge.preview(b.settings,'test-user',doc)
    assert ledger.list_requests(b.settings,'test-user')[0]['issued_document_id']==doc


def test_concurrent_submission_prevents_exclusion(credit):
    b,doc,ident,remote=credit
    def competing(*args):
        with service.warehouse_connection(b.settings) as c:
            c.execute("INSERT INTO warehouse_transfer_bridge_intents VALUES(?,?,?,?,?,'pending',NULL,?)",(doc,'key','{}','test-user','now','now'))
        return rejected(shortage())
    remote.side_effect=competing
    with pytest.raises(service.WarehouseAssistantError):bridge.preview(b.settings,'test-user',doc)
    assert ledger.list_requests(b.settings,'test-user')[0]['issued_document_id']==doc


def test_stale_successful_preview_cannot_submit_after_exclusion(credit):
    b,doc,ident,remote=credit;add_good_line(b,doc,ident);req=request(credit)
    remote.return_value=rejected(shortage())
    bridge.preview(b.settings,'test-user',doc)
    with pytest.raises(service.WarehouseAssistantError):bridge.submit(b.settings,'test-user',doc,req)
    assert remote.call_count==2


def test_second_exclusion_reports_current_items_separately_from_history(credit):
    b,doc,ident,remote=credit;add_good_line(b,doc,ident)
    remote.return_value=rejected(shortage())
    bridge.preview(b.settings,'test-user',doc)
    remote.return_value=rejected(shortage(code='GOOD'))
    result=bridge.preview(b.settings,'test-user',doc)
    assert [r['product_code'] for r in result['excluded_items']]==['GOOD']
    assert len(result['stock_exclusions'])==2


def test_nonreserved_shortage_stays_in_document_when_reserved_item_removed(credit):
    b,doc,ident,remote=credit;add_good_line(b,doc,ident)
    remote.return_value=rejected(shortage(),shortage(code='GOOD',reserved=0))
    result=bridge.preview(b.settings,'test-user',doc)
    assert result['remaining_item_count']==1
    assert [r['product_code'] for r in result['excluded_items']]==['00123']
