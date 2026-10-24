"""Evidence ledger for the pending annual candidates; never infer membership."""
import json
import re
from datetime import datetime
from pathlib import Path
import requests
from onnuri_live import SOURCE, KST, search
from nationwide import name_key, region, row_id, non_vehicle, reviewed_exclusions
from refresh_regions import ORDER
from live_merchants import classify

OUT = Path(__file__).resolve().parents[1]/'output'

def read(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))

def main():
    baseline = read('candidate_review_baseline_20261024.json')['rows']
    annual = read('onnuri_official_snapshot.json')
    live = read('onnuri_live_snapshot.json')
    registry = read('station_locations.json')['rows'] + read('lpg_locations.json')['rows']
    grouped = {}
    for row in baseline:
        grouped.setdefault(row['candidate_id'], []).append(row)
    def order(pair):
        row = pair[1][0]
        area = row['region']
        if area == '전남광주':
            area = '전남' if row['market'] == '웃장' else '광주'
        return ORDER.index(area)
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': SOURCE, 'Origin': 'https://www.onnuri.gift'})
    result = []
    for cid, entries in sorted(grouped.items(), key=order):
        item = entries[0]
        source = next(r for r in annual['rows'] if row_id(r) == cid)
        record = {**item, 'source_rows': [r['row_number'] for r in entries], 'items': source['취급품목'],
                  'source_date': annual['source_date'], 'sources': [annual['source_url']], 'queries': []}
        if non_vehicle(source):
            record.update(status='excluded_non_vehicle_fuel', reason='공식 품목이 자동차 주유 업종 아님: '+source['취급품목'])
            for exclusion in reviewed_exclusions():
                if all(source.get(k)==v for k,v in exclusion['match'].items()):
                    record.update(reason=exclusion['reason'])
                    record['sources'] += exclusion['sources']
        else:
            def relevant(row):
                return name_key(row['mrktNm']) == name_key(item['market']) and region(row['frcsAddr']) in (
                    ['전남','광주'] if item['region']=='전남광주' else [item['region']])
            matches = [r for r in live['rows'] if relevant(r) and name_key(r['frcsNm'])==name_key(item['name'])]
            if matches:
                record.update(status='needs_vehicle_type', reason='현재 가맹점·주소는 확인되지만 차량 직접 주유·충전 업종 미확인',
                              official_matches=matches, checked_at=live['checked_at'])
            else:
                keyword = re.sub(r'주식회사|유한회사|\(주\)|\(유\)|㈜|\s', '', item['name'])
                stem = re.sub(r'주유소$|에너지산업$|에너지$|종합석유얼음$|석유$', '', keyword)
                candidates = {}
                for word in dict.fromkeys([keyword, stem] if len(stem)>=2 else [keyword]):
                    batch, query = search(session, word)
                    record['queries'].append(query)
                    for row in batch:
                        if relevant(row): candidates[row['frCd']] = row
                # Registry coordinates are search anchors, never evidence that
                # an annual merchant inherits that site's address or membership.
                anchors = [r for r in registry if name_key(r['CONM_NM'])==name_key(item['name']) and
                           region(r.get('LCTN_ROAD_NM')) in (['전남','광주'] if item['region']=='전남광주' else [item['region']])]
                record['registry_name_candidates'] = [{'name':r['CONM_NM'],'address':r['LCTN_ROAD_NM']} for r in anchors]
                # Explicit gas-station names only; generic gas sellers may be
                # unrelated same-name businesses (e.g. 제일가스).
                if '주유소' in item['name'] and len(anchors)<=3:
                    for anchor in anchors:
                        batch, query = search(session, '', center=(anchor['LAT'],anchor['LOT']), radius=2)
                        query['anchor_source'] = 'https://www.data.go.kr/data/15129441/standard.do'
                        query['anchor_address'] = anchor['LCTN_ROAD_NM']
                        record['queries'].append(query)
                        for row in batch:
                            if relevant(row) and ('주유' in row['frcsNm'] or name_key(row['frcsNm'])==name_key(item['name'])):
                                candidates[row['frCd']] = row
                rejected = [r for r in candidates.values() if classify(r, [], {})[0]=='excluded_non_vehicle_fuel']
                record['rejected_name_matches'] = rejected
                candidates = {k:r for k,r in candidates.items() if r not in rejected}
                record.update(status='needs_current_membership' if not candidates else 'needs_identity_review',
                              reason='상호 변형·상점가 대조 후 현행 가맹점 연결 미확인' if not candidates else '추가 검색 후보: 동일 업장 여부 별도 검증 필요',
                              official_matches=list(candidates.values()), checked_at=datetime.now(KST).isoformat(timespec='seconds'))
        result.append(record)
        (OUT/'candidate_review_20261024.json').write_text(json.dumps({'status':'in_progress','rows':result},ensure_ascii=False,indent=2),encoding='utf-8')
        print(item['region'],item['name'],record['status'],flush=True)
    (OUT/'candidate_review_20261024.json').write_text(json.dumps({'status':'complete','checked_at':datetime.now(KST).isoformat(timespec='seconds'),
        'baseline_rows':len(baseline),'unique_candidates':len(grouped),'rows':result},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__ == '__main__':
    main()
