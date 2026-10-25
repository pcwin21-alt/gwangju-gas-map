"""Resumable, keyword-free Onnuri geographic search with explicit coverage.

Grid centres are sampling coordinates, never merchant locations. The service's
public client uses radius 2 km. Raw tile results stay in a local cache; the
published audit contains hashes, pagination and the exact planned cells.
"""
import argparse
import hashlib
import json
import math
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime
from pathlib import Path

import requests

try:
    from onnuri_live import search, SOURCE, BASE, KST
    from nationwide import region, name_key
    from live_merchants import address_key, identity
except ModuleNotFoundError:
    from scripts.onnuri_live import search, SOURCE, BASE, KST
    from scripts.nationwide import region, name_key
    from scripts.live_merchants import address_key, identity

OUT = Path(__file__).resolve().parents[1] / 'output'
BOUNDARY_URL = 'https://raw.githubusercontent.com/vuski/admdongkor/master/ver20261001/HangJeongDong_ver20261001.geojson'
ATTRIBUTION = ('통계청 통계지리정보서비스(SGIS, https://sgis.kostat.go.kr)에서 공공누리 제1유형으로 '
               '개방한 행정동 경계를 가공(가공: vuski/admdongkor, https://github.com/vuski/admdongkor), CC BY 4.0. '
               '본 프로젝트는 검색용 격자·완충 영역으로 재가공함.')


def now():
    return datetime.now(KST).isoformat(timespec='seconds')


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    # Windows/OneDrive can briefly lock a progress file while it is read or
    # synced. Keep atomic replacement and retry only this transient condition.
    for attempt in range(6):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(.1 * (attempt + 1))


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def make_plan(features, area, spacing=2600, buffer=250):
    from pyproj import Transformer
    from shapely.geometry import box, shape
    from shapely.ops import transform, unary_union
    from shapely import make_valid, STRtree
    if not 0 < spacing <= 2600 or buffer < 0:
        raise ValueError('Grid spacing must fit inside the 2 km search radius')
    forward = Transformer.from_crs(4326, 5179, always_xy=True).transform
    backward = Transformer.from_crs(5179, 4326, always_xy=True).transform
    chosen = [f for f in features if region(f['properties']['adm_nm']) == area]
    if not chosen:
        raise ValueError('No boundary for ' + area)
    districts = {}
    for feature in chosen:
        districts.setdefault(feature['properties']['sggnm'], []).append(
            transform(forward, make_valid(shape(feature['geometry']))))
    names = sorted(districts)
    shapes = [unary_union(districts[n]).buffer(buffer) for n in names]
    tree = STRtree(shapes)
    boundary = unary_union(shapes)
    xmin, ymin, xmax, ymax = boundary.bounds
    tiles = []
    cells = []
    for y in range(math.floor(ymin / spacing), math.floor(ymax / spacing) + 1):
        for x in range(math.floor(xmin / spacing), math.floor(xmax / spacing) + 1):
            cell = box(x * spacing, y * spacing, (x + 1) * spacing, (y + 1) * spacing)
            indices = tree.query(cell, predicate='intersects')
            if len(indices) == 0:
                continue
            lng, lat = backward((x + .5) * spacing, (y + .5) * spacing)
            tiles.append({'id': f'{x}_{y}', 'center': [round(lat, 7), round(lng, 7)],
                          'districts': sorted(names[int(i)] for i in indices)})
            cells.append(cell)
    # Every point of the buffered land polygon is in a searched square. Its
    # farthest corner is 1.839 km from the centre, with margin for projection.
    uncovered = boundary.difference(unary_union(cells)).area
    if uncovered > .01:
        raise ValueError('Grid has uncovered boundary area')
    tiles.sort(key=lambda t: (0 if '순천시' in t['districts'] else 1, t['districts'], t['id']))
    return {'schema_version': 1, 'region': area, 'created_at': now(),
            'scope': 'boundary_grid_nearby_search', 'keyword': '', 'radius_km': 2,
            'spacing_m': spacing, 'boundary_buffer_m': buffer, 'projection': 'EPSG:5179',
            'max_cell_corner_distance_m': spacing / math.sqrt(2),
            'uncovered_buffered_boundary_m2': uncovered,
            'boundary_source_url': BOUNDARY_URL, 'boundary_version': '2026-10-01',
            'boundary_attribution': ATTRIBUTION, 'districts': names,
            'tile_count': len(tiles), 'tiles': tiles}


