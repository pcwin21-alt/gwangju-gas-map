import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from scripts.grid_search import make_plan, check_tile, summarize, augment_snapshot, distance_km


def row(code='a', name='전남주유소', address='전라남도 순천시 중앙로 1'):
    return dict(frCd=code, frcsNm=name, frcsAddr=address, mrktNm='시장', latitude=34.95,
                longitude=127.48, paperYn='Y', cardYn='Y', qrYn='N', placeTypeNm='기타소매업')


class GeographicGrid(unittest.TestCase):
    def test_transient_windows_replace_lock_keeps_previous_file(self):
        from scripts.grid_search import write
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'progress.json'
            path.write_text('previous')
            replace = Path.replace
            attempts = []
            def temporarily_locked(source, target):
                attempts.append(True)
                if len(attempts) == 1:
                    self.assertEqual(path.read_text(),'previous')
                    raise PermissionError('file is temporarily open')
                return replace(source,target)
            with patch.object(Path,'replace',temporarily_locked), patch('scripts.grid_search.time.sleep'):
                write(path,{'status':'complete'})
            self.assertEqual(json.loads(path.read_text()),{'status':'complete'})
            self.assertEqual(len(attempts),2)

    def test_recorded_access_block_prevents_automatic_resume(self):
        from scripts.grid_search import run
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder)
            (cache/'progress.json').write_text(json.dumps({'status':'blocked'}))
            with patch('scripts.grid_search.requests.Session') as session:
                with self.assertRaises(PermissionError):
                    run({},cache)
            session.assert_not_called()

    def test_islands_boundary_edges_and_no_gaps(self):
        from shapely.geometry import Polygon, MultiPolygon, mapping
        mainland = Polygon([(127.45,34.9),(127.5,34.9),(127.5,34.96),(127.45,34.96)])
        island = Polygon([(125.2,34.4),(125.202,34.4),(125.202,34.402),(125.2,34.402)])
        f = {'properties': {'adm_nm': '전남광주통합특별시 신안군 도초면', 'sggnm':'신안군'},
             'geometry': mapping(MultiPolygon([mainland, island]))}
        plan = make_plan([f], '전남')
        self.assertEqual(plan['uncovered_buffered_boundary_m2'], 0)
        for polygon in (mainland, island):
            for lng, lat in polygon.exterior.coords:
                self.assertLess(min(distance_km((lat,lng),t['center']) for t in plan['tiles']), 2)
        with self.assertRaises(ValueError):
            make_plan([f], '전남', spacing=3000)

    def test_wrong_radius_anchor_and_truncation_rejected(self):
        tile = dict(id='1_1', center=[34.95,127.48])
        query = dict(keyword='', radius=2, center=tile['center'], status='complete', expected=1, received=1)
        result = dict(tile_id=tile['id'], query=query, rows=[row()])
        check_tile(tile, result)
        for changes in ({'radius':0}, {'center':[37.5,127]}, {'received':0}):
            with self.assertRaises(ValueError):
                check_tile(tile, dict(result, query=dict(query, **changes)))
        with self.assertRaises(ValueError):
            check_tile(tile, dict(result, rows=[dict(row(), latitude=35.1)]))

    def test_incomplete_coverage_cannot_be_summarized(self):
        with self.assertRaises(ValueError):
            summarize({'tiles':[{'id':'1_1'}]}, {}, [], set())

    def test_partial_audit_keeps_original_plan_and_cannot_be_published(self):
        tile = dict(id='1_1', center=[34.95,127.48], districts=['순천시'])
        plan = dict(tiles=[tile,dict(tile,id='1_2')], region='전남', districts=['순천시'])
        data = dict(tile_id='1_1', checked_at='2026-10-25T11:00:00+09:00', rows=[row()],
                    query=dict(keyword='', radius=2, center=tile['center'], status='complete', expected=1, received=1))
        partial = summarize(plan, {'1_1':data}, [], set(), allow_partial=True)
        self.assertEqual(partial['status'],'partial')
        self.assertEqual(partial['planned_tiles'],2)
        self.assertEqual(partial['remaining_tile_ids'],['1_2'])
        with self.assertRaises(ValueError):
            augment_snapshot(dict(status='complete',queries=[data['query']]),partial)

    def test_unparseable_address_never_matches_missing_registry_key(self):
        tile = dict(id='1_1', center=[34.95,127.48], districts=['순천시'])
        plan = dict(tiles=[tile], region='전남', districts=['순천시'])
        data = dict(tile_id='1_1', checked_at='2026-10-25T11:00:00+09:00',
                    rows=[row(name='황금보석',address='전라남도 순천시 중앙로 지하104')],
                    query=dict(keyword='', radius=2, center=tile['center'], status='complete', expected=1, received=1))
        result = summarize(plan, {'1_1':data}, [], {None})
        self.assertEqual(result['rows'],[])

    def test_merge_does_not_redate_nation_or_remove_missing_places(self):
        base_time = '2026-10-25T09:00:00+09:00'
        grid_time = '2026-10-25T11:00:00+09:00'
        query = dict(status='complete', expected=1, received=1)
        baseline = dict(status='complete', checked_at=base_time, queries=[query],
                        rows=[row('missing'), row('seoul', address='서울특별시 강남구 중앙로 1')])
        grid = dict(status='complete', scope='regional_geographic_grid', region='전남',
                    planned_tiles=1, completed_tiles=1, started_at=grid_time, checked_at=grid_time,
                    raw_unique_regional_merchants=1, plan_sha256='hash',
                    queries=[dict(query, tile_id='1_1', keyword='', radius=2)],
                    rows=[dict(row('new'), _observed_at=grid_time)])
        merged = augment_snapshot(baseline, grid)
        self.assertEqual(merged['checked_at'], base_time)
        self.assertEqual({r['frCd'] for r in merged['rows']}, {'missing','seoul','new'})
        self.assertEqual(next(r for r in merged['rows'] if r['frCd']=='seoul')['_observed_at'], base_time)
        self.assertEqual(next(r for r in merged['rows'] if r['frCd']=='new')['_observed_at'], grid_time)
        with self.assertRaises(ValueError):
            augment_snapshot(baseline, dict(grid, completed_tiles=0))

    def test_keyword_free_scan_finds_generic_legal_name_by_registry_address(self):
        merchant = row(name='주식회사 새로운상사')
        tile = dict(id='1_1', center=[34.95,127.48], districts=['순천시'])
        plan = dict(tiles=[tile], region='전남', districts=['순천시'])
        data = dict(tile_id='1_1', checked_at='2026-10-25T11:00:00+09:00', rows=[merchant],
                    query=dict(keyword='', radius=2, center=tile['center'], status='complete', expected=1, received=1))
        from scripts.live_merchants import address_key
        summary = summarize(plan, {'1_1':data}, [], {address_key(merchant['frcsAddr'])})
        self.assertEqual(summary['rows'][0]['frcsNm'], '주식회사 새로운상사')
        self.assertEqual(summary['rows'][0]['_grid_candidate_basis'], ['fuel_registry_address_requires_identity_review'])

    def test_public_station_retains_its_own_observation_date(self):
        from scripts.live_merchants import prepare
        earlier = '2026-10-25T09:00:00+09:00'
        later = '2026-10-26T11:00:00+09:00'
        snapshot = dict(status='complete', source_url='https://www.onnuri.gift/place', checked_at=earlier,
                        rows=[dict(row(), _observed_at=later), row('old')],
                        queries=[dict(status='complete', expected=2, received=2)])
        selected, *_ = prepare(snapshot, {'rows':[]}, [], [])
        dates = {r['frCd']:r['_verification']['checked_at'] for r in selected}
        self.assertEqual(dates, {'a':later, 'old':earlier})
