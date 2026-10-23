"""Bounded, read-only diagnostics for the public Onnuri search endpoint."""
import json
import platform
import socket
import time

import requests

from onnuri_live import BASE, SOURCE


def probe(label, operation):
    started = time.monotonic()
    try:
        result = {'ok': True, **operation()}
    except (OSError, requests.RequestException, ValueError) as error:
        result = {'ok': False, 'error': type(error).__name__, 'message': str(error)[:500]}
    result.update(probe=label, seconds=round(time.monotonic() - started, 2))
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return result


def tcp(family, address):
    with socket.socket(family, socket.SOCK_STREAM) as connection:
        connection.settimeout(8)
        connection.connect(address)
    return {'address': address[0]}


def homepage(session):
    response = session.get(SOURCE, timeout=(10, 15))
    response.raise_for_status()
    return {'status': response.status_code, 'url': response.url}


def search(session):
    response = session.post(BASE + '/place/search', json={
        'keyword': '주유소', 'addrNm': '', 'addrCd': '', 'placeTypeList': [],
        'paperYn': '', 'cardYn': '', 'qrYn': '', 'latitude': '37.5667',
        'longitude': '126.9784', 'baseRange': 0, 'currPage': 1,
    }, timeout=(10, 15))
    response.raise_for_status()
    body = response.json()
    if body.get('resCode') != '0000':
        raise ValueError('Unexpected result: ' + str(body.get('resCode')))
    return {'status': response.status_code, 'resCode': body['resCode'],
            'total': body['data']['totalCnt'], 'received': len(body['data']['list'])}


def main():
    print(json.dumps({'platform': platform.system(), 'python': platform.python_version()}), flush=True)
    try:
        addresses = socket.getaddrinfo('www.onnuri.gift', 443, type=socket.SOCK_STREAM)
    except OSError as error:
        print(json.dumps({'probe': 'dns', 'ok': False, 'error': type(error).__name__}), flush=True)
        return 1
    seen = set()
    for family, _, _, _, address in addresses:
        if family in seen:
            continue
        seen.add(family)
        probe('tcp_' + socket.AddressFamily(family).name, lambda: tcp(family, address))
    with requests.Session() as session:
        session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': SOURCE,
                                'Origin': 'https://www.onnuri.gift'})
        page = probe('public_page', lambda: homepage(session))
        # Do not proceed after an explicit access rejection.
        if not page['ok'] and 'HTTPError' == page.get('error'):
            return 1
        result = probe('public_search', lambda: search(session))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
