"""Validate reviewed policy facts and create an offline browser fallback.

This reads local public policy data only; it never collects merchant records.
"""
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_HOSTS = {'www.korea.kr', 'm.korea.kr', 'www.mss.go.kr', 'www.semas.or.kr',
                 'www.komsco.com', 'play.google.com', 'apps.apple.com'}


def validate(data):
    if data.get('schemaVersion') != 1:
        raise ValueError('Unsupported policy schema')
    date.fromisoformat(data['checkedAt'])
    if not 1 <= data['reviewAfterDays'] <= 7:
        raise ValueError('Policy review window must be 1–7 days')
    base = data['digitalBase']
    if not isinstance(base['rate'], (int, float)) or not 0 <= base['rate'] <= 30:
        raise ValueError('Invalid digital base rate')
    date.fromisoformat(base['recheckBy'])
    sources = {s['id'] for s in data['sources']}
    if len(sources) != len(data['sources']) or base['sourceId'] not in sources:
        raise ValueError('Missing or duplicate policy source')
    if len(data['notices']) > 30:
        raise ValueError('Too many policy notices')
    for item in data['notices']:
        date.fromisoformat(item['publishedAt'])
        if item['sourceId'] not in sources:
            raise ValueError('Notice source missing')
        if item['kind'] not in {'temporary', 'planned', 'confirmed'}:
            raise ValueError('Unknown policy state')
        if item['kind'] == 'planned' and item.get('startsOn'):
            raise ValueError('A proposed change cannot carry an active start date')
        if item.get('affects') and (item['affects'] != 'digital_base' or item['kind'] != 'confirmed' or 'rate' not in item):
            raise ValueError('Only a confirmed purchase-base change may replace the base rate')
        if item['kind'] != 'planned':
            start = date.fromisoformat(item['startsOn'])
            end = date.fromisoformat(item['endsOn']) if item.get('endsOn') else None
            if end and start > end:
                raise ValueError('Policy dates reversed')
        if 'rate' in item and not 0 <= item['rate'] <= 30:
            raise ValueError('Invalid notice rate')
    links = data['sources'] + data['registration']['links']
    for link in links:
        for key in ('url', 'documentUrl'):
            if key in link:
                url = urlparse(link[key])
                if url.scheme != 'https' or url.hostname not in ALLOWED_HOSTS or url.username or url.password:
                    raise ValueError('Unapproved policy URL')
    return data


def browser_script(data):
    validate(data)
    return "(function(root){\n  const data = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n  if(typeof module==='object'&&module.exports)module.exports=data;else root.GasOnnuriPolicyData=data;\n})(typeof globalThis!=='undefined'?globalThis:this);\n"


def platform_script(source):
    data = json.loads(source.split('  const data = ', 1)[1].split(';\n  if(typeof module=', 1)[0])
    data['registration']['links'] = []
    return browser_script(data)


def build():
    data = validate(json.loads((ROOT / 'assets/onnuri-policy.json').read_text(encoding='utf-8')))
    (ROOT / 'assets/onnuri-policy-data.js').write_text(browser_script(data), encoding='utf-8')
    return data


if __name__ == '__main__':
    data = build()
    print(f"Policy fallback built: checked {data['checkedAt']}, {len(data['notices'])} sourced notices")
