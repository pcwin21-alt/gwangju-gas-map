"""A resumable, source-budgeted collection loop, without access-control bypass.

Every outbound attempt is reserved and durably committed before transmission.
The state checkout is separate from main and is never included in the site.
"""
import argparse
import hashlib
import gzip
import json
import re
import subprocess
import time
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    from discover_kb_fuel import parse_response, URL as KB_URL
    from nationwide import name_key, region, valid_coords
    from supplemental_onnuri import station_from_evidence, meters
    from survey_inventory import (install_survey, survey_jobs, make_inventory,
                                  survey_progress, completed_recheck, sync_mapped_inventory, candidate_regions)
    from collector_limits import limits, run_limit, observe, snapshot as limits_snapshot
    import independent_place
except ModuleNotFoundError:
    from scripts.discover_kb_fuel import parse_response, URL as KB_URL
    from scripts.nationwide import name_key, region, valid_coords
    from scripts.supplemental_onnuri import station_from_evidence, meters
    from scripts.survey_inventory import (install_survey, survey_jobs, make_inventory,
                                          survey_progress, completed_recheck, sync_mapped_inventory, candidate_regions)
    from scripts.collector_limits import limits, run_limit, observe, snapshot as limits_snapshot
    from scripts import independent_place

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'config/collector-policy.json'
PORTAL = 'https://www.data.go.kr/data/3060079/fileData.do'
DOWNLOAD_META = 'https://www.data.go.kr/tcs/dss/selectFileDataDownload.do'
TERMINAL = {'done', 'needs_review', 'blocked'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone(timedelta(hours=9))).isoformat(timespec='seconds')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


def retry_after(value, now):
    if not value:
        return None
    try:
        return now + max(0, int(value))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                return None
            return max(now, date.timestamp())
        except (ValueError, TypeError, OverflowError):
            return None


class Store:
    def __init__(self, directory, persist_git=False):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / 'responses').mkdir(exist_ok=True)
        self.persist_git = persist_git
        if persist_git:
            # Never accidentally commit the task workspace as collection state.
            root = subprocess.check_output(['git', '-C', str(self.directory), 'rev-parse', '--show-toplevel'], text=True, encoding='utf-8').strip()
            if Path(root).resolve() != self.directory:
                raise ValueError('State must have its own Git checkout')
            branch = subprocess.check_output(['git', '-C', str(self.directory), 'branch', '--show-current'], text=True, encoding='utf-8').strip()
            if branch != 'merchant-collector-state':
                raise ValueError('Refuse to write collector state to an application branch')

    def save(self, state, blob=None):
        if blob:
            name, content = blob
            if not re.fullmatch(r'[a-f0-9]{24}\.(json|csv)', name):
                raise ValueError('Invalid response filename')
            path = self.directory / 'responses' / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(content)
        path = self.directory / 'state.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temp.replace(path)
        if self.persist_git:
            self.git('add', '--', 'state.json')
            if any((self.directory/'responses').iterdir()):
                self.git('add', '--', 'responses')
            if subprocess.run(['git', '-C', str(self.directory), 'diff', '--cached', '--quiet']).returncode:
                self.git('commit', '-m', 'checkpoint: incremental merchant collection')
                self.git('push', 'origin', 'HEAD:merchant-collector-state')

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.directory), *args], check=True, stdout=subprocess.DEVNULL)


def initial_state(plan, policy):
    jobs = []
    for raw in plan['jobs']:
        job = dict(raw)
        job.setdefault('id', fingerprint(raw))
        job.update(status='pending', attempts=0, page=1, observed_ids=[])
        jobs.append(job)
    if len({j['id'] for j in jobs}) != len(jobs):
        raise ValueError('Repeated job identity')
    return {'schema_version': 1, 'plan_id': plan['id'], 'scope': plan['scope'],
            'sources': {key: {**value, 'next_allowed_at': 0} for key, value in policy['sources'].items()},
            'attempts': [], 'jobs': jobs, 'evidence': [], 'review': [],
            'source_gaps': plan.get('source_gaps', []), 'status': 'running'}


