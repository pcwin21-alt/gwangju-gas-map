import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from discover_kb_regions import jobs,wait_existing


class QueueTests(unittest.TestCase):
    def test_jeonnam_gap_precedes_other_regions_and_seoul_last(self):
        plan=jobs(Path('out'),'20261026',Path('first.json'),Path('gaps.json'))
        self.assertEqual([(j['region'],j['kind']) for j in plan[:3]],
                         [('전남','fuel_index'),('전남','municipal_address_gap'),('광주','fuel_index')])
        self.assertEqual(plan[-1]['region'],'서울')
        self.assertEqual(len({j['region'] for j in plan}),17)

    def test_failed_current_scan_does_not_advance_regions(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'progress.json'
            p.write_text(json.dumps({'status':'stopped_error','error':'HTTP 504'}))
            with self.assertRaises(RuntimeError):wait_existing(p)
            p.write_text(json.dumps({'status':'candidate_queue_complete','completed_queries':902}))
            self.assertEqual(wait_existing(p)['completed_queries'],902)
