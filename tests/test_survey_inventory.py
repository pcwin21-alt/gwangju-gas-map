import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.survey_inventory import (make_inventory, survey_jobs, install_survey, merge_jobs,
                                      map_links, refresh_rechecks, completed_recheck, survey_progress, sync_mapped_inventory)
from scripts.incremental_collector import initial_state, configure_regions, merge_plan, summarize, handle_response
from scripts.publish_collector_results import attach_rechecks, reached_regions
from scripts.supplemental_onnuri import station_from_evidence


class SurveyTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.e = copy.deepcopy(json.loads((root/'output/supplemental_onnuri_evidence.json').read_text(encoding='utf-8'))['rows'][0])
        self.e['checked_at'] = '2026-11-02T01:00:00+09:00'
        self.s = station_from_evidence(self.e, self.e['checked_at'])
        self.area = self.e['commercial_record']['region']
        self.s['region'] = self.area
        self.other = '서울' if self.area != '서울' else '전남'
        self.order = [self.area, self.other]
        self.fuel = {**self.e['commercial_source'], 'rows': [self.e['commercial_record']]}
        self.annual_row = {'가맹점명': self.s['name'], '소속 시장명(또는 상점가)': '검증시장',
                           '소재지': self.area, '취급품목': '주유소', '지류형 가맹 여부': 'Y',
                           '디지털형 가맹 여부': 'Y', '가맹 등록년도': '2025'}
        self.s['verification']['onnuri']['market'] = '검증시장'
        self.annual = {'source_url': 'https://www.data.go.kr/data/3060079/fileData.do',
                       'source_date': '2026-07-31', 'retrieved_at': '2026-10-30T12:00:00+09:00',
                       'sha256': 'baseline', 'total_rows': 225803, 'rows': [self.annual_row]}
        self.policy = {'sources': {'kbcard': {'status': 'active'}, 'onnuri': {'status': 'blocked'}},
                       'region_order': self.order}

    def inventory(self):
        return make_inventory([self.s], self.fuel, self.annual, self.order)

    def state(self):
        inv = self.inventory()
        plan = {'id': 'survey-test', 'scope': 'test', 'jobs': survey_jobs(inv, self.fuel, self.order),
                'survey_inventory': inv, 'source_gaps': []}
        state = initial_state(plan, self.policy)
        configure_regions(state, self.policy)
        merge_plan(state, plan)
        return state, plan

    def test_same_checklist_in_empty_and_nonempty_regions(self):
        inv = self.inventory()
        self.assertEqual([r['region'] for r in inv['regions']], self.order)
        state, _ = self.state()
        for area in self.order:
            self.assertIn('market_coverage', survey_progress(state, area)['missing_standard_checks'])
        self.assertEqual(survey_progress(state, self.other)['mapped_records_to_recheck'], 0)
        self.assertFalse(survey_progress(state, self.other)['standard_checks_complete'])

    def test_combined_region_is_explicitly_ambiguous_not_gwangju_assignment(self):
        self.annual_row['소재지'] = '전남광주'
        inv = make_inventory([], self.fuel, self.annual, ['전남', '광주', '서울'])
        self.assertEqual(inv['annual_candidates'][0]['possible_regions'], ['전남', '광주'])
        self.assertEqual([r['annual_ambiguous_region_rows'] for r in inv['regions']], [1, 1, 0])

    def test_historical_zero_cache_is_not_nonmembership(self):
        inv = make_inventory([self.s], self.fuel, self.annual, self.order,
                             {self.area: {'dated_cache': 1, 'new_query': 0}})
        jobs = survey_jobs(inv, self.fuel, self.order)
        checks = [j for j in jobs if j.get('station_ids')]
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]['target']['keyword'], '')

    def test_install_keeps_existing_failure_pages_budget_and_source_block(self):
        state, plan = self.state()
        job = next(j for j in state['jobs'] if j.get('station_ids'))
        job.update(status='needs_review', page=3, attempts=2)
        state['attempts'] = [{'source': 'kbcard', 'status': 'done', 'at': 1234}]
        previous = copy.deepcopy(state)
        merge_plan(state, plan)
        self.assertEqual(state['attempts'], previous['attempts'])
        self.assertEqual(state['sources'], previous['sources'])
        self.assertEqual(state['jobs'], previous['jobs'])

    def test_query_identity_deduplicates_different_purposes_and_names(self):
        state, _ = self.state()
        job = copy.deepcopy(next(j for j in state['jobs'] if j.get('station_ids')))
        old_count = len(state['jobs'])
        job['target']['name'] = '법인명 별칭'
        job['purpose'] = 'annual_reverse_discovery'
        job['candidate_ids'] = ['discovery-only']
        merge_jobs(state, [job])
        self.assertEqual(len(state['jobs']), old_count)
        self.assertIn('discovery-only', next(j for j in state['jobs'] if j.get('station_ids'))['candidate_ids'])

    def test_old_membership_proof_does_not_satisfy_post_renewal_check(self):
        state, _ = self.state()
        self.e['checked_at'] = '2026-10-25T01:00:00+09:00'
        state['evidence'] = [self.e]
        refresh_rechecks(state)
        self.assertEqual(state['membership_rechecks'], {})

    def test_exact_current_issuer_proof_refreshes_same_premise_only(self):
        state, _ = self.state()
        state['evidence'] = [self.e]
        refresh_rechecks(state)
        check = state['membership_rechecks'][self.s['id']]
        self.assertEqual(check['status'], 'confirmed_in_issuer_scope')
        self.assertEqual(check['other_payment_methods'], 'not_reverified')
        inv = state['survey_inventory']
        for field, value in [('address', '전라남도 다른군 다른로 100'), ('fuel_kind', 'lpg' if self.s['fuel_kind']=='liquid' else 'liquid'), ('lat', self.s['lat']+1)]:
            known = copy.deepcopy(inv['known_stations']);known[0][field] = value
            self.assertEqual(map_links(self.e, known), [])

    def test_current_proof_does_not_rewrite_original_payment_methods_or_check_date(self):
        state, _ = self.state()
        state['evidence'] = [self.e];refresh_rechecks(state)
        state['summary'] = {'active_region': self.area}
        old = copy.deepcopy(self.s)
        out = attach_rechecks([self.s], state)[0]
        self.assertEqual(self.s, old)
        self.assertEqual(out['verification']['onnuri']['checked_at'], old['verification']['onnuri']['checked_at'])
        self.assertEqual(out.get('onnuri_methods'), old.get('onnuri_methods'))
        self.assertEqual(out['verification']['onnuri']['issuer_checks']['kbcard']['other_payment_methods'], 'not_reverified')

    def test_neighbor_proof_does_not_turn_empty_target_into_nonmember_or_confirmed(self):
        state, _ = self.state()
        target = next(j for j in state['jobs'] if j.get('station_ids'))
        different = copy.deepcopy(self.e);different['commercial_record']['도로명주소'] = '전라남도 다른군 다른로 100'
        state['evidence'] = [different]
        completed_recheck(state, target, self.e['checked_at'])
        self.assertEqual(state['membership_rechecks'][self.s['id']]['status'], 'needs_review_not_found')
        self.assertEqual(state['membership_rechecks'][self.s['id']]['nonmembership'], 'not_established')
        self.assertEqual(state['review'][0]['station_id'], self.s['id'])

    def test_unparsed_addresses_cannot_match_each_other_as_null(self):
        state, _ = self.state()
        proof = copy.deepcopy(self.e);proof['commercial_record']['도로명주소'] = '주소 미확인'
        known = copy.deepcopy(state['survey_inventory']['known_stations']);known[0]['address'] = '주소 미확인'
        self.assertEqual(map_links(proof, known), [])

    def test_mere_complete_receipt_cannot_skip_missing_standard_checks(self):
        state, _ = self.state()
        for j in state['jobs']:j['status'] = 'done'
        for area in self.order:
            state['regional_reviews'][area] = {'status': 'complete', 'evidence': ['review'], 'checked_at': '2026-11-02'}
        result = summarize(state)
        self.assertEqual(result['active_region'], self.area)
        self.assertEqual(result['status'], 'needs_attention')
        self.assertTrue(result['counts_are_not_regional_totals'])

    def test_unknown_annual_identity_stays_open_even_with_some_location(self):
        self.annual_row['소속 시장명(또는 상점가)'] = '다른시장'
        state, _ = self.state()
        progress = survey_progress(state, self.area)
        self.assertEqual(progress['unresolved_annual_identities'], 1)
        cid = state['survey_inventory']['annual_candidates'][0]['candidate_id']
        self.assertTrue(any(g.get('candidate_id') == cid for g in state['source_gaps']))
        state['candidate_resolutions'] = {cid: {'status': 'linked', 'evidence': ['independent premise/market review'], 'checked_at': '2026-11-02'}}
        self.assertEqual(survey_progress(state, self.area)['unresolved_annual_identities'], 0)

    def test_current_snapshot_is_not_overwritten_by_bundled_old_snapshot(self):
        state, plan = self.state()
        state['survey_inventory']['annual_source']['retrieved_at'] = '2026-11-02T02:00:00+09:00'
        state['survey_inventory']['annual_source']['sha256'] = 'downloaded'
        merge_plan(state, plan)
        self.assertEqual(state['survey_inventory']['annual_source']['sha256'], 'downloaded')

    def regional_identity_state(self):
        annual = copy.deepcopy(self.annual)
        annual['rows'][0]['소재지'] = '전남광주'
        inv = make_inventory([], {**self.fuel, 'rows': []}, annual, ['전남', '광주'])
        plan = {'id': 'region-test', 'scope': 'test', 'jobs': [], 'survey_inventory': inv, 'source_gaps': []}
        state = initial_state(plan, {**self.policy, 'region_order': ['전남', '광주']})
        configure_regions(state, {**self.policy, 'region_order': ['전남', '광주']})
        merge_plan(state, plan)
        candidate = inv['annual_candidates'][0]
        state['candidate_resolutions'] = {candidate['candidate_id']: {
            'status': 'region_identified', 'source_kind': 'archived_operator_place',
            'annual_row': copy.deepcopy(candidate['row']), 'evidence': ['archived exact name and market'],
            'checked_at': '2026-11-03T17:00:00+09:00', 'source_checked_at': '2026-10-25T10:51:11+09:00',
            'operator_record': {'frCd': 'archived-identity', 'frcsNm': candidate['row']['가맹점명'],
                                'mrktNm': candidate['row']['소속 시장명(또는 상점가)'],
                                'frcsAddr': '광주광역시 북구 검증로 1', 'latitude': 35.17, 'longitude': 126.91}}}
        return state, candidate['candidate_id']

    def test_region_only_identity_removes_wrong_region_gap_but_keeps_home_identity_open(self):
        state, cid = self.regional_identity_state()
        previous = copy.deepcopy(state)
        result = summarize(state)
        jeonnam, gwangju = result['regions']
        self.assertEqual((jeonnam['unresolved_annual_identities'], jeonnam['source_gaps']), (0, 0))
        self.assertEqual((gwangju['unresolved_annual_identities'], gwangju['source_gaps']), (1, 1))
        self.assertEqual(state['candidate_resolutions'][cid]['status'], 'region_identified')
        self.assertFalse(jeonnam['standard_checks_complete'])
        for field in ('survey_inventory', 'source_gaps', 'candidate_resolutions', 'attempts', 'jobs', 'sources'):
            self.assertEqual(state[field], previous[field])

    def test_region_narrowing_requires_exact_annual_premise_market_and_dated_evidence(self):
        state, cid = self.regional_identity_state()
        for field, value in [('evidence', []), ('source_kind', 'keyword_search'),
                             ('checked_at', 'invalid'), ('source_checked_at', '2026-10-25'),
                             ('annual_row', {}), ('operator_record', {})]:
            with self.subTest(field=field):
                changed = copy.deepcopy(state);changed['candidate_resolutions'][cid][field] = value
                self.assertEqual(survey_progress(changed, '전남')['unresolved_annual_identities'], 1)
                self.assertEqual(summarize(changed)['regions'][0]['source_gaps'], 1)
        for field, value in [('frcsNm', '다른사업장'), ('mrktNm', '다른시장'), ('latitude', None), ('frcsAddr', '미확인')]:
            with self.subTest(record_field=field):
                changed = copy.deepcopy(state);changed['candidate_resolutions'][cid]['operator_record'][field] = value
                self.assertEqual(survey_progress(changed, '전남')['unresolved_annual_identities'], 1)

    def test_border_observation_is_not_published_to_unreached_region(self):
        state, _ = self.state();state['summary'] = {'active_region': self.area}
        later = copy.deepcopy(self.s);later['region'] = self.other
        state['membership_rechecks'] = {later['id']: {'status': 'confirmed_in_issuer_scope'}}
        out = attach_rechecks([later], state)[0]
        self.assertNotIn('issuer_checks', out['verification']['onnuri'])
        self.assertEqual(reached_regions(state), {self.area})

    def market_region_state(self):
        state, cid = self.regional_identity_state()
        proof = state['candidate_resolutions'][cid]
        record = proof.pop('operator_record')
        record['frcsNm'] = '다른 상권 입점업소'
        second = {**record, 'frCd': 'second-market-witness', 'frcsAddr': '광주광역시 북구 검증로 2'}
        proof.update(source_kind='archived_operator_market', source_url='https://www.onnuri.gift/place',
                     market_records=[record, second])
        return state, cid

    def test_market_region_evidence_keeps_business_identity_open_and_preserves_inputs(self):
        state, cid = self.market_region_state()
        before = copy.deepcopy(state)
        jeonnam, gwangju = summarize(state)['regions']
        self.assertEqual((jeonnam['unresolved_annual_identities'], jeonnam['source_gaps']), (0, 0))
        self.assertEqual((gwangju['unresolved_annual_identities'], gwangju['source_gaps']), (1, 1))
        self.assertFalse(jeonnam['standard_checks_complete'])
        self.assertEqual(state['candidate_resolutions'][cid]['status'], 'region_identified')
        for field in ('survey_inventory', 'source_gaps', 'candidate_resolutions', 'attempts', 'jobs', 'sources', 'evidence', 'membership_rechecks'):
            self.assertEqual(state[field], before[field])

    def test_market_region_requires_two_distinct_consistent_dated_official_records(self):
        state, cid = self.market_region_state()
        for field, value in [('source_url', 'https://example.test'), ('source_checked_at', '2026-10-25'),
                             ('annual_row', {}), ('evidence', []), ('market_records', [])]:
            with self.subTest(field=field):
                changed = copy.deepcopy(state);changed['candidate_resolutions'][cid][field] = value
                self.assertEqual(survey_progress(changed, '전남')['unresolved_annual_identities'], 1)
        proof = state['candidate_resolutions'][cid]
        variants = [proof['market_records'][:1], [proof['market_records'][0]] * 2]
        for field, value in [('frCd', None), ('mrktNm', '다른시장'), ('latitude', None),
                             ('frcsAddr', '전라남도 나주시 검증로 2'), ('frcsAddr', '광주광역시 북구 검증로 1')]:
            records = copy.deepcopy(proof['market_records']);records[1][field] = value;variants.append(records)
        for records in variants:
            with self.subTest(records=records):
                changed = copy.deepcopy(state);changed['candidate_resolutions'][cid]['market_records'] = records
                self.assertEqual(survey_progress(changed, '전남')['unresolved_annual_identities'], 1)

    def test_neutral_or_conflicting_bank_category_is_retained_as_lead_not_promoted(self):
        for category in ('기타소매업', '근린상권서비스', '식당'):
            state, _ = self.state()
            bank = copy.deepcopy(self.e['bank_record']);bank['content']['category'] = category
            html = '총 1건 <script>var resultJson = '+json.dumps([bank])+';</script>'
            response = Mock(content=html.encode('utf-8'))
            job = next(j for j in state['jobs'] if j.get('station_ids'))
            handle_response(state, job, response, 1793552400, self.fuel['rows'], self.e['commercial_source'])
            self.assertEqual(state['evidence'], [])
            self.assertTrue(any(r.get('independent_fuel_candidate_ids') for r in state['review']))

    def test_new_map_identity_joins_next_run_without_losing_current_snapshot(self):
        state, _ = self.state()
        state['survey_inventory']['annual_source']['sha256'] = 'live-download'
        state['survey_inventory']['annual_source']['retrieved_at'] = '2026-11-02T02:00:00+09:00'
        state['attempts'] = [{'source': 'kbcard', 'at': 100, 'status': 'done'}]
        newer = copy.deepcopy(self.s);newer['id'] = 'new-published-id';newer['name'] += '신규'
        newer['lat'] += 0.05
        sync_mapped_inventory(state, [self.s, newer], self.fuel, self.order)
        self.assertEqual(state['survey_inventory']['annual_source']['sha256'], 'live-download')
        self.assertEqual(len(state['survey_inventory']['known_stations']), 2)
        self.assertTrue(any('new-published-id' in j.get('station_ids', []) for j in state['jobs']))
        count = len(state['jobs'])
        sync_mapped_inventory(state, [self.s, newer], self.fuel, self.order)
        self.assertEqual(len(state['jobs']), count)
        self.assertEqual(state['attempts'], [{'source': 'kbcard', 'at': 100, 'status': 'done'}])


if __name__ == '__main__':
    unittest.main()
