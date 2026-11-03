"""One named public-place lookup for identity review, never membership."""
try:
    from nationwide import valid_coords
except ModuleNotFoundError:
    from scripts.nationwide import valid_coords

URL = 'https://k-skill-proxy.nomadamas.org/v1/kakao-map/search/keyword'
SOURCE = 'https://developers.kakao.com/docs/ko/local/dev-guide#search-by-keyword'


def request_for(job):
    query = job['target'].get('query')
    if job['source'] != 'kakao_local' or not isinstance(query, str) or not 1 <= len(query.strip()) <= 120:
        raise ValueError('Invalid named place identity query')
    # No caller-controlled host, headers, proxy, pagination or broad grid scan.
    return 'GET', URL, {'params': {'q': query.strip(), 'page': 1, 'size': 15, 'sort': 'accuracy'}}


def validate(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('documents'), list) or not isinstance(payload.get('meta'), dict):
        raise ValueError('Unexpected independent place response')
    rows, meta = payload['documents'], payload['meta']
    if len(rows) > 15 or not isinstance(meta.get('is_end'), bool) or type(meta.get('total_count')) is not int or meta['total_count'] < len(rows):
        raise ValueError('Invalid bounded place response metadata')
    ids = []
    for row in rows:
        if not isinstance(row, dict) or not row.get('id') or not row.get('place_name') or \
                not isinstance(row.get('phone'), str) or not isinstance(row.get('category_name'), str) or \
                not isinstance(row.get('category_group_code'), str) or \
                not (row.get('road_address_name') or row.get('address_name')) or not valid_coords(row.get('y'), row.get('x')):
            raise ValueError('Invalid independent place identity')
        ids.append(row['id'])
    if len(ids) != len(set(ids)):
        raise ValueError('Repeated independent place identity')
    return payload
