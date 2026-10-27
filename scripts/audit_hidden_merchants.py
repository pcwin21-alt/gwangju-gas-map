"""Offline broad recall audit. A matching phone or nearby point is not identity."""
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from nationwide import name_key, region, valid_coords
from supplemental_onnuri import meters

OUT=Path(__file__).resolve().parents[1]/'output'


def main():
    read=lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
    banks=read('alternatives/kb_address_progress_20261027.json')['rows']
    previous={r['bank_record']['content']['franchiseNo'] for r in read('alternatives/kb_address_review_20261027.json')['rows']}
    fuels=[]
    for filename in ('station_locations.json','lpg_locations.json'):
        for r in read(filename)['rows']:
            if region(r.get('LCTN_ROAD_NM',''))=='전남':
                fuels.append({'name':r['CONM_NM'],'address':r['LCTN_ROAD_NM'],
                    'phone':r.get('TELNO',''),'lat':r['LAT'],'lng':r['LOT'],
                    'source_file':filename,'source_record':r})
    registry_count=len(fuels)
    for r in read('alternatives/vehicle_fuel_index_20261026.json')['rows']:
        if r['region']=='전남':
            fuels.append({'name':r['상호명'],'address':r['도로명주소'],
                'phone':'','lat':r['위도'],'lng':r['경도'],
                'source_file':'vehicle_fuel_index_20261026.json','source_record':r})
    phone=lambda p:re.sub(r'\D','',p or '')
    bycounty=defaultdict(list);byphone=defaultdict(list);byname=defaultdict(list);spatial=defaultdict(list)
    for i,r in enumerate(fuels):
        r['name_key']=name_key(r['name'])
        bycounty[r['address'].split()[1]].append(i)
        byname[r['name_key']].append(i)
        if phone(r['phone']):byphone[phone(r['phone'])].append(i)
        if valid_coords(r['lat'],r['lng']):spatial[(int(float(r['lat'])*1000),int(float(r['lng'])*1000))].append(i)
    results=[]
    for b in banks:
        c=b['content'];key=name_key(c['title'])
        if c['franchiseNo'] in previous:continue
        pool=set(byphone.get(phone(c['tel']),[])+byname.get(key,[]));similar={}
        for i in bycounty.get(c['address'].split()[1],[]):
            fk=fuels[i]['name_key']
            if min(len(key),len(fk))>=3:
                score=SequenceMatcher(None,key,fk).ratio()
                if score>=.75:pool.add(i);similar[i]=round(score,3)
        loc=b.get('location',{});point=(loc.get('lat'),loc.get('lng'));distances={}
        if valid_coords(*point):
            lat,lng=map(float,point);gx,gy=int(lat*1000),int(lng*1000)
            for x in range(gx-1,gx+2):
                for y in range(gy-1,gy+2):
                    for i in spatial.get((x,y),[]):
                        r=fuels[i];d=meters((lat,lng),(float(r['lat']),float(r['lng'])))
                        if d<=50:pool.add(i);distances[i]=round(d,1)
        if pool:
            results.append({'bank_record':b,'status':'candidate_only_no_promotion',
                'matches':[{'fuel_record':fuels[i],
                    'phone_match':bool(phone(c['tel'])) and phone(c['tel'])==phone(fuels[i]['phone']),
                    'name_match':key==fuels[i]['name_key'],'name_similarity':similar.get(i),
                    'distance_m':distances.get(i)} for i in sorted(pool)]})
    report={'scope':'candidate recall audit; no map writes, no current membership inference',
        'bank_merchants':len(banks),'already_reviewed_bank_ids':len(previous),
        'registry_rows':registry_count,'commercial_rows':len(fuels)-registry_count,
        'candidate_bank_ids':len(results),'rows':results}
    (OUT/'alternatives/hidden_merchant_audit_20261027.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print({k:v for k,v in report.items() if k!='rows'})
    for r in results:
        c=r['bank_record']['content']
        print(c['title'],c['category'],c['address'],[(m['fuel_record']['name'],m['phone_match'],m['name_similarity'],m['distance_m']) for m in r['matches']])


if __name__=='__main__':main()
