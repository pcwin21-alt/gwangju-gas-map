"""Official annual CSV; join historical locations only by name AND market.

The published CSV contains regional labels, not street addresses or coordinates.
Unmatched locations must not be invented, removed, or marked freshly verified.
"""
import csv
import hashlib
import io
import re
from datetime import datetime, timedelta

PORTAL = 'https://www.data.go.kr/data/3060079/fileData.do'
FIELDS = ('가맹점명', '소속 시장명(또는 상점가)', '소재지', '취급품목',
          '지류형 가맹 여부', '디지털형 가맹 여부', '가맹 등록년도')


def normalize(value):
    return re.sub(r'[^\w]', '', value or '').lower()


def fuel_row(row):
    return bool(re.search(r'주유소|충전소|석유|에너지', row['가맹점명']) or
                re.search(r'휘발유|경유|등유|^유류$|^주유', row['취급품목']))


def parse_csv(content, source_date, checked, download_url):
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('온누리 CSV 인코딩 확인 필요')
    reader = csv.DictReader(io.StringIO(text))
    if not set(FIELDS).issubset(reader.fieldnames or []):
        raise ValueError('온누리 CSV 필수 컬럼 누락')
    rows, total = [], 0
    for row in reader:
        total += 1
        row = {key: (row.get(key) or '').strip() for key in FIELDS}
        if any(row[key] not in ('Y', 'N', '') for key in FIELDS[4:6]):
            raise ValueError('온누리 결제수단 값 변경')
        if row['소재지'] in ('전남광주', '광주', '광주광역시') and fuel_row(row):
            rows.append(row)
    if total < 100000 or len(rows) < 50:
        raise ValueError('온누리 CSV 불완전 또는 지역 형식 변경')
    return {'source_url': PORTAL, 'download_url': download_url, 'source_date': source_date,
            'retrieved_at': checked, 'sha256': hashlib.sha256(content).hexdigest(),
            'total_rows': total, 'regional_fuel_rows': len(rows), 'rows': rows}


def fetch_snapshot(session, cached, checked):
    response = session.get(PORTAL, timeout=30)
    response.raise_for_status()
    # Structured metadata is published with the file page; do not guess file IDs.
    match = re.search(r'"contentUrl"\s*:\s*"(https://www\.data\.go\.kr/cmm/cmm/fileDownload\.do\?[^"\s]+)"', response.text)
    dates = re.findall(r'전국 온누리상품권 가맹점 현황_(\d{8})', response.text)
    if not match or not dates:
        raise ValueError('온누리 공식 다운로드 메타데이터 변경')
    source_date = datetime.strptime(max(dates), '%Y%m%d').date().isoformat()
    url = match.group(1).replace('&amp;', '&')
    # Recheck the page daily; re-download unchanged 17 MB files once a week.
    if cached and cached['source_date'] == source_date and cached['download_url'] == url:
        age = datetime.fromisoformat(checked) - datetime.fromisoformat(cached['retrieved_at'])
        if age < timedelta(days=7):
            return cached
    response = session.get(url, timeout=(20, 90))
    response.raise_for_status()
    return parse_csv(response.content, source_date, checked, url)


def reconcile(snapshot, historical):
    index = {}
    for row in snapshot['rows']:
        key = (normalize(row['가맹점명']), normalize(row['소속 시장명(또는 상점가)']))
        if row not in index.setdefault(key, []):
            index[key].append(row)
    result, review, used = [], [], set()
    for old in historical:
        key = (normalize(old.get('frcsNm')), normalize(old.get('mrktNm')))
        matches = index.get(key, []) if all(key) else []
        item = dict(old)
        if len(matches) == 1:
            row = matches[0]
            used.add(key)
            # A combined digital flag proves neither individual card nor QR support.
            item.update(paperYn=row['지류형 가맹 여부'], digitalYn=row['디지털형 가맹 여부'],
                        cardYn='', qrYn='')
            item['_verification'] = {
                'checked_at': snapshot['retrieved_at'], 'source_date': snapshot['source_date'],
                'status': 'published_snapshot', 'source_url': PORTAL,
                'match_basis': 'merchant_name_and_market', 'source_id': old['frCd'],
                'source_ids': [old['frCd']], 'market': row['소속 시장명(또는 상점가)']}
        elif re.search(r'주유소|충전소|석유|에너지', old.get('frcsNm', '')):
            review.append({'reason': '공식 파일 상호·상점가 매칭 미완료: 과거 기록 유지',
                           'name': old['frcsNm'], 'market': old.get('mrktNm'), 'source_id': old['frCd']})
        result.append(item)
    for key, rows in index.items():
        if key not in used:
            for row in rows:
                review.append({'reason': '전남광주 통합 지역 자료: 광주 상세주소·좌표 확인 필요',
                               'name': row['가맹점명'], 'market': row['소속 시장명(또는 상점가)'],
                               'region': row['소재지']})
    return result, review