def distance_km(a, b):
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    v = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lng2-lng1)/2)**2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(v)))


def check_tile(tile, result):
    query = result['query']
    if (result.get('tile_id') != tile['id'] or query.get('center') != tile['center'] or
            query.get('keyword') != '' or query.get('radius') != 2 or
            query.get('status') != 'complete' or query.get('received') != query.get('expected') or
            len(result['rows']) != query['received'] or
            len({r['frCd'] for r in result['rows']}) != len(result['rows'])):
        raise ValueError('Incomplete or mismatched tile')
    for row in result['rows']:
        # A small tolerance allows the service's distance rounding/projection.
        if distance_km(tile['center'], (float(row['latitude']), float(row['longitude']))) > 2.05:
            raise ValueError('Service returned a merchant outside its nearby radius')


def load_tiles(plan, cache):
    result = {}
    for tile in plan['tiles']:
        path = cache / (tile['id'] + '.json')
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            check_tile(tile, data)
            result[tile['id']] = data
    return result


class RequestPacer:
    """One global request budget, including paginated requests and retries."""
    def __init__(self, interval):
        self.interval = interval
        self.lock = threading.Lock()
        self.next_at = 0

    def pace(self):
        with self.lock:
            delay = self.next_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self.next_at = time.monotonic() + self.interval


def run(plan, cache, pause=.5, limit=None, workers=2):
    cache.mkdir(parents=True, exist_ok=True)
    for progress_path in (cache/'progress.json', OUT/'grid_search/progress.json'):
        if progress_path.exists() and json.loads(progress_path.read_text(encoding='utf-8')).get('status') == 'blocked':
            raise PermissionError('This scan recorded a site access block. Normal authorized access must be restored before resuming.')
    identity_file = cache / 'plan_identity.json'
    plan_hash = digest(plan)
    if identity_file.exists():
        if json.loads(identity_file.read_text())['sha256'] != plan_hash:
            raise ValueError('Cache belongs to a different grid plan')
    else:
        write(identity_file, {'sha256': plan_hash})
    results = load_tiles(plan, cache)
    started = now()
    pacer = RequestPacer(pause)
    local = threading.local()

    class PacedSession(requests.Session):
        def post(self, *args, **kwargs):
            pacer.pace()
            response = super().post(*args, **kwargs)
            if response.status_code >= 400:
                write(cache / f'error_{threading.get_ident()}_{time.monotonic_ns()}.json',
                      {'observed_at':now(), 'status_code':response.status_code,
                       'request':kwargs.get('json'), 'response_excerpt':response.text[:1000],
                       'retry_after':response.headers.get('Retry-After')})
            return response

    def fetch(tile):
        if not hasattr(local, 'session'):
            local.session = PacedSession()
            local.session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': SOURCE, 'Origin': 'https://www.onnuri.gift'})
        rows, query = search(local.session, '', pause=0, center=tile['center'], radius=2)
        result = {'tile_id': tile['id'], 'checked_at': now(), 'query': query, 'rows': rows}
        check_tile(tile, result)
        write(cache / (tile['id'] + '.json'), result)
        return result

    todo = [t for t in plan['tiles'] if t['id'] not in results]
    priority_path = OUT/'grid_search'/('jeonnam_priority_cells.json' if plan['region'] == '전남' else 'priority_'+plan['region']+'.json')
    if priority_path.exists():
        priority = json.loads(priority_path.read_text(encoding='utf-8'))['tiles']
        todo.sort(key=lambda t: t['id'] not in priority)
    if limit is not None:
        todo = todo[:limit]
    iterator = iter(todo)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(fetch, t): t for t in [next(iterator, None) for _ in range(workers)] if t is not None}
        while pending:
            finished, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in finished:
                tile = pending.pop(future)
                try:
                    result = future.result()
                except Exception as error:
                    for task in pending:
                        task.cancel()
                    write(cache / 'progress.json', {'status': 'blocked' if isinstance(error, PermissionError) else 'failed', 'started_at': started, 'updated_at': now(),
                          'completed': len(results), 'planned': len(plan['tiles']), 'failed_tile': tile,
                          'error': type(error).__name__, 'message': str(error)[:400]})
                    raise
                results[tile['id']] = result
                write(cache / 'progress.json', {'status': 'running', 'started_at': started, 'updated_at': now(),
                      'completed': len(results), 'planned': len(plan['tiles']), 'last_tile': tile['id'],
                      'max_requests_per_second': 1/pause, 'workers': workers})
                if len(results) % 50 == 0 or len(results) == len(plan['tiles']):
                    print(f"{plan['region']} grid {len(results)}/{len(plan['tiles'])}; last={len(result['rows'])} merchants", flush=True)
                next_tile = next(iterator, None)
                if next_tile is not None:
                    pending[pool.submit(fetch, next_tile)] = next_tile
    complete = len(results) == len(plan['tiles'])
    write(cache / 'progress.json', {'status': 'complete' if complete else 'partial',
          'started_at': started, 'updated_at': now(), 'completed': len(results), 'planned': len(plan['tiles'])})
    return results


