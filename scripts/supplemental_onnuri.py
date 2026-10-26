"""Reconcile independently evidenced bank-listed fuel merchants.

Keep bank IDs, issuer scope, unknown payment types and dates separate from the
Onnuri operator's snapshot. Neither a short name nor proximity alone is enough.
"""
from copy import deepcopy
from datetime import date
import math
import re
try:
    from nationwide import name_key, region, valid_coords
    from discover_address_candidates import address_key
except ModuleNotFoundError:
    from scripts.nationwide import name_key, region, valid_coords
    from scripts.discover_address_candidates import address_key

SOURCE = 'https://card.kbcard.com/BON/DVIEW/HBGV0701'
# Reviewed exact record pair: the commercial file contains both the short name
# and corporate trading name at the same lot and road address. Never apply
# this spelling exception to another merchant or to arbitrary suffix matches.
REVIEWED_NAMES = {
    ('000000070023590', 'MA010120220809284963'):
        ('대원석유주식회사직영명륜주유소', '대원석유직영명륜주유소주', ['명륜주유소'])
}


def locality_tokens(address):
    tokens=address.split()[1:]
    # Official rename effective 2021-04-01 (MOIS notice nttId=83647).
    if tokens[:2]==['경주시','양북면']:
        tokens[1]='문무대왕면'
    return tokens


def meters(a,b):
    lat1,lng1,lat2,lng2=map(math.radians,(*a,*b))
    v=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lng2-lng1)/2)**2
    return 6371008.8*2*math.asin(min(1,math.sqrt(v)))


def station_from_evidence(evidence, as_of):
    bank=evidence['bank_record'];c=bank['content'];f=evidence['commercial_record']
    if evidence.get('source_url')!=SOURCE or evidence.get('identity_review')!='same_premise_confirmed':
        raise ValueError('Unreviewed supplemental source')
    if not re.fullmatch(r'\d{15}',c['franchiseNo']) or c['onNuliGb']!='1':
        raise ValueError('Bank Onnuri identity missing')
    if c['category'] not in ('주유소','충전소','LPG충전소','LPG 충전소','가스충전소'):
        raise ValueError('Not a bank-classified vehicle fuel business')
    if f['상권업종소분류코드'] not in ('G21401','G21402'):
        raise ValueError('Not a commercial vehicle fuel business')
    reviewed=REVIEWED_NAMES.get((c['franchiseNo'], f['상가업소번호']))
    aliases=[]
    if reviewed and (c['title'],f['상호명'])==reviewed[:2]:
        aliases=reviewed[2]+[f['상호명']]
    elif name_key(c['title']) != name_key(f['상호명']):
        raise ValueError('Names disagree')
    addr=f['도로명주소']
    if not address_key(addr) or region(c['address'])!=region(addr):
        raise ValueError('Address/region mismatch')
    # Card-company address ends at town level; all published locality tokens
    # must agree with the commercial detailed address (province labels vary).
    if not any(locality_tokens(c['address']) == locality_tokens(full)[:len(locality_tokens(c['address']))]
               for full in (addr, f.get('지번주소',''))):
        raise ValueError('Locality mismatch')
    a=tuple(float(bank['location'][k]) for k in ('lat','lng'))
    b=tuple(float(f[k]) for k in ('위도','경도'))
    if not valid_coords(*a) or not valid_coords(*b) or meters(a,b)>100:
        raise ValueError('Premises coordinates disagree')
    age=(date.fromisoformat(as_of[:10])-date.fromisoformat(evidence['checked_at'][:10])).days
    if age<0:raise ValueError('Future evidence date')
    current=age<=30
    sid='kb:'+c['franchiseNo']
    return {'id':'onnuri:'+sid,'name':c['title'],'address':addr,'lat':b[0],'lng':b[1],
        'payment_types':['onnuri'],'source':['kb_onnuri'],'aliases':aliases,
        'fuel_kind':'lpg' if f['상권업종소분류코드']=='G21402' else 'liquid',
        'route_eligible':current,'region':region(addr),
        'onnuri_methods':{'paper':None,'card':True,'qr':None,'digital':True},
        'verification':{'onnuri':{'status':'confirmed' if current else 'stale',
            'checked_at':evidence['checked_at'],'source_date':None,'source_url':SOURCE,
            'source_id':sid,'source_ids':[sid],'provider':'kbcard','issuer_scope':['KB국민카드'],
            'match_basis':'bank_onnuri_flag_fuel_category_name_locality_coordinates_commercial_address',
            'candidate_ids':evidence.get('annual_candidate_ids',[]),
            'note':'KB국민카드 온누리 사용처 조회 기준. 카드사 반영 지연 가능. 지류·QR·다른 카드사는 별도 확인.'}},
        'location_evidence':{'source_type':'commercial_registry','source_url':evidence['commercial_source']['source_url'],
            'source_date':evidence['commercial_source']['source_date'],'source_id':f['상가업소번호'],
            'bank_distance_m':round(meters(a,b),1)}}


