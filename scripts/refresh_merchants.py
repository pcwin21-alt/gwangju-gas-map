"""Refresh complete merchant snapshots; never replace a source with partial data."""
import json
import math
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
KST = timezone(timedelta(hours=9))

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
        if 34.8 < lat < 35.5 and 126.5 < lng < 127.2:
            return lat, lng
    except (TypeError, ValueError):
        pass
    return None, None

def merge(sangsaeng, onnuri, old, checked):
    result, review = [], []
    for row in sangsaeng:
        lat, lng = coords(row.get('lot'), row.get('lalt'))
        key = road_key(row['storeAddr'])
        previous = [s for s in old if key and road_key(s.get('address')) == key]
        # Only borrow a coordinate when the full road address identifies one location.
        locations = {(s.get('lat'), s.get('lng')) for s in previous if s.get('lat') and s.get('lng')}
        if lat is None and len(locations) == 1:
            lat, lng = next(iter(locations))
        station = {'id': 'sangsaeng:' + str(row['sn']), 'name': row['storeNm'].strip(),
                   'address': row['storeAddr'].strip(), 'lat': lat, 'lng': lng,
                   'payment_types': ['saengsaeng'], 'source': ['gwangju'],
                   'verification': {'saengsaeng': {'checked_at': checked, 'status': 'confirmed',
                        'source_date': row.get('storeDate'), 'source_id': str(row['sn'])}},
                   'aliases': sorted({n for s in previous for n in [s['name'], *s.get('aliases', [])] if n != row['storeNm'].strip()}),
                   'fuel_kind': 'lpg' if '가스' in row.get('storeCtgy', '') else 'liquid',
                   'route_eligible': lat is not None}
        result.append(station)
    for row in onnuri:
        name = row.get('frcsNm', '').strip()
        # Avoid substring false positives such as "광주유촌점" cafes and convenience stores.
        if not re.search(r'주유소|충전소|석유|에너지', name):
            review.append({'reason': '업종 확인 필요', 'name': name, 'source_id': row.get('frCd')})
            continue
        lat, lng = coords(row.get('latitude'), row.get('longitude'))
        station = {'id': 'onnuri:' + row['frCd'], 'name': name,
                   'address': row.get('frcsAddr', ''), 'lat': lat, 'lng': lng,
                   'payment_types': ['onnuri'], 'source': ['onnuri_place'], 'aliases': [],
                   'fuel_kind': 'lpg' if '충전소' in name else 'liquid',
                   'route_eligible': lat is not None and bool(re.search(r'주유소|충전소', name))}
        key = road_key(station['address'])
        candidates = [s for s in result if key and road_key(s['address']) == key and distance(s, station) < 40]
        # Do not merge neighboring forecourts merely because their coordinates are close.
        if len(candidates) == 1:
            target = candidates[0]
            if 'onnuri' not in target['payment_types']:
                target['payment_types'].append('onnuri')
            if 'onnuri_place' not in target['source']:
                target['source'].append('onnuri_place')
            if name != target['name']:
                target['aliases'].append(name)
        else:
            target = station
            target['verification'] = {}
            result.append(target)
        prior = target.get('onnuri_methods')
        target['onnuri_methods'] = {k: row.get(v) == 'Y' for k, v in
                                   [('paper', 'paperYn'), ('card', 'cardYn'), ('qr', 'qrYn')]}
        if prior:
            target['onnuri_methods'] = {k: prior[k] and v for k, v in target['onnuri_methods'].items()}
        previous = target['verification'].get('onnuri', {})
        ids = previous.get('source_ids', [previous['source_id']] if previous.get('source_id') else [])
        target['verification']['onnuri'] = {'checked_at': '2026-03-03', 'status': 'stale',
                                            'source_id': row['frCd'], 'source_ids': sorted(set(ids + [row['frCd']]))}
    for station in result:
        if not station['route_eligible']:
            review.append({'reason': '내비 추천 제외: 좌표 또는 자동차 주유 업종 확인 필요',
                           'name': station['name'], 'id': station['id']})
    return result, review

def sync_map(stations, status):
    path = OUT / 'map.html'
    html = path.read_text(encoding='utf-8')
    html, count = re.subn(r'const STATIONS = \[.*?\];',
        lambda _: 'const STATIONS = ' + json.dumps(stations, ensure_ascii=False) + ';', html, flags=re.S)
    if count != 1:
        raise ValueError('지도 STATIONS 상수 없음 또는 중복')
    metadata = 'const MERCHANT_STATUS = ' + json.dumps(status, ensure_ascii=False) + ';'
    if 'const MERCHANT_STATUS = ' in html:
        html = re.sub(r'const MERCHANT_STATUS = .*?;\n', lambda _: metadata+'\n', html)
    else:
        html = html.replace('const STATIONS = ', metadata+'\nconst STATIONS = ', 1)
    path.write_text(html, encoding='utf-8')

def main():
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
    # Probe once: this historical endpoint currently rejects direct public calls.
    # A probe is never a full snapshot; successful responses still need full scan verification.
    try:
        response = session.post('https://onnuri.gift/api/v1/place/search', timeout=20,
            json={'keyword': '주유소', 'addrNm': '', 'placeTypeList': [], 'paperYn': '',
                  'cardYn': '', 'qrYn': '', 'latitude': '35.081858', 'longitude': '126.831485'},
            headers={'Origin': 'https://onnuri.gift', 'Referer': 'https://onnuri.gift/'})
        status['onnuri'] = {'status': 'stale', 'checked_at': '2026-03-03', 'attempted_at': checked,
                            'http_status': response.status_code,
                            'reason': '최근 전체 수집 미완료. 기존 확인 기록 유지'}
    except requests.RequestException:
        status['onnuri'] = {'status': 'stale', 'checked_at': '2026-03-03', 'attempted_at': checked,
                            'reason': '조회 연결 실패. 기존 확인 기록 유지'}
    stations, review = merge(live, load('raw_onnuri_place.json', []), old, checked)
    # Legacy rows with only a city as address cannot establish a navigation destination.
    review.extend({'reason': '기존 상세주소 없음', 'name': s['name']} for s in old if not road_key(s.get('address')))
    save('filtered_sangsaeng.json', live)
    save('gas_stations.json', stations)
    save('merchant_status.json', status)
    save('merchant_review.json', review)
    sync_map(stations, status)
    print(f'상생카드 {len(live)}건 / 지도 {len(stations)}건 / 검토 {len(review)}건. 온누리 최신 확인 미완료.')

if __name__ == '__main__':
    main()