def summarize(plan, results, annual, known_addresses, *, allow_partial=False):
    planned_ids = {t['id'] for t in plan['tiles']}
    complete = set(results) == planned_ids
    if not results or not set(results).issubset(planned_ids) or (not complete and not allow_partial):
        raise ValueError('Cannot publish an incomplete grid')
    annual_keys = {(name_key(r['가맹점명']), name_key(r['소속 시장명(또는 상점가)'])) for r in annual}
    by_id, observations, queries = {}, {}, []
    for tile in plan['tiles']:
        if tile['id'] not in results:
            continue
        data = results[tile['id']]
        check_tile(tile, data)
        query = dict(data['query'], tile_id=tile['id'], checked_at=data['checked_at'],
                     result_sha256=digest(data), districts=tile['districts'])
        queries.append(query)
        for row in data['rows']:
            if region(row['frcsAddr']) != plan['region']:
                continue
            if row['frCd'] in by_id and by_id[row['frCd']] != row:
                raise ValueError('Merchant changed during scan: ' + row['frCd'])
            by_id[row['frCd']] = row
            observations[row['frCd']] = max(observations.get(row['frCd'], ''), data['checked_at'])
    candidates = []
    for row in by_id.values():
        reasons = []
        if re.search(r'주유|충전|석유|에너지|LPG|엘피지|오일|유류|가스', row['frcsNm'], re.I):
            reasons.append('fuel_name')
        if identity(row) in annual_keys:
            reasons.append('annual_fuel_identity')
        key = address_key(row['frcsAddr'])
        if key is not None and key in known_addresses:
            reasons.append('fuel_registry_address_requires_identity_review')
        if reasons:
            candidates.append(dict(row, _observed_at=observations[row['frCd']], _grid_candidate_basis=reasons))
    return {'schema_version': 1, 'status': 'complete' if complete else 'partial',
            'scope': 'regional_geographic_grid' if complete else 'regional_geographic_grid_partial',
            'source_url': SOURCE, 'endpoint': BASE + '/place/search', 'region': plan['region'],
            'checked_at': max(d['checked_at'] for d in results.values()),
            'started_at': min(d['checked_at'] for d in results.values()),
            'plan_sha256': digest(plan), 'planned_tiles': len(plan['tiles']), 'completed_tiles': len(results),
            'remaining_tile_ids': [t['id'] for t in plan['tiles'] if t['id'] not in results],
            'districts': plan['districts'], 'raw_unique_regional_merchants': len(by_id),
            'candidate_selection': 'Fuel name OR exact annual identity OR fuel registry address; not automatic promotion',
            'queries': queries, 'rows': sorted(candidates, key=lambda r: r['frCd'])}


