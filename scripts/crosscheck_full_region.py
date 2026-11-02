"""Offline, all-category merchant-to-fuel comparison. Never publish matches.

Annual regional labels may combine Gwangju/Jeonnam and omit street addresses.
Issuer address-option snapshots are issuer-scoped, dated inputs, not a census.
Names, phone reuse and co-located shops all produce review leads, never proof.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from nationwide import name_key, region, valid_coords, row_id
    from discover_address_candidates import address_key
    from supplemental_onnuri import meters
except ModuleNotFoundError:
    from scripts.nationwide import name_key, region, valid_coords, row_id
    from scripts.discover_address_candidates import address_key
    from scripts.supplemental_onnuri import meters

ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))
FUEL_CATEGORIES = {'주유소', '충전소', 'LPG충전소', 'LPG 충전소', '가스충전소'}


def phone_key(value):
    value = re.sub(r'\D', '', value or '')
    # No partial numbers, call-center numbers or placeholders.
    return value if re.fullmatch(r'0\d{8,10}', value) and len(set(value)) > 2 else None


def reduced_name(value):
    value = re.sub(r'주식회사|유한회사|\(주\)|\(유\)|㈜', '', value or '')
    value = re.sub(r'주유소|충전소|직영|셀프|self|LPG|에스케이|SK|GS|S[ -]?OIL', '', value, flags=re.I)
    key = name_key(value)
    # Generic company/brand tokens must not create a large false match pool.
    return key if len(key) >= 2 and key not in {'에너지', '석유', '오일', '가스', '농협', '현대', '알뜰', '주유', '충전'} else None


def county(value):
    return next((token for token in (value or '').split()
                 if re.fullmatch(r'[가-힣]+[시군]', token)
                 and not token.endswith(('광역시', '특별시'))), None)


def read(path):
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding='utf-8'))


def validate_bank_snapshot(snapshot, area):
    if snapshot.get('region') != area or snapshot.get('status') != 'all_listed_addresses_complete':
        raise ValueError('Wrong region or incomplete issuer address snapshot')
    if not snapshot.get('planned_queries') or snapshot['planned_queries'] != snapshot.get('completed_queries'):
        raise ValueError('Issuer address queries were not all completed')
    ids = [r['content']['franchiseNo'] for r in snapshot['rows']]
    if len(ids) != len(set(ids)) or len(ids) != snapshot.get('unique_merchants'):
        raise ValueError('Issuer snapshot contains duplicate or missing merchant IDs')
    if any(region(r['content'].get('address')) != area for r in snapshot['rows']):
        raise ValueError('Issuer snapshot contains unresolved or other-region merchants')


def source_ref(path, **extra):
    return {'file': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **extra}


def load_physical(area):
    rows, sources = [], []
    for filename, kind in [('station_locations.json', 'liquid'), ('lpg_locations.json', 'lpg')]:
        path = ROOT/'output'/filename
        data = read(path)
        sources.append(source_ref(path, source_url=data['source_url'], retrieved_at=data['retrieved_at']))
        for i, raw in enumerate(data['rows']):
            address = raw.get('LCTN_ROAD_NM') or raw.get('LCTN_LOTNO_ADDR') or ''
            if region(address) == area:
                rows.append({'source_id': f'{filename}:{i}', 'name': raw['CONM_NM'],
                             'address': address, 'phone': raw.get('TELNO'), 'lat': raw.get('LAT'),
                             'lng': raw.get('LOT'), 'fuel_kind': kind, 'source_date': raw.get('DATA_CRTR_YMD'),
                             'source_url': data['source_url']})
    path = ROOT/'config/collector-fuel-index.json.gz'
    data = read(path)
    sources.append(source_ref(path, source_url=data['source_url'], source_date=data['source_date']))
    for raw in data['rows']:
        if raw['region'] != area:
            continue
        rows.append({'source_id': raw['상가업소번호'], 'name': raw['상호명'], 'branch': raw.get('지점명', ''),
                     'address': raw['도로명주소'], 'phone': None, 'lat': raw['위도'], 'lng': raw['경도'],
                     'fuel_kind': 'lpg' if raw['상권업종소분류코드'] == 'G21402' else 'liquid',
                     'source_date': data['source_date'], 'source_url': data['source_url']})
    return rows, sources


class FuelIndex:
    def __init__(self, rows):
        self.rows = rows
        self.names, self.reduced, self.phones, self.addresses, self.grid = (defaultdict(set) for _ in range(5))
        self.points = {}
        for i, row in enumerate(rows):
            for name in [row['name'], row['name'] + (row.get('branch') or '')]:
                if name_key(name):
                    self.names[name_key(name)].add(i)
                reduced = reduced_name(name)
                if reduced:
                    self.reduced[reduced].add(i)
            phone = phone_key(row.get('phone'))
            if phone:
                self.phones[phone].add(i)
            address = address_key(row.get('address'))
            if address:
                self.addresses[address].add(i)
            if valid_coords(row.get('lat'), row.get('lng')):
                point = (float(row['lat']), float(row['lng']))
                self.points[i] = point
                self.grid[(math.floor(point[0]*100), math.floor(point[1]*100))].add(i)

    def match(self, name, address='', phone=None, lat=None, lng=None):
        reasons = defaultdict(set)
        lookups = [('exact_normalized_name', self.names.get(name_key(name), set())),
                   ('reduced_name_only', self.reduced.get(reduced_name(name), set())),
                   ('exact_phone_only', self.phones.get(phone_key(phone), set())),
                   ('same_street_address_only', self.addresses.get(address_key(address), set()))]
        for reason, ids in lookups:
            for i in ids:
                reasons[i].add(reason)
        point = None
        if valid_coords(lat, lng):
            point = (float(lat), float(lng))
            gx, gy = math.floor(point[0]*100), math.floor(point[1]*100)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for i in self.grid.get((gx+dx, gy+dy), set()):
                        if meters(point, self.points[i]) <= 100:
                            reasons[i].add('within_100m_only')
        matches = []
        for i, signals in reasons.items():
            row = self.rows[i]
            distance = meters(point, self.points[i]) if point and i in self.points else None
            conflict = bool(county(address) and county(row['address']) and county(address) != county(row['address']))
            # Retain conflicting phone/name observations with an explicit flag.
            if conflict and signals == {'reduced_name_only'}:
                continue
            matches.append({'physical': row, 'signals': sorted(signals),
                            'distance_m': round(distance, 2) if distance is not None else None,
                            'county_conflict': conflict,
                            'status': 'review_only_not_same_business_or_membership_proof'})
        return sorted(matches, key=lambda x: x['physical']['source_id'])


def mapped_links(matches, stations):
    """Address+kind+distance links to existing map coverage; not issuer proof."""
    links = set()
    for match in matches:
        f = match['physical']
        key = address_key(f['address'])
        if not key or not valid_coords(f.get('lat'), f.get('lng')):
            continue
        for station in stations:
            if station.get('fuel_kind') != f['fuel_kind'] or address_key(station['address']) != key:
                continue
            if valid_coords(station.get('lat'), station.get('lng')) and meters(
                    (float(station['lat']), float(station['lng'])), (float(f['lat']), float(f['lng']))) <= 100:
                links.add(station['id'])
    return sorted(links)


def write_gzip(path, value):
    # Stable, auditable exports; source dates live in the data, never mtime.
    with path.open('wb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream:
            stream.write(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--region', default='전남', choices=['전남'])
    ap.add_argument('--state-dir', type=Path, required=True)
    ap.add_argument('--bank-snapshot', type=Path, default=ROOT/'output/alternatives/kb_address_progress_20261027.json')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    state_path = args.state_dir/'state.json'
    state = read(state_path)
    if state['summary']['active_region'] != args.region:
        raise ValueError('Compare only the active region')
    source = state['survey_inventory']['annual_source']
    annual_path = args.state_dir/'responses/0224a260c55f4ca38e1d9f89.csv'
    annual_raw = annual_path.read_bytes()
    if hashlib.sha256(annual_raw).hexdigest() != source['sha256']:
        raise ValueError('Annual snapshot differs from recorded official source')
    annual = list(csv.DictReader(io.StringIO(annual_raw.decode('utf-8-sig'))))
    if len(annual) != source['total_rows']:
        raise ValueError('Incomplete annual input')
    related = [r for r in annual if r['소재지'] == '전남광주' or region(r['소재지']) == args.region]
    physical, physical_sources = load_physical(args.region)
    index = FuelIndex(physical)
    stations = [s for s in read(ROOT/'output/gas_stations.json') if s.get('region') == args.region and 'onnuri' in s.get('payment_types', [])]
    bank_path = args.bank_snapshot.resolve()
    bank_source = read(bank_path)
    validate_bank_snapshot(bank_source, args.region)
    # Preserve each source/version. Latest-per-ID is for offline comparison only.
    versions = list(bank_source['rows'])
    for attempt in state['attempts']:
        if attempt.get('source') != 'kbcard' or attempt.get('status') != 'done':
            continue
        path = args.state_dir/'responses'/(attempt['id']+'.json')
        if not path.exists():
            raise ValueError('Completed bank response missing')
        payload = read(path)
        versions.extend({**row, 'checked_at': payload['checked_at']} for row in payload['rows']
                        if region(row['content'].get('address')) == args.region)
    bank = {}
    for row in versions:
        if region(row['content'].get('address')) != args.region:
            continue
        fid = row['content']['franchiseNo']
        if row.get('checked_at', '') >= bank.get(fid, {}).get('checked_at', ''):
            bank[fid] = row
    bank_rows = sorted(bank.values(), key=lambda b: b['content']['franchiseNo'])
    annual_matches, bank_matches, unlocated_fuel_categories = [], [], []
    for row in related:
        matches = index.match(row['가맹점명'])
        if matches:
            annual_matches.append({'candidate_id': row_id(row), 'annual_row': row,
                                   'ambiguous_region': row['소재지'] == '전남광주',
                                   'matches': matches, 'mapped_location_ids': mapped_links(matches, stations),
                                   'status': 'review_only_annual_has_no_premise_address'})
    for row in bank_rows:
        c, loc = row['content'], row.get('location', {})
        matches = index.match(c['title'], c.get('address', ''), c.get('tel'), loc.get('lat'), loc.get('lng'))
        if matches:
            bank_matches.append({'bank_record': row, 'matches': matches,
                                 'mapped_location_ids': mapped_links(matches, stations),
                                 'status': 'review_only_no_auto_publication'})
        elif c.get('category') in FUEL_CATEGORIES:
            unlocated_fuel_categories.append(row)
    args.output.mkdir(parents=True)
    exports = {'issuer_address_snapshot.json.gz': bank_source,
               'annual_region_unresolved.json.gz': related, 'issuer_merchant_versions.json.gz': versions,
               'issuer_latest_by_id.json.gz': bank_rows, 'physical_fuel_records.json.gz': physical}
    for name, value in exports.items():
        write_gzip(args.output/name, value)
    report = {'reviewed_at': datetime.now(KST).isoformat(timespec='seconds'), 'region': args.region,
              'status': 'dated_inputs_compared_current_region_incomplete', 'live_requests': 0, 'map_changed': False,
              'source_refs': {'annual': source_ref(annual_path, **source),
                              'bank': source_ref(bank_path, source_url=bank_source['source_url'],
                                                 checked_at=bank_source['checked_at'], scope=bank_source['scope']),
                              'state': source_ref(state_path), 'physical': physical_sources},
              'summary': {'annual_all_rows_scanned': len(annual), 'annual_region_related_rows': len(related),
                          'annual_ambiguous_region_rows': sum(r['소재지'] == '전남광주' for r in related),
                          'physical_source_rows': len(physical),
                          'physical_unique_parsed_addresses': len({address_key(r['address']) for r in physical if address_key(r['address'])}),
                          'bank_source_rows': len(bank_source['rows']), 'bank_latest_unique_ids': len(bank_rows),
                          'bank_categories_scanned': len({r['content'].get('category') for r in bank_rows}),
                          'annual_match_rows_for_review': len(annual_matches),
                          'bank_match_ids_for_review': len(bank_matches),
                          'bank_nonfuel_category_match_ids_for_review': sum(r['bank_record']['content'].get('category') not in FUEL_CATEGORIES for r in bank_matches),
                          'unlocated_fuel_category_ids_for_review': len(unlocated_fuel_categories),
                          'new_verified_stations': 0},
              'annual_matches': annual_matches, 'bank_matches': bank_matches,
              'unlocated_fuel_category_records': unlocated_fuel_categories,
              'exports': {name: source_ref(args.output/name, rows=len(value['rows']) if isinstance(value, dict) else len(value))
                          for name, value in exports.items()},
              'limitations': ['No current all-issuer Jeonnam merchant census was obtained.',
                              'Annual combined Jeonnam/Gwangju rows are retained unresolved, not counted as Jeonnam.',
                              'No name, phone, coordinate or market-only match automatically proves the same fuel business.',
                              'Phone numbers can be reused and a shop can share a station premise.',
                              'No response absence establishes nonmembership; no previous map entry was deleted.',
                              'Old source/issuer dates and paper/QR/operator verification dates are preserved.']}
    (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
