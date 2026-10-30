"""Bounded public bank-form crosscheck at independently published locations."""
import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from discover_kb_fuel import parse_response, URL
from onnuri_live import KST


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    result = {'source_url': URL, 'scope': 'targeted_crosscheck_not_nationwide_census', 'queries': []}
    session = requests.Session()
    for item in plan:
        pages = []
        rows = []
        total = None
        entry = {'target': item, 'status': 'running', 'pages': pages, 'rows': rows,
                 'checked_at': datetime.now(KST).isoformat(timespec='seconds')}
        result['queries'].append(entry)
        try:
            for page in range(1, 21):
                payload = {'mainCC': 'a', 'isNoFrame': 'Y',
                           'situXCdnt': item['lat'], 'situYCdnt': item['lng'],
                           '페이지번호': page, 'useCase': '1', 'locationType': '1',
                           'startRow': (page-1)*10, 'endRow': page*10, 'mmcNm': item['keyword']}
                response = session.post(URL, data=payload, timeout=(8, 25))
                response.raise_for_status()
                count, batch = parse_response(response.content.decode('utf-8'), require_coordinates=False)
                if total is None:
                    total = count
                if count != total:
                    raise ValueError('Count changed during pagination')
                rows.extend(batch)
                pages.append({'query': payload, 'sha256': hashlib.sha256(response.content).hexdigest(), 'count': len(batch)})
                if len(rows) >= total:
                    break
                time.sleep(1.5)
            if len(rows) != total or len({r['content']['franchiseNo'] for r in rows}) != total:
                raise ValueError('Incomplete or repeated pages')
            entry.update(status='complete', total=total)
        except (requests.RequestException, ValueError, KeyError) as exc:
            entry.update(status='error', error_type=type(exc).__name__, error=str(exc))
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({'target': item['keyword'], 'status': entry['status'],
                          'total': entry.get('total'), 'names': [r['content']['title'] for r in rows]}, ensure_ascii=True), flush=True)
        if entry['status'] == 'error':
            break  # Stop on denied/changed responses; no bypass or blind retries.
        time.sleep(1.5)


if __name__ == '__main__':
    main()