def request_for(job):
    kind = job['kind']
    if kind == 'kakao_place_identity':
        return independent_place.request_for(job)
    if kind == 'kb_search':
        target = job['target']
        if not valid_coords(target['lat'], target['lng']):
            raise ValueError('Invalid published anchor')
        page = job['page']
        return 'POST', KB_URL, {'data': {
            'mainCC': 'a', 'isNoFrame': 'Y', 'situXCdnt': target['lat'], 'situYCdnt': target['lng'],
            '페이지번호': page, 'useCase': '1', 'locationType': '1', 'startRow': (page-1)*10,
            'endRow': page*10, 'mmcNm': target['keyword']}}
    if kind == 'annual_page':
        return 'GET', PORTAL, {}
    if kind == 'annual_metadata':
        return 'POST', DOWNLOAD_META, {'data': job['data']}
    if kind == 'annual_download':
        # Follow only an observed, validated portal attachment. No arbitrary URLs.
        file_id, sequence = job['file_id'], job['sequence']
        if not re.fullmatch(r'FILE_\d+', file_id) or not re.fullmatch(r'\d+', sequence):
            raise ValueError('Invalid public attachment')
        return 'GET', 'https://www.data.go.kr/cmm/cmm/fileDownload.do', {
            'params': {'atchFileId': file_id, 'fileDetailSn': sequence, 'insertDataPrcus': 'N'}}
    raise ValueError('Unknown job kind')


def corroborate(bank, checked, commercial, commercial_source, candidate_ids=()):
    c = bank['content']
    matches = []
    for f in commercial:
        if name_key(c['title']) != name_key(f['상호명']) or region(c['address']) != f['region']:
            continue
        evidence = {'identity_review': 'same_premise_confirmed', 'source_url': KB_URL,
                    'checked_at': checked, 'bank_record': bank, 'commercial_record': f,
                    'commercial_source': commercial_source, 'annual_candidate_ids': list(candidate_ids)}
        try:
            station_from_evidence(evidence, checked)
        except (ValueError, KeyError, TypeError):
            continue
        matches.append(evidence)
    # Duplicate publications at a premise are not extra businesses. Conflicting
    # premises/types are left for review. No suffix/fuzzy/nearby-only promotion.
    unique = {(e['commercial_record']['도로명주소'], e['commercial_record']['상권업종소분류코드']): e for e in matches}
    return next(iter(unique.values())) if len(unique) == 1 else None


def independent_fuel_leads(bank, commercial):
    """Retain neutral/misclassified bank categories for review, not promotion."""
    c, loc = bank['content'], bank.get('location', {})
    if not valid_coords(loc.get('lat'), loc.get('lng')):
        return []
    point = (float(loc['lat']), float(loc['lng']))
    return [f['상가업소번호'] for f in commercial if f.get('상권업종소분류코드') in ('G21401', 'G21402') and
            name_key(c['title']) == name_key(f['상호명']) and region(c.get('address')) == f['region'] and
            valid_coords(f.get('위도'), f.get('경도')) and
            meters(point, (float(f['위도']), float(f['경도']))) <= 100]


