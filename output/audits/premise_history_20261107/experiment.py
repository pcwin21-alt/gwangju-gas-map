"""Offline test of a dated premises history lead. No source calls or state writes."""
import datetime
import gzip
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCHIVE = ROOT / 'output/audits/full_region_crosscheck_20261103'


def load(name):
    path = ARCHIVE / name
    data = path.read_bytes()
    return json.loads(gzip.decompress(data)), {
        'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(data).hexdigest(),
    }


def name_key(value):
    return re.sub(r'\s+', '', re.sub(r'^\s*(\(주\)|㈜|주식회사)\s*', '', value or ''))


def phone_key(value):
    return re.sub(r'\D', '', value or '')


def address_key(value):
    match = re.search(r'(담양군\s+담양읍)\s+(\S+)\s+(\d+(?:-\d+)?)(?=$|\s|[,(])', value or '')
    return tuple(re.sub(r'\s+', '', part) for part in match.groups()) if match else None


def main():
    physical, physical_input = load('physical_fuel_records.json.gz')
    issuer, issuer_input = load('issuer_latest_by_id.json.gz')
    county = [r for r in physical if '담양군' in r.get('address', '')]
    candidate_names = {'백동산업', '백동주유소', '백동'}
    address = '담양군 담양읍 무정로 35'
    candidate_phones = {'0613832115', '0613818878'}
    tests = {
        'historical_name': [r['source_id'] for r in county if name_key(r.get('name')) in candidate_names],
        'exact_road_address': [r['source_id'] for r in county if address_key(r.get('address')) == address_key(address)],
        'historical_or_archived_issuer_phone': [r['source_id'] for r in county if phone_key(r.get('phone')) in candidate_phones],
    }
    controls = []
    for name, road in [('대나무주유소', '죽향대로 1179'), ('남문주유소', '죽향대로 1102')]:
        addr = '담양군 담양읍 ' + road
        matched = [r['source_id'] for r in county if name_key(r['name']) == name and address_key(r['address']) == address_key(addr)]
        assert matched, f'Expected physical inventory control absent: {name}'
        controls.append({'name': name, 'address': addr, 'source_rows': matched})
    assert address_key(address) != address_key('담양군 담양읍 무정로 350')

    pairs = [r for r in issuer if r['content'].get('franchiseNo') in {'000000094538059', '000000099830408'}]
    assert len(pairs) == 2 and len({r['content']['franchiseNo'] for r in pairs}) == 2
    assert len({r['checked_at'] for r in pairs}) == 1
    assert len({phone_key(r['content']['tel']) for r in pairs}) == 1
    assert pairs[0]['location'] == pairs[1]['location']
    records = [{'id': r['content']['franchiseNo'], 'title': r['content']['title'],
                'category': r['content']['category'], 'observed_at': r['checked_at'],
                'location': r['location']} for r in pairs]
    report = {
        'reviewed_at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec='seconds'),
        'region': '전남', 'base_main': '5320a90', 'collector_state': 'ad0b62dfd33626bcc174bc9c7e6ad3ab7c7c3c13',
        'method': 'historical_premise_timeline_with_distinct_operator_checks',
        'candidate': {'name': '(주)백동산업', 'historical_address_lead': address, 'status': 'hold_conflicting_current_business'},
        'primary_history_access': [
            {'url': 'https://www.damyang.go.kr/board/getFile?boardId=BBS_0000283&fileSid=208856&isInline=true',
             'result': 'Damyang fuel registration procedure; no named operator-change record located.'},
            {'url': 'https://www.kpetro.or.kr/download.do?uuid=aa7e8a1c-96c7-4a34-86b2-759fd64aec68.pdf',
             'result': 'Public records index lists a nonpublic change-registration document; not a record for this facility.'},
        ],
        'secondary_leads': [
            {'url': 'https://dreamermemory.tistory.com/271', 'page_updated': '2022-08-15',
             'reported': '(주)백동산업 fuel listing at 무정로 35, phone 061-383-2115',
             'limit': 'Reposted directory; page update does not date the underlying business observation.'},
            {'url': 'https://bizno.net/article/1292617097', 'reported_closed_on': '2019-06-30',
             'reported': '백동주유소 old sole-proprietor listing with masked address and phone',
             'limit': 'Secondary closure lead. Cannot identify this permit or apply closure to the later company or premise.'},
            {'url': 'https://www.saramin.co.kr/zf_user/company-info/view/csn/ZFFVSWxXdm5YNVRzYlE0THZ4ZVdodz09/company_nm/%28%EC%A3%BC%29%EB%B0%B1%EB%8F%99',
             'reported': 'Later corporate profile for (주)백동 lists building materials and vehicle fuel among business lines at 무정로 35',
             'limit': 'Declared business lines are not active station permission or payment terminal evidence.'},
        ],
        'inputs': [physical_input, issuer_input],
        'counts': {'jeonnam_physical_rows_loaded': len(physical), 'damyang_physical_rows_compared': len(county),
                   'historical_candidates_tested': 1, 'positive_control_premises': len(controls),
                   'archived_issuer_records_compared': len(records), 'live_merchant_source_requests': 0,
                   'new_fuel_identities_resolved': 0, 'new_memberships': 0, 'existing_fresh_rechecks': 0,
                   'map_additions': 0, 'deployments': 0},
        'candidate_matches': tests, 'controls': controls, 'issuer_pair': records,
        'issuer_pair_has_same_observation_time_phone_and_coordinate': True,
        'decision': 'Keep review open. The archived fuel and hardware IDs are separate, and no dated permit ties a current vehicle-fuel operation to either terminal.',
        'next_pilot': 'Look for a recent Jeonnam municipal fleet fuel contract that specifies the actual filling premise, not just a vendor headquarters. Use it only as independent fuel-identity evidence.',
    }
    (HERE / 'findings.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'counts': report['counts'], 'matches': tests, 'controls': controls}, ensure_ascii=False))


if __name__ == '__main__':
    main()