def apply_evidence(stations, review, evidence_rows, as_of):
    # Replace our own old supplemental rows idempotently; never modify the
    # operator snapshot or transfer an issuer flag to a neighboring station.
    result=[deepcopy(s) for s in stations if s.get('source')!=['kb_onnuri']]
    rows=deepcopy(review);accepted=[];seen=set()
    for e in evidence_rows:
        s=station_from_evidence(e,as_of)
        if s['id'] in seen:raise ValueError('Duplicate supplemental identity')
        seen.add(s['id'])
        same=[r for r in result if address_key(r['address'])==address_key(s['address']) and
              r.get('fuel_kind')==s['fuel_kind']]
        if same:
            # Do not transfer a bank registration across an operator/name change
            # or add another marker to a site already represented in the map.
            continue
        result.append(s);accepted.append(s)
        if s['verification']['onnuri']['status']=='confirmed':
            for r in rows:
                if r.get('candidate_id') in s['verification']['onnuri']['candidate_ids']:
                    if name_key(r['name']) not in {name_key(n) for n in [s['name']]+s['aliases']} or r.get('region')!=s['region']:
                        raise ValueError('Pending identity mismatch')
                    r.update(status='located',show_pending=False,
                        reason='KB국민카드 온누리 조회와 상권자료의 상호·주소권역·좌표 일치',
                        supplemental_source_id=s['verification']['onnuri']['source_id'])
        else:
            for r in rows:
                if r.get('candidate_id') in s['verification']['onnuri']['candidate_ids']:
                    r.update(status='needs_review',show_pending=True,
                        reason='KB국민카드 조회 후 30일 경과: 현재 가맹 재확인 필요')
    metadata={'source_url':SOURCE,'checked_at':max((e['checked_at'] for e in evidence_rows),default=None),
        'confirmed_count':sum(s['verification']['onnuri']['status']=='confirmed' for s in accepted),
        'stale_count':sum(s['verification']['onnuri']['status']=='stale' for s in accepted),
        'scope':'issuer_specific_corroboration_not_nationwide_refresh'}
    return result,rows,metadata


def reconcile_ledger(ledger, stations):
    result=deepcopy(ledger)
    matches={cid:s for s in stations if s.get('source')==['kb_onnuri']
             for cid in s['verification']['onnuri'].get('candidate_ids',[])}
    for row in result:
        if row.get('candidate_id') in matches:
            s=matches[row['candidate_id']]
            current=s['verification']['onnuri']['status']=='confirmed'
            row.update(status='located' if current else 'needs_review',
                reason='KB국민카드 온누리 조회와 상세주소 교차확인' if current else '카드사 조회 유효기간 경과: 재확인 필요',
                supplemental_source_id=s['verification']['onnuri']['source_id'])
    return result
