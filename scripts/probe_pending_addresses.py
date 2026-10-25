"""Probe commercial-registry addresses for pending aliases; never promote rows."""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import requests
from onnuri_live import KST, SOURCE, search
from live_merchants import address_key
from refresh_regions import ORDER

OUT = Path(__file__).resolve().parents[1] / 'output'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('archive')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    destination = Path(args.output)
    if destination.exists():
        raise FileExistsError(destination)
    audit = json.loads((OUT / 'pending_commercial_crosscheck_20261025.json').read_text(encoding='utf-8'))
    pending = {r['candidate_id']: r for r in json.loads((OUT / 'merchant_review.json').read_text(encoding='utf-8')) if r.get('show_pending')}
    records = [{**r, 'commercial_matches': [m for m in r['commercial_matches'] if m['상권업종소분류명'] in
                ('주유소', '가스 충전소', '가정용 연료 소매업')]} for r in audit['rows'] if r['candidate_id'] in pending]
    records.sort(key=lambda r: ORDER.index(r['region']) if r['region'] in ORDER else 1.5)
    wanted = {m['상가업소번호']: m for r in records for m in r['commercial_matches']}
    archive = Path(args.archive)
    with archive.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    if digest != audit['archive_sha256']:
        raise ValueError('Archive is not the previously reviewed official source')
    with zipfile.ZipFile(archive, metadata_encoding='cp949') as z:
        for name in z.namelist():
            if not name.endswith('.csv'):
                continue
            for raw in csv.DictReader(io.TextIOWrapper(z.open(name), encoding='utf-8-sig')):
                match = wanted.get(raw['상가업소번호'])
                if match is not None:
                    assert raw['상호명'] == match['상호명'] and raw['도로명주소'] == match['도로명주소']
                    match.update(latitude=float(raw['위도']), longitude=float(raw['경도']))
    result = {'status': 'in_progress', 'source_url': audit['source_url'], 'source_date': audit['source_date'],
              'archive_sha256': digest, 'scope': 'commercial_address_anchors_not_verified_merchant_identity', 'rows': []}
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': SOURCE, 'Origin': 'https://www.onnuri.gift'})
    cache = {}
    for record in records:
        entry = {k: record[k] for k in ('candidate_id', 'region', 'name', 'market')}
        entry['probes'] = []
        for anchor in record['commercial_matches']:
            if not 33 <= anchor['latitude'] <= 39 or not 124 <= anchor['longitude'] <= 132:
                raise ValueError('Invalid public registry anchor')
            key = (anchor['latitude'], anchor['longitude'])
            if key not in cache:
                batch, query = search(session, '', center=key, radius=2)
                cache[key] = batch, query
            batch, query = cache[key]
            exact = [r for r in batch if address_key(r['frcsAddr']) == address_key(anchor['도로명주소'])]
            fuel = [r for r in batch if re.search(r'주유소|충전소|에너지|석유|엘피지|lpg', r['frcsNm'], re.I)]
            entry['probes'].append({'anchor': anchor, 'query': query, 'same_address': exact, 'nearby_fuel_names': fuel})
        entry['checked_at'] = datetime.now(KST).isoformat(timespec='seconds')
        result['rows'].append(entry)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(entry['region'], entry['name'], 'anchors', len(entry['probes']),
              'same_address', [(x['frcsNm'], x['frcsAddr']) for p in entry['probes'] for x in p['same_address']], flush=True)
    result.update(status='complete', checked_at=datetime.now(KST).isoformat(timespec='seconds'), unique_queries=len(cache))
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
