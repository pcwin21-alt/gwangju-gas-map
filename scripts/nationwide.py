"""Resolve official Onnuri rows against public municipal station locations.

No guessed coordinates, geocoding credentials or first-result fuzzy matches.
"""
import hashlib
import json
import math
import re
from pathlib import Path

STANDARD_URL = 'https://www.data.go.kr/data/15129441/standard.do'
REGIONS = {'서울':'서울', '부산':'부산', '대구':'대구', '인천':'인천', '광주':'광주',
           '대전':'대전', '울산':'울산', '세종':'세종', '경기':'경기', '강원':'강원',
           '충북':'충북', '충남':'충남', '전북':'전북', '전남':'전남', '경북':'경북',
           '경남':'경남', '제주':'제주'}

def region(address):
    value = (address or '').split(' ')[0]
    for full, short in [('충청북','충북'),('충청남','충남'),('경상북','경북'),('경상남','경남'),
                        ('전라북','전북'),('전라남','전남')]:
        if value.startswith(full): return short
    if value.startswith('전남광주'):
        return '광주' if re.search(r'\s(?:광산구|동구|서구|남구|북구)(?:\s|$)', address) else '전남'
    return next((v for k,v in REGIONS.items() if value.startswith(k)), None)

def name_key(name):
    name = re.sub(r'주식회사|유한회사|\(주\)|\(유\)|㈜', '', name or '')
    return re.sub(r'[^가-힣a-z0-9]', '', name.lower())

def row_id(row):
    text = '\x1f'.join(row.get(k,'') for k in ('소재지','소속 시장명(또는 상점가)','가맹점명'))
    return hashlib.sha256(text.encode()).hexdigest()[:24]

def non_vehicle(row):
    return bool(re.search(r'음식|한식|중식|식당|주류|주점|술집|소주|맥주|건강|학원|과자|화장품|의류|카페|스낵|편의점',row.get('취급품목','')) or
                re.search(r'기사식당|^CU.*주유소점$|알콜주유소|주류\s*충전소|뻥튀기충전소|비타민충전소|단짠충전소|인생충전소|기술학원',row['가맹점명']))

def valid_coords(lat, lng):
    try:
        a,b=float(lat),float(lng)
        return math.isfinite(a) and math.isfinite(b) and 32 <= a <= 39 and 124 <= b <= 132
    except (ValueError,TypeError): return False

def fetch_locations(session):
    header = session.get('https://www.data.go.kr/download/columList.json',
                         params={'pk':'15129441','ext':'JSON'}, timeout=30)
    header.raise_for_status()
    meta = header.json()
    total = int(meta['totalCount'])
    if not 1000 <= total <= 50000: raise ValueError('주유소 위치 원천 건수 확인 필요')
    table = meta['tableVO']
    rows=[]
    for page in range(1, math.ceil(total / 10000)+1):
        params=[('publicDataPk','15129441'),('totalCount',total),
                ('svcTableNm',table['svcTableNm']),('perPage',10000),('page',page)]
        params.extend(('colNmList', col) for col in table['colNmList'])
        response=session.get('https://www.data.go.kr/download/standard.json',params=params,timeout=60)
        response.raise_for_status()
        data=response.json()
        if not isinstance(data,list): raise ValueError('주유소 위치 응답 변경')
        for r in data:
            if not r.get('CONM_NM'): raise ValueError('주유소 위치 필수 필드 누락')
            rows.append({k:r.get(k) for k in ('CONM_NM','CTPV_NM','SGG_NM','LCTN_ROAD_NM',
                        'LCTN_LOTNO_ADDR','LAT','LOT','TELNO','DATA_CRTR_YMD')})
    if len(rows) != total: raise ValueError('주유소 위치 페이지 불완전')
    return rows

def resolve(snapshot, historical, locations):
    index={}
    for loc in locations:
        key=(region(loc.get('CTPV_NM')),name_key(loc['CONM_NM']))
        index.setdefault(key,[]).append(loc)
    known={(name_key(r.get('frcsNm')), re.sub(r'\W','',r.get('mrktNm',''))) for r in historical}
    added, review=[],[]
    for row in snapshot['rows']:
        identity=(name_key(row['가맹점명']),re.sub(r'\W','',row['소속 시장명(또는 상점가)']))
        raw_region=row['소재지']
        regions=['광주','전남'] if raw_region=='전남광주' else [region(raw_region)]
        candidates=[r for reg in regions for r in index.get((reg,identity[0]),[])]
        # Duplicate publications of one location are not separate candidates.
        unique={re.sub(r'\s','',r.get('LCTN_ROAD_NM') or r.get('LCTN_LOTNO_ADDR') or ''):r for r in candidates}
        candidates=list(unique.values())
        item={'candidate_id':row_id(row),'name':row['가맹점명'],'market':row['소속 시장명(또는 상점가)'],
              'region':raw_region,'paper':row['지류형 가맹 여부'],'digital':row['디지털형 가맹 여부']}
        if non_vehicle(row):
            review.append({**item,'status':'excluded_non_vehicle_fuel','reason':'자동차 주유 업종 아님: '+row['취급품목']})
            continue
        if identity in known: continue
        if len(candidates)!=1:
            review.append({**item,'status':'needs_review','reason':'위치 후보 없음' if not candidates else '동명 지점 구분 필요'})
            continue
        loc=candidates[0]
        if not valid_coords(loc.get('LAT'),loc.get('LOT')):
            review.append({**item,'status':'needs_review','reason':'공식 위치 좌표 미확인'})
            continue
        address=loc.get('LCTN_ROAD_NM') or loc.get('LCTN_LOTNO_ADDR')
        if not address:
            review.append({**item,'status':'needs_review','reason':'상세주소 미확인'});continue
        added.append({'frCd':'national-'+row_id(row),'frcsNm':row['가맹점명'],
          'frcsAddr':address,'mrktNm':row['소속 시장명(또는 상점가)'],
          'latitude':float(loc['LAT']),'longitude':float(loc['LOT']),
          'paperYn':row['지류형 가맹 여부'],'digitalYn':row['디지털형 가맹 여부'],
          'cardYn':'','qrYn':'', '_location_evidence':{'source_url':STANDARD_URL,
            'source_date':loc.get('DATA_CRTR_YMD'),'match_basis':'unique_exact_name_and_region'},
          '_verification':{'status':'published_snapshot','checked_at':snapshot['retrieved_at'],
            'source_date':snapshot['source_date'],'source_url':snapshot['source_url'],
            'source_id':'national-'+row_id(row),'candidate_id':row_id(row),
            'match_basis':'official_name_region_and_municipal_station','market':row['소속 시장명(또는 상점가)']}})
    return added,review