def handle_response(state, job, response, now, commercial, commercial_source):
    checked = stamp(now)
    if job['kind'] == 'kakao_place_identity':
        payload = independent_place.validate(response.json())
        result = {'checked_at': checked, 'source': 'kakao_local', 'source_url': independent_place.SOURCE,
                  'query': job['target']['query'], 'payload': payload,
                  'scope': 'one named first-page identity observation; not membership or a complete area search'}
        state.setdefault('independent_place_checks', {})[job['id']] = result
        job.update(status='done', result='independent_identity_observations_saved', last_observed_at=checked)
        return json.dumps(result, ensure_ascii=False).encode(), 'json'
    if job['kind'] == 'kb_search':
        total, rows = parse_response(response.content.decode('utf-8'), require_coordinates=False)
        page = job['page']
        if page > 1 and job.get('expected') != total:
            raise ValueError('Page count changed; no complete snapshot claimed')
        ids = [r['content']['franchiseNo'] for r in rows]
        if len(ids) != len(set(ids)) or set(ids) & set(job['observed_ids']):
            raise ValueError('Repeated bank result/page')
        if len(job['observed_ids']) + len(ids) > total or (len(job['observed_ids']) + len(ids) < total and not rows):
            raise ValueError('Incomplete bank pages')
        job['expected'] = total
        job['observed_ids'].extend(ids)
        job['last_observed_at'] = checked
        for bank in rows:
            e = corroborate(bank, checked, commercial, commercial_source)
            if e:
                # A name query can return neighboring merchants. Annual IDs may
                # attach only to the exact target legal name, never every result.
                if job.get('annual_link_reviewed') and name_key(bank['content']['title']) == name_key(job['target']['name']):
                    e['annual_candidate_ids'] = job.get('candidate_ids', [])
                state['evidence'].append(e)
            else:
                leads = independent_fuel_leads(bank, commercial)
                if bank['content'].get('category') in ('주유소', '충전소', 'LPG충전소', 'LPG 충전소', '가스충전소') or leads:
                    state['review'].append({'job_id': job['id'], 'bank_record': bank, 'checked_at': checked,
                                            'independent_fuel_candidate_ids': leads,
                                            'reason': 'Independent exact business/address/category evidence incomplete; do not exclude by bank category alone'})
        if len(job['observed_ids']) == total:
            job.update(status='done', result='no_match_not_nonmembership' if not total else 'observations_saved')
            completed_recheck(state, job, checked)
        elif page >= 100:
            raise ValueError('Page bound exceeded')
        else:
            job['page'] += 1
        return json.dumps({'checked_at': checked, 'total': total, 'page': page, 'rows': rows}, ensure_ascii=False).encode(), 'json'
    if job['kind'] == 'annual_page':
        dates = re.findall(r'전국 온누리상품권 가맹점 현황_(\d{8})', response.text)
        button = re.search(r"fn_fileDataDown\(\s*'3060079'\s*,\s*'(uddi:[a-fA-F0-9-]+)'\s*,\s*'([^']*)'\s*,\s*'(\d+)'\s*,\s*'2'\s*\)", response.text)
        if not dates or not button:
            raise ValueError('Official portal download metadata changed')
        detail, attachment, sequence = button.groups()
        new = {'kind': 'annual_metadata', 'source': 'datagov', 'region': '전남', 'source_date': max(dates),
               'data': {'publicDataPk': '3060079', 'publicDataDetailPk': detail, 'atchFileId': attachment,
                        'fileDetailSn': sequence, 'publicDataTyCode': 'PR0051'}}
        add_job(state, new)
        job.update(status='done', result='public_download_metadata_discovered')
    elif job['kind'] == 'annual_metadata':
        metadata = response.json()
        if not isinstance(metadata, dict):
            raise ValueError('Invalid official attachment response')
        file_id, sequence = metadata.get('atchFileId', ''), str(metadata.get('fileDetailSn', ''))
        if metadata.get('status') is not True or not re.fullmatch(r'FILE_\d+', file_id) or not sequence.isdigit():
            raise ValueError('Invalid official attachment metadata')
        add_job(state, {'kind': 'annual_download', 'source': 'datagov', 'region': '전남',
                        'source_date': job['source_date'], 'file_id': file_id, 'sequence': sequence})
        job.update(status='done', result='public_attachment_discovered')
    elif job['kind'] == 'annual_download':
        try:
            from official_onnuri import parse_csv
        except ModuleNotFoundError:
            from scripts.official_onnuri import parse_csv
        date = job['source_date']
        if re.fullmatch(r'\d{8}', date):
            date = datetime.strptime(date, '%Y%m%d').date().isoformat()
        keys = {(f['region'], name_key(f['상호명'])) for f in commercial}
        for c in state.get('survey_inventory', {}).get('annual_candidates', []):
            keys.update((area, name_key(c['row']['가맹점명'])) for area in c['possible_regions'])
        snapshot = parse_csv(response.content, date, checked, response.url, keys)
        job.update(status='done', result='official_file_downloaded', sha256=snapshot['sha256'],
                   total_rows=snapshot['total_rows'], source_date=date)
        if state.get('survey_inventory'):
            current = state['survey_inventory']
            fuel = {**commercial_source, 'rows': commercial}
            historic = {r['region']: r['historic_point_lookup'] for r in current['regions']}
            inventory = make_inventory(current['known_stations'], fuel, snapshot, state['region_order'], historic)
            install_survey(state, inventory, survey_jobs(inventory, fuel, state['region_order']))
            for area in state['region_order']:
                state['coverage_checks'][area]['annual_inventory'] = {
                    'status': 'complete', 'evidence': [snapshot['source_url'], snapshot['sha256']],
                    'checked_at': checked, 'source_date': snapshot['source_date'],
                    'scope': 'latest advertised public snapshot downloaded; not all current merchants'}
        # The whole file is retained; names alone never authorize publication.
        return response.content, 'csv'
    return json.dumps({'checked_at': checked, 'kind': job['kind'], 'sha256': hashlib.sha256(response.content).hexdigest()}, ensure_ascii=False).encode(), 'json'


