"""Offline candidate discovery; name agreement never proves merchant identity.

Reverse the previous pending-only comparison: extract vehicle-fuel businesses
from the complete public commercial archive and compare all annual merchants.
No requests to the live Onnuri service and no map/publication writes.
"""
import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from nationwide import name_key, region, row_id, non_vehicle
from onnuri_live import KST
from refresh_regions import ORDER

OUT = Path(__file__).resolve().parents[1] / 'output'
FIELDS = ('상가업소번호', '상호명', '지점명', '상권업종소분류코드', '상권업종소분류명',
          '표준산업분류코드', '표준산업분류명', '시군구명', '도로명주소', '지번주소', '위도', '경도')


def vehicle_fuel(row):
    # The source calls G21402 "가스 충전소", not "차량용 가스 충전소".
    # Keep conflicting industry records as discovery candidates, never proof.
    return row.get('상권업종소분류코드') in ('G21401', 'G21402')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fuel-index', type=Path, help='Optional complete discovery inventory, not an Onnuri list')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.fuel_index and args.fuel_index.exists():
        raise FileExistsError(args.fuel_index)
    sys.stdout.reconfigure(encoding='utf-8')
    with args.archive.open('rb') as source:
        archive_hash = hashlib.file_digest(source, 'sha256').hexdigest()
    provenance = json.loads((OUT/'pending_commercial_crosscheck_20261025.json').read_text(encoding='utf-8'))
    if archive_hash != provenance['archive_sha256']:
        raise ValueError('Archive differs from the verified public source')
    fuels, counts = [], {}
    with zipfile.ZipFile(args.archive, metadata_encoding='cp949') as archive:
        files = [n for n in archive.namelist() if n.endswith('.csv')]
        expected = set(provenance['scanned_files'])
        if set(files) != expected:
            raise ValueError('Regional files do not match source audit')
        def file_order(n):
            area = n.split('_')[-2]
            return ORDER.index('전남' if area == '전남광주' else area)
        for filename in sorted(files, key=file_order):
            reader = csv.DictReader(io.TextIOWrapper(archive.open(filename), encoding='utf-8-sig'))
            if not set(FIELDS).issubset(reader.fieldnames or []):
                raise ValueError('Commercial fields missing')
            count = 0
            for row in reader:
                count += 1
                if not vehicle_fuel(row):
                    continue
                area = region(row['도로명주소'])
                if area not in ORDER:
                    raise ValueError('Unresolved fuel region')
                fuels.append({**{k:row[k] for k in FIELDS}, 'region':area})
            if count != provenance['scanned_files'][filename]:
                raise ValueError('Row count mismatch')
            counts[filename] = count
            print(filename, count, flush=True)
    index = defaultdict(dict)
    if args.fuel_index:
        args.fuel_index.write_text(json.dumps({'archive_sha256':archive_hash,
            'source_date':provenance['source_date'], 'source_url':provenance['source_url'],
            'scope':'all_vehicle_fuel_candidates_not_Onnuri_verification', 'rows':fuels},
            ensure_ascii=False,indent=2),encoding='utf-8')
    for fuel in fuels:
        names = [fuel['상호명']]
        if fuel['지점명']:
            names.append(fuel['상호명'] + fuel['지점명'])
        for name in names:
            key = name_key(name)
            if key:
                index[(fuel['region'], key)][fuel['상가업소번호']] = fuel
    annual_bytes = (OUT/'onnuri_official.csv').read_bytes()
    snapshot = json.loads((OUT/'onnuri_official_snapshot.json').read_text(encoding='utf-8'))
    if hashlib.sha256(annual_bytes).hexdigest() != snapshot['sha256']:
        raise ValueError('Annual CSV differs from source snapshot')
    existing = {row_id(r) for r in snapshot['rows']}
    candidates, seen, annual_count = [], set(), 0
    for row in csv.DictReader(io.StringIO(annual_bytes.decode('utf-8-sig'))):
        annual_count += 1
        areas = ['전남', '광주'] if row['소재지'] == '전남광주' else [region(row['소재지'])]
        matches = {k:v for area in areas for k,v in index.get((area, name_key(row['가맹점명'])), {}).items()}
        if not matches:
            continue
        identity = row_id(row)
        # Different source rows with the same name/market remain visible.
        signature = tuple(sorted(row.items()))
        if signature in seen:
            continue
        seen.add(signature)
        candidates.append({'candidate_id':identity, 'annual_row':row,
            'already_selected':identity in existing,
            'existing_non_vehicle_rule_flag':non_vehicle(row),
            'status':'name_match_only_requires_market_and_identity_review',
            'commercial_matches':list(matches.values())})
    if annual_count != snapshot['total_rows']:
        raise ValueError('Annual row count mismatch')
    candidates.sort(key=lambda r:min(ORDER.index(m['region']) for m in r['commercial_matches']))
    new = [r for r in candidates if not r['already_selected']]
    result = {'checked_at':datetime.now(KST).isoformat(timespec='seconds'),
        'status':'offline_comparison_complete_not_membership_verification',
        'live_requests':0, 'map_changed':False,
        'annual_source':{k:snapshot[k] for k in ('source_url','source_date','sha256','total_rows')},
        'commercial_source':{k:provenance[k] for k in ('source_url','source_date','archive_sha256')},
        'scanned_files':counts, 'fuel_records':len(fuels),
        'fuel_records_by_region':dict(Counter(f['region'] for f in fuels)),
        'matched_annual_rows':len(candidates), 'not_previously_selected_rows':len(new),
        'new_rows_unflagged_by_existing_rule_not_verified':sum(not r['existing_non_vehicle_rule_flag'] for r in new),
        'limitations':['Names alone do not prove the same business.',
                      'Annual source has regional labels, not street addresses.',
                      'Commercial coordinates identify a candidate, not an Onnuri merchant.',
                      'A historical listing does not confirm current membership.'],
        'rows':candidates}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','scanned_files','limitations')},ensure_ascii=False))
    for r in new:
        print('NEW_NAME_MATCH',r['annual_row'],[(m['region'],m['상호명'],m['도로명주소']) for m in r['commercial_matches']],flush=True)


if __name__ == '__main__':
    main()
