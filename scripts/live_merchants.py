"""Classify public search results and reconcile evidence without name-only joins."""
import re
from collections import Counter

try:
    from nationwide import name_key, non_vehicle, region, row_id, valid_coords
except ModuleNotFoundError:
    from scripts.nationwide import name_key, non_vehicle, region, row_id, valid_coords


def identity(row):
    return name_key(row.get('frcsNm')), name_key(row.get('mrktNm'))


def address_key(address):
    parts = (address or '').split()
    road = re.search(r'([가-힣0-9]+(?:대로|로|길))\s*[, ]?\s*(\d+(?:-\d+)?)', address or '')
    return (region(address), parts[1] if len(parts) > 1 else '', ''.join(road.groups())) if road else None


def classify(row, annual_rows, known_fuel_addresses):
    name, category = row['frcsNm'], row.get('placeTypeNm', '')
    items = ' '.join(r.get('취급품목', '') for r in annual_rows)
    if category and category not in ('기타소매업', '근린상권서비스'):
        return 'excluded_non_vehicle_fuel', '공식 업종: ' + category, None
    if any(non_vehicle(r) for r in annual_rows) or re.search(
            r'기사식당|^CU|^GS25|^Gs25|세븐일레븐|쎄븐일레븐|이마트24|약국|다이어트|댄스|주류|알콜|카페|커피|가스케트|보일러|가스기구|가스설비|가스엔지니어링', name):
        return 'excluded_non_vehicle_fuel', '연료 외 상품 또는 업종', None
    vehicle = bool(re.search(r'주유소|충전소|오일뱅크', name) or
                   re.search(r'휘발유|무연|차량용.*(?:기름|가스|엘피지|충전)|^주유소|^주유$|^충전소|가스충전소', items) or
                   address_key(row['frcsAddr']) in known_fuel_addresses)
    if not vehicle:
        # Heating-oil delivery, gas cylinders and energy companies are not
        # automatically places where a motorist can fill a vehicle.
        candidate = bool(re.search(r'석유|에너지|엘피지|lpg|가스|오일', name, re.I))
        return ('needs_review' if candidate else 'excluded_non_vehicle_fuel',
                '자동차 주유·충전 업종 확인 필요' if candidate else '자동차 연료 상호·품목 근거 없음', None)
    if not valid_coords(row.get('latitude'), row.get('longitude')) or not address_key(row['frcsAddr']):
        return 'needs_review', '공식 상세주소·좌표 확인 필요', None
    if not any(row.get(k) == 'Y' for k in ('paperYn', 'cardYn', 'qrYn')):
        return 'needs_review', '사용 가능한 결제수단 미확인', None
    registry_lpg = isinstance(known_fuel_addresses, dict) and known_fuel_addresses.get(address_key(row['frcsAddr'])) == 'lpg'
    kind = 'lpg' if registry_lpg or re.search(r'충전소|엘피지|lpg|차량용.*가스', name + ' ' + items, re.I) else 'liquid'
    return 'located', '공식 검색의 가맹점 ID·주소·좌표·결제수단 확인', kind


