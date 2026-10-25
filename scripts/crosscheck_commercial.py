"""Extract public commercial-registry matches for pending merchants (no promotion)."""
import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from nationwide import name_key, region
from live_merchants import address_key
from refresh_regions import ORDER
from onnuri_live import KST

OUT = Path(__file__).resolve().parents[1] / 'output'
FIELDS = ('상가업소번호','상호명','지점명','상권업종소분류코드','상권업종소분류명',
          '표준산업분류코드','표준산업분류명','시도명','시군구명','도로명주소','지번주소')

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('archive')
    parser.add_argument('--output', required=True, help='New raw comparison JSON; never overwrite a reviewed audit')
    args = parser.parse_args()
    destination = Path(args.output)
    if destination.exists():
        raise FileExistsError(destination)
    pending = {r['candidate_id']:r for r in json.loads((OUT/'merchant_review.json').read_text(encoding='utf-8')) if r.get('show_pending')}
    def order(r):
        return ORDER.index(r['region']) if r['region'] in ORDER else 1.5
    records = [{**r, 'commercial_matches':[]} for r in sorted(pending.values(),key=order)]
    by_name, by_address = {}, {}
    for r in records:
        by_name.setdefault(name_key(r['name']),[]).append(r)
        if r.get('address'):
            by_address.setdefault(address_key(r['address']),[]).append(r)
    archive = Path(args.archive)
    with archive.open('rb') as file:
        digest = hashlib.file_digest(file,'sha256').hexdigest()
    counts = {}
    with zipfile.ZipFile(archive, metadata_encoding='cp949') as z:
        names = [n for n in z.namelist() if n.lower().endswith('.csv')]
        expected = (set(ORDER) - {'전남', '광주'}) | {'전남광주'}
        if len(names) != len(expected) or {n.split('_')[-2] for n in names} != expected:
            raise ValueError('Expected all regional CSVs, with Jeonnam/Gwangju combined')
        names.sort(key=lambda n: ORDER.index('전남' if n.split('_')[-2] == '전남광주' else n.split('_')[-2]))
        for n in names:
            reader = csv.DictReader(io.TextIOWrapper(z.open(n),encoding='utf-8-sig'))
            if not set(FIELDS).issubset(reader.fieldnames):
                raise ValueError('Commercial registry schema changed')
            count=0
            for raw in reader:
                count+=1
                targets = by_name.get(name_key(raw['상호명']),[]) + by_address.get(address_key(raw['도로명주소']),[])
                for r in {x['candidate_id']:x for x in targets}.values():
                    if r['region'] != '지역 미확정' and region(raw['도로명주소']) != r['region']:
                        continue
                    r['commercial_matches'].append({k:raw[k] for k in FIELDS})
            counts[n]=count
            print(n,count,flush=True)
    result={'source_url':'https://www.data.go.kr/data/15083033/fileData.do',
            'source_date':'2026-06-30','checked_at':datetime.now(KST).isoformat(timespec='seconds'),
            'archive_sha256':digest,'scanned_files':counts,'rows':records,
            'scope':'industry_and_identity_candidates_only_not_Onnuri_membership'}
    with destination.open('x', encoding='utf-8') as result_file:
        result_file.write(json.dumps(result,ensure_ascii=False,indent=2))
    for r in records:
        print(r['region'],r['name'],[(m['상호명'],m['상권업종소분류명'],m['도로명주소']) for m in r['commercial_matches']],flush=True)

if __name__ == '__main__':
    main()