def add_job(state, raw):
    identity = fingerprint(raw)
    if not any(j['id'] == identity for j in state['jobs']):
        state['jobs'].append({**raw, 'id': identity, 'status': 'pending', 'attempts': 0, 'page': 1, 'observed_ids': []})


def configure_regions(state, policy):
    order = policy.get('region_order')
    if order is None:
        return
    if not order or len(set(order)) != len(order):
        raise ValueError('Invalid regional collection order')
    if any(j.get('region') not in order for j in state['jobs']):
        raise ValueError('Job region missing from configured order')
    state.setdefault('initial_scope', state['scope'])
    state['scope'] = 'strictly sequential regional fuel-merchant verification; not a geographic census'
    state['region_order'] = list(order)
    receipts = state.setdefault('regional_reviews', {})
    for area in order:
        receipts.setdefault(area, {'status': 'pending', 'evidence': [], 'checked_at': None})


def merge_plan(state, plan):
    inventory = plan.get('survey_inventory')
    if not inventory:
        return
    install_survey(state, inventory, plan['jobs'])
    for gap in state.get('source_gaps', []):
        if gap.get('status') == 'needs_source_inventory' and gap.get('region'):
            gap.setdefault('gap_id', 'market-coverage:' + gap['region'])
    identities = {g.get('gap_id') or g.get('candidate_id') for g in state['source_gaps']}
    for gap in plan.get('source_gaps', []):
        identity = gap.get('gap_id') or gap.get('candidate_id')
        if identity not in identities:
            state['source_gaps'].append(dict(gap))
            identities.add(identity)
    state.setdefault('initial_plan_id', state['plan_id'])
    state['plan_id'] = plan['id']
    applied = state.setdefault('applied_plans', [])
    if plan['id'] not in applied:
        applied.append(plan['id'])


def regional_progress(state):
    order = state.get('region_order', [])
    if not order:
        return None
    active = None
    rows = []
    jobs_by_id = {j['id']: j for j in state['jobs']}
    annual_regions = {c['candidate_id']: candidate_regions(c, state.get('candidate_resolutions', {}).get(c['candidate_id']))
                      for c in state.get('survey_inventory', {}).get('annual_candidates', [])}
    unresolved = lambda item: item.get('status') not in ('resolved', 'excluded')
    for area in order:
        def covers(label, candidate_id=None):
            if candidate_id in annual_regions and area not in annual_regions[candidate_id]:
                return False
            return not label or label == area or label == '전남광주' and area in ('전남', '광주')
        jobs = [j for j in state['jobs'] if j.get('region') == area]
        gaps = [g for g in state.get('source_gaps', []) if unresolved(g) and
                    covers(g.get('region'), g.get('candidate_id'))]
        reviews = [r for r in state['review'] if unresolved(r) and
                   covers(r.get('region') or jobs_by_id.get(r.get('job_id'), {}).get('region'))]
        receipt = state.get('regional_reviews', {}).get(area, {})
        verified = receipt.get('status') == 'complete' and bool(receipt.get('evidence')) and bool(receipt.get('checked_at'))
        pending = sum(j['status'] not in TERMINAL for j in jobs)
        failed = sum(j['status'] in ('needs_review', 'blocked') for j in jobs)
        survey = survey_progress(state, area)
        ready = verified and not (pending or failed or gaps or reviews) and survey.get('standard_checks_complete', True)
        if active is None and ready:
            status = 'complete'
        elif active is None:
            active = area
            status = 'collecting' if pending else 'needs_review'
        else:
            status = 'queued'
        rows.append({'region': area, 'status': status, 'jobs_total': len(jobs),
                     'jobs_remaining': pending, 'jobs_needing_review': failed,
                     'source_gaps': len(gaps), 'review_records': len(reviews),
                     'inventory_reviewed': bool(verified), **survey})
    return {'active_region': active, 'regions': rows}


