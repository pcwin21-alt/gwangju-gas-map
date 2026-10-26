"""Refresh complete merchant snapshots; never replace a source with partial data."""
import json
import math
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
try:
    from onnuri_live import collect, SOURCE
    from live_merchants import prepare, address_key
    from market_regions import resolve_pending_regions
    from pending_evidence import annotate_pending
    from supplemental_onnuri import apply_evidence, reconcile_ledger
except ModuleNotFoundError:
    from scripts.onnuri_live import collect, SOURCE
    from scripts.live_merchants import prepare, address_key
    from scripts.market_regions import resolve_pending_regions
    from scripts.pending_evidence import annotate_pending
    from scripts.supplemental_onnuri import apply_evidence, reconcile_ledger
try:
    from official_onnuri import fetch_snapshot
except ModuleNotFoundError:
    from scripts.official_onnuri import fetch_snapshot
try:
    from nationwide import fetch_locations, fetch_lpg_locations, region, name_key, valid_coords
except ModuleNotFoundError:
    from scripts.nationwide import fetch_locations, fetch_lpg_locations, region, name_key, valid_coords

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
KST = timezone(timedelta(hours=9))

def refresh_context():
    """Identify this attempt, never carry a previous failed run's URL forward."""
    hosted = os.environ.get('GITHUB_ACTIONS') == 'true'
    repository = os.environ.get('GITHUB_REPOSITORY', '')
    run = os.environ.get('GITHUB_RUN_ID', '')
    url = (f'https://github.com/{repository}/actions/runs/{run}'
           if hosted and re.fullmatch(r'[\w.-]+/[\w.-]+', repository) and run.isdigit() else None)
    return {'refresh_environment': 'github_actions' if hosted else 'local',
            'refresh_run_url': url}

def load(name, default=None):
    path = OUT / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def save(name, value):
    path = OUT / name
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

def request(session, url, **kwargs):
    for attempt in range(3):
        try:
            r = session.post(url, timeout=25, **kwargs)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
            time.sleep(1 + attempt)

def fetch_sangsaeng(session):
    rows = []
    for query in ('주유', '가스'):
        def page(n):
            response = request(session, 'https://www.gwangju.go.kr/pg/getGjCardList.do',
                               data={'movePage': n, 'pageId': 'www788',
                                     'searchTy02': 'C', 'searchQuery': query})
            if response.get('error') != 'N' or 'dataMap' not in response:
                raise ValueError('상생카드 응답 구조 변경')
            return response['dataMap']
        first = page(1)
        expected = int(first['totalCnt'])
        collected = list(first['list'])
        for n in range(2, int(first['pageCnt']) + 1):
            time.sleep(.25)
            collected.extend(page(n)['list'])
        if expected < 1 or len(collected) != expected:
            raise ValueError('상생카드 페이지 수집 불완전')
        if len({r['sn'] for r in collected}) != expected:
            raise ValueError('상생카드 반복 페이지 감지')
        if not all(r.get('storeNm') and r.get('storeAddr') for r in collected):
            raise ValueError('상생카드 필수 필드 누락')
        rows.extend(collected)
    return list({(r['storeNm'], r['storeAddr']): r for r in rows}.values())

def road_key(address):
    # Administrative names may change. Match the road and building number only.
    match = re.search(r'([가-힣0-9]+(?:대로|로|길))\s*[, ]?\s*(\d+(?:-\d+)?)', address or '')
    return ''.join(match.groups()) if match else ''

def distance(a, b):
    if not all(a.get(k) is not None and b.get(k) is not None for k in ('lat', 'lng')):
        return float('inf')
    la, lb = math.radians(a['lat']), math.radians(b['lat'])
    dg = math.radians(b['lng'] - a['lng'])
    return 6371000 * 2 * math.asin(math.sqrt(math.sin((lb-la)/2)**2 + math.cos(la)*math.cos(lb)*math.sin(dg/2)**2))

def coords(lat, lng):
    try:
        lat, lng = float(lat), float(lng)
        if valid_coords(lat, lng):
            return lat, lng
    except (TypeError, ValueError):
        pass
    return None, None

