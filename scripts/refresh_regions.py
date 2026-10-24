"""Sequential official regional search; publish only a complete nationwide run."""
import json
import re
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import requests
try:
    from onnuri_live import post, search, write_snapshot, SOURCE, BASE, KEYWORDS, KST
    from nationwide import region, non_vehicle
except ModuleNotFoundError:
    from scripts.onnuri_live import post, search, write_snapshot, SOURCE, BASE, KEYWORDS, KST
    from scripts.nationwide import region, non_vehicle

ORDER = ['전남', '광주', '전북', '경남', '경북', '부산', '대구', '울산',
         '충남', '충북', '대전', '세종', '강원', '제주', '경기', '인천', '서울']
OUT = Path(__file__).resolve().parents[1] / 'output'

def merge_rows(target, batch, area):
    for item in batch:
        if region(item['frcsAddr']) != area:
            continue
        old = target.get(item['frCd'])
        if old is not None and old != item:
            raise ValueError('Merchant changed during regional collection: ' + item['frCd'])
        target[item['frCd']] = item


def combine_regions(snapshots):
    """Reject missing, misordered or mixed-area evidence before publication."""
    if [s.get('region') for s in snapshots] != ORDER:
        raise ValueError('Regional run must cover all 17 areas in the requested order')
    rows, queries, manifest = {}, [], []
    previous = None
    for snapshot in snapshots:
        area = snapshot['region']
        checked = datetime.fromisoformat(snapshot['checked_at'])
        if previous is not None and checked < previous:
            raise ValueError('Regional completion times are out of order')
        previous = checked
        if snapshot.get('status') != 'complete' or not snapshot.get('queries'):
            raise ValueError('Incomplete region: ' + area)
        for query in snapshot['queries']:
            if query.get('region') != area or query.get('status') != 'complete' or query.get('expected') != query.get('received'):
                raise ValueError('Incomplete regional query: ' + area)
        if any(region(r['frcsAddr']) != area for r in snapshot['rows']):
            raise ValueError('Mixed-area snapshot: ' + area)
        if len({r['frCd'] for r in snapshot['rows']}) != len(snapshot['rows']):
            raise ValueError('Duplicate regional merchant ID')
        merge_rows(rows, snapshot['rows'], area)
        queries.extend(snapshot['queries'])
        manifest.append({'region': area, 'checked_at': snapshot['checked_at'],
                         'query_count': len(snapshot['queries']), 'raw_count': len(snapshot['rows'])})
    return {'status': 'complete', 'schema_version': 1, 'source_url': SOURCE,
            'endpoint': BASE+'/place/search', 'checked_at': snapshots[-1]['checked_at'],
            'scope': 'nationwide_sequential_regional_search', 'region_order': ORDER,
            'regions': manifest, 'queries': queries,
            'rows': sorted(rows.values(), key=lambda r:r['frCd'])}


def validate_combined(snapshot):
    if snapshot.get('region_order') != ORDER or [r['region'] for r in snapshot.get('regions', [])] != ORDER:
        raise ValueError('Missing full regional manifest')
    parts = []
    for entry in snapshot['regions']:
        area = entry['region']
        rows = [r for r in snapshot['rows'] if region(r['frcsAddr']) == area]
        queries = [q for q in snapshot['queries'] if q.get('region') == area]
        if len(rows) != entry['raw_count'] or len(queries) != entry['query_count']:
            raise ValueError('Regional evidence count mismatch: ' + area)
        parts.append(dict(region=area, rows=rows, queries=queries,
                          checked_at=entry['checked_at'], status=snapshot['status']))
    rebuilt = combine_regions(parts)
    if (rebuilt['rows'] != sorted(snapshot['rows'], key=lambda r:r['frCd']) or
            len(rebuilt['queries']) != len(snapshot['queries']) or
            rebuilt['checked_at'] != snapshot['checked_at']):
        raise ValueError('Unassigned or inconsistent regional evidence')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true', help='Validate all regions, then refresh local map files (no git push)')
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': SOURCE,
                            'Origin': 'https://www.onnuri.gift'})
    annual = json.loads((OUT/'onnuri_official_snapshot.json').read_text(encoding='utf-8'))
    snapshots, completed, cache = [], [], {}
    folder = OUT/'regional_search'
    folder.mkdir(exist_ok=True)
    (folder/'progress.json').write_text(json.dumps({'order': ORDER, 'completed': [], 'remaining': ORDER}, ensure_ascii=False), encoding='utf-8')
    for area in ORDER:
        names = []
        for item in annual['rows']:
            if non_vehicle(item):
                continue
            if region(item['소재지']) == area or (item['소재지'] == '전남광주' and area in ('전남', '광주')):
                name = re.sub(r'주식회사|유한회사|\(주\)|\(유\)|㈜', '', item['가맹점명']).strip()
                if len(name) >= 2 and not any(k.lower() in name.lower() for k in KEYWORDS):
                    names.append(name)
        local_rows, local_queries = {}, []
        for keyword in dict.fromkeys((*KEYWORDS, *names)):
            if keyword not in cache:
                cache[keyword] = search(session, keyword)
            batch, original_query = cache[keyword]
            query = dict(original_query, region=area, strategy='national_search_address_filter')
            local_queries.append(query)
            merge_rows(local_rows, batch, area)
        checked = datetime.now(KST).isoformat(timespec='seconds')
        regional = {'status': 'complete', 'source_url': SOURCE, 'checked_at': checked,
                    'scope': 'regional_keyword_search', 'region': area,
                    'queries': local_queries, 'rows': list(local_rows.values())}
        write_snapshot(folder/(area+'.json'), regional)
        snapshots.append(regional)
        completed.append(area)
        (folder/'progress.json').write_text(json.dumps({'order': ORDER, 'completed': completed,
            'remaining': ORDER[len(completed):], 'checked_at': checked}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'{area}: complete; {len(local_queries)} queries, {len(local_rows)} raw records', flush=True)
    write_snapshot(OUT/'onnuri_regional_snapshot.json', combine_regions(snapshots))
    if args.publish:
        subprocess.run([sys.executable, str(OUT.parent/'scripts'/'refresh_merchants.py'),
                        '--live-snapshot', str(OUT/'onnuri_regional_snapshot.json')], check=True)

if __name__ == '__main__':
    main()