def summarize(state):
    remaining = [j for j in state['jobs'] if j['status'] not in TERMINAL]
    waiting = any(r.get('status') not in ('resolved', 'excluded') for r in state['review'] + state.get('source_gaps', [])) or any(j['status'] in ('needs_review', 'blocked') for j in state['jobs'])
    state['status'] = 'running' if remaining else 'needs_attention' if waiting else 'complete'
    progress = regional_progress(state)
    if progress:
        current = next((r for r in progress['regions'] if r['region'] == progress['active_region']), None)
        state['status'] = 'running' if current and current['status'] == 'collecting' else 'needs_attention' if current or waiting else 'complete'
    result = {'status': state['status'], 'jobs_total': len(state['jobs']),
            'jobs_done': sum(j['status'] == 'done' for j in state['jobs']),
            'jobs_remaining': len(remaining), 'review_records': len(state['review']),
            'evidence_records': len(state['evidence']), 'source_gaps': len(state.get('source_gaps', [])),
            'source_status': {k: v['status'] for k, v in state['sources'].items()}}
    if progress:
        result.update(progress, region_order=state['region_order'])
    if state.get('survey_inventory'):
        result.update(counts_are_not_regional_totals=True,
                      recheck_after=state['survey_inventory']['recheck_after'], survey_revision=2)
    if state.get('effective_collection_limits'):
        result['collection_limits'] = state['effective_collection_limits']
    if state.get('collection_schedule'):
        result['collection_schedule'] = state['collection_schedule']
    return result


DISCOVERY_PURPOSES = {'annual_reverse_discovery', 'full_inventory_identity_followup'}


def ordered_jobs(state, policy, run_id, active_region):
    """Give discovery a turn without moving regions or rewriting checkpoints.

    Only order KB slots; portal dependency jobs keep their existing positions.
    Availability, quotas, blocked sources and page handling are checked by run.
    """
    if not active_region:
        return list(state['jobs'])
    target = max(0, int(policy.get('discovery_first_requests_per_run', 0)))
    jobs_by_id = {j['id']: j for j in state['jobs']}
    used = sum(a.get('run_id') == run_id and a.get('source') == 'kbcard' and
               jobs_by_id.get(a.get('job_id'), {}).get('purpose') in DISCOVERY_PURPOSES
               for a in state['attempts'])
    if used >= target:
        return list(state['jobs'])
    favored = {j['id'] for j in state['jobs'] if j['status'] == 'pending' and
               j['source'] == 'kbcard' and j.get('region') == active_region and
               j.get('purpose') in DISCOVERY_PURPOSES}
    kb = [j for j in state['jobs'] if j['source'] == 'kbcard']
    kb.sort(key=lambda j: j['id'] not in favored)
    ordered = iter(kb)
    return [next(ordered) if j['source'] == 'kbcard' else j for j in state['jobs']]


def collection_schedule(state, policy, now):
    """Share the run cadence across manual/scheduled runs and zero-request upkeep."""
    interval = int(policy.get('minimum_run_interval_seconds', 0))
    if interval < 0:
        raise ValueError('Invalid run interval')
    attempts = state['attempts']
    latest = attempts[-1] if attempts else None
    started = min(a['at'] for a in attempts if a.get('run_id') == latest['run_id']) \
        if latest and latest.get('run_id') else latest['at'] if latest else None
    allowed = started + interval if started is not None else 0
    return {'minimum_run_interval_seconds': interval, 'last_collection_started_at': started,
            'next_allowed_at': allowed, 'waiting': now < allowed}