def merge(sangsaeng, onnuri, old, checked):
    result, review = [], []
    for row in sangsaeng:
        lat, lng = coords(row.get('lot'), row.get('lalt'))
        key = road_key(row['storeAddr'])
        previous = [s for s in old if key and road_key(s.get('address')) == key and
                    (not region(row['storeAddr']) or region(s.get('address')) == region(row['storeAddr']))]
        # Only borrow a coordinate when the full road address identifies one location.
        locations = {(s.get('lat'), s.get('lng')) for s in previous if s.get('lat') and s.get('lng')}
        live_locations = {(float(s['latitude']), float(s['longitude'])) for s in onnuri
                          if s.get('_verification', {}).get('status') == 'confirmed' and
                          address_key(s.get('frcsAddr')) == address_key(row['storeAddr']) and
                          valid_coords(s.get('latitude'), s.get('longitude'))}
        if lat is None:
            if len(live_locations) == 1:
                lat, lng = next(iter(live_locations))
            elif not live_locations and len(locations) == 1:
                lat, lng = next(iter(locations))
        station = {'id': 'sangsaeng:' + str(row['sn']), 'name': row['storeNm'].strip(),
                   'address': row['storeAddr'].strip(), 'lat': lat, 'lng': lng,
                   'payment_types': ['saengsaeng'], 'source': ['gwangju'],
                   'verification': {'saengsaeng': {'checked_at': checked, 'status': 'confirmed',
                        'source_date': row.get('storeDate'), 'source_id': str(row['sn'])}},
                   'aliases': sorted({n for s in previous for n in [s['name'], *s.get('aliases', [])] if n != row['storeNm'].strip()}),
                   'fuel_kind': 'lpg' if '가스' in row.get('storeCtgy', '') else 'liquid',
                   'route_eligible': lat is not None}
        duplicates = [s for s in result if key and road_key(s['address']) == key and distance(s, station) < 40 and s['fuel_kind'] == station['fuel_kind']]
        if len(duplicates) == 1:
            target = duplicates[0]
            target['aliases'] = sorted(set(target['aliases'] + station['aliases'] + [station['name']]) - {target['name']})
            v = target['verification']['saengsaeng']
            v['source_ids'] = sorted(set(v.get('source_ids', [v['source_id']]) + [str(row['sn'])]))
        else:
            result.append(station)
    for row in onnuri:
        name = row.get('frcsNm', '').strip()
        # Avoid substring false positives such as "광주유촌점" cafes and convenience stores.
        if not row.get('_fuel_kind') and not re.search(r'주유소|충전소|석유|에너지', name):
            review.append({'reason': '업종 확인 필요', 'name': name, 'source_id': row.get('frCd')})
            continue
        lat, lng = coords(row.get('latitude'), row.get('longitude'))
        station = {'id': 'onnuri:' + row['frCd'], 'name': name,
                   'address': row.get('frcsAddr', ''), 'lat': lat, 'lng': lng,
                   'payment_types': ['onnuri'], 'source': ['onnuri_place' if row.get('_verification', {}).get('status') == 'confirmed' or not row.get('_verification') else 'onnuri_csv'], 'aliases': [],
                   'fuel_kind': row.get('_fuel_kind') or ('lpg' if '충전소' in name else 'liquid'),
                   'route_eligible': lat is not None and bool(row.get('_fuel_kind') or re.search(r'주유소|충전소', name))}
        key = road_key(station['address'])
        candidates = [s for s in result if key and road_key(s['address']) == key and distance(s, station) < 40 and s['fuel_kind'] == station['fuel_kind']]
        # Do not merge neighboring forecourts merely because their coordinates are close.
        if len(candidates) == 1:
            target = candidates[0]
            if 'onnuri' not in target['payment_types']:
                target['payment_types'].append('onnuri')
            for source in station['source']:
                if source not in target['source']:
                    target['source'].append(source)
            if name != target['name']:
                target['aliases'].append(name)
        else:
            target = station
            target['verification'] = {}
            result.append(target)
        if row.get('_location_evidence'):
            target['location_evidence'] = row['_location_evidence']
        if row.get('_fuel_evidence'):
            target['fuel_evidence'] = row['_fuel_evidence']
        target['aliases'] = sorted(set(target['aliases'] + row.get('_annual_aliases', [])) - {target['name']})
        if row.get('_verification', {}).get('status') == 'confirmed':
            target['fuel_kind'] = station['fuel_kind']
            # Prefer current official coordinates for a unique physical site.
            target['address'], target['lat'], target['lng'] = station['address'], lat, lng
            target['route_eligible'] = station['route_eligible']
        prior = target.get('onnuri_methods')
        target['onnuri_methods'] = {k: row.get(v) == 'Y' for k, v in
                                   [('paper', 'paperYn'), ('card', 'cardYn'), ('qr', 'qrYn')]}
        if row.get('_verification', {}).get('status') == 'published_snapshot':
            target['onnuri_methods']['card'] = None
            target['onnuri_methods']['qr'] = None
        target['onnuri_methods']['digital'] = (row['digitalYn'] == 'Y' if 'digitalYn' in row
            else target['onnuri_methods']['card'] or target['onnuri_methods']['qr'])
        previous = target['verification'].get('onnuri', {})
        current_verified = row.get('_verification', {}).get('status') == 'confirmed'
        if prior and previous.get('status') == 'confirmed' and not current_verified:
            # A legacy alias cannot downgrade a current place's payment evidence.
            target['onnuri_methods'] = prior
            continue
        if prior and (previous.get('status') == 'confirmed') == current_verified:
            target['onnuri_methods'] = {k: prior.get(k, False) and v for k, v in target['onnuri_methods'].items()}
        ids = previous.get('source_ids', [previous['source_id']] if previous.get('source_id') else [])
        target['verification']['onnuri'] = {'checked_at': '2026-03-03', 'status': 'stale',
                                            'source_id': row['frCd'], 'source_ids': sorted(set(ids + [row['frCd']]))}
        if row.get('_verification'):
            target['verification']['onnuri'].update(row['_verification'])
            target['verification']['onnuri']['source_ids'] = sorted(set(ids + [row['frCd']]))
    for station in result:
        station['region'] = region(station.get('address'))
        if not station['route_eligible']:
            review.append({'reason': '내비 추천 제외: 좌표 또는 자동차 주유 업종 확인 필요',
                           'name': station['name'], 'id': station['id']})
    return result, review

