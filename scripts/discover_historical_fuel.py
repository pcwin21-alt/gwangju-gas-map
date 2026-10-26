"""Find fuel leads across the entire old paper-merchant file, not pending IDs."""
import csv
import hashlib
import io
import json
import re
from pathlib import Path
from nationwide import name_key, region
from refresh_regions import ORDER
from discover_address_candidates import address_key

OUT = Path(__file__).resolve().parents[1] / 'output'


def main():
    source = json.loads((OUT/'alternatives/paper_merchants_source.json').read_text(encoding='utf-8'))
    raw = (OUT/'alternatives/paper_merchants_20210928.csv').read_bytes()
    if hashlib.sha256(raw).hexdigest() != source['sha256']:
        raise ValueError('Historical source changed')
    historical = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    if len(historical) != source['total_rows']:
        raise ValueError('Incomplete historical file')
    fuels = json.loads((OUT/'alternatives/vehicle_fuel_index_20261026.json').read_text(encoding='utf-8'))['rows']
    selected = []
    for row in historical:
        if not re.search('주유소|충전소',row['점포명']) or re.search('호프|비타민|카드충전|가판',row['점포명']):
            continue
        area = region(row['주소'])
        matches = [r for r in fuels if r['region']==area and name_key(r['상호명'])==name_key(row['점포명'])]
        key = address_key(row['주소'])
        selected.append({'historical_merchant':row,'region':area,
            'same_name_commercial_candidates':matches,
            'same_road_address_candidates':[r for r in matches if key and address_key(r['도로명주소'])==key],
            'status':'historical_lead_requires_current_identity_and_membership_check'})
    selected.sort(key=lambda r: ORDER.index(r['region']) if r['region'] in ORDER else len(ORDER))
    result = {'scope':'historical_discovery_not_current_membership', 'live_requests':0,
        'source':source, 'count':len(selected), 'rows':selected,
        'priority_jeonnam':[{'name':'동부주유소','market':'해제면5일시장',
            'address':'전남 무안군 해제면 현해로 1441',
            'evidence':'2021 paper merchant address exactly matches 2026 commercial address',
            'next_check':'Current official merchant entry, address and payment type'},
            {'name':'해제주유소','market':'해제면5일시장',
            'historical_lot':'전남 무안군 해제면 신정리 21-2',
            'commercial_address':'전남 무안군 해제면 현해로 1699',
            'commercial_lot':'전남 무안군 해제면 신정리 22-3',
            'evidence':'Same name and village; lot mismatch is unresolved',
            'next_check':'Resolve historical/current premise identity before membership check'}]}
    with (OUT/'alternatives/historical_fuel_discovery_20261026.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'historical_candidates':len(selected), 'jeonnam':[r['historical_merchant'] for r in selected if r['region']=='전남']},ensure_ascii=False))


if __name__ == '__main__':
    main()
