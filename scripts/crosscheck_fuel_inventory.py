"""Compare the expanded annual candidates with ALL commercial industries.

Retain address/category conflicts. An equal name never establishes identity.
"""
import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

from nationwide import name_key, region
from refresh_regions import ORDER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidates', type=Path, required=True)
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path(__file__).resolve().parents[1]
    source = json.loads((root / 'output/pending_commercial_crosscheck_20261025.json').read_text(encoding='utf-8'))
    with args.archive.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != source['archive_sha256']:
            raise ValueError('Commercial archive hash differs from source evidence')
    audit = json.loads(args.candidates.read_text(encoding='utf-8'))
    targets = defaultdict(list)
    rows = []
    for candidate in audit['rows']:
        if candidate['map_ids']:
            continue
        entry = {'candidate_id': candidate['candidate_id'], 'annual_row': candidate['annual_row'],
                 'existing_ledger': candidate['existing_ledger'], 'commercial_matches': []}
        rows.append(entry)
        a = candidate['annual_row']
        areas = ['전남', '광주'] if a['소재지'] == '전남광주' else [region(a['소재지'])]
        for area in areas:
            targets[(area, name_key(a['가맹점명']))].append(entry)
    fields = ('상가업소번호', '상호명', '지점명', '상권업종소분류코드', '상권업종소분류명',
              '표준산업분류코드', '표준산업분류명', '시군구명', '도로명주소', '지번주소', '위도', '경도')
    counts = {}
    with zipfile.ZipFile(args.archive, metadata_encoding='cp949') as archive:
        files = [n for n in archive.namelist() if n.endswith('.csv')]
        if set(files) != set(source['scanned_files']):
            raise ValueError('Commercial region list differs from verified archive')
        files.sort(key=lambda n: ORDER.index('전남' if n.split('_')[-2] == '전남광주' else n.split('_')[-2]))
        for filename in files:
            count = 0
            for commercial in csv.DictReader(io.TextIOWrapper(archive.open(filename), encoding='utf-8-sig')):
                count += 1
                for entry in targets.get((region(commercial['도로명주소']), name_key(commercial['상호명'])), []):
                    entry['commercial_matches'].append({k: commercial[k] for k in fields})
            if count != source['scanned_files'][filename]:
                raise ValueError('Commercial regional row count differs')
            counts[filename] = count
            print(json.dumps({'file': filename, 'scanned': count}, ensure_ascii=True), flush=True)
    report = {'scope': 'all_industry_name_candidates_not_identity_or_membership_verification',
              'commercial_source': {k: source[k] for k in ('source_url', 'source_date', 'archive_sha256')},
              'scanned_files': counts, 'annual_candidate_rows': len(rows), 'rows': rows}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