def script_json(value):
    # Public merchant names are data, including in an inline script element.
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def sync_map(stations, status):
    path = OUT / 'map.html'
    html = path.read_text(encoding='utf-8')
    html, count = re.subn(r'const STATIONS = \[.*?\];',
        lambda _: 'const STATIONS = ' + script_json(stations) + ';', html, flags=re.S)
    if count != 1:
        raise ValueError('지도 STATIONS 상수 없음 또는 중복')
    metadata = 'const MERCHANT_STATUS = ' + script_json(status) + ';'
    pending = [r for r in load('merchant_review.json', []) if r.get('status') == 'needs_review' and r.get('show_pending', True) and r.get('candidate_id')]
    pending = list({r['candidate_id']:r for r in pending}.values())
    pending_const = 'const NATIONAL_PENDING = ' + script_json(pending) + ';'
    if 'const NATIONAL_PENDING = ' in html:
        html = re.sub(r'const NATIONAL_PENDING = .*?;\n', lambda _: pending_const+'\n', html)
    else:
        html = html.replace('const STATIONS = ', pending_const+'\nconst STATIONS = ', 1)
    if 'const MERCHANT_STATUS = ' in html:
        html = re.sub(r'const MERCHANT_STATUS = .*?;\n', lambda _: metadata+'\n', html)
    else:
        html = html.replace('const STATIONS = ', metadata+'\nconst STATIONS = ', 1)
    path.write_text(html, encoding='utf-8')

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--live-snapshot', help='Use a complete saved search run for reproducible publication')
    args = parser.parse_args()
    checked = datetime.now(KST).isoformat(timespec='seconds')
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.gwangju.go.kr/'})
    old = load('gas_stations.json', [])
    status = load('merchant_status.json', {})
    try:
        live = fetch_sangsaeng(session)
        if len(live) < 30:
            raise ValueError('상생카드 수집 건수 급감: 수동 확인 필요')
        status['saengsaeng'] = {'status': 'confirmed', 'checked_at': checked, 'count': len(live)}
    except Exception as error:
        status['saengsaeng'] = {**status.get('saengsaeng', {}), 'status': 'error',
                               'attempted_at': checked, 'error': type(error).__name__}
        save('merchant_status.json', status)
        sync_map(old, status)
        raise
    # The live public search supplies identity/address/payment together. The
    # annual file and registry discover legal-name candidates; neither supplies
    # an unverified address by same-name/province inference.
    location_cache = load('station_locations.json', {})
    try:
        age = (datetime.now(KST) - datetime.fromisoformat(location_cache['retrieved_at'])).days if location_cache else 999
        if age >= 7 or not location_cache.get('complete_registry'):
            locations = fetch_locations(session)
            location_cache = {'retrieved_at': checked, 'complete_registry': True,
                              'source_url': 'https://www.data.go.kr/data/15129441/standard.do',
                              'total_rows': len(locations), 'rows': locations}
    except (requests.RequestException, ValueError, KeyError):
        # Current official addresses remain usable without this supplementary registry.
        pass
    lpg_cache = load('lpg_locations.json', {})
    try:
        age = (datetime.now(KST) - datetime.fromisoformat(lpg_cache['retrieved_at'])).days if lpg_cache else 999
        if age >= 7:
            lpg_cache = {'retrieved_at': checked, 'source_url': 'https://www.data.go.kr/data/15001643/fileData.do',
                         'rows': fetch_lpg_locations(session)}
    except (requests.RequestException, ValueError, KeyError):
        pass
    locations = location_cache.get('rows', []) + lpg_cache.get('rows', [])
    registry_keys = {(region(r.get('CTPV_NM')), name_key(r['CONM_NM'])) for r in locations}
    live_session = requests.Session()
    live_session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': SOURCE,
                                 'Origin': 'https://www.onnuri.gift'})
    historical_by_id = {r['frCd']: r for r in load('raw_onnuri_place.json', [])}
    previous_snapshot = load('onnuri_live_snapshot.json', {})
    for row in previous_snapshot.get('retained_history', []):
        historical_by_id[row['frCd']] = row
    previous_ids = {sid for s in old for sid in s.get('verification', {}).get('onnuri', {}).get('source_ids', [])}
    for row in previous_snapshot.get('rows', []):
        if row['frCd'] in previous_ids:
            historical_by_id[row['frCd']] = {**row, '_verification': {
                'status': 'stale', 'checked_at': row.get('_observed_at', previous_snapshot['checked_at']),
                'source_url': SOURCE, 'source_id': row['frCd'], 'market': row['mrktNm']}}
    stage = 'annual_snapshot'
    try:
        snapshot = fetch_snapshot(session, load('onnuri_official_snapshot.json'), checked, registry_keys)
        stage = 'public_search'
        places = (json.loads(Path(args.live_snapshot).read_text(encoding='utf-8')) if args.live_snapshot else
                  collect(live_session, candidates=snapshot['rows']))
        if places.get('scope') == 'nationwide_sequential_regional_search':
            try:
                from refresh_regions import validate_combined
            except ModuleNotFoundError:
                from scripts.refresh_regions import validate_combined
            validate_combined(places)
        historical, official_review, ledger, compact = prepare(
            places, snapshot, list(historical_by_id.values()), live,
            locations, load('verified_fuel_evidence.json', {}).get('rows', []))
        places['retained_history'] = [r for r in historical if r.get('_verification', {}).get('status') != 'confirmed']
        if len(compact['rows']) < 80:
            raise ValueError('온누리 검색 결과 급감: 이전 지도 유지')
    except (requests.RequestException, ValueError, KeyError, PermissionError) as error:
        status = load('merchant_status.json', {})
        previous_stations, previous_review = old, load('merchant_review.json', [])
        old, retained_review, supplemental = apply_evidence(old, previous_review,
            load('supplemental_onnuri_evidence.json', {}).get('rows', []), checked)
        status['supplemental_onnuri'] = supplemental
        if old != previous_stations:
            save('gas_stations.json', old)
        if retained_review != previous_review:
            save('merchant_review.json', retained_review)
        status['onnuri'] = {**status.get('onnuri', {}), **refresh_context(),
                            'refresh_error': type(error).__name__, 'refresh_stage': stage, 'attempted_at': checked}
        status['onnuri']['pending_count'] = len({r['candidate_id'] for r in retained_review if r.get('show_pending') and r.get('candidate_id')})
        save('merchant_status.json', status)
        sync_map(old, status)
        raise
    stations, review = merge(live, historical, old, checked)
    review.extend(official_review)
    review = resolve_pending_regions(review, load('market_region_evidence.json', {}).get('rows', []))
    review = annotate_pending(review, load('pending_identity_evidence.json', {}).get('rows', []))
    stations, review, supplemental = apply_evidence(stations, review,
        load('supplemental_onnuri_evidence.json', {}).get('rows', []), checked)
    status['supplemental_onnuri'] = supplemental
    ledger = reconcile_ledger(ledger, stations)
    status['onnuri'] = {'status': 'confirmed', 'source_date': places['checked_at'][:10],
        'checked_at': places['checked_at'], 'attempted_at': checked, 'source_url': SOURCE,
        'scope': places['scope'], 'query_count': len(places['queries']),
        'candidate_rows': len(snapshot['rows']), 'raw_search_rows': len(places['rows']),
        'matched_count': sum(s.get('verification', {}).get('onnuri', {}).get('status') == 'confirmed' and s.get('source') != ['kb_onnuri'] for s in stations),
        'unmatched_count': sum(s.get('verification', {}).get('onnuri', {}).get('status') == 'stale' for s in stations),
        'pending_count': len({r['candidate_id'] for r in review if r.get('show_pending') and r.get('candidate_id')}),
        **refresh_context(), 'refresh_error': None,
        'reason': '공식 검색 결과 확인. 검색어·품목·등록자료 기반이며 전국 모든 가맹 주유소의 완전성은 보장하지 않음'}
    if places.get('regions'):
        status['onnuri']['regions'] = [{**entry,
            'visible_count': sum(region(s['address']) == entry['region'] and valid_coords(s.get('lat'), s.get('lng')) for s in stations),
            'confirmed_count': sum(region(s['address']) == entry['region'] and s.get('verification', {}).get('onnuri', {}).get('status') == 'confirmed' for s in stations)
        } for entry in places['regions']]
    if places.get('regional_grids'):
        status['onnuri']['regional_grids'] = places['regional_grids']
    save('onnuri_official_snapshot.json', snapshot)
    save('onnuri_live_snapshot.json', places)
    save('station_locations.json', location_cache)
    save('lpg_locations.json', lpg_cache)
    save('nationwide_candidates.json', {'source_sha256': snapshot['sha256'], 'source_date': snapshot['source_date'],
                                      'candidate_rows': len(ledger), 'rows': ledger})
    # Legacy rows with only a city as address cannot establish a navigation destination.
    review.extend({'reason': '기존 상세주소 없음', 'name': s['name']} for s in old if not road_key(s.get('address')))
    save('filtered_sangsaeng.json', live)
    save('gas_stations.json', stations)
    save('merchant_status.json', status)
    save('merchant_review.json', review)
    sync_map(stations, status)
    print(f'상생카드 {len(live)}건 / 지도 {len(stations)}건 / 온누리 공식 매칭 {status["onnuri"]["matched_count"]}건 / 과거 기록 {status["onnuri"]["unmatched_count"]}건 / 검토 {len(review)}건.')

if __name__ == '__main__':
    main()
