"""Offline address-first discovery, including non-fuel merchant names.

Shared address and shortened names produce leads only. Never alter map data.
"""
import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from pathlib import Path
from nationwide import name_key, region, row_id
from refresh_regions import ORDER

OUT = Path(__file__).resolve().parents[1] / 'output'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def address_key(address):
    # Old files put spaces inside road names. Never read "19길" as no. 19.
    text = re.sub(r'(?<=[로길])\s+(?=\d+(?:번)?길)', '', address or '')
    road = re.search(r'([가-힣0-9·.]+(?:대로|로|길))\s+(\d+(?:-\d+)?)(?=$|[\s,(])', text)
    if not road:
        return None
    districts = tuple(t for t in text[:road.start()].split()[1:] if re.fullmatch(r'[가-힣]+[시군구]',t))
    return (region(text), districts, road.group(1), road.group(2))


def main():
    fuel_source = read(OUT/'alternatives/vehicle_fuel_index_20261026.json')
    fuels = fuel_source['rows']
    by_address, by_alias = defaultdict(list), defaultdict(list)
    for fuel in fuels:
        key = address_key(fuel['도로명주소'])
        if key:
            by_address[key].append(fuel)
        raw = re.sub(r'주식회사|유한회사|\(주\)|\(유\)|㈜', ' ', fuel['상호명'])
        stripped = re.sub(r'주유소|충전소|직영|셀프|[Ll][Pp][Gg]|에스케이|[Ss][Kk]|[Gg][Ss]|[Ss][ -]?[Oo][Ii][Ll]', ' ', raw)
        aliases = {name_key(stripped), *[name_key(t) for t in re.split(r'[\s()]+', stripped)]}
        for alias in aliases:
            if len(alias) >= 2 and alias != name_key(fuel['상호명']):
                by_alias[(fuel['region'],alias)].append(fuel)
    mapped = {address_key(r['address']) for r in read(OUT/'gas_stations.json')}
    annual = read(OUT/'onnuri_official_snapshot.json')
    selected_ids = {row_id(r) for r in annual['rows']}
    # Reuse complete tiles; no additional requests to blocked services.
    cache = OUT/'grid_cache/jeonnam_20261025'
    live = {}
    for path in cache.glob('*.json'):
        data = read(path)
        if data.get('query', {}).get('status') != 'complete':
            continue
        for row in data.get('rows', []):
            live[row['frCd']] = row
    cached_regional = sum(region(r['frcsAddr']) == '전남' for r in live.values())
    for row in read(OUT/'onnuri_live_snapshot.json')['rows']:
        live.setdefault(row['frCd'],row)
    live_matches = []
    for row in live.values():
        key = address_key(row['frcsAddr'])
        if key in by_address:
            live_matches.append({'merchant':row,'commercial_matches':by_address[key],
                'already_mapped_address':key in mapped,
                'status':'same_address_requires_same_business_and_fuel_type_verification'})
    historic_source = read(OUT/'alternatives/paper_merchants_source.json')
    raw = (OUT/'alternatives/paper_merchants_20210928.csv').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == historic_source['sha256']
    text = raw.decode('utf-8-sig')
    historical_matches = []
    count = 0
    for row in csv.DictReader(io.StringIO(text)):
        count += 1
        key = address_key(row['주소'])
        if key in by_address:
            historical_matches.append({'merchant':row,'commercial_matches':by_address[key],
                'already_mapped_address':key in mapped,
                'status':'historical_same_address_not_current_membership'})
    assert count == historic_source['total_rows']
    annual_raw = (OUT/'onnuri_official.csv').read_bytes()
    assert hashlib.sha256(annual_raw).hexdigest() == annual['sha256']
    alias_matches = []
    for row in csv.DictReader(io.StringIO(annual_raw.decode('utf-8-sig'))):
        if row_id(row) in selected_ids:
            continue
        areas = ['전남','광주'] if row['소재지']=='전남광주' else [region(row['소재지'])]
        matches = {f['상가업소번호']:f for area in areas for f in by_alias.get((area,name_key(row['가맹점명'])),[])}
        if matches:
            alias_matches.append({'annual_row':row,'commercial_matches':list(matches.values()),
                'status':'short_name_only_not_identity_or_membership'})
    def order(row):
        return min(ORDER.index(f['region']) for f in row['commercial_matches'])
    for rows in (live_matches,historical_matches,alias_matches):
        rows.sort(key=order)
    result = {'scope':'candidate_discovery_only_no_map_promotion', 'live_requests':0,
        'commercial_source':{k:v for k,v in fuel_source.items() if k!='rows'},
        'cached_jeonnam_merchants':cached_regional,'live_address_matches':live_matches,
        'historical_address_matches':historical_matches,'new_short_name_matches':alias_matches,
        'summary':{'vehicle_records':len(fuels),
            'live_same_address':len(live_matches),
            'live_unmapped_address':sum(not r['already_mapped_address'] for r in live_matches),
            'historical_same_address':len(historical_matches),
            'historical_unmapped_address':sum(not r['already_mapped_address'] for r in historical_matches),
            'short_name_candidates':len(alias_matches)}}
    dest = OUT/'alternatives/address_discovery_20261026.json'
    with dest.open('x',encoding='utf-8') as file:
        json.dump(result,file,ensure_ascii=False,indent=2)
    print(json.dumps(result['summary'],ensure_ascii=False))


if __name__ == '__main__':
    main()
