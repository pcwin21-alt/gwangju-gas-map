"""Budgeted Opinet detail refresh. Keys are station IDs, never merchant names."""
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'
FUEL_NAMES={'B027':'휘발유','D047':'경유','B034':'고급휘발유','C004':'등유','K015':'LPG'}
KST=timezone(timedelta(hours=9))

def read(name,default):
    p=OUT/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def write(name,value):
    p=OUT/name
    tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(p)

def key(name):
    return re.sub(r'[^가-힣a-z0-9]','',re.sub(r'주식회사|유한회사|\(주\)|\(유\)|㈜','',name or '').lower())

def road(address):
    m=re.search(r'([가-힣0-9]+(?:대로|로|길))\s*[, ]?\s*(\d+(?:-\d+)?)',address or '')
    return ''.join(m.groups()) if m else None

def same_station(station,detail):
    from scripts.nationwide import region
    names={key(n) for n in [station['name'],*station.get('aliases',[])]}
    address=detail.get('NEW_ADR') or detail.get('VAN_ADR') or ''
    return bool(key(detail.get('OS_NM')) in names and road(address) and
                road(address)==road(station.get('address')) and
                len(address.split())>1 and len(station.get('address','').split())>1 and
                address.split()[1]==station['address'].split()[1] and
                region(address)==region(station.get('address')))

def parse_prices(detail):
    prices={}
    for row in detail.get('OIL_PRICE',[]):
        code=row.get('PRODCD')
        price=row.get('PRICE')
        if code not in FUEL_NAMES or isinstance(price,bool):continue
        try: price=float(price)
        except (ValueError,TypeError):continue
        if not 0<price<10000:continue
        day=str(row.get('TRADE_DT',''))
        if not re.fullmatch(r'\d{8}',day):continue
        prices[FUEL_NAMES[code]]={'price':price,'source_date':day,'source_time':str(row.get('TRADE_TM',''))}
    return prices

def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    api_key=os.getenv('OPINET_API_KEY')
    if not api_key:raise SystemExit('OPINET_API_KEY 미설정: 가격 수집 미실행')
    checked=datetime.now(KST)
    today=checked.date().isoformat()
    budget=min(200,max(0,int(os.getenv('OPINET_DAILY_BUDGET','200'))))
    usage=read('opinet_usage.json',{})
    if usage.get('date')!=today:usage={'date':today,'attempts':0}
    stations=read('gas_stations.json',[])
    legacy=read('opinet_cache.json',{})
    old=read('gas_prices.json',{})
    counts=Counter(s['name'] for s in stations)
    results={}
    for s in stations:
        previous=old.get(s['id'],{})
        if previous.get('schema_version')==2:results[s['id']]=previous
    # Rotate the start so a restricted quota does not permanently starve later IDs.
    offset=int(checked.strftime('%j'))%max(1,len(stations))
    ordered=stations[offset:]+stations[:offset]
    fetched={}
    errors=0
    for s in ordered:
        if usage['attempts']>=budget or errors>=5:break
        uid=s.get('opinet_id') or old.get(s['id'],{}).get('uni_id')
        if not uid and counts[s['name']]==1:uid=legacy.get(s['name'],{}).get('uni_id')
        if not uid:continue
        try:
            if uid not in fetched:
                usage['attempts']+=1
                write('opinet_usage.json',usage)
                r=requests.get('https://www.opinet.co.kr/api/detailById.do',
                    # Keep the previously verified legacy key contract. New keys can opt in.
                    params={os.getenv('OPINET_KEY_PARAM','code'):api_key,'out':'json','id':uid},timeout=15)
                if r.status_code in (401,403):
                    print('가격 API 인증 확인 필요; 추가 요청 중단')
                    break
                r.raise_for_status()
                body=r.json()
                result=body.get('RESULT',{})
                oils=result.get('OIL',[])
                if not oils:
                    if 'ERROR' not in result:
                        # Retired station IDs return an empty OIL array, not a global auth error.
                        fetched[uid]={}
                        continue
                    error=result.get('ERROR',{})
                    if isinstance(error,list):error=error[0] if error else {}
                    code=str(error.get('CODE',error.get('code','unknown'))) if isinstance(error,dict) else 'unknown'
                    code=code if re.fullmatch(r'[A-Za-z0-9_-]{1,24}',code) else 'unavailable'
                    print('가격 API 오류 코드: '+code+'; 응답 필드: '+','.join(str(k) for k in result.keys()))
                    break
                fetched[uid]=oils[0]
            detail=fetched[uid]
            if not same_station(s,detail):continue
            parsed=parse_prices(detail)
            if parsed:
                results[s['id']]={'schema_version':2,'uni_id':uid,'matched_name':detail.get('OS_NM'),
                    'checked_at':checked.isoformat(timespec='seconds'),
                    'prices':{k:v['price'] for k,v in parsed.items()},'price_evidence':parsed}
        except (requests.RequestException,ValueError,KeyError):
            errors+=1
            # Never print exceptions containing authenticated request URLs.
            print('가격 응답 확인 실패; 기존 정상 가격 유지')
    # Drop stale price entries after 72h; never mislabel old diesel/LPG caches.
    for sid,v in list(results.items()):
        v['prices']={k:p for k,p in v['prices'].items() if k in v.get('price_evidence',{}) and
            (checked.date()-datetime.strptime(v['price_evidence'][k]['source_date'],'%Y%m%d').date()).days<=3}
    write('gas_prices.json',results)
    print(f'ID 기준 가격 {len(results)}개 / 오늘 요청 {usage["attempts"]}/{budget} / 오류 {errors}회')

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT))
    main()
