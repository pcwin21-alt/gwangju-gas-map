import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.collector_limits import limits, observe
from scripts.incremental_collector import initial_state, run
from tests.test_incremental_collector import Clock, response, job


class LimitsTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((Path(__file__).resolve().parents[1]/'config/collector-policy.json').read_text(encoding='utf-8'))
        self.clock = Clock()
        self.state = initial_state({'id': 'ramp', 'scope': 'test', 'jobs': [job(i) for i in range(50)]}, self.policy)
        self.policy.pop('region_order', None)
        self.store = Mock();self.session = Mock()
        self.session.request.return_value = response()

    def quota(self):
        return limits(self.state, self.policy, 'kbcard', self.clock())

    def execute(self, maximum=4):
        return run(self.state, self.store, self.policy, self.session, [], {},
                   clock=self.clock, sleeper=self.clock.sleep, max_requests=maximum)

    def clean_sample(self, count=24):
        self.quota()
        for i in range(count):
            self.state['attempts'].append({'source': 'kbcard', 'at': self.clock()+i,
                                           'status': 'done', 'network_duration_seconds': 3})

    def test_pilot_is_three_requests_three_minutes_apart(self):
        self.execute(100)
        self.assertEqual(self.session.request.call_count, 3)
        self.assertEqual([a['at']-self.state['attempts'][0]['at'] for a in self.state['attempts']], [0, 180, 360])
        self.assertEqual(self.quota()['requests_per_24h'], 24)

    def test_existing_requests_count_against_new_budget(self):
        self.state['attempts'] = [{'source': 'kbcard', 'at': self.clock()-100, 'status': 'done'} for _ in range(24)]
        self.execute()
        self.session.request.assert_not_called()

    def test_time_without_valid_samples_cannot_promote(self):
        self.quota();self.clock.value += 172800
        self.assertEqual(self.quota()['stage'], 'pilot')
        self.clean_sample(23)
        self.assertEqual(self.quota()['stage'], 'pilot')

    def test_samples_without_forty_eight_hours_cannot_promote(self):
        self.clean_sample();self.clock.value += 172799
        self.assertEqual(self.quota()['stage'], 'pilot')

    def test_old_samples_after_long_idle_cannot_promote(self):
        self.clean_sample();self.clock.value += 172800+86400
        self.assertEqual(self.quota()['stage'], 'pilot')

    def test_promotion_has_fixed_ceiling_of_thirty_two_and_four_per_run(self):
        self.clean_sample();self.clock.value += 172800
        self.assertEqual((self.quota()['stage'], self.quota()['requests_per_24h']), ('promoted', 32))
        self.execute(100)
        self.assertEqual(self.session.request.call_count, 4)
        self.clock.value += 172800*10
        self.assertEqual(self.quota()['requests_per_24h'], 32)

    def test_rate_limit_backs_off_without_resetting_history(self):
        self.session.request.return_value = response(429, headers={'Retry-After': '3600'})
        self.execute()
        self.assertEqual(self.quota()['stage'], 'backoff')
        self.assertEqual(self.quota()['requests_per_24h'], 12)
        self.assertEqual(self.state['sources']['kbcard']['status'], 'cooldown')
        self.assertEqual(len(self.state['attempts']), 1)
        self.assertGreaterEqual(self.state['sources']['kbcard']['next_allowed_at'], self.clock()+3600)

    def test_explicit_block_stays_stopped_even_with_old_clean_samples(self):
        self.clean_sample();self.clock.value += 172800
        self.session.request.return_value = response(403)
        self.execute()
        self.clock.value += 86400*10
        self.execute()
        self.assertEqual(self.session.request.call_count, 1)
        self.assertEqual(self.quota()['stage'], 'stopped')
        self.assertEqual(self.state['sources']['kbcard']['status'], 'blocked')

    def test_http_200_with_invalid_contract_is_not_a_clean_sample(self):
        self.session.request.return_value = response(text='<html>unexpected</html>')
        self.execute()
        self.assertEqual(self.state['attempts'][0]['health_signal'], 'needs_review')
        self.assertEqual(self.state['sources']['kbcard']['status'], 'needs_review')
        self.assertEqual(self.quota()['stage'], 'stopped')

    def test_transient_failure_keeps_six_hour_cooldown_and_reduces_budget(self):
        self.session.request.return_value = response(503)
        self.execute()
        self.assertEqual(self.quota()['stage'], 'backoff')
        self.assertGreaterEqual(self.state['sources']['kbcard']['next_allowed_at'], self.clock()+21600)

    def test_repeated_slow_responses_reduce_budget_and_block_promotion(self):
        self.quota()
        for i in range(5):
            self.state['attempts'].append({'source': 'kbcard', 'at': self.clock()+i, 'status': 'done', 'network_duration_seconds': 3})
        for i in range(2):
            a = {'source': 'kbcard', 'at': self.clock(), 'status': 'done', 'network_duration_seconds': 35}
            self.state['attempts'].append(a)
            observe(self.state, self.policy, 'kbcard', a, self.clock())
        self.assertEqual(self.quota()['stage'], 'backoff')
        self.assertEqual(self.quota()['interval_seconds'], 300)

    def test_backoff_recovers_to_pilot_before_promotion(self):
        self.quota()
        observe(self.state, self.policy, 'kbcard', {'status': 'transient_error'}, self.clock())
        self.clean_sample(12);self.clock.value += 172800
        self.assertEqual(self.quota()['stage'], 'pilot')
        self.assertEqual(self.quota()['requests_per_24h'], 24)
        self.assertNotEqual(self.quota()['stage'], 'promoted')

    def test_download_source_retains_its_twenty_request_limit(self):
        q = limits(self.state, self.policy, 'datagov', self.clock())
        self.assertEqual(q['requests_per_24h'], 20)
        self.assertEqual(q['stage'], 'fixed')

    def test_cold_restart_keeps_pilot_start_and_budget_reservations(self):
        self.execute(1)
        before = copy.deepcopy(self.state)
        self.state = json.loads(json.dumps(self.state))
        self.assertEqual(self.quota()['clean_since'], before['sources']['kbcard']['volume_ramp']['clean_since'])
        self.assertEqual(self.state['attempts'], before['attempts'])


if __name__ == '__main__':
    unittest.main()
