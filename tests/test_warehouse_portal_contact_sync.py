import pytest
from test_warehouse_fulfillment import case
from test_warehouse_supplier_portal import store
from test_warehouse_portal_access import shared
from app import warehouse_assistant_service as service, warehouse_supplier_portal as portal


def test_contact_save_renames_existing_login_preserves_password_and_revokes_old_session(case):
    account=portal.create_account(case.settings,'staff',username='09120000000',password='Keep-Password123',supplier_name='supplier',mobile='09120000000')
    token,_=portal.authenticate(case.settings,'09120000000','Keep-Password123')
    case.save_contact(mobile='09121112233')
    assert portal.authenticate(case.settings,'09120000000','Keep-Password123') is None
    assert portal.session_profile(case.settings,token) is None
    _,profile=portal.authenticate(case.settings,'09121112233','Keep-Password123')
    assert profile['id']==account['id'] and profile['mobile']=='09121112233'
    assert portal.authenticate(case.settings,'09121112233','1') is None


def test_phone_conflict_rolls_back_contact_and_does_not_merge_accounts(case):
    portal.create_account(case.settings,'staff',username='09120000000',password='Keep-Password123',supplier_name='supplier',mobile='09120000000')
    portal.create_account(case.settings,'staff',username='09121112233',password='Other-Password123',supplier_name='other',mobile='09121112233')
    with pytest.raises(service.WarehouseAssistantError):case.save_contact(mobile='09121112233')
    assert case.order()['contact_mobile']==''
    assert portal.authenticate(case.settings,'09120000000','Keep-Password123')


def test_ambiguous_account_is_not_arbitrarily_renamed(case):
    for phone in ['09120000000','09120000001']:
        portal.create_account(case.settings,'staff',username=phone,password='Keep-Password123',supplier_name='supplier',mobile=phone)
    with pytest.raises(service.WarehouseAssistantError):case.save_contact(mobile='09121112233')
    assert case.order()['contact_mobile']==''


def test_old_phone_cannot_be_recreated_by_a_stale_publication_form(case):
    from app.warehouse_portal_publication import ensure_phone_account
    portal.create_account(case.settings,'staff',username='09120000000',password='Keep-Password123',supplier_name='supplier',mobile='09120000000')
    case.save_contact(mobile='09121112233')
    with service.warehouse_connection(case.settings) as conn:
        with pytest.raises(service.WarehouseAssistantError):
            ensure_phone_account(conn,'supplier','09120000000','staff',warehouse_code='karaj')


def test_scoped_representative_rename_preserves_scopes_and_group_manager(shared):
    from app import warehouse_portal_access as access
    settings,group,manager,worker,_=shared
    portal._init(settings)
    with service.warehouse_connection(settings) as conn:
        before=access.account_access(conn,worker['id'])
        conn.execute("""INSERT INTO warehouse_supplier_auto_order_settings
            (id,warehouse_code,warehouse_name,supplier,contact_mobile,created_at,updated_at)
            VALUES(90,'karaj','Karaj','شرکت دوم','09121111111','now','now')""")
        current=conn.execute('SELECT * FROM warehouse_supplier_auto_order_settings WHERE id=90').fetchone()
        access.sync_setting_phone(conn,current,'09123333333','staff')
        conn.execute("UPDATE warehouse_supplier_auto_order_settings SET contact_mobile='09123333333' WHERE id=90")
        assert access.account_access(conn,worker['id'])==before
        assert access.default_login(conn,portal._supplier_key('شرکت دوم'),'karaj')=='09123333333'
        assert conn.execute('SELECT username FROM warehouse_supplier_portal_accounts WHERE id=?',(manager['id'],)).fetchone()[0]=='09120000000'
        assert not access.can_access(conn,worker['id'],portal._supplier_key('شرکت دوم'),'tehran')