def run(state, store, policy, session, commercial, commercial_source, *, clock=time.time, sleeper=time.sleep, max_requests=5):
    maximum = min(max_requests, run_limit(state, policy, clock()))
    if maximum < 0:
        raise ValueError('Invalid request limit')
    configure_regions(state, policy)
    # An interrupted reservation consumed budget but never proves success.
    for attempt in state['attempts']:
        if attempt['status'] == 'reserved':
            attempt['status'] = 'uncertain'
            attempt['finished_at'] = clock()
            job = next(j for j in state['jobs'] if j['id'] == attempt['job_id'])
            job.update(status='needs_review', reason='Interrupted attempt; not retried automatically')
            observe(state, policy, attempt['source'], attempt, clock())
    maximum = min(max_requests, run_limit(state, policy, clock()))
    if collection_schedule(state, policy, clock())['waiting']:
        maximum = 0
    session.trust_env = False
    progress = regional_progress(state)
    for job in state['jobs']:
        source = state['sources'][job['source']]
        if job['status'] == 'pending' and source['status'] in ('blocked', 'needs_review') and \
                (not progress or job.get('region') == progress['active_region']):
            job.update(status='blocked', reason=source.get('reason', 'Source unavailable'))
    count = 0
    run_id = uuid.uuid4().hex
    while count < maximum:
        now = clock()
        chosen, earliest = None, None
        progress = regional_progress(state)
        for job in ordered_jobs(state, policy, run_id, progress['active_region'] if progress else None):
            if job['status'] != 'pending':
                continue
            if progress and job.get('region') != progress['active_region']:
                continue
            source = state['sources'][job['source']]
            quota = limits(state, policy, job['source'], now)
            if source['status'] in ('blocked', 'needs_review'):
                job.update(status='blocked', reason=source.get('reason', 'Source unavailable'))
                continue
            if source['status'] == 'cooldown' and source['next_allowed_at'] > now:
                continue
            recent = [a for a in state['attempts'] if a['source'] == job['source'] and now-a.get('finished_at', a['at']) < 86400]
            source_run_count = sum(a.get('run_id') == run_id and a['source'] == job['source'] for a in state['attempts'])
            if len(recent) >= quota['requests_per_24h'] or source_run_count >= quota['requests_per_run']:
                continue
            allowed = max(source.get('next_allowed_at', 0), max((a['at'] + quota['interval_seconds'] for a in recent), default=0))
            if allowed > now:
                earliest = min(earliest or allowed, allowed)
                continue
            chosen = job
            break
        if chosen is None:
            # Wait only inside this bounded invocation, never through a long
            # provider cooldown. Scheduled runs resume persisted timers.
            wait_bound = max(limits(state, policy, name, clock())['interval_seconds'] for name in state['sources'])
            if earliest is not None and earliest-clock() <= wait_bound and count:
                sleeper(max(0, earliest-clock()))
                continue
            break
        job = chosen
        method, url, kwargs = request_for(job)
        source = state['sources'][job['source']]
        expected_host = {'kbcard': 'card.kbcard.com', 'datagov': 'www.data.go.kr',
                         'kakao_local': 'k-skill-proxy.nomadamas.org'}.get(job['source'])
        if urlparse(url).hostname != expected_host:
            raise ValueError('Unexpected source host')
        source.update(status='active', next_allowed_at=now + quota['interval_seconds'])
        attempt = {'id': uuid.uuid4().hex[:24], 'job_id': job['id'], 'source': job['source'],
                   'at': now, 'status': 'reserved', 'run_id': run_id,
                   'request': {'method': method, 'url': url, **kwargs}}
        state['attempts'].append(attempt)
        job['attempts'] += 1
        store.save(state)  # Must succeed remotely before any target request.
        count += 1
        blob = None
        try:
            attempt['request_started_at'] = clock()
            response = session.request(method, url, **kwargs, timeout=(10, 45), allow_redirects=False)
            attempt['network_duration_seconds'] = max(0, clock()-attempt['request_started_at'])
            attempt.update(http_status=response.status_code, response_sha256=hashlib.sha256(response.content).hexdigest())
            if job['source'] == 'kakao_local':
                # Preserve the one response even if its contract fails; no retry
                # through a different route, host or transport is attempted.
                blob = (attempt['id'] + '.json', json.dumps({'checked_at': stamp(clock()),
                        'http_status': response.status_code, 'raw_response': response.text}, ensure_ascii=False).encode())
            blocked = response.status_code in (401, 403) or 'request blocked' in response.text[:4096].lower()
            if blocked:
                source.update(status='blocked', reason='Explicit access rejection at ' + stamp(clock()))
                job.update(status='blocked', reason=source['reason'])
                attempt['status'] = 'blocked'
            elif response.status_code == 429:
                until = retry_after(response.headers.get('Retry-After'), clock())
                source.update(status='cooldown' if until is not None else 'needs_review',
                              next_allowed_at=max(until or 0, source['next_allowed_at']), reason='HTTP 429')
                attempt['status'] = 'rate_limited'
            elif response.status_code in (500, 502, 503, 504):
                if job['source'] == 'kakao_local':
                    attempt['status'] = 'needs_review'
                    source.update(status='needs_review', reason='Independent place relay error; manual review required')
                    job.update(status='needs_review', reason=source['reason'])
                else:
                    attempt['status'] = 'transient_error'
                    job.update(status='pending' if job['attempts'] < 2 else 'needs_review', reason='Upstream server error')
                    source['next_allowed_at'] = max(source['next_allowed_at'], clock() + 21600)
            elif 300 <= response.status_code < 400:
                job.update(status='needs_review', reason='Redirect not followed automatically')
                attempt['status'] = 'needs_review'
            else:
                response.raise_for_status()
                content, extension = handle_response(state, job, response, clock(), commercial, commercial_source)
                blob = (attempt['id'] + '.' + extension, content)
                attempt['status'] = 'done'
        except (requests.Timeout, requests.ConnectionError):
            attempt['status'] = 'transient_error'
            job.update(status='pending' if job['attempts'] < 2 else 'needs_review', reason='Network failure')
            source['next_allowed_at'] = max(source['next_allowed_at'], clock() + 21600)
        except (requests.RequestException, ValueError, KeyError, TypeError, UnicodeError) as exc:
            attempt['status'] = 'needs_review'
            job.update(status='needs_review', reason=type(exc).__name__ + ': ' + str(exc)[:250])
            if job['source'] == 'kakao_local':
                source.update(status='needs_review', reason='Independent place response requires manual review')
        attempt['finished_at'] = clock()
        attempt.setdefault('network_duration_seconds', max(0, clock()-attempt.get('request_started_at', clock())))
        observe(state, policy, job['source'], attempt, clock())
        quota = limits(state, policy, job['source'], clock())
        # A reservation precedes the Git push. Wait from response completion
        # so uneven push/network times cannot shorten the transmission gap.
        source['next_allowed_at'] = max(source['next_allowed_at'], clock() + quota['interval_seconds'])
        store.save(state, blob)
        if attempt['status'] != 'done':
            break
    limits_snapshot(state, policy, clock())
    state['collection_schedule'] = collection_schedule(state, policy, clock())
    state['summary'] = summarize(state)
    jobs_by_id = {j['id']: j for j in state['jobs']}
    purposes = Counter(jobs_by_id[a['job_id']].get('purpose', jobs_by_id[a['job_id']]['kind'])
                       for a in state['attempts'] if a.get('run_id') == run_id)
    state['last_run'] = {'id': run_id, 'checked_at': stamp(clock()), 'requests': count,
                         'request_purposes': dict(purposes)}
    store.save(state)
    return state['summary']


