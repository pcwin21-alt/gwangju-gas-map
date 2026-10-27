"""Bounded independent fuel-location audit; never promotes Onnuri membership.

Select one dense commercial-index anchor per Jeonnam district. Query gasoline
and LPG in a 5 km circle, retaining raw responses and coordinates. This is NOT
a regional census. Resume from cached completed requests, stop on any failure.
"""
import argparse
import hashlib
import json
import math
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests
from pyproj import CRS, Transformer
from onnuri_live import KST

OUT = Path(__file__).resolve().parents[1] / 'output/alternatives'
PROXY = 'https://k-skill-proxy.nomadamas.org/v1/opinet/around'
OFFICIAL = 'https://www.opinet.co.kr/user/custapi/openApiInfoDtl.do?apiId=3'
# KATEC, not EPSG:5174. Validate against returned stations/independent WGS84
# controls before interpreting a successful but empty response as coverage.
KATEC = CRS.from_proj4('+proj=tmerc +lat_0=38 +lon_0=128 +k=0.9999 '
                     '+x_0=400000 +y_0=600000 +ellps=bessel '
                     '+towgs84=-146.43,507.89,681.46 +units=m +no_defs')
FORWARD = Transformer.from_crs('EPSG:4326', KATEC, always_xy=True)
INVERSE = Transformer.from_crs(KATEC, 'EPSG:4326', always_xy=True)


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))


def point(row):
    return float(row['위도']), float(row['경도'])


def anchors(rows):
    groups = defaultdict(list)
    for row in rows:
        if row['region'] == '전남':
            groups[row['시군구명']].append(row)
    if len(groups) != 22:
        raise ValueError('Expected 22 Jeonnam districts')
    return [(district, max(group, key=lambda r: sum(distance(point(r),point(s)) < 5000 for s in group)))
            for district, group in sorted(groups.items())]


def decode(payload):
    rows = payload['RESULT']['OIL']
    if not isinstance(rows, list):
        raise ValueError('Unexpected Opinet response')
    converted=[]
    for row in rows:
        lon,lat = INVERSE.transform(float(row['GIS_X_COOR']),float(row['GIS_Y_COOR']))
        if not row.get('UNI_ID') or not row.get('OS_NM') or not (32 < lat < 40 and 124 < lon < 132):
            raise ValueError('Invalid fuel identity/coordinate')
        converted.append({**row,'lat':lat,'lng':lon})
    return converted


def gaps(rows, centers, threshold=450):
    if not centers:
        raise ValueError('Completed KB centers required for gap audit')
    result=[]
    for row in rows:
        nearest=min(distance((row['lat'],row['lng']),p) for p in centers)
        if nearest > threshold:
            result.append({**row,'nearest_completed_kb_query_m':round(nearest,1)})
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--stamp', default='20261027')
    ap.add_argument('--interval',type=float,default=3)
    args=ap.parse_args()
    if args.interval < 3: raise ValueError('Minimum interval 3 seconds')
    rows=json.loads((OUT/'vehicle_fuel_index_20261026.json').read_text(encoding='utf-8'))['rows']
    cache=OUT/('opinet_cache_'+args.stamp);cache.mkdir(exist_ok=True)
    report=OUT/('opinet_district_audit_'+args.stamp+'.json')
    found={};queries=[];last=0
    session=requests.Session()
    for district, anchor in anchors(rows):
        lat,lon=point(anchor);x,y=FORWARD.transform(lon,lat)
        for product in ('B027','K015'):
            path=cache/(district+'_'+product+'.json')
            params={'x':x,'y':y,'radius':5000,'prodcd':product,'sort':2}
            if path.exists():
                item=json.loads(path.read_text(encoding='utf-8'))
                if item['params'] != params: raise ValueError('Cache mismatch')
            else:
                time.sleep(max(0,args.interval-(time.monotonic()-last)))
                last=time.monotonic()
                response=session.get(PROXY,params=params,timeout=(8,30));response.raise_for_status()
                data=response.json();decode(data)
                item={'district':district,'anchor':anchor,'params':params,
                      'checked_at':datetime.now(KST).isoformat(timespec='seconds'),
                      'response_sha256':hashlib.sha256(response.content).hexdigest(),'response':data}
                path.write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
            batch=decode(item['response'])
            # Geometric sanity check: retain provider DISTANCE and compare to WGS84.
            if any(abs(distance((lat,lon),(r['lat'],r['lng']))-float(r['DISTANCE']))>100 for r in batch):
                raise ValueError('Coordinate transform/distance mismatch')
            for r in batch:found[r['UNI_ID']]={**r,'checked_at':item['checked_at'],'product':product}
            queries.append({k:item[k] for k in ('district','anchor','params','checked_at','response_sha256')})
            result={'scope':'22_district_dense_anchor_5km_sample_not_census',
                    'source_url':OFFICIAL,'transport_url':PROXY,'queries':queries,'rows':list(found.values()),
                    'status':'complete' if len(queries)==44 else 'partial',
                    'limitations':['Opinet fuel listings do not verify Onnuri membership.',
                                   'One dense anchor per district omits rural and island coverage.']}
            report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(district,product,len(batch),'unique',len(found),flush=True)
    centers=[]
    for path in (OUT/'kb_location_cache/unfiltered/전남').glob('*.json'):
        item=json.loads(path.read_text(encoding='utf-8'))
        if item.get('status')=='complete':centers.append(item['query']['center'])
    candidates=[]
    for row in gaps(list(found.values()), centers):
        path=cache/(row['UNI_ID']+'_detail.json')
        if path.exists():
            detail=json.loads(path.read_text(encoding='utf-8'))
        else:
            time.sleep(max(0,args.interval-(time.monotonic()-last)));last=time.monotonic()
            response=session.get(PROXY.replace('/around','/detail'),params={'id':row['UNI_ID']},timeout=(8,30))
            response.raise_for_status();detail=response.json()
            path.write_text(json.dumps(detail,ensure_ascii=False,indent=2),encoding='utf-8')
        record=detail['RESULT']['OIL']
        if len(record)!=1 or record[0]['UNI_ID']!=row['UNI_ID']:raise ValueError('Detail identity mismatch')
        record=record[0]
        from nationwide import region
        address=record.get('NEW_ADR') or record.get('VAN_ADR')
        if region(address)!='전남':continue
        candidates.append({'상가업소번호':'opinet:'+row['UNI_ID'], '상호명':record['OS_NM'],
                           '도로명주소':address,'상권업종소분류코드':'',
                           '위도':row['lat'],'경도':row['lng'],'region':'전남',
                           'source_url':OFFICIAL,'opinet_record':row,'opinet_detail':record,
                           'scope':'fuel_location_only_not_Onnuri_evidence'})
        print('new query center',record['OS_NM'],row['nearest_completed_kb_query_m'],flush=True)
    (OUT/('opinet_kb_targets_'+args.stamp+'.json')).write_text(json.dumps({
        'scope':'Opinet fuel sites more than 450m from completed KB centers; not guaranteed uncovered',
        'completed_kb_centers':len(centers),'rows':candidates},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
