import pytest
from app import warehouse_checkbar as cb
from app import warehouse_assistant_service as service
from test_warehouse_checkbar import case, active_scope, payload, partial


@pytest.mark.parametrize('update',[
    'UPDATE warehouse_snapshot_items SET stock=stock+100, reserved=reserved+20',
    "UPDATE warehouse_snapshots SET imported_at='2099-01-01T00:00:00'",
])
def test_live_inventory_refresh_does_not_invalidate_open_form(case,update):
    case.send();before=cb.prepare(case.settings,'karaj','supplier',[1])
    body=payload(before);body['lines'][0]['cartons']=2;body['lines'][0]['units']=3
    case.change(update)
    after=cb.prepare(case.settings,'karaj','supplier',[1])
    assert before['expected_token']==after['expected_token']
    saved=cb.issue(case.settings,'tester',body)
    assert saved['lines'][0]['actual_qty']==27


def test_new_snapshot_with_same_product_definitions_keeps_token(case):
    case.send();before=cb.prepare(case.settings,'karaj','supplier',[])
    with service.warehouse_connection(case.settings) as conn:
        def clone(table, overrides):
            cols=[r['name'] for r in conn.execute(f'PRAGMA table_info({table})') if r['name']!='id']
            conn.execute(f'INSERT INTO {table} ({",".join(cols)}) SELECT '+
                         ','.join(overrides.get(k,k) for k in cols)+f' FROM {table} WHERE '+
                         ('id=1' if table=='warehouse_snapshots' else 'snapshot_id=1'))
        clone('warehouse_snapshots',{'content_sha256':"'new-stock-only-snapshot'"})
        clone('warehouse_snapshot_items',{'snapshot_id':'(SELECT max(id) FROM warehouse_snapshots)','stock':'stock+10'})
    assert cb.prepare(case.settings,'karaj','supplier',[])['expected_token']==before['expected_token']


@pytest.mark.parametrize('column', ['conversion_rate','consumer_price','manufacturer_price'])
def test_changes_that_affect_count_or_price_comparison_still_require_review(case,column):
    before=cb.prepare(case.settings,'karaj','supplier',[])
    case.change(f'UPDATE warehouse_snapshot_items SET {column}={column}+1')
    body=payload(before);body['order_ids']=[];body['lines'][0]['preorder_id']=None
    with pytest.raises(service.WarehouseAssistantError,match='تغییر'):
        cb.issue(case.settings,'tester',body)