def merge_sources(state, policy):
    """Add a separately scoped source without resetting any previous source."""
    for source, setting in policy['sources'].items():
        current = state['sources'].setdefault(source, {**setting, 'next_allowed_at': 0})
        if setting['status'] == 'blocked':
            current.update(status='blocked', reason=setting['reason'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--state-dir', type=Path, required=True)
    ap.add_argument('--plan', type=Path, default=ROOT/'output/collector_plan.json')
    ap.add_argument('--max-requests', type=int, default=4)
    ap.add_argument('--persist-git', action='store_true')
    args = ap.parse_args()
    policy = read(POLICY)
    store = Store(args.state_dir, args.persist_git)
    path = args.state_dir/'state.json'
    plan = read(args.plan)
    state = read(path) if path.exists() else initial_state(plan, policy)
    merge_plan(state, plan)
    # Persist current restrictions; changing a config to active never clears a
    # previous rejection. Unblocking requires a separately reviewed state edit.
    merge_sources(state, policy)
    with gzip.open(ROOT/'config/collector-fuel-index.json.gz', 'rt', encoding='utf-8') as stream:
        fuel = json.load(stream)
    sync_mapped_inventory(state, read(ROOT/'output/gas_stations.json'), fuel, policy.get('region_order', []))
    store.save(state)
    with requests.Session() as session:
        summary = run(state, store, policy, session, fuel['rows'], {k: v for k, v in fuel.items() if k != 'rows'}, max_requests=args.max_requests)
    print(json.dumps(summary, ensure_ascii=False))
    summary_path = args.state_dir/'summary.json'
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
