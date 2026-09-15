import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_warehouse_supplier_portal import store
from app import warehouse_supplier_portal as portal, warehouse_assistant_service as service
from app import warehouse_portal_access as access
from app.warehouse_portal_publication import mark_viewed
from app.routes.warehouse_supplier_portal import public_router


@pytest.fixture
def shared(store):
    names=['تأمین‌کننده نمونه','شرکت دوم','شرکت سوم']
    with service.warehouse_connection(store) as conn:
        base=dict(conn.execute('SELECT * FROM supplier_orders WHERE id=1').fetchone())
        lines=[dict(r) for r in conn.execute('SELECT * FROM supplier_order_lines WHERE order_id=1')]
        for i,name,warehouse in [(2,names[1],'karaj'),(3,names[2],'karaj'),(4,names[1],'tehran'),(5,'شرکت بیرونی','karaj')]:
            row=dict(base,id=i,order_number=f'SUP-{i}',supplier=name,warehouse_code=warehouse,warehouse_name=warehouse)
            conn.execute('INSERT INTO supplier_orders('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
            for line in lines:
                data={k:v for k,v in line.items() if k!='id'};data['order_id']=i
                conn.execute('INSERT INTO supplier_order_lines('+','.join(data)+') VALUES('+','.join('?' for _ in data)+')',tuple(data.values()))
        # Warehouse catalog comes from inventory.
        snap=dict(conn.execute('SELECT * FROM warehouse_snapshot_items LIMIT 1').fetchone())
        snap.pop('id',None);snap.update(warehouse_code='tehran',warehouse_name='تهران',source_row=99)
        conn.execute('INSERT INTO warehouse_snapshot_items('+','.join(snap)+') VALUES('+','.join('?' for _ in snap)+')',tuple(snap.values()))
    manager=portal.create_account(store,'staff',username='09120000000',password='1',supplier_name=names[0],mobile='09120000000')
    group=access.create_cartable(store,'staff','گروه مشترک',names,manager['id'])
    worker=portal.create_account(store,'staff',username='09121111111',password='1',supplier_name=names[1],mobile='09121111111')
    access.set_account_access(store,'staff',worker['id'],group['id'],False,
        [{'supplier_name':names[1],'warehouse_code':'karaj'},{'supplier_name':names[2],'warehouse_code':'tehran'}],0)
    orders=[portal.create_assignment(store,'staff',document_kind='supplier_order',document_id=i,requested_delivery_date='1405/06/22') for i in range(1,6)]
    return store,group,manager,worker,orders


def test_group_manager_and_pair_scopes(shared):
    store,group,manager,worker,orders=shared
    assert {o['document_id'] for o in portal.list_assignments(store,account_id=manager['id'])}=={1,2,3,4}
    assert {o['document_id'] for o in portal.list_assignments(store,account_id=worker['id'])}=={2}
    for i in [0,2,3,4]:
        with pytest.raises(service.WarehouseAssistantError):
            portal.get_assignment(store,orders[i]['id'],account_id=worker['id'])
        with pytest.raises(service.WarehouseAssistantError):
            mark_viewed(store,orders[i]['id'],account_id=worker['id'])


def test_http_all_order_surfaces_enforce_account_scope(shared):
    store,group,manager,worker,orders=shared
    app=FastAPI();app.state.settings=store;app.include_router(public_router)
    with TestClient(app) as client:
        assert client.post('/supplier-portal/api/login',json={'username':worker['username'],'password':'1'}).status_code==200
        assert len(client.get('/supplier-portal/api/orders').json()['orders'])==1
        denied=orders[3]['id']
        for path in [f'/orders/{denied}',f'/orders/{denied}/document.xlsx']:
            assert client.get('/supplier-portal/api'+path).status_code==409
        assert client.post(f'/supplier-portal/api/orders/{denied}/comments',json={'body':'no'}).status_code==409
        payload={'expected_revision':0,'proposed_delivery_date':'1405/06/22','submit':True,
                 'lines':[{'product_code':'00123','proposed_cartons':2,'line_status':'confirmed'},{'product_code':'00456','proposed_cartons':1,'line_status':'confirmed'}]}
        assert client.put(f'/supplier-portal/api/orders/{denied}/response',json=payload).status_code==409
        allowed=orders[1]['id']
        assert client.get(f'/supplier-portal/api/orders/{allowed}').status_code==200
        # Scope revocation applies immediately to an existing session.
        access.set_account_access(store,'staff',worker['id'],group['id'],False,[],1)
        assert client.get('/supplier-portal/api/orders').json()['orders']==[]
        assert client.get(f'/supplier-portal/api/orders/{allowed}').status_code==409
        assert client.put(f'/supplier-portal/api/orders/{allowed}/response',json=payload).status_code==409


def test_shared_manager_can_publish_other_supplier_without_account_collision(shared):
    store,group,manager,worker,orders=shared
    second=portal.create_assignment(store,'staff',document_kind='supplier_order',document_id=2,
        requested_delivery_date='1405/06/22',publish=True,portal_username=manager['username'])
    assert second['portal_account']['username']==manager['username']
    assert second['publication_state']=='published'
    profile=portal.authenticate(store,worker['username'],'1')[1]
    reply=portal.save_response(store,profile,second['id'],expected_revision=second['revision'],
        proposed_delivery_date='1405/06/22',supplier_comment='',submit=True,
        lines=[{'product_code':'00123','proposed_cartons':2},{'product_code':'00456','proposed_cartons':1}])
    assert reply['status']=='accepted'


def test_scopes_reject_stale_invalid_and_group_overlap(shared):
    store,group,manager,worker,orders=shared
    for scopes,revision in [([],0),([{'supplier_name':'شرکت بیرونی','warehouse_code':'karaj'}],1),
                            ([{'supplier_name':'شرکت دوم','warehouse_code':'not-a-warehouse'}],1)]:
        with pytest.raises(service.WarehouseAssistantError):
            access.set_account_access(store,'staff',worker['id'],group['id'],False,scopes,revision)
    with pytest.raises(service.WarehouseAssistantError):
        access.create_cartable(store,'staff','duplicate',['تأمین‌کننده نمونه'],manager['id'])
    assert len(portal.list_assignments(store,account_id=worker['id']))==1


def test_new_group_account_starts_closed_and_default_login_is_manager(shared):
    store,group,manager,worker,orders=shared
    new=portal.create_account(store,'staff',username='09122222222',password='1',supplier_name='شرکت دوم',mobile='09122222222')
    assert portal.list_assignments(store,account_id=new['id'])==[]
    with service.warehouse_connection(store) as conn:
        assert access.default_login(conn,portal._supplier_key('شرکت دوم'),'tehran')==manager['username']
    # The manager can respond to a supplier different from the account's original supplier.
    profile=portal.authenticate(store,manager['username'],'1')[1]
    order=orders[2]
    answer=portal.save_response(store,profile,order['id'],expected_revision=order['revision'],
        proposed_delivery_date='1405/06/22',supplier_comment='',submit=True,
        lines=[{'product_code':'00123','proposed_cartons':2},{'product_code':'00456','proposed_cartons':1}])
    assert answer['status']=='accepted'
