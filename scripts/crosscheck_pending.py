"""Recheck the pending cohort in regional order; evidence only, no promotion."""
import json
import re
from datetime import datetime
from pathlib import Path
import requests
from onnuri_live import search, SOURCE, KST
from nationwide import name_key, region
from live_merchants import address_key
from refresh_regions import ORDER

OUT = Path(__file__).resolve().parents[1] / 'output'
def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))
def main():
    candidates = {r['candidate_id']: r for r in read('merchant_review.json') if r.get('show_pending')}
    registry = read('station_locations.json')['rows'] + read('lpg_locations.json')['rows']
    session = requests.Session()
    session.headers.update({'User-Agent':'Mozilla/5.0','Referer':SOURCE,'Origin':'https://www.onnuri.gift'})
    result = {'checked_at':datetime.now(KST).isoformat(timespec='seconds'), 'status':'in_progress', 'rows':[]}
    def order(r):
        return ORDER.index(r['region']) if r['region'] in ORDER else ORDER.index('광주') + 0.5
    for item in sorted(candidates.values(), key=order):
        name = item['name']
        matches = [r for r in registry if (name_key(r['CONM_NM']) == name_key(name) and region(r.get('LCTN_ROAD_NM')) == item['region']) or (item.get('address') and address_key(r.get('LCTN_ROAD_NM')) == address_key(item['address']))]
        record = {**item, 'registry_candidates':matches, 'queries':[], 'official_matches':[]}
        keyword = re.sub(r'주식회사|유한회사|\(주\)|\(유\)|㈜', '', name).strip()
        try:
            rows, query = search(session, keyword)
            record['queries'].append(query)
            record['same_name_candidates'] = [r for r in rows if name_key(r['frcsNm']) == name_key(name) and (region(r['frcsAddr']) == item['region'] or item['region'] == '지역 미확정')]
            record['official_matches'] = [r for r in record['same_name_candidates'] if name_key(r['mrktNm']) == name_key(item['market'])]
            if not record['official_matches'] and '주유소' in name and 0 < len(matches) <= 3:
                for anchor in matches:
                    nearby, q = search(session, '', center=(anchor['LAT'],anchor['LOT']), radius=2)
                    record['queries'].append(q)
                    record.setdefault('nearby_same_address', []).extend(r for r in nearby if address_key(r['frcsAddr']) == address_key(anchor['LCTN_ROAD_NM']))
            record['result'] = 'needs_vehicle_type' if record['official_matches'] else 'needs_current_membership'
        except (requests.RequestException, ValueError) as exc:
            record['result'] = 'lookup_failed'
            record['error_type'] = type(exc).__name__
        result['rows'].append(record)
        (OUT/'pending_crosscheck_20261025.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(item['region'], name, record['result'], 'registry', len(matches), 'nearby',len(record.get('nearby_same_address',[])),flush=True)
    result['status'] = 'complete'
    (OUT/'pending_crosscheck_20261025.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__ == '__main__':
    main()
