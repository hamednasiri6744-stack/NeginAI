"""Worksheet handoff → physical count → ERP, using isolated DB and fake ERP."""
import pytest
from test_warehouse_fulfillment import case
from test_warehouse_order_receipts import orders, details, prepared
from test_checkbar_confirmation import draft, edit, checked
from app import warehouse_checkbar as cb, warehouse_checkbar_print as printing
from app import warehouse_receipt_bridge as bridge
from app import warehouse_assistant_service as service


def worksheet(orders, counted=False):
    payload=draft(orders)
    payload['worksheet_workflow']=True
    if not counted:
        payload['lines'][0].update(cartons=None,units=None)
    return cb.issue(orders.settings,'buyer',payload)


def approve(orders,doc,key='approve'):
    return cb.approve_worksheet(orders.settings,'buyer',doc['id'],dict(expected_revision=doc['revision'],request_id=key))


def test_blank_save_approve_print_reopen_count_and_convert(orders):
    doc=worksheet(orders)
    assert doc['lines'][0]['order_quantity']==200
    assert doc['lines'][0]['actual_qty'] is None
    assert details(orders,1)['received_qty']==0
    with pytest.raises(service.WarehouseAssistantError,match='چاپ'):
        printing.print_document(orders.settings,doc['id'])
    approved=approve(orders,doc)
    assert approved['worksheet_approved_by']=='buyer' and approved['revision']==1
    assert approve(orders,doc)==approved
    assert details(orders,1)['received_qty']==0
    printed=printing.print_document(orders.settings,doc['id'])
    assert printed['lines'][0]['order_quantity']==200 and printed['lines'][0]['actual_qty'] is None
    assert 'تعداد سفارش' in printing.render(printed)
    assert orders.remote.calls==[]
    raw=draft(orders,120,'count-and-prices')
    raw['lines'][0].update(manufacturer_price_new=700,consumer_price_new=900)
    payload=checked(orders,raw,document_id=approved['id'],expected_revision=approved['revision'])
    counted=cb.edit_document(orders.settings,'warehouse-worker',doc['id'],dict(expected_revision=approved['revision'],
        **{k:v for k,v in payload.items() if k not in ('warehouse','supplier','order_ids','expected_token')}))
    assert counted['receipt_confirmed'] and counted['revision']==2
    assert (details(orders,1)['remaining_qty'],details(orders,2)['remaining_qty'])==(0,80)
    assert counted['lines'][0]['manufacturer_price_new']==700
    request=bridge.ReceiptRequest(expected_revision=counted['revision'],voucher_date='1405/06/15',reference_no='2222',matching_confirmed=False)
    preview=bridge.preview(orders.settings,'warehouse-worker',doc['id'],request)
    request=request.model_copy(update={'preview_token':preview['preview_token'],'validation_token':preview['result']['ValidationToken']})
    assert bridge.submit(orders.settings,'warehouse-worker',doc['id'],request)['status']=='sent'
    assert details(orders,2)['remaining_qty']==80
    history=cb.document_history(orders.settings,doc['id'])['versions']
    assert len(history)==3
    assert history[0]['document']['lines'][0]['actual_qty'] is None


def test_initial_numbers_do_not_confirm_receipt_or_allow_erp_even_after_approval(orders):
    doc=worksheet(orders,counted=True)
    for candidate in [doc,approve(orders,doc)]:
        assert not candidate.get('receipt_confirmed')
        with pytest.raises(service.WarehouseAssistantError,match='انباردار'):
            prepared(orders,candidate)
        assert details(orders,1)['received_qty']==0
    assert orders.remote.calls==[]


def test_draft_can_be_revised_blank_and_stale_approval_cannot_approve_new_revision(orders):
    doc=worksheet(orders)
    payload=dict(expected_revision=0,request_id='draft-edit',metadata={'reference_no':'2222','note':'new'},
                 lines=[dict(product_code='00123',preorder_id=None,cartons=None,units=None)])
    changed=cb.edit_document(orders.settings,'buyer',doc['id'],payload)
    assert changed['revision']==1 and changed['lines'][0]['actual_qty'] is None
    with pytest.raises(service.WarehouseAssistantError,match='تغییر'):
        approve(orders,doc)
    approved=approve(orders,changed)
    assert approved['worksheet_approved_revision']==2
    assert details(orders,1)['received_qty']==0


