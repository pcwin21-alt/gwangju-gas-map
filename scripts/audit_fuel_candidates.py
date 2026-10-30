"""Full annual-file recall audit. Discovery joins never promote map markers."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    from nationwide import name_key, non_vehicle, region, row_id
    from onnuri_live import KST
except ModuleNotFoundError:
    from scripts.nationwide import name_key, non_vehicle, region, row_id
    from scripts.onnuri_live import KST

OUT = Path(__file__).resolve().parents[1] / 'output'


def fuel_signals(row):
    # Remove substring collisions before broad recall. Unknown gas/energy uses
    # remain candidates and require independent vehicle-business evidence.
    product = re.sub(r'우유류|섬유류', '', row.get('취급품목', ''))
    signals = []
    if re.search(r'주유소|주유마트|충전소|석유|에너지|엘피지|lpg|오일뱅크', row['가맹점명'], re.I):
        signals.append('fuel_name')
    if re.search(r'주유|휘발유|휴발유|경유|등유|석유|유류|무연|차량용.*(?:기름|연료|가스)|자동차용.*연료|엘피지|lpg|충전소', product, re.I):
        signals.append('fuel_product')
    return signals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    read = lambda n: json.loads((OUT / n).read_text(encoding='utf-8'))
    mapped = read('gas_stations.json')
    existing = read('onnuri_official_snapshot.json')
    source_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if source_hash != existing['sha256']:
        raise ValueError('Annual input differs from the dated official snapshot; update source metadata first')
    ledger = {r['candidate_id']: r for r in read('nationwide_candidates.json')['rows']}
    commercial = read('alternatives/vehicle_fuel_index_20261026.json')
    locations = read('station_locations.json')['rows'] + read('lpg_locations.json')['rows']
    index = defaultdict(list)
    for r in locations:
        index[(region(r.get('LCTN_ROAD_NM') or r.get('CTPV_NM')), name_key(r['CONM_NM']))].append(
            {'source': 'public_fuel_registry', 'record': r})
    for r in commercial['rows']:
        names = {r['상호명'], r['상호명'] + r.get('지점명', '')}
        for name in names:
            index[(r['region'], name_key(name))].append({'source': 'commercial_registry', 'record': r})
    by_candidate = defaultdict(list)
    for s in mapped:
        v = s.get('verification', {}).get('onnuri', {})
        for cid in v.get('candidate_ids', []) + ([v['candidate_id']] if v.get('candidate_id') else []):
            by_candidate[cid].append(s['id'])
    rows = []
    total = 0
    with args.source.open(encoding='utf-8-sig', newline='') as f:
        for annual in csv.DictReader(f):
            total += 1
            annual = {k: (v or '').strip() for k, v in annual.items()}
            areas = ['전남', '광주'] if annual['소재지'] == '전남광주' else [region(annual['소재지'])]
            matches = [m for area in areas for m in index.get((area, name_key(annual['가맹점명'])), [])]
            signals = fuel_signals(annual)
            if not signals and not matches:
                continue
            cid = row_id(annual)
            if matches:
                signals.append('independent_fuel_registry_name_candidate')
            rows.append({'source_row': total, 'candidate_id': cid, 'annual_row': annual,
                         'signals': signals, 'excluded_non_vehicle': non_vehicle(annual),
                         'map_ids': sorted(set(by_candidate[cid])),
                         'existing_ledger': ledger.get(cid), 'location_candidates': matches})
    summary = {
        'checked_at': datetime.now(KST).isoformat(timespec='seconds'),
        'scope': 'full_annual_file_name_product_and_reverse_registry_discovery_not_current_membership',
        'annual_source_url': existing['source_url'], 'annual_source_date': existing['source_date'],
        'annual_sha256': source_hash,
        'total_annual_rows': total, 'candidate_rows': len(rows),
        'candidate_identity_groups': len({r['candidate_id'] for r in rows}),
        'excluded_non_vehicle_rows': sum(r['excluded_non_vehicle'] for r in rows),
        'with_map_identity_rows': sum(bool(r['map_ids']) for r in rows),
        'without_map_identity_rows': sum(not r['map_ids'] and not r['excluded_non_vehicle'] for r in rows),
        'new_to_previous_candidate_selection': sum(r['existing_ledger'] is None for r in rows),
        'product_values': dict(Counter(r['annual_row']['취급품목'] for r in rows)),
        'registry_rows_scanned': len(locations), 'commercial_rows_scanned': len(commercial['rows']),
        'limitations': ['Candidate name/region joins do not establish business identity.',
                       'Map absence requires address/identity review, not only candidate-ID absence.',
                       'Annual publication and bank/operator live verification dates remain distinct.'],
        'rows': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('rows', 'product_values', 'limitations')}, ensure_ascii=True))


if __name__ == '__main__':
    main()