def augment_snapshot(baseline, grid):
    """Add a complete geographic run without claiming a new national refresh."""
    for snapshot in (baseline, grid):
        if snapshot.get('status') != 'complete' or not snapshot.get('queries') or any(
                q.get('status') != 'complete' or q.get('received') != q.get('expected')
                for q in snapshot['queries']):
            raise ValueError('Cannot merge incomplete searches')
    if (grid.get('scope') != 'regional_geographic_grid' or
            grid.get('completed_tiles') != grid.get('planned_tiles') or
            len(grid['queries']) != grid['planned_tiles'] or
            len({q['tile_id'] for q in grid['queries']}) != grid['planned_tiles'] or
            any(q.get('keyword') != '' or q.get('radius') != 2 for q in grid['queries']) or
            any(region(r['frcsAddr']) != grid['region'] for r in grid['rows'])):
        raise ValueError('Grid coverage is incomplete or has mixed regions')
    rows = {r['frCd']: dict(r, _observed_at=r.get('_observed_at', baseline['checked_at'])) for r in baseline['rows']}
    old_ids = set(rows)
    for row in grid['rows']:
        if not row.get('_observed_at') or not grid['started_at'] <= row['_observed_at'] <= grid['checked_at']:
            raise ValueError('Missing or inconsistent grid observation date')
        # Absence never revokes a previously observed merchant. Only fresh
        # exact-ID observations replace records.
        rows[row['frCd']] = row
    manifest = [r for r in baseline.get('regional_grids', []) if r['region'] != grid['region']]
    manifest.append({k: grid[k] for k in ('region', 'checked_at', 'started_at', 'planned_tiles',
        'completed_tiles', 'raw_unique_regional_merchants', 'plan_sha256')})
    manifest[-1]['new_candidate_ids'] = sorted({r['frCd'] for r in grid['rows']} - old_ids)
    queries = [q for q in baseline['queries'] if q.get('grid_region') != grid['region']]
    queries += [dict(q, grid_region=grid['region']) for q in grid['queries']]
    return dict(baseline, scope='national_search_with_regional_grids', regional_grids=manifest,
                queries=queries, rows=sorted(rows.values(), key=lambda r:r['frCd']))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--boundary', required=True)
    p.add_argument('--region', required=True)
    p.add_argument('--output', required=True)
    p = sub.add_parser('scan')
    p.add_argument('--plan', required=True)
    p.add_argument('--cache', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--pause', type=float, default=.5)
    p.add_argument('--workers', type=int, choices=range(1, 5), default=2)
    p.add_argument('--limit', type=int)
    p.add_argument('--fuel-addresses', help='Additional registry road addresses as a JSON array')
    args = parser.parse_args()
    if args.command == 'plan':
        path = Path(args.boundary)
        plan = make_plan(json.loads(path.read_text(encoding='utf-8-sig'))['features'], args.region)
        plan['boundary_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        if Path(args.output).exists():
            raise ValueError('Plan already exists; reuse it to resume a scan')
        write(args.output, plan)
        print(f"{args.region}: {plan['tile_count']} cells; {len(plan['districts'])} districts")
    else:
        if args.pause < .3:
            raise ValueError('Minimum request pause is 0.3 seconds')
        plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
        results = run(plan, Path(args.cache), args.pause, args.limit, args.workers)
        if len(results) != plan['tile_count']:
            print('Partial run saved; no snapshot published')
            return
        annual = json.loads((OUT/'onnuri_official_snapshot.json').read_text(encoding='utf-8'))['rows']
        known = set()
        for filename in ('station_locations.json', 'lpg_locations.json'):
            known.update(address_key(r.get('LCTN_ROAD_NM')) for r in json.loads((OUT/filename).read_text(encoding='utf-8'))['rows'])
        if args.fuel_addresses:
            known.update(address_key(a) for a in json.loads(Path(args.fuel_addresses).read_text(encoding='utf-8')))
        known.discard(None)
        summary = summarize(plan, results, annual, known)
        write(args.output, summary)
        print(f"Complete: {summary['raw_unique_regional_merchants']} unique regional merchants; {len(summary['rows'])} fuel candidates")


if __name__ == '__main__':
    main()
