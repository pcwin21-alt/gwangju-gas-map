"""Public identity details via the existing Opinet price collector and budget.

This is an independent fuel-business source, never Onnuri membership evidence.
Only the price workflow calls this module; reservations persist before HTTP.
"""
import re
import time
from datetime import datetime, timedelta, timezone

from scripts.nationwide import region

URL = 'https://www.opinet.co.kr/api/detailById.do'
PUBLIC_FIELDS = ('UNI_ID', 'OS_NM', 'NEW_ADR', 'VAN_ADR', 'TEL', 'LPG_YN',
                 'POLL_DIV_CO', 'POLL_DIV_CD', 'GIS_X_COOR', 'GIS_Y_COOR')
KST = timezone(timedelta(hours=9))


def public_identity(detail):
    return {k: detail[k] for k in PUBLIC_FIELDS if k in detail and
            isinstance(detail[k], (str, int, float)) and len(str(detail[k])) <= 1000}


def collect(targets, usage, journal, api_key, checkpoint, request, *, budget=200,
            clock=time.time, sleeper=time.sleep, key_param='code', maximum=3):
    if not targets or any(t.get('region') != '전남' or not re.fullmatch(r'[A-Z]\d{7}', t.get('id', ''))
                          or not t.get('independent_source') for t in targets):
        raise ValueError('Independent Jeonnam ID anchors required')
    if len({t['id'] for t in targets}) != len(targets):
        raise ValueError('Duplicate Opinet target IDs')
    journal.setdefault('source_url', URL)
    journal.setdefault('scope', 'Independent fuel business identity only; not Onnuri verification')
    journal.setdefault('attempts', [])
    journal.setdefault('details', {})
    journal.setdefault('status', 'active')
    # An interrupted reservation is not silently retried with a different key.
    if any(a['status'] in ('reserved', 'uncertain') for a in journal['attempts']):
        for a in journal['attempts']:
            if a['status'] == 'reserved':
                a['status'] = 'uncertain'
        journal['status'] = 'needs_review'
        checkpoint(usage, journal)
    if journal['status'] != 'active':
        return 0
    count = 0
    today = datetime.fromtimestamp(clock(), KST).date().isoformat()
    if usage.get('date') != today:
        usage.clear()
        usage.update(date=today, attempts=0)
    # Three pilot detail requests/rolling 24h, sharing the price daily budget.
    recent = [a for a in journal['attempts'] if clock()-a['reserved_at'] < 86400]
    remaining = min(max(0, min(3, maximum)-len(recent)), max(0, min(200, budget)-usage['attempts']))
    for target in targets:
        if count >= remaining:
            break
        if any(a['id'] == target['id'] for a in recent):
            continue
        wait = max(0, journal.get('next_allowed_at', 0)-clock())
        if wait and not count:
            break
        if wait:
            sleeper(wait)
        attempt = {'id': target['id'], 'region': '전남', 'reserved_at': clock(), 'status': 'reserved'}
        journal['attempts'].append(attempt)
        usage['attempts'] += 1
        # If remote persistence fails, the caller raises before any transmission.
        checkpoint(usage, journal)
        count += 1
        try:
            response = request('GET', URL, params={key_param: api_key, 'out': 'json', 'id': target['id']},
                               timeout=30, allow_redirects=False)
            attempt['http_status'] = response.status_code
            if response.status_code in (400, 401, 403, 429):
                attempt['status'] = 'stopped_http'
                journal['status'] = 'needs_review'
            elif response.status_code != 200:
                attempt['status'] = 'http_error'
                journal['status'] = 'needs_review'
            else:
                result = response.json().get('RESULT', {})
                oils = result.get('OIL', [])
                if result.get('ERROR') or len(oils) != 1 or oils[0].get('UNI_ID') != target['id']:
                    attempt['status'] = 'invalid_or_empty_response'
                    journal['status'] = 'needs_review'
                else:
                    detail = public_identity(oils[0])
                    valid = region(detail.get('NEW_ADR') or detail.get('VAN_ADR')) == '전남' and \
                        detail.get('LPG_YN') in ('N', 'Y', 'C')
                    journal['details'][target['id']] = {
                        'checked_at': datetime.fromtimestamp(clock(), KST).isoformat(timespec='seconds'),
                        'source_url': URL, 'target': target, 'detail': detail,
                        'status': 'fuel_identity_observed' if valid else 'needs_identity_review',
                        'onnuri_membership': 'not_checked_by_this_source'}
                    attempt['status'] = 'done' if valid else 'needs_review'
        except Exception as exc:
            # Authenticated URLs and upstream bodies must never enter the log.
            attempt.update(status='request_error', error_type=type(exc).__name__)
            journal['status'] = 'needs_review'
        attempt['finished_at'] = clock()
        journal['next_allowed_at'] = clock()+180
        checkpoint(usage, journal)
        if journal['status'] != 'active':
            break
    journal['last_run'] = {'checked_at': datetime.fromtimestamp(clock(), KST).isoformat(timespec='seconds'),
                           'requests': count}
    checkpoint(usage, journal)
    return count
