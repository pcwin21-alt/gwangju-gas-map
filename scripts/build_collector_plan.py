"""Prepare a finite regional inventory. Cached observations retain their dates."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from incremental_collector import ROOT, POLICY, fingerprint, read
from nationwide import valid_coords, region, name_key, non_vehicle
from official_onnuri import fuel_row
from discover_address_candidates import address_key
ORDER = read(POLICY)['region_order']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=ROOT/'output/collector_plan.json')
    args = ap.parse_args()
    fuel = read(ROOT/'output/alternatives/vehicle_fuel_index_20261026.json')
    mapped = read(ROOT/'output/gas_stations.json')
    mapped_addresses = {address_key(s['address']) for s in mapped if s.get('lat') and s.get('lng') and 'onnuri' in s.get('payment_types', [])}
    known_queries = set()
    # Cache reuse is a dated discovery observation, never current membership or
    # proof of nonmembership. Keep source paths/hashes so it is auditable.
    cached = []
    for path in (ROOT/'output/alternatives/kb_location_cache/unfiltered').rglob('*.json'):
        data = read(path)
        q = data.get('query', {})
        if data.get('status') != 'complete' or q.get('keyword') != '' or len(q.get('center', [])) != 2:
            continue
        point = tuple(round(float(v), 6) for v in q['center'])
        known_queries.add(point)
        cached.append({'point': point, 'checked_at': data['checked_at'],
                       'cache_file': str(path.relative_to(ROOT)).replace('\\', '/'), 'total': data.get('total')})
    jobs = []
    control = next(s for s in mapped if s.get('region') == '전남' and '현대주유소' == s['name'])
    jobs.append({'kind': 'kb_search', 'source': 'kbcard', 'region': '전남', 'control': True,
                 'target': {'name': control['name'], 'keyword': '현대', 'lat': control['lat'], 'lng': control['lng'],
                            'coordinate_source_id': control['id']}})
    seen = set()
    counts = {area: {'fuel_records': 0, 'mapped_address': 0, 'dated_cache': 0, 'new_query': 0} for area in ORDER}
    for f in sorted(fuel['rows'], key=lambda f: (ORDER.index(f['region']), f['도로명주소'])):
        area = f['region']; counts[area]['fuel_records'] += 1
        if address_key(f['도로명주소']) in mapped_addresses:
            counts[area]['mapped_address'] += 1
            continue
        if not valid_coords(f['위도'], f['경도']):
            continue
        point = tuple(round(float(f[k]), 6) for k in ('위도', '경도'))
        if point in known_queries:
            counts[area]['dated_cache'] += 1
            continue
        if point in seen:
            continue
        seen.add(point); counts[area]['new_query'] += 1
    # The campaign is not another nationwide grid crawl. Start from actual
    # annual fuel registrations, and retain missing-location cases explicitly.
    audit = read(ROOT/'output/audits/onnuri_count_20261030/expanded_v2.json')
    inventory = {f['상가업소번호']: f for f in fuel['rows']}
    gaps = []
    for candidate in audit['rows']:
        annual = candidate['annual_row']
        if candidate['map_ids'] or (candidate.get('existing_ledger') or {}).get('status') == 'excluded_non_vehicle_fuel' or non_vehicle(annual) or not fuel_row(annual):
            continue
        matches = {m['record']['상가업소번호']: m['record'] for m in candidate['location_candidates']
                   if m['source'] == 'commercial_registry'}
        if not matches:
            gaps.append({'candidate_id': candidate['candidate_id'], 'name': annual['가맹점명'],
                         'region': annual['소재지'], 'status': 'needs_location',
                         'reason': 'No independently linked vehicle-fuel location; no guessed point'})
        for f in matches.values():
            if address_key(f['도로명주소']) in mapped_addresses or not valid_coords(f['위도'], f['경도']):
                continue
            jobs.append({'kind': 'kb_search', 'source': 'kbcard', 'region': f['region'],
                         'target': {'name': annual['가맹점명'], 'keyword': name_key(annual['가맹점명']),
                                    'lat': float(f['위도']), 'lng': float(f['경도']),
                                    'coordinate_source_id': f['상가업소번호'], 'address': f['도로명주소']},
                         'scope': 'targeted annual fuel candidate; annual link remains unverified'})
    # Two unresolved Jeonnam card identities were not independently located.
    # Their public card points can seed discovery, never navigation promotion.
    bank_review = read(ROOT/'output/alternatives/kb_address_review_20261027.json')
    for record in bank_review['rows']:
        bank = record['bank_record']; c = bank['content']
        if record.get('mapped_name_matches') or c['category'] != '주유소' or c['title'] == '주유소':
            continue
        if any(c['franchiseNo'] == e['bank_record']['content']['franchiseNo'] for e in read(ROOT/'output/supplemental_onnuri_evidence.json')['rows']):
            continue
        loc = bank.get('location', {})
        if valid_coords(loc.get('lat'), loc.get('lng')):
            jobs.append({'kind': 'kb_search', 'source': 'kbcard', 'region': '전남',
                         'target': {'name': c['title'], 'keyword': name_key(c['title']),
                                    'lat': float(loc['lat']), 'lng': float(loc['lng']),
                                    'coordinate_source_id': 'public-bank:'+c['franchiseNo']},
                         'scope': 'public discovery point only; independent location still required'})
    control_job = jobs.pop(0)
    jobs = [control_job] + sorted({fingerprint(j): j for j in jobs}.values(), key=lambda j: ORDER.index(j['region']))
    # Bulk source refresh is an independent path, not a retry of blocked API.
    jobs.insert(1, {'kind': 'annual_page', 'source': 'datagov', 'region': '전남'})
    # Nationwide jobs are ordered already; this explicit scope prevents an
    # implementation handoff from misreporting the campaign as a census.
    plan = {'id': 'fuel-candidate-inventory-20261102-v1',
            'scope': 'finite cross-source fuel registration candidates, strictly sequential regional review; not a geographic census',
            'region_order': ORDER,
            'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'regional_inventory': counts, 'reused_cache_queries': len(cached),
            'cached_observations': cached,
            'source_gaps': [{'region': '전남', 'status': 'needs_source_inventory',
                             'reason': 'Latest 22-municipality designated-market shop lists not yet all available; no complete census claim'}] + gaps,
            'jobs': jobs}
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'jobs': len(jobs), 'cached_queries': len(cached), 'regions': counts}, ensure_ascii=True))


if __name__ == '__main__':
    main()
