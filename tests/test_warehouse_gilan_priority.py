"""Gilan has no upper coverage limit; central warehouses retain thirty days."""
import pytest
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_balance_proposals import add_gilan, preview, accept
from app import warehouse_assistant_service as service
from app import warehouse_rebalancing as ledger


@pytest.fixture
def regional(balance):
    add_gilan(balance)
    balance.change("UPDATE warehouse_snapshot_items SET stock=60 WHERE warehouse_code='karaj'")
    balance.change("UPDATE warehouse_snapshot_items SET stock=180 WHERE warehouse_code='tehran'")
    return balance


def test_gilan_can_exceed_30_but_other_warehouses_retain_30(regional):
    data=preview(regional,'tehran','gilan');row=data['lines'][0]
    assert row['minimum_cartons']==4  # 48 units cover 24 days; 36 cover only 18.
    assert row['available_cartons']==8
    assert row['source_after_days']==42 and row['destination_after_days']==48
    assert row['other_central_days']==30
    accept(regional,data)
    regional.transport.assert_not_called()


@pytest.mark.parametrize('gilan_stock',[40,41,60])
def test_gilan_already_at_20_is_not_offered(regional,gilan_stock):
    regional.change(f"UPDATE warehouse_snapshot_items SET stock={gilan_stock} WHERE warehouse_code='gilan'")
    assert not preview(regional,'tehran','gilan')['lines']


def test_gilan_at_19_is_eligible(regional):
    regional.change("UPDATE warehouse_snapshot_items SET stock=38 WHERE warehouse_code='gilan'")
    assert preview(regional,'tehran','gilan')['lines'][0]['minimum_cartons']==1


@pytest.mark.parametrize('peer_stock',[0,59])
def test_other_central_warehouse_must_already_cover_30(regional,peer_stock):
    regional.change(f"UPDATE warehouse_snapshot_items SET stock={peer_stock} WHERE warehouse_code='karaj'")
    assert not preview(regional,'tehran','gilan')['lines']


def test_insufficient_surplus_for_gilan_minimum_does_not_offer(regional):
    regional.change("UPDATE warehouse_snapshot_items SET stock=100 WHERE warehouse_code='tehran'")
    assert not preview(regional,'tehran','gilan')['lines']  # retaining 60 leaves <40 for Gilan


def test_exact_twenty_and_thirty_and_below_minimum_rejected(regional):
    regional.change('UPDATE warehouse_snapshot_items SET conversion_rate=10')
    regional.change("UPDATE warehouse_snapshot_items SET stock=100 WHERE warehouse_code='tehran'")
    data=preview(regional,'tehran','gilan');row=data['lines'][0]
    assert row['minimum_cartons']==row['available_cartons']==4
    assert row['source_after_days']==30 and row['destination_after_days']==20
    with pytest.raises(service.WarehouseAssistantError):accept(regional,data,3)
    assert not ledger.list_requests(regional.settings,'test-user',include_all=True)
    accept(regional,data,4)


def test_third_warehouse_change_invalidates_token(regional):
    data=preview(regional,'tehran','gilan')
    regional.change("UPDATE warehouse_snapshot_items SET stock=59 WHERE warehouse_code='karaj'")
    with pytest.raises(service.WarehouseAssistantError):accept(regional,data)
    assert not ledger.list_requests(regional.settings,'test-user',include_all=True)


def test_confirm_near_route_before_gilan_using_approved_inbound(regional):
    regional.change("UPDATE warehouse_snapshot_items SET stock=240 WHERE warehouse_code='tehran'")
    regional.change("UPDATE warehouse_snapshot_items SET stock=0 WHERE warehouse_code='karaj'")
    assert not preview(regional,'tehran','gilan')['lines']
    accept(regional,preview(regional,'tehran','karaj'),key='near')
    data=preview(regional,'tehran','gilan')
    assert data['lines'][0]['other_central_days']==60
    assert data['lines'][0]['source_after_days']>=30
    accept(regional,data,key='far')


def test_two_sources_cannot_both_fill_gilan_from_stale_proposals(regional):
    regional.change("UPDATE warehouse_snapshot_items SET stock=180 WHERE warehouse_code='karaj'")
    tehran=preview(regional,'tehran','gilan');karaj=preview(regional,'karaj','gilan')
    accept(regional,tehran,4,key='first')
    with pytest.raises(service.WarehouseAssistantError):accept(regional,karaj,4,key='second')
    assert not preview(regional,'karaj','gilan')['lines']


@pytest.mark.parametrize('change',[
    "DELETE FROM warehouse_snapshot_items WHERE warehouse_code='karaj'",
    "UPDATE warehouse_snapshot_items SET period_out=0 WHERE warehouse_code='karaj'",
])
def test_unknown_peer_coverage_fails_closed(regional,change):
    regional.change(change)
    assert not preview(regional,'tehran','gilan')['lines']
