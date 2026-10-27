import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_opinet_gaps import decode, distance, gaps


class OpinetAuditTests(unittest.TestCase):
    def test_katec_against_independent_commercial_station_coordinate(self):
        # Opinet A0019816; commercial MA010120220807533538, same name/address.
        rows=decode({'RESULT':{'OIL':[{'UNI_ID':'A0019816','OS_NM':'대나무주유소',
                                     'GIS_X_COOR':307543.06530,'GIS_Y_COOR':301810.61190}]}})
        self.assertLess(distance((rows[0]['lat'],rows[0]['lng']),
                                 (35.3111671969697,126.981196649484)),30)

    def test_invalid_coordinate_does_not_become_empty_success(self):
        with self.assertRaises(ValueError):
            decode({'RESULT':{'OIL':[{'UNI_ID':'x','OS_NM':'x','GIS_X_COOR':0,'GIS_Y_COOR':0}]}})

    def test_missing_completed_queries_cannot_claim_uncovered(self):
        with self.assertRaises(ValueError):gaps([],[])

    def test_station_already_near_completed_query_is_not_new_gap(self):
        rows=[{'lat':35,'lng':127,'UNI_ID':'same'},
              {'lat':35.01,'lng':127,'UNI_ID':'gap'}]
        self.assertEqual([r['UNI_ID'] for r in gaps(rows,[(35,127)])],['gap'])
