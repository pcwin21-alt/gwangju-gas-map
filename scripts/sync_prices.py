"""Publish only ID-linked, date-stamped prices with the corrected fuel schema."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def sync():
    raw=json.loads((ROOT/'output/gas_prices.json').read_text(encoding='utf-8'))
    today=datetime.now(timezone(timedelta(hours=9))).date()
    prices,info={},{}
    for sid,row in raw.items():
        if row.get('schema_version')!=2:continue
        valid={}
        for fuel,price in row.get('prices',{}).items():
            evidence=row.get('price_evidence',{}).get(fuel,{})
            try: age=(today-datetime.strptime(evidence['source_date'],'%Y%m%d').date()).days
            except (ValueError,KeyError):continue
            if 0<=age<=3 and isinstance(price,(int,float)) and not isinstance(price,bool) and 0<price<10000:
                valid[fuel]=price
        if valid:
            prices[sid]=valid
            info[sid]={'checked_at':row.get('checked_at'), 'source_dates':sorted({row['price_evidence'][k]['source_date'] for k in valid})}
    path=ROOT/'output/map.html'
    html=path.read_text(encoding='utf-8')
    html,n=re.subn(r'const PRICES = \{.*?\};',lambda _: 'const PRICES = '+json.dumps(prices,ensure_ascii=False)+';',html,flags=re.S)
    if n!=1:raise ValueError('가격 상수 중복 또는 누락')
    const='const PRICE_INFO = '+json.dumps(info,ensure_ascii=False)+';'
    if 'const PRICE_INFO = ' in html:
        html=re.sub(r'const PRICE_INFO = .*?;\n',lambda _:const+'\n',html)
    else:html=html.replace('const PRICES = ',const+'\nconst PRICES = ',1)
    path.write_text(html,encoding='utf-8')
    print(f'유종·시각·ID 확인 가격 {len(prices)}곳 반영')

if __name__=='__main__':sync()
