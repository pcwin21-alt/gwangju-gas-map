"""Link pending names to dated official address evidence without promotion."""
import csv
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path
from nationwide import name_key, region
from refresh_regions import ORDER

OUT = Path(__file__).resolve().parents[1] / 'output'


def main():
    folder = OUT / 'alternatives'
    source = json.loads((folder/'paper_merchants_source.json').read_text(encoding='utf-8'))
    raw = (folder/'paper_merchants_20210928.csv').read_bytes()
    if hashlib.sha256(raw).hexdigest() != source['sha256']:
        raise ValueError('Historical source hash mismatch')
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('Unknown source encoding')
    index = defaultdict(list)
    rows = list(csv.DictReader(io.StringIO(content)))
    if len(rows) != source['total_rows']:
        raise ValueError('Historical source count mismatch')
    for row in rows:
        index[name_key(row['점포명'])].append(row)
    pending = {r['candidate_id']:r for r in json.loads((OUT/'merchant_review.json').read_text(encoding='utf-8')) if r.get('show_pending')}
    results = []
    for cid, item in pending.items():
        matches = [r for r in index[name_key(item['name'])] if item['region'] == '지역 미확정' or region(r['주소']) == item['region']]
        if matches:
            results.append({'candidate_id':cid, 'name':item['name'], 'region':item['region'],
                'annual_market':item['market'], 'historical_matches':matches,
                'exact_market_matches':[r for r in matches if name_key(r['시장명']) == name_key(item['market'])],
                'status':'historical_address_evidence_requires_identity_review',
                'current_membership_confirmed':False})
    results.sort(key=lambda r:ORDER.index(r['region']) if r['region'] in ORDER else 1.5)
    result = {**source, 'pending_candidates':len(pending),
        'same_name_region_matches':len(results),
        'same_name_region_exact_market_matches':sum(bool(r['exact_market_matches']) for r in results),
        'scope':'historical_address_links_not_current_payment_verification', 'rows':results}
    path = folder / 'pending_historical_addresses_20261026.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Historical candidate links:',len(results), 'Exact market:',result['same_name_region_exact_market_matches'])


if __name__ == '__main__':
    main()
