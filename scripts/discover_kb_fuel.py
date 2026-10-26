"""Public KB Onnuri lookup using actual public business coordinates.

Mirrors the public HBGV0701 name-search form. No login or browser session.
This audits candidate locations, not complete regional coverage or payment success.
"""
import argparse
import hashlib
import json
import re
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import requests
from nationwide import name_key, region
from onnuri_live import KST
from refresh_regions import ORDER

OUT = Path(__file__).resolve().parents[1] / 'output'
URL = 'https://card.kbcard.com/BON/DVIEW/HBGV0701'


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data.strip())


def parse_response(html):
    match = re.search(r'var resultJson\s*=\s*(\[.*?\]);', html, re.S)
    if not match:
        raise ValueError('Public merchant result missing')
    rows = json.loads(match.group(1))
    text=VisibleText();text.feed(html)
    label=' '.join(p for p in text.parts if p)
    count = re.search(r'총\s*([\d,]+)건', label)
    if not count:
        raise ValueError('Result count missing')
    total = int(count.group(1).replace(',', ''))
    for row in rows:
        c = row['content']
        if c.get('onNuliGb') != '1' or not c.get('franchiseNo') or not c.get('title'):
            raise ValueError('Result is not an explicit Onnuri merchant')
        lat, lng = float(row['location']['lat']), float(row['location']['lng'])
        if not (32 < lat < 40 and 124 < lng < 132):
            raise ValueError('Invalid merchant coordinate')
    if len(rows) > total or (total and not rows):
        raise ValueError('Inconsistent result count')
    return total, rows


def queue(area, targets=None):
    fuels = json.loads((targets or OUT/'alternatives/vehicle_fuel_index_20261026.json').read_text(encoding='utf-8'))['rows']
    mapped = json.loads((OUT/'gas_stations.json').read_text(encoding='utf-8'))
    mapped_names = {name_key(r['name']) for r in mapped if region(r['address']) == area}
    items = {}
    for f in fuels:
        if area != 'all' and f['region'] != area:
            continue
        name = f['상호명']
        keyword = '주유' if '주유' in name else '충전' if '충전' in name else re.sub(r'주식회사|유한회사|\(주\)|\(유\)|㈜', '', name).strip()
        if len(keyword) < 2:
            continue
        point = [round(float(f[k]),6) for k in ('위도','경도')]
        if not (32 < point[0] < 40 and 124 < point[1] < 132):
            raise ValueError('Invalid public business coordinate')
        key = hashlib.sha256(json.dumps([point,keyword],ensure_ascii=False).encode()).hexdigest()[:16]
        if key not in items:
            items[key] = {'id':key, 'center':point, 'keyword':keyword, 'businesses':[],
                'priority':0 if name in ('현대주유소','동부주유소','해제주유소') else 1 if name_key(name) not in mapped_names and f['상권업종소분류코드']=='G21402' else 2 if name_key(name) not in mapped_names else 3}
        items[key]['businesses'].append({'name':name,'address':f['도로명주소'],'id':f['상가업소번호']})
    return sorted(items.values(),key=lambda r:(ORDER.index(region(r['businesses'][0]['address'])),r['priority'],r['businesses'][0]['address'],r['id']))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--region',default='전남')
    ap.add_argument('--limit',type=int,default=10000)
    ap.add_argument('--interval',type=float,default=1.5)
    ap.add_argument('--targets',type=Path)
    ap.add_argument('--output',type=Path,default=OUT/'alternatives/kb_location_progress_20261026.json')
    args=ap.parse_args()
    if args.interval < 1.5:
        raise ValueError('Minimum interval 1.5 seconds')
    directory=OUT/'alternatives/kb_location_cache'/args.region
    directory.mkdir(parents=True,exist_ok=True)
    progress_path=args.output
    plan=queue(args.region,args.targets)
    session=requests.Session()
    done=0
    found={}
    last=0
    status='running'
    error=None
    def save():
        result={'source_url':URL,'checked_at':datetime.now(KST).isoformat(timespec='seconds'),
            'region':args.region,'scope':'candidate_location_name_search_not_geographic_census',
            'status':status,'planned_queries':len(plan),'completed_queries':done,'error':error,
            'unique_merchants':len(found),'rows':list(found.values()),
            'limitations':['Bank selection updates are not real time.',
                'No result does not prove nonmembership.',
                'Bank address is coarse; exact premises need independent matching.',
                'This does not verify all card issuers, paper acceptance or actual payment.']}
        temp=progress_path.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(progress_path)
    for item in plan:
        path=directory/(item['id']+'.json')
        try:
            if path.exists():
                cached=json.loads(path.read_text(encoding='utf-8'))
                if cached['query']!=item or cached['status']!='complete':
                    raise ValueError('Cache mismatch')
            else:
                if done >= args.limit:
                    status='partial_limit';break
                rows=[];expected=None;pages=[]
                for page in range(1,101):
                    time.sleep(max(0,args.interval-(time.monotonic()-last)))
                    payload={'mainCC':'a','isNoFrame':'Y','situXCdnt':item['center'][0],
                        'situYCdnt':item['center'][1],'페이지번호':page,'useCase':'1',
                        'locationType':'1','startRow':(page-1)*10,'endRow':page*10,'mmcNm':item['keyword']}
                    last=time.monotonic()
                    response=session.post(URL,data=payload,timeout=(8,20))
                    response.raise_for_status()
                    html=response.content.decode('utf-8')
                    total,batch=parse_response(html)
                    if expected is None:expected=total
                    if total!=expected:raise ValueError('Count changed during pagination')
                    rows.extend(batch)
                    pages.append({'page':page,'count':len(batch),'response_sha256':hashlib.sha256(response.content).hexdigest()})
                    if len(rows)>=total:break
                if len(rows)!=expected or len({r['content']['franchiseNo'] for r in rows})!=expected:
                    raise ValueError('Incomplete or repeated merchant pages')
                cached={'query':item,'status':'complete','source_url':URL,
                    'checked_at':datetime.now(KST).isoformat(timespec='seconds'),'total':expected,'pages':pages,'rows':rows}
                path.write_text(json.dumps(cached,ensure_ascii=False,indent=2),encoding='utf-8')
            for row in cached['rows']:
                c=row['content'];identity=c['franchiseNo']
                found[identity]={**row,'checked_at':cached['checked_at'],'query_id':item['id']}
            done+=1
            save()
            if cached['rows'] or done%20==0:
                print(json.dumps({'done':done,'planned':len(plan),'seed':item['businesses'][0]['name'],
                    'found':[r['content']['title'] for r in cached['rows']],'unique':len(found)},ensure_ascii=False),flush=True)
        except (requests.RequestException,ValueError,KeyError) as exc:
            status='stopped_error';error=type(exc).__name__+': '+str(exc);save();raise
    else:status='candidate_queue_complete'
    save()
    print(status,done,len(found),flush=True)


if __name__=='__main__':main()
