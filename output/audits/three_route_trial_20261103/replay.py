"""Reproduce the three-route trial using public, dated local inputs; no network."""
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.crosscheck_full_region import phone_key

OUT = Path(__file__).resolve().parent
BASE = ROOT / 'output/audits/full_region_crosscheck_20261103'


def read(path):
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding='utf-8'))


def ref(path):
    return {'file': path.relative_to(ROOT).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


bank = read(BASE / 'issuer_address_snapshot.json.gz')
assert bank['unique_merchants'] == len(bank['rows']) == 11385
assert bank['status'] == 'all_listed_addresses_complete'
annual = read(BASE / 'annual_region_unresolved.json.gz')
physical = read(BASE / 'physical_fuel_records.json.gz')
details_path = ROOT / 'output/opinet_discovery_details.json'
details = read(details_path)
phone_results = []
for station_id, row in details['details'].items():
    telephone = phone_key(row['detail'].get('TEL'))
    hits = [b for b in bank['rows'] if telephone and phone_key(b['content'].get('tel')) == telephone]
    phone_results.append({'opinet_id': station_id, 'name': row['detail']['OS_NM'],
                          'address': row['detail'].get('NEW_ADR'), 'phone': row['detail'].get('TEL'),
                          'checked_at': row['checked_at'], 'issuer_phone_hits': hits,
                          'decision': 'identity_review_required' if hits else 'no_full_phone_match_in_dated_KB_snapshot',
                          'membership': 'not_verified_by_Opinet_or_empty_join'})

notice_base = 'https://www.mokpo.go.kr/www/mokpo_news/notification/public_notice?mode=view&idx='
markets = [
    ('하당푸른솔', '비파로 4', 136, '2026-08-31', '55083'),
    ('당가두로', '당가두로 24', 102, '2026-08-31', '55083'),
    ('목포평화통일원형로', '원형동로 10', 200, '2026-08-31', '55083'),
    ('텃골로십일자', '텃골로13번길 76', 53, '2026-09-16', '55187'),
    ('비치앤팔레스', '청호로 206', 34, '2026-09-16', '55187'),
    ('비파', '백년대로337번길 25', 203, '2026-09-16', '55187'),
    ('옥암번영', '옥암로 18', 270, '2026-09-16', '55187'),
    ('금호사랑', '백년대로375번길 29-1', 208, '2026-09-16', '55187'),
]
market_results = []
for name, address, shops, registered, idx in markets:
    matches = [r for r in annual if name in r['소속 시장명(또는 상점가)']]
    market_results.append({'market': name, 'anchor_address': '목포시 ' + address,
                           'registered_at': registered, 'notice_url': notice_base + idx,
                           'shops_in_notice_not_Onnuri_or_fuel_count': shops,
                           'change': 'expanded_from_70_shops' if name == '금호사랑' else 'new',
                           'annual_market_name_matches': len(matches),
                           'boundary': 'anchor_and_area_only_no_polygon_or_parcel_list',
                           'shop_member_inventory': 'not_in_attachment',
                           'status': 'pending_boundary_members_and_membership_crosscheck'})
mokpo = [r for r in physical if '목포시' in r['address']]
roads = ['비파로', '당가두로', '원형동로', '텃골로', '청호로', '백년대로', '옥암로']
road_leads = [r for r in mokpo if any(road in r['address'] for road in roads)]
report = {
    'checked_at': datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds'),
    'region': '전남', 'scope': 'bounded three-route discovery trial, not provincial census',
    'inputs': [ref(BASE / name) for name in ['issuer_address_snapshot.json.gz',
               'annual_region_unresolved.json.gz', 'physical_fuel_records.json.gz']] + [ref(details_path)],
    'opinet': {'run': 'https://github.com/pcwin21-alt/gwangju-gas-map/actions/runs/41529851826',
               'shared_price_collector_budget': True, 'max_calls_rolling_24h': 3,
               'interval_seconds': 180, 'attempts': details['attempts'],
               'results': phone_results, 'bank_snapshot_at': bank['checked_at'],
               'bank_scope': bank['scope'], 'full_phone_field': 'content.tel',
               'snapshot_ids_compared_per_station': 11385},
    'new_market_scope': {'press_url': 'https://www.mokpo.go.kr/www/mokpo_news/press_release/report_material?idx=548867&mode=view',
                         'press_date': '2026-09-22', 'annual_cutoff': '2026-07-31',
                         'markets': market_results, 'new_markets': 7,
                         'new_market_shops': 998, 'expansion_extra_shops': 138,
                         'mokpo_physical_raw_rows_reviewed': len(mokpo),
                         'same_road_raw_rows': len(road_leads), 'same_road_leads': road_leads,
                         'same_road_is_not_boundary_inclusion_or_membership': True,
                         'attachments': read(OUT / 'mokpo_attachment_sources.json')},
    'paper_qr': {'status': 'attempted_no_new_current_primary_membership_proof',
                 'sources': [
                     {'url': 'https://economypub.tistory.com/26', 'published_at': '2025-06-13',
                      'leads': ['현대주유소 순천 중앙로172', '호남주유소 순천 팔마로9', '순천주유소 강남로45'],
                      'decision': 'already_mapped_secondary_claim_no_current_reconfirmation'},
                     {'url': 'https://infospot2.anyddingyouneed.com/2026/03/2026-Onnuri-Gift-Certificate-Gas-Station-Discount.html',
                      'leads': ['부원주유소 담양 죽녹원로199'],
                      'decision': 'already_mapped_secondary_QR_claim_not_payment_evidence'},
                     {'url': 'https://www.dealbada.com/bbs/board.php?bo_table=gal_free&wr_id=64598',
                      'decision': 'same_Buwon_list_not_independent_confirmation'},
                     {'url': 'https://emarryeight.tistory.com/entry/전남전북충남충북대구세종-온누리상품권-주유소-가능한-곳│종이-및-모바일-온누리상품권-사용처-주유소',
                      'published_at': '2025-09-09',
                      'paper_leads': ['해제주유소 무안 신정리18-4', '동부주유소 무안 현해로1441',
                                      '순천주유소 강남로45', '현대주유소 중앙로172', '호남주유소 팔마로9'],
                      'decision': 'three_already_mapped_two_historical_Muan_leads_already_in_review_not_new',
                      'primary_receipt_or_business_announcement': False},
                 ], 'never_refresh_paper_QR_or_operator_dates_from_secondary_lists': True,
                 'no_blocked_endpoint_or_Naver_proxy_retry': True},
    'map_new_additions': 0, 'jeonnam_mapped_count': 28,
    'map_or_payment_dates_changed': False,
    'remaining': ['new-market precise boundaries and member inventories',
                  'current issuer/operator evidence for any independent identity match',
                  'current primary paper/QR evidence beyond recycled lists'],
}
(OUT / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'opinet_details': len(phone_results),
                  'phone_hits': sum(len(r['issuer_phone_hits']) for r in phone_results),
                  'new_markets_missing_from_annual': sum(r['change'] == 'new' and not r['annual_market_name_matches'] for r in market_results),
                  'mokpo_physical_raw_rows': len(mokpo), 'same_road_raw_rows': len(road_leads),
                  'map_additions': 0}, ensure_ascii=False))
