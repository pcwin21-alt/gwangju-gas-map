"""Build a review queue from all address-list merchants; never publish it."""
import argparse
import json
import re
from collections import Counter,defaultdict
from pathlib import Path
from nationwide import name_key,region
from supplemental_onnuri import meters

OUT=Path(__file__).resolve().parents[1]/'output'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stamp',default='20261027');args=ap.parse_args()
    def read(path):return json.loads((OUT/path).read_text(encoding='utf-8'))
    scan=read(f'alternatives/kb_address_progress_{args.stamp}.json')
    mapped=read('gas_stations.json');commercial=read('alternatives/vehicle_fuel_index_20261026.json')['rows']
    opinet=read(f'alternatives/opinet_district_audit_{args.stamp}.json')['rows']
    previous={r['content']['franchiseNo'] for r in read('alternatives/kb_unfiltered_jeonnam_20261026.json')['rows']}
    commercial_index=defaultdict(list);map_index=defaultdict(list);opinet_index=defaultdict(list)
    for r in commercial:
        if r['region']==scan['region']:commercial_index[name_key(r['상호명'])].append(r)
    for r in mapped:
        if region(r['address'])==scan['region']:
            for name in [r['name']]+r.get('aliases',[]):map_index[name_key(name)].append(r)
    for r in opinet:opinet_index[name_key(r['OS_NM'])].append(r)
    rows=[]
    for bank in scan['rows']:
        c=bank['content'];key=name_key(c['title']);comm=commercial_index.get(key,[])
        fuel_category=c['category'] in ('주유소','충전소','LPG충전소','LPG 충전소','가스충전소')
        if not (fuel_category or re.search('주유|충전|석유|에너지',c['title']) or comm):continue
        row={'bank_record':bank,'bank_fuel_category':fuel_category,
             'in_previous_coordinate_scan':c['franchiseNo'] in previous,
             'commercial_name_matches':comm,'opinet_name_matches':opinet_index.get(key,[]),
             'mapped_name_matches':[{'id':r['id'],'name':r['name'],'address':r['address']} for r in map_index.get(key,[])],
             'status':'needs_identity_review_not_automatically_publishable'}
        if bank.get('coordinate_status')!='unusable':
            a=tuple(float(bank['location'][k]) for k in ('lat','lng'))
            row['commercial_name_distances_m']=[round(meters(a,(float(r['위도']),float(r['경도']))),1) for r in comm]
        rows.append(row)
    result={'source_url':scan['source_url'],'checked_at':scan['checked_at'],'scan_status':scan['status'],
            'planned_queries':scan['planned_queries'],'completed_queries':scan['completed_queries'],
            'unique_merchants':scan['unique_merchants'],
            'unusable_coordinate_merchants':sum(r.get('coordinate_status')=='unusable' for r in scan['rows']),
            'fuel_category_rows':sum(r['bank_fuel_category'] for r in rows),
            'fuel_category_by_county':dict(Counter(r['bank_record']['query_address'][1] for r in rows if r['bank_fuel_category'])),
            'rows':rows,'scope':'review_candidates_not_new_station_count'}
    destination=OUT/f'alternatives/kb_address_review_{args.stamp}.json'
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print({k:v for k,v in result.items() if k!='rows'})
    for r in rows:
        if not r['mapped_name_matches']:
            c=r['bank_record']['content'];print(c['franchiseNo'],c['title'],c['category'],c['address'],r.get('commercial_name_distances_m'))


if __name__=='__main__':main()
