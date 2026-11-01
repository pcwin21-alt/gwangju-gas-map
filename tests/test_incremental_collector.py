import copy
import json
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.incremental_collector import initial_state, run, retry_after, request_for, corroborate, Store, summarize
from scripts.collector_policy import require_managed_collection


class Clock:
    def __init__(self): self.value = 1793592000.0
    def __call__(self): return self.value
    def sleep(self, seconds): self.value += seconds


def response(status=200, total=0, rows=None, headers=None, text=None):
    rows = rows or []
    html = text if text is not None else '총 %s건 <script>var resultJson = %s;</script>' % (total, json.dumps(rows))
    r = Mock(status_code=status, content=html.encode(), text=html, headers=headers or {}, url='https://card.kbcard.com/BON/DVIEW/HBGV0701')
    if status >= 400:
        import requests
        r.raise_for_status.side_effect = requests.HTTPError(str(status))
    return r


def job(i=0, source='kbcard'):
    return {'id': str(i), 'kind': 'kb_search', 'source': source, 'region': '전남',
            'target': {'name': '샘플주유소', 'keyword': '샘플', 'lat': 35.1, 'lng': 126.9}}


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.policy = {'interval_seconds': 120, 'requests_per_run': 5, 'requests_per_24h': 20,
                       'sources': {'kbcard': {'status': 'active'}, 'onnuri': {'status': 'blocked'}}}
        self.clock = Clock(); self.store = Mock(); self.session = Mock()
        self.session.request.return_value = response()

    def state(self, count=8):
        return initial_state({'id': 'test', 'scope': 'test', 'jobs': [job(i) for i in range(count)]}, self.policy)

    def execute(self, state, maximum=5):
        return run(state, self.store, self.policy, self.session, [], {}, clock=self.clock, sleeper=self.clock.sleep, max_requests=maximum)

    def test_five_transmissions_per_run_and_two_minutes_apart(self):
        s=self.state(); self.execute(s)
        self.assertEqual(self.session.request.call_count, 5)
        self.assertEqual([a['at']-s['attempts'][0]['at'] for a in s['attempts']], [0,120,240,360,480])
        for call in self.session.request.call_args_list:
            self.assertFalse(call.kwargs['allow_redirects'])

    def test_completion_and_checkpoint_not_a_requery(self):
        s=self.state(1); self.assertEqual(self.execute(s)['status'], 'complete')
        self.clock.value+=21600; self.execute(s)
        self.assertEqual(self.session.request.call_count,1)

    def test_budget_reservation_failure_sends_nothing(self):
        self.store.save.side_effect=RuntimeError('push failed')
        with self.assertRaises(RuntimeError): self.execute(self.state())
        self.session.request.assert_not_called()

    def test_explicit_block_persists_across_later_runs(self):
        self.session.request.return_value=response(400,text='<h1>Request Blocked</h1>')
        s=self.state(); self.execute(s); self.clock.value+=172800; self.execute(s)
        self.assertEqual(self.session.request.call_count,1)
        self.assertEqual(s['sources']['kbcard']['status'],'blocked')
        self.assertEqual(s['status'],'needs_attention')

    def test_seeded_blocked_source_has_no_request(self):
        s=initial_state({'id':'x','scope':'x','jobs':[job(source='onnuri')]},self.policy)
        self.execute(s); self.session.request.assert_not_called()

    def test_rolling_twenty_request_budget_not_midnight_reset(self):
        s=self.state(30)
        for i in range(20):s['attempts'].append({'source':'kbcard','at':self.clock()-3600+i,'status':'done'})
        self.execute(s); self.session.request.assert_not_called()
        self.clock.value+=86400; self.execute(s,1)
        self.assertEqual(self.session.request.call_count,1)

    def test_uncertain_reserved_request_is_never_blindly_retried(self):
        s=self.state(1);s['attempts']=[{'source':'kbcard','at':self.clock(),'status':'reserved','job_id':'0'}]
        self.execute(s);self.session.request.assert_not_called()
        self.assertEqual(s['attempts'][0]['status'],'uncertain')
        self.assertEqual(s['jobs'][0]['status'],'needs_review')

    def test_retry_after_limits_and_unknown_header_stops(self):
        self.assertEqual(retry_after('300',self.clock()),self.clock()+300)
        self.assertEqual(retry_after('Mon, 02 Nov 2026 12:00:00 GMT',0),1793620800)
        self.assertIsNone(retry_after('nonsense',self.clock()))
        for headers in ({'Retry-After':'3600'},{}):
            self.setUp();self.session.request.return_value=response(429,headers=headers)
            s=self.state(1);self.execute(s)
            self.assertEqual(s['sources']['kbcard']['status'],'cooldown' if headers else 'needs_review')
            self.execute(s);self.assertEqual(self.session.request.call_count,1)

    def test_redirect_and_auth_errors_do_not_retransmit(self):
        for status in (301,401,403):
            self.setUp();self.session.request.return_value=response(status)
            s=self.state(1);self.execute(s)
            self.assertEqual(self.session.request.call_count,1)
            self.assertIn(s['jobs'][0]['status'],('blocked','needs_review'))

    def test_pages_resumed_and_repeated_page_rejected(self):
        b={'location':{},'content':{'franchiseNo':'1','title':'상점','category':'식당','onNuliGb':'1'}}
        self.session.request.return_value=response(total=2,rows=[b])
        s=self.state(1);self.execute(s,1)
        self.assertEqual(s['jobs'][0]['page'],2)
        self.clock.value+=21600;self.execute(s,1)
        self.assertEqual(s['jobs'][0]['status'],'needs_review')
        self.assertEqual(s['evidence'],[])

    def test_absence_does_not_delete_existing_merchant_or_make_nonmembership(self):
        s=self.state(1);self.execute(s)
        self.assertEqual(s['jobs'][0]['result'],'no_match_not_nonmembership')
        self.assertEqual(s['evidence'],[])

    def test_unfinished_municipal_inventory_prevents_false_completion(self):
        s=self.state(0);s['source_gaps']=[{'region':'전남','status':'needs_source_inventory'}]
        self.assertEqual(summarize(s)['status'],'needs_attention')

    def test_snapshot_store_reload_preserves_all_dates_and_block(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(d);s=self.state(1);store.save(s)
            loaded=json.loads((Path(d)/'state.json').read_text(encoding='utf-8'))
            self.assertEqual(loaded,s)

    def test_git_reservation_is_on_remote_before_any_target_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bare=root/'remote.git';checkout=root/'checkout'
            def git(*args):
                return subprocess.check_output(['git',*map(str,args)],stderr=subprocess.DEVNULL,text=True,encoding='utf-8')
            git('init','--bare','--quiet',bare)
            git('init','--quiet','-b','merchant-collector-state',checkout)
            git('-C',checkout,'config','user.name','Collector Test')
            git('-C',checkout,'config','user.email','test@example.invalid')
            git('-C',checkout,'remote','add','origin',bare)
            store=Store(checkout,persist_git=True);s=self.state(1)
            def transmit(*args,**kwargs):
                saved=json.loads(git('--git-dir',bare,'show','refs/heads/merchant-collector-state:state.json'))
                self.assertEqual(saved['attempts'][-1]['status'],'reserved')
                return response()
            self.session.request.side_effect=transmit
            run(s,store,self.policy,self.session,[],{},clock=self.clock,sleeper=self.clock.sleep,max_requests=1)
            saved=json.loads(git('--git-dir',bare,'show','refs/heads/merchant-collector-state:state.json'))
            self.assertEqual(saved['attempts'][-1]['status'],'done')
            self.assertEqual(saved['status'],'complete')

    def test_unknown_download_url_rejected_before_request(self):
        with self.assertRaises(ValueError):request_for({'kind':'annual_download','file_id':'https://invalid','sequence':'1'})
        with self.assertRaises(ValueError):request_for({'kind':'annual_download','file_id':'FILE_123','sequence':'1&x=2'})

    def test_false_fuel_category_or_different_premises_cannot_be_promoted(self):
        root=Path(__file__).resolve().parents[1]
        e=json.loads((root/'output/supplemental_onnuri_evidence.json').read_text(encoding='utf-8'))['rows'][0]
        self.assertIsNotNone(corroborate(e['bank_record'],e['checked_at'],[e['commercial_record']],e['commercial_source']))
        for category in ['식당','가스판매점','차량 정비/부품/인테리어']:
            b=copy.deepcopy(e['bank_record']);b['content']['category']=category
            self.assertIsNone(corroborate(b,e['checked_at'],[e['commercial_record']],e['commercial_source']))

    def test_legacy_entry_never_sends_through_unmanaged_path(self):
        for source in ('onnuri','kbcard'):
            with self.assertRaises(PermissionError):require_managed_collection(source)


if __name__=='__main__':unittest.main()
