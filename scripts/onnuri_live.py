"""Public Onnuri place search, discovered from the site's current public client.

No login, tokens, browser state or guessed coordinates. A failed/truncated query
must never replace a complete snapshot. Radius 0 is the site's keyword-search mode.
"""
import argparse
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
try:
    from nationwide import name_key, non_vehicle
except ModuleNotFoundError:
    from scripts.nationwide import name_key, non_vehicle

BASE = 'https://www.onnuri.gift/api/v3/onrgt'
SOURCE = 'https://www.onnuri.gift/place'
KEYWORDS = ('주유', '충전', '석유', '에너지', 'LPG', '엘피지', '오일', '유류', '가스')
FIELDS = ('frCd', 'frcsNm', 'frcsAddr', 'mrktNm', 'placeTypeCd', 'placeTypeNm',
          'addrCd', 'latitude', 'longitude', 'paperYn', 'cardYn', 'qrYn')
KST = timezone(timedelta(hours=9))


def post(session, path, payload):
    for attempt in range(3):
        try:
            response = session.post(BASE + path, json=payload, timeout=(10, 45))
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
            continue
        # The public service intermittently returns 400 for an identical valid
        # request. Bound retries; never retry authentication/permission failures.
        if response.status_code not in (400, 500, 502, 503, 504) or attempt == 2:
            break
        time.sleep(2 * (attempt + 1))
    response.raise_for_status()
    body = response.json()
    if body.get('resCode') != '0000' or not isinstance(body.get('data'), dict):
        raise ValueError('Onnuri search failed: ' + str(body.get('resCode')))
    return body['data']


def search(session, keyword, area='', pause=1):
    rows, ids, pages, expected = [], set(), None, None
    page = 1
    while pages is None or page <= pages:
        payload = dict(keyword=keyword, addrNm='', addrCd=area, placeTypeList=[],
                       paperYn='', cardYn='', qrYn='', latitude='37.5667',
                       longitude='126.9784', baseRange=0, currPage=page)
        data = post(session, '/place/search', payload)
        total, last = int(data['totalCnt']), int(data['totalPage'])
        if pages is None:
            expected, pages = total, last
        if total != expected or last != pages or int(data['currPage']) != page:
            raise ValueError('Onnuri pagination changed during collection')
        if not 0 <= total <= 50000 or not 0 <= last <= 100:
            raise ValueError('Unexpected Onnuri count')
        batch = data['list']
        if not isinstance(batch, list) or (total and not batch):
            raise ValueError('Empty/malformed Onnuri page')
        for raw in batch:
            if not all(raw.get(k) for k in ('frCd', 'frcsNm', 'frcsAddr')):
                raise ValueError('Missing Onnuri identity/address')
            if raw['frCd'] in ids:
                raise ValueError('Repeated Onnuri page/merchant ID')
            if any(raw.get(k) not in ('Y', 'N') for k in ('paperYn', 'cardYn', 'qrYn')):
                raise ValueError('Unknown payment flag')
            ids.add(raw['frCd'])
            rows.append({k: raw.get(k) for k in FIELDS})
        page += 1
        time.sleep(pause)
    if len(rows) != expected:
        raise ValueError('Incomplete Onnuri result: expected %s, got %s' % (expected, len(rows)))
    return rows, {'keyword': keyword, 'area_code': area, 'status': 'complete',
                  'expected': expected, 'received': len(rows), 'pages': pages}


def expand_names(session, snapshot, candidates, progress=print):
    """Reverse search fuel-item / registry candidates whose legal name hides fuel."""
    by_id = {r['frCd']: r for r in snapshot['rows']}
    known = {(name_key(r['frcsNm']), name_key(r['mrktNm'])) for r in by_id.values()}
    searched = {q['keyword'] for q in snapshot['queries']}
    for row in candidates:
        key = (name_key(row['가맹점명']), name_key(row['소속 시장명(또는 상점가)']))
        if key in known or non_vehicle(row):
            continue
        keyword = re.sub(r'주식회사|유한회사|\(주\)|\(유\)|㈜', '', row['가맹점명']).strip()
        if keyword in searched or len(keyword) < 2:
            continue
        rows, query = search(session, keyword)
        for item in rows:
            old = by_id.get(item['frCd'])
            if old and old != item:
                raise ValueError('Merchant changed during reverse lookup')
            by_id[item['frCd']] = item
        query['strategy'] = 'annual_fuel_or_registry_name'
        snapshot['queries'].append(query)
        searched.add(keyword)
        progress(f'Reverse {keyword}: {len(rows)} records', flush=True)
    snapshot['rows'] = sorted(by_id.values(), key=lambda r: r['frCd'])
    return snapshot


def collect(session, extra_names=(), progress=print, candidates=()):
    by_id, queries = {}, []
    for keyword in dict.fromkeys((*KEYWORDS, *extra_names)):
        rows, query = search(session, keyword)
        for row in rows:
            old = by_id.get(row['frCd'])
            if old and old != row:
                raise ValueError('Merchant changed between queries: ' + row['frCd'])
            by_id[row['frCd']] = row
        queries.append(query)
        progress(f'{keyword}: {len(rows)} records', flush=True)
    # Independently check known small areas, including Gwangju's five districts.
    districts = {}
    for province in ('11000', '12000', '41000', '50000'):
        for item in post(session, '/addr/' + province, {})['list']:
            districts[(province, item['addrNm'])] = item['addrCd']
    pilots = [('11000', '양천구'), ('41000', '가평군'), ('50000', '제주시')]
    pilots += [('12000', name) for name in ('동구', '서구', '남구', '북구', '광산구')]
    for province, district in pilots:
        code = districts[(province, district)]
        for keyword in ('주유소', '충전소'):
            rows, query = search(session, keyword, code)
            if any(row['frCd'] not in by_id for row in rows):
                raise ValueError('National query missed pilot merchant: ' + district)
            query.update(pilot=district)
            queries.append(query)
        progress('Pilot verified: ' + district, flush=True)
    snapshot = {'schema_version': 1, 'source_url': SOURCE, 'endpoint': BASE + '/place/search',
            'checked_at': datetime.now(KST).isoformat(timespec='seconds'),
            'status': 'complete', 'scope': 'nationwide_keyword_search',
            'keywords': list(KEYWORDS), 'queries': queries,
            'rows': sorted(by_id.values(), key=lambda r: r['frCd'])}
    snapshot = expand_names(session, snapshot, candidates, progress)
    snapshot['checked_at'] = datetime.now(KST).isoformat(timespec='seconds')
    return snapshot


def write_snapshot(path, snapshot):
    if snapshot.get('status') != 'complete' or not snapshot.get('queries') or any(
            q.get('status') != 'complete' or q.get('expected') != q.get('received') for q in snapshot['queries']):
        raise ValueError('Refusing partial snapshot')
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': SOURCE,
                            'Origin': 'https://www.onnuri.gift'})
    snapshot = collect(session)
    write_snapshot(args.output, snapshot)
    print('Complete snapshot:', len(snapshot['rows']))


if __name__ == '__main__':
    main()
