"""Price routing and fixed identities for one atomic receipt/reservation bundle."""
import json
from uuid import UUID


def price_fields(line, number, text, label):
    current, effective = [], []
    for field, title in [('consumer_price','قیمت مصرف‌کننده'),('manufacturer_price','قیمت تولیدکننده')]:
        # Unknown data is not evidence that a product is intrinsically unpriced.
        old = number(line.get(field), label+' '+title+' فعلی')
        value = line.get(field+'_new')
        current.append(old)
        effective.append(old if value is None else number(value,label+' '+title+' جدید'))
    mode = 'unpriced' if all(p == 0 for p in current+effective) else (
        'changed' if current != effective else 'unchanged')
    return dict(price_mode=mode,consumer_price_current=text(current[0]),manufacturer_price_current=text(current[1]),
                consumer_price_effective=text(effective[0]),manufacturer_price_effective=text(effective[1]),
                item_comment='-'.join(map(text,effective)))


def expected_roles(payload):
    modes={line['price_mode'] for line in payload['lines']}
    return ({'confirmed_receipt'} if modes-{'unpriced'} else set()) | (
        {'unpriced_receipt'} if 'unpriced' in modes else set()) | ({'price_reserve'} if 'changed' in modes else set())


def documents(result):
    value=result.get('DocumentsJson')
    rows=json.loads(value) if isinstance(value,str) else value
    if not isinstance(rows,list) or not rows:
        raise ValueError('Missing bundle documents')
    return rows


def validate_result(payload, result, commit):
    if result.get('PriceWorkflowVersion') != 2:
        raise ValueError('Receipt price workflow is not installed')
    if result.get('BridgeStatus') != 'sent':
        return
    rows=documents(result)
    if not commit or {r['Role'] for r in rows} != expected_roles(payload) or len(rows)!=len(expected_roles(payload)):
        raise ValueError('Incomplete receipt bundle')
    if len({r['VocherId'] for r in rows}) != len(rows) or len({str(UUID(r['UniqueId'])) for r in rows})!=len(rows):
        raise ValueError('Duplicate document identity')
    for row in rows:
        confirmed=row['Role']!='unpriced_receipt'
        if (int(row['VocherId'])<=0 or int(row['VocherNo'])<=0 or int(row['StockDCRef'])!=payload['stock_dc_ref']
                or row['Confirmed'] != confirmed or row['VocherTypeCode'] != (76 if row['Role']=='price_reserve' else 20)):
            raise ValueError('Unexpected receipt bundle document')
    primary=next(r for r in rows if r['Role']==('confirmed_receipt' if 'confirmed_receipt' in expected_roles(payload) else 'unpriced_receipt'))
    if any(result.get(k)!=primary[k] for k in ('VocherId','VocherNo','Confirmed')):
        raise ValueError('Primary receipt identity mismatch')


def component_payload(payload, component):
    role=component['Role']
    lines=[l for l in payload['lines'] if (l['price_mode']=='changed' if role=='price_reserve'
          else l['price_mode']=='unpriced' if role=='unpriced_receipt' else l['price_mode']!='unpriced')]
    return dict(payload,lines=lines,comment='بابت تغییر قیمت' if role=='price_reserve' else payload['comment'])
