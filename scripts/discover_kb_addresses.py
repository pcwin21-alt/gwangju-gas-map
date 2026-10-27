"""Collect public Onnuri address lists, independent of station coordinates.

The public form's locationType=2 requires all three address components. Never
interpret a province-only blank result as an entire province's merchant list.
Raw query/cache provenance is retained; this script does not publish markers.
"""
import argparse
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from discover_kb_fuel import parse_response, URL
from onnuri_live import KST
from nationwide import valid_coords

OUT=Path(__file__).resolve().parents[1]/'output/alternatives'
AREA_URL='https://card.kbcard.com/BON/API/HBGV0701'


def area_values(data, parent):
    # The response also contains default Gangwon lists; only `area` is selected.
    rows=data['area']
    if not isinstance(rows,list) or not rows:
        raise ValueError('Missing selected address enumeration')
    if any(r.get('KEY1')!=parent or not r.get('VALUE') for r in rows):
        raise ValueError('Address parent mismatch')
    values=[r['VALUE'] for r in rows]
    if len(values)!=len(set(values)):raise ValueError('Duplicate address options')
    return values


def validate_locality(rows, address):
    expected=' '.join(address)
    if any(' '.join(r['content']['address'].split())!=expected for r in rows):
        raise ValueError('Returned locality differs from selected address')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--region',default='전남')
    ap.add_argument('--stamp',default='20261027')
    ap.add_argument('--interval',type=float,default=1.5)
    args=ap.parse_args()
    if args.interval<1.5:raise ValueError('Minimum interval 1.5 seconds')
    directory=OUT/('kb_address_cache_'+args.stamp)/args.region
    directory.mkdir(parents=True,exist_ok=True)
    progress=OUT/('kb_address_progress_'+args.stamp+'.json')
    session=requests.Session();last=0
    def post(url,payload):
        nonlocal last
        time.sleep(max(0,args.interval-(time.monotonic()-last)))
        last=time.monotonic()
        r=session.post(url,data=payload,timeout=(8,30));r.raise_for_status()
        return r
    def write(path,value):
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
    def areas(parent,level):
        payload={'isAjax':'Y','ajaxStep':'area','isNoFrame':'Y','code':parent,
                 'areaNm1':args.region,'level':str(level)}
        if level==3:payload['areaNm2']=parent
        path=directory/('areas_'+hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()[:16]+'.json')
        if path.exists():item=json.loads(path.read_text(encoding='utf-8'))
        else:
            response=post(AREA_URL,payload);data=response.json();area_values(data,parent)
            item={'query':payload,'checked_at':datetime.now(KST).isoformat(timespec='seconds'),'data':data}
            write(path,item)
        if item['query']!=payload:raise ValueError('Area cache mismatch')
        return area_values(item['data'],parent)
    districts=areas(args.region,2)
    if args.region=='전남' and len(districts)!=22:raise ValueError('Expected 22 Jeonnam districts')
    plan=[(args.region,d,t) for d in districts for t in areas(d,3)]
    write(directory/'plan.json',{'region':args.region,'districts':districts,'addresses':plan})
    print('address plan',len(districts),'districts',len(plan),'addresses',flush=True)
    found={};done=[];status='running';error=None
    def save():
        write(progress,{'source_url':URL,'checked_at':datetime.now(KST).isoformat(timespec='seconds'),
              'region':args.region,'scope':'KB_all_listed_address_options_not_all_issuers_or_payment_verification',
              'status':status,'error':error,'planned_queries':len(plan),'completed_queries':len(done),
              'queries':done,'unique_merchants':len(found),'rows':list(found.values())})
    save()
    for address in plan:
        key=hashlib.sha256(json.dumps(address,ensure_ascii=False).encode()).hexdigest()[:16]
        path=directory/(key+'.json')
        try:
            if path.exists():item=json.loads(path.read_text(encoding='utf-8'))
            else:
                rows=[];pages=[];total=None
                for page in range(1,1001):
                    payload={'mainCC':'a','isNoFrame':'Y','situXCdnt':35.309082,'situYCdnt':126.984899,
                             '페이지번호':page,'useCase':'1','locationType':'2','startRow':(page-1)*10,'endRow':page*10,
                             'area1':address[0],'area2':address[1],'area3':address[2],'mmcNm':''}
                    response=post(URL,payload)
                    count,batch=parse_response(response.content.decode('utf-8'),require_coordinates=False)
                    if total is None:total=count
                    if total!=count:raise ValueError('Address count changed during pagination')
                    validate_locality(batch,address);rows.extend(batch)
                    if len(rows)!=len({r['content']['franchiseNo'] for r in rows}):raise ValueError('Repeated merchant page or ID')
                    pages.append({'query':payload,'count':len(batch),'sha256':hashlib.sha256(response.content).hexdigest()})
                    if len(rows)>=total:break
                if len(rows)!=total:raise ValueError('Incomplete address list')
                item={'address':list(address),'status':'complete','total':total,'rows':rows,'pages':pages,
                      'checked_at':datetime.now(KST).isoformat(timespec='seconds'),'source_url':URL}
                write(path,item)
            if item['address']!=list(address) or item['status']!='complete':raise ValueError('Address cache mismatch')
            validate_locality(item['rows'],address)
            if item['total']!=len(item['rows']) or item['total']!=len({r['content']['franchiseNo'] for r in item['rows']}):
                raise ValueError('Address cache count mismatch')
            for r in item['rows']:
                loc=r.get('location',{})
                found[r['content']['franchiseNo']]={**r,'checked_at':item['checked_at'],'query_address':list(address),
                    'coordinate_status':'present_unverified' if valid_coords(loc.get('lat'),loc.get('lng')) else 'unusable'}
            done.append({'address':list(address),'count':item['total'],'checked_at':item['checked_at'],'cache_file':path.name})
            save()
            fuels=[r['content']['title'] for r in item['rows'] if re.search('주유|충전|석유|에너지',r['content']['title']+' '+r['content']['category'])]
            if fuels or len(done)%20==0:print(json.dumps({'done':len(done),'total':len(plan),'address':address,'fuel_candidates':fuels,'unique':len(found)},ensure_ascii=False),flush=True)
        except (requests.RequestException,ValueError,KeyError) as exc:
            status='stopped_error';error={'address':address,'message':str(exc)};save();raise
    status='all_listed_addresses_complete';save();print(status,len(done),len(found),flush=True)


if __name__=='__main__':main()