def test_receipt_confirmation_requires_prior_worksheet_approval(orders):
    payload=draft(orders)
    payload.update(worksheet_workflow=True)
    payload=checked(orders,payload)
    with pytest.raises(service.WarehouseAssistantError,match='ابتدا برگه'):
        cb.issue(orders.settings,'buyer',payload)
    with service.warehouse_connection(orders.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_checkbars').fetchone()[0]==0


def test_archive_tracks_saved_approved_and_counted_stages(orders):
    doc=worksheet(orders)
    row=cb.documents(orders.settings)[0]
    assert row['worksheet_workflow'] and not row['worksheet_approved_at'] and not row['receipt_confirmed']
    approved=approve(orders,doc)
    row=cb.documents(orders.settings)[0]
    assert row['worksheet_approved_at'] and not row['receipt_confirmed']
    edit(orders,approved,120)
    assert cb.documents(orders.settings)[0]['receipt_confirmed']


def count_without_matching(orders,doc,key='no-matching',**overrides):
    payload=dict(expected_revision=doc['revision'],request_id=key,metadata={'reference_no':'2222'},
                 lines=[dict(product_code='00123',cartons=0,units=120,manufacturer_price_new=700)],
                 confirm_receipt=True,skip_order_matching=True)
    payload.update(overrides)
    return cb.edit_document(orders.settings,'worker',doc['id'],payload)


def test_optional_matching_preserves_orders_through_save_retry_and_erp(orders):
    approved=approve(orders,worksheet(orders))
    doc=count_without_matching(orders,approved)
    assert doc==count_without_matching(orders,approved)
    assert doc['receipt_confirmed'] and doc['order_matching']['skipped']
    assert doc['order_matching']['allocations']==[]
    assert doc['lines'][0]['manufacturer_price_new']==700
    assert details(orders,1)['received_qty']==details(orders,2)['received_qty']==0
    request=bridge.ReceiptRequest(expected_revision=doc['revision'],voucher_date='1405/06/15',reference_no='2222')
    preview=bridge.preview(orders.settings,'worker',doc['id'],request)
    request=request.model_copy(update={'preview_token':preview['preview_token'],'validation_token':preview['result']['ValidationToken']})
    assert bridge.submit(orders.settings,'worker',doc['id'],request)['status']=='sent'
    assert details(orders,1)['received_qty']==details(orders,2)['received_qty']==0
    assert cb.document_history(orders.settings,doc['id'])['document']['order_matching']['skipped']


def test_counting_can_switch_matching_mode_before_erp(orders):
    approved=approve(orders,worksheet(orders))
    matched=edit(orders,approved,120)
    assert details(orders,1)['received_qty']==100
    unmatched=count_without_matching(orders,matched)
    assert details(orders,1)['received_qty']==details(orders,2)['received_qty']==0
    # A new request must carry a distinct id when changing the original matching choice.
    raw=checked(orders,draft(orders,60,'match-again'),document_id=unmatched['id'],expected_revision=unmatched['revision'])
    changed=cb.edit_document(orders.settings,'worker',unmatched['id'],dict(expected_revision=unmatched['revision'],
        **{k:v for k,v in raw.items() if k not in ('warehouse','supplier','order_ids','expected_token')}))
    assert not changed['order_matching'].get('skipped')
    assert details(orders,1)['received_qty']==60


def test_skip_matching_still_requires_approval_complete_counts_and_no_allocations(orders):
    doc=worksheet(orders)
    with pytest.raises(service.WarehouseAssistantError,match='ابتدا برگه'):
        count_without_matching(orders,doc)
    doc=approve(orders,doc)
    with pytest.raises(service.WarehouseAssistantError,match='خالی'):
        count_without_matching(orders,doc,lines=[dict(product_code='00123',cartons=None,units=None)])
    with pytest.raises(service.WarehouseAssistantError,match='تخصیص'):
        count_without_matching(orders,doc,allocation_revision='a'*64)
    assert details(orders,1)['received_qty']==0