def prepare(snapshot, annual, historical, sangsaeng, locations=()):
    if snapshot.get('status') != 'complete' or not snapshot.get('queries') or any(
            q['status'] != 'complete' or q['expected'] != q['received'] for q in snapshot['queries']):
        raise ValueError('Incomplete live snapshot')
    index = {}
    for row in annual['rows']:
        index.setdefault((name_key(row['가맹점명']), name_key(row['소속 시장명(또는 상점가)'])), []).append(row)
    known_addresses = {address_key(r['storeAddr']): 'lpg' if '가스' in r.get('storeCtgy', '') else 'liquid' for r in sangsaeng}
    known_addresses.update({address_key(r.get('LCTN_ROAD_NM')): r.get('_fuel_kind', 'liquid') for r in locations})
    known_addresses.pop(None, None)
    selected, review = [], []
    seen_ids, seen_keys = set(), set()
    for row in snapshot['rows']:
        seen_ids.add(row['frCd'])
        seen_keys.add((identity(row), address_key(row['frcsAddr'])))
        annual_rows = index.get(identity(row), [])
        # A name/market can recur in another province. Never transfer its items.
        annual_rows = [r for r in annual_rows if region(row['frcsAddr']) in
                       (['광주', '전남'] if r['소재지'] == '전남광주' else [region(r['소재지'])])]
        decision, reason, kind = classify(row, annual_rows, known_addresses)
        candidate_ids = [row_id(r) for r in annual_rows]
        evidence = {'source_id': row['frCd'], 'name': row['frcsNm'], 'market': row['mrktNm'],
                    'region': region(row['frcsAddr']), 'address': row['frcsAddr'],
                    'status': decision, 'reason': reason, 'candidate_id': 'live-' + row['frCd'],
                    'annual_candidate_ids': candidate_ids}
        if decision != 'located':
            # Keep an audit decision, without flooding the user with unrelated
            # shops returned by a broad substring search such as "가스".
            evidence['show_pending'] = bool(annual_rows) and decision == 'needs_review'
            review.append(evidence)
            continue
        item = dict(row)
        item['_fuel_kind'] = kind
        item['_verification'] = {'status': 'confirmed', 'checked_at': snapshot['checked_at'],
            'source_date': snapshot['checked_at'][:10], 'source_url': snapshot['source_url'],
            'source_id': row['frCd'], 'source_ids': [row['frCd']],
            'match_basis': 'official_place_id_address_coordinates', 'market': row['mrktNm'],
            'candidate_ids': candidate_ids}
        selected.append(item)
    # Preserve genuine older fuel records not returned today, with their old
    # date and no newly inferred payment/coordinate state. Never treat absence
    # in keyword searches as proof of cancellation.
    for row in historical:
        if row['frCd'] in seen_ids or (identity(row), address_key(row.get('frcsAddr'))) in seen_keys:
            continue
        annual_rows = index.get(identity(row), [])
        decision, _, kind = classify(row, annual_rows, known_addresses)
        if decision == 'located':
            item = {k: v for k, v in row.items() if not k.startswith('_')}
            item['_fuel_kind'] = kind
            if row.get('_verification'):
                item['_verification'] = {**row['_verification'], 'status': 'stale'}
            selected.append(item)
        else:
            review.append({'name': row['frcsNm'], 'status': 'needs_review', 'reason': '과거 연료 기록 재검토',
                           'source_id': row['frCd'], 'show_pending': False})
    ledger = []
    for number, row in enumerate(annual['rows'], 1):
        cid = row_id(row)
        matches = [r for r in selected if r.get('_verification', {}).get('status') == 'confirmed' and cid in r['_verification'].get('candidate_ids', [])]
        decisions = [r for r in review if cid in r.get('annual_candidate_ids', [])]
        if matches:
            status, reason = 'located', '현행 공식 검색으로 주소·결제수단 확인'
        elif decisions:
            status, reason = decisions[0]['status'], decisions[0]['reason']
        elif non_vehicle(row):
            status, reason = 'excluded_non_vehicle_fuel', '자동차 연료 업종 아님'
        else:
            status, reason = 'needs_review', '연간 자료에 있으나 현행 검색에서 상호·상점가 미대조'
            review.append({'candidate_id': cid, 'name': row['가맹점명'], 'market': row['소속 시장명(또는 상점가)'],
                           'region': row['소재지'], 'status': status, 'reason': reason, 'show_pending': True})
        ledger.append({'row_number': number, 'candidate_id': cid, 'name': row['가맹점명'],
                       'market': row['소속 시장명(또는 상점가)'], 'region': row['소재지'],
                       'status': status, 'reason': reason})
    compact = {k: v for k, v in snapshot.items() if k != 'rows'}
    compact.update(raw_result_count=len(snapshot['rows']), rows=[r for r in selected if r.get('_verification', {}).get('status') == 'confirmed'],
                   decisions=dict(Counter(r['status'] for r in review)))
    return selected, review, ledger, compact
