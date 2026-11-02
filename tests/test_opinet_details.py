import copy
import json
import unittest
from unittest.mock import Mock

from scripts.opinet_details import collect


class Clock:
    def __init__(self): self.value = 1793649600.
    def __call__(self): return self.value
    def sleep(self, seconds): self.value += seconds


class OpinetDetailsTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.targets = [{'id': 'A000000'+str(i), 'region': '전남', 'name': '시험충전소',
                         'independent_source': {'source_url': 'https://www.data.go.kr'}} for i in range(3)]
        self.usage, self.journal, self.saved = {}, {}, []
        self.request = Mock(side_effect=self.response)

    def response(self, *args, **kwargs):
        return Mock(status_code=200, json=lambda: {'RESULT': {'OIL': [{
            'UNI_ID': kwargs['params']['id'], 'OS_NM': '시험충전소',
            'NEW_ADR': '전라남도 여수시 한재로 9', 'TEL': '061-123-4567',
            'LPG_YN': 'Y', 'internal': 'not public', 'certkey': 'test-secret'}]}})

    def checkpoint(self, usage, journal):
        self.saved.append(copy.deepcopy((usage, journal)))

    def execute(self, **kwargs):
        return collect(self.targets, self.usage, self.journal, 'test-secret', self.checkpoint,
                       self.request, clock=self.clock, sleeper=self.clock.sleep, **kwargs)

    def test_three_details_share_budget_and_wait_from_response(self):
        self.assertEqual(self.execute(), 3)
        self.assertEqual(self.usage['attempts'], 3)
        times = [a['reserved_at'] for a in self.journal['attempts']]
        self.assertEqual([t-times[0] for t in times], [0, 180, 360])
        self.assertEqual(self.saved[0][1]['attempts'][0]['status'], 'reserved')
        self.assertEqual(len(self.journal['details']), 3)

    def test_credentials_and_nonpublic_fields_never_persist(self):
        self.execute()
        self.assertNotIn('test-secret', json.dumps(self.saved))
        detail = self.journal['details'][self.targets[0]['id']]
        self.assertEqual(detail['onnuri_membership'], 'not_checked_by_this_source')
        self.assertNotIn('internal', detail['detail'])

    def test_completed_discovery_does_not_restart_when_daily_cap_expires(self):
        self.assertEqual(self.execute(), 3)
        previous = copy.deepcopy(self.journal['details'])
        self.clock.sleep(86401)
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.request.call_count, 3)
        self.assertEqual(self.usage['attempts'], 0)
        self.assertEqual(self.journal['details'], previous)
        self.assertEqual(len(self.journal['attempts']), 3)

    def test_next_day_continues_to_new_ids_without_spending_on_completed_ids(self):
        self.targets.append({'id': 'A0000003', 'region': '전남', 'name': '다음충전소',
                             'independent_source': {'source_url': 'https://www.data.go.kr'}})
        self.assertEqual(self.execute(), 3)
        self.clock.sleep(86401)
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.request.call_count, 4)
        self.assertEqual(self.journal['attempts'][-1]['id'], 'A0000003')
        self.assertEqual(self.usage['attempts'], 1)

    def test_reservation_failure_prevents_transmission(self):
        with self.assertRaises(RuntimeError):
            collect(self.targets, {}, {}, 'test-secret', Mock(side_effect=RuntimeError('push')),
                    self.request, clock=self.clock, sleeper=self.clock.sleep)
        self.request.assert_not_called()

    def test_price_budget_exhaustion_and_rolling_pilot_cap(self):
        self.usage.update(date='2026-11-03', attempts=200)
        self.assertEqual(self.execute(), 0)
        self.request.assert_not_called()
        self.usage['attempts'] = 0
        self.assertEqual(self.execute(), 3)
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.request.call_count, 3)

    def test_auth_failure_stops_without_alternate_parameter_or_retry(self):
        self.request.side_effect = None
        self.request.return_value = Mock(status_code=403)
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.journal['status'], 'needs_review')
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.request.call_count, 1)

    def test_non_jeonnam_anchor_rejected_before_request(self):
        self.targets[0]['region'] = '광주'
        with self.assertRaises(ValueError): self.execute()
        self.request.assert_not_called()

    def test_uncertain_reservation_is_not_retried(self):
        self.journal['attempts'] = [{'id': 'A0000000', 'status': 'reserved', 'reserved_at': self.clock()}]
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.journal['attempts'][0]['status'], 'uncertain')
        self.request.assert_not_called()
