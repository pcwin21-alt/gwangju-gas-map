"""Comparable regional inputs and post-renewal checks, without network access.

Annual rows and physical businesses are discovery inputs, never membership.
Historic empty queries are not a present-day exclusion. Issuer evidence does
not renew paper/QR or operator verification dates on an existing map record.
"""
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    from nationwide import name_key, region, row_id, non_vehicle, valid_coords
    from discover_address_candidates import address_key
    from supplemental_onnuri import meters
except ModuleNotFoundError:
    from scripts.nationwide import name_key, region, row_id, non_vehicle, valid_coords
    from scripts.discover_address_candidates import address_key
    from scripts.supplemental_onnuri import meters

ROOT = Path(__file__).resolve().parents[1]
RECHECK_AFTER = '2026-11-01T00:00:00+09:00'
REQUIRED_CHECKS = ['annual_inventory', 'location_inventory', 'annual_identities', 'membership_rechecks', 'market_coverage']


def load_compressed(name):
    with gzip.open(ROOT/'config'/name, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]


def query_key(job):
    if job['kind'] == 'kb_search':
        t = job['target']
        return digest([job['kind'], job['source'], job['region'], round(float(t['lat']), 6),
                       round(float(t['lng']), 6), t['keyword']])
    if job['kind'] == 'annual_page':
        return digest([job['kind'], job['source'], job['region']])
    return digest({k: v for k, v in job.items() if k not in
                   ('id', 'status', 'attempts', 'page', 'observed_ids', 'logical_key')})


def after_cutoff(value, cutoff=RECHECK_AFTER):
    try:
        checked = datetime.fromisoformat(value)
        return checked.tzinfo is not None and checked >= datetime.fromisoformat(cutoff)
    except (TypeError, ValueError):
        return False


def map_links(evidence, known):
    """A source's exact verified identity can refresh only the same premise."""
    c, f = evidence['bank_record']['content'], evidence.get('commercial_record')
    if not f:
        return []
    names = {name_key(c['title']), name_key(f['상호명'])}
    address = address_key(f['도로명주소'])
    if address is None:
        return []
    kind = 'lpg' if f['상권업종소분류코드'] == 'G21402' else 'liquid'
    return [s['id'] for s in known if s['region'] == region(c['address']) and
            s['fuel_kind'] == kind and valid_coords(s['lat'], s['lng']) and
            meters((s['lat'], s['lng']), (float(f['위도']), float(f['경도']))) <= 100 and
            address_key(s['address']) == address and
            names & {name_key(s['name']), *(name_key(a) for a in s.get('aliases') or [])}]


def make_inventory(stations, fuel, annual, order, historical=None):
    known = [{k: s.get(k) for k in ('id', 'name', 'aliases', 'address', 'region', 'lat', 'lng', 'fuel_kind')}
             | {'payment_types': ['onnuri'], 'prior_verification': s.get('prior_verification', s.get('verification', {}).get('onnuri', {}))}
             for s in stations if 'onnuri' in s.get('payment_types', [])]
    locations = defaultdict(list)
    for f in fuel['rows']:
        locations[(f['region'], name_key(f['상호명']))].append(f)
    candidates = []
    seen = set()
    for row in annual['rows']:
        cid = row_id(row)
        if cid in seen:
            continue
        seen.add(cid)
        areas = ['전남', '광주'] if row['소재지'] == '전남광주' else [region(row['소재지'])]
        excluded = non_vehicle(row)
        matches = []
        for area in areas:
            matches.extend(locations.get((area, name_key(row['가맹점명'])), []))
        mapped = [s['id'] for s in known if s['region'] in areas and
                  (cid in s['prior_verification'].get('candidate_ids', []) or
                   name_key(row['가맹점명']) in {name_key(s['name']), *(name_key(a) for a in s.get('aliases') or [])} and
                   name_key(row['소속 시장명(또는 상점가)']) == name_key(s['prior_verification'].get('market', '')))]
        candidates.append({'candidate_id': cid, 'row': row, 'possible_regions': areas,
                           'status': 'excluded_non_vehicle' if excluded else 'discovery_only',
                           'mapped_ids': mapped,
                           'location_ids': sorted({f['상가업소번호'] for f in matches}),
                           'paper': row['지류형 가맹 여부'], 'digital': row['디지털형 가맹 여부']})
    regions = []
    for area in order:
        records = [f for f in fuel['rows'] if f['region'] == area]
        registered = [s for s in known if s['region'] == area]
        related = [c for c in candidates if area in c['possible_regions']]
        regions.append({'region': area, 'physical_business_records': len(records),
                        'physical_unique_addresses': len({address_key(f['도로명주소']) for f in records if address_key(f['도로명주소']) is not None}),
                        'physical_unparsed_address_records': sum(address_key(f['도로명주소']) is None for f in records),
                        'mapped_records': len(registered),
                        'mapped_statuses': dict(Counter(s['prior_verification'].get('status', 'unknown') for s in registered)),
                        'annual_discovery_rows': len(related),
                        'annual_ambiguous_region_rows': sum(len(c['possible_regions']) > 1 for c in related),
                        'annual_non_vehicle_exclusions': sum(c['status'] == 'excluded_non_vehicle' for c in related),
                        'historic_point_lookup': (historical or {}).get(area, {}),
                        'physical_inventory_status': 'discovery pool; not a completed current lookup',
                        'scope': 'input inventory only; none of these counts estimates current regional membership'})
    return {'schema_version': 2, 'recheck_after': RECHECK_AFTER,
            'scope': 'same regional checklist; no total merchant estimate or current census claim',
            'known_stations': known, 'annual_candidates': candidates,
            'annual_source': {k: v for k, v in annual.items() if k != 'rows'},
            'location_source': {k: v for k, v in fuel.items() if k != 'rows'},
            'regions': regions, 'required_checks': REQUIRED_CHECKS}


def survey_jobs(inventory, fuel, order):
    jobs = [{'kind': 'annual_page', 'source': 'datagov', 'region': order[0]}]
    # Unfiltered results also catch legal company names and non-fuel categories.
    # Promotion remains independently exact; neighboring stores cannot refresh
    # the chosen station's membership just because the query returned rows.
    for s in inventory['known_stations']:
        if valid_coords(s['lat'], s['lng']):
            jobs.append({'kind': 'kb_search', 'source': 'kbcard', 'region': s['region'],
                         'station_ids': [s['id']], 'purpose': 'post_renewal_recheck',
                         'target': {'name': s['name'], 'keyword': '', 'lat': s['lat'], 'lng': s['lng'],
                                    'address': s['address'], 'coordinate_source_id': s['id']}})
    by_id = {f['상가업소번호']: f for f in fuel['rows']}
    for c in inventory['annual_candidates']:
        if c['status'] == 'excluded_non_vehicle' or c['mapped_ids']:
            continue
        for fid in c['location_ids']:
            f = by_id[fid]
            if valid_coords(f['위도'], f['경도']):
                jobs.append({'kind': 'kb_search', 'source': 'kbcard', 'region': f['region'],
                             'candidate_ids': [c['candidate_id']], 'purpose': 'annual_reverse_discovery',
                             'target': {'name': c['row']['가맹점명'], 'keyword': '',
                                        'lat': float(f['위도']), 'lng': float(f['경도']),
                                        'address': f['도로명주소'], 'coordinate_source_id': fid}})
    unique = {}
    for job in jobs:
        key = query_key(job)
        if key not in unique:
            unique[key] = {**job, 'logical_key': key}
        else:
            for field in ('station_ids', 'candidate_ids'):
                unique[key][field] = sorted(set(unique[key].get(field, []) + job.get(field, [])))
    return sorted(unique.values(), key=lambda j: (order.index(j['region']), j['kind'] != 'annual_page',
                                                  j.get('purpose') != 'post_renewal_recheck'))


def merge_jobs(state, jobs):
    """Install new work without resetting pages, failures, budgets or evidence."""
    known = {query_key(j): j for j in state['jobs']}
    for raw in jobs:
        key = query_key(raw)
        if key in known:
            for field in ('station_ids', 'candidate_ids'):
                known[key][field] = sorted(set(known[key].get(field, []) + raw.get(field, [])))
            continue
        value = {**raw, 'id': key, 'logical_key': key, 'status': 'pending',
                 'attempts': 0, 'page': 1, 'observed_ids': []}
        state['jobs'].append(value)
        known[key] = value


def refresh_rechecks(state):
    inv = state.get('survey_inventory')
    if not inv:
        return
    checks = state.setdefault('membership_rechecks', {})
    for e in state['evidence']:
        if not after_cutoff(e['checked_at'], inv['recheck_after']):
            continue
        for sid in map_links(e, inv['known_stations']):
            prior = checks.get(sid, {})
            if e['checked_at'] >= prior.get('checked_at', ''):
                checks[sid] = {'status': 'confirmed_in_issuer_scope', 'issuer': 'kbcard',
                               'checked_at': e['checked_at'], 'source_url': e['source_url'],
                               'bank_id': e['bank_record']['content']['franchiseNo'],
                               'other_payment_methods': 'not_reverified'}
    # A valid recent independent observation may reuse the query for that
    # same station; do not issue another full page just to fill a checklist.
    for j in state['jobs']:
        targets = j.get('station_ids', [])
        if j['status'] == 'pending' and j.get('purpose') == 'post_renewal_recheck' and targets and not j.get('candidate_ids') and all(checks.get(sid, {}).get('status') == 'confirmed_in_issuer_scope' for sid in targets):
            j.update(status='done', result='recent_exact_issuer_evidence_reused')


def completed_recheck(state, job, checked):
    refresh_rechecks(state)
    if not state.get('survey_inventory'):
        return
    checks = state.setdefault('membership_rechecks', {})
    for sid in job.get('station_ids', []):
        if checks.get(sid, {}).get('status') == 'confirmed_in_issuer_scope':
            continue
        checks[sid] = {'status': 'needs_review_not_found', 'checked_at': checked,
                       'job_id': job['id'], 'nonmembership': 'not_established'}
        if not any(r.get('station_id') == sid and r.get('job_id') == job['id'] for r in state['review']):
            state['review'].append({'region': job['region'], 'station_id': sid, 'job_id': job['id'],
                                    'checked_at': checked, 'reason': 'No independently matched current issuer record; preserve previous station'})


def install_survey(state, inventory, jobs):
    # A live downloaded snapshot always outranks the bundled dated baseline.
    current = state.get('survey_inventory')
    if current and current['annual_source'].get('retrieved_at', '') > inventory['annual_source'].get('retrieved_at', ''):
        inventory = {**inventory, 'annual_source': current['annual_source'],
                     'annual_candidates': current['annual_candidates']}
        for row in inventory['regions']:
            old = next((r for r in current['regions'] if r['region'] == row['region']), {})
            for key in ('annual_discovery_rows', 'annual_ambiguous_region_rows', 'annual_non_vehicle_exclusions'):
                if key in old:
                    row[key] = old[key]
    state['survey_inventory'] = inventory
    merge_jobs(state, jobs)
    gap_candidates = {g.get('candidate_id') for g in state.get('source_gaps', [])}
    for c in inventory['annual_candidates']:
        if c['status'] != 'excluded_non_vehicle' and not c['mapped_ids'] and c['candidate_id'] not in gap_candidates:
            state.setdefault('source_gaps', []).append({
                'gap_id': 'annual-identity:' + c['candidate_id'], 'candidate_id': c['candidate_id'],
                'region': c['row']['소재지'], 'name': c['row']['가맹점명'],
                'status': 'needs_identity', 'reason': 'Annual identity needs independent same-premise linkage or documented exclusion'})
    checks = state.setdefault('coverage_checks', {})
    for r in inventory['regions']:
        fields = checks.setdefault(r['region'], {})
        for check in REQUIRED_CHECKS:
            fields.setdefault(check, {'status': 'pending', 'evidence': [], 'checked_at': None})
        fields['location_inventory'] = {'status': 'complete', 'evidence': [inventory['location_source']['source_url']],
                                        'checked_at': inventory['location_source']['source_date'],
                                        'scope': 'dated physical source inventory only; not current membership'}
    refresh_rechecks(state)


def survey_progress(state, area):
    inv = state.get('survey_inventory')
    if not inv:
        return {}
    known = [s for s in inv['known_stations'] if s['region'] == area]
    checks = state.get('membership_rechecks', {})
    counts = Counter(checks.get(s['id'], {}).get('status', 'pending') for s in known)
    coverage = state.get('coverage_checks', {}).get(area, {})
    required = [name for name in REQUIRED_CHECKS if name not in ('membership_rechecks', 'annual_identities')]
    missing = [name for name in required if not (coverage.get(name, {}).get('status') == 'complete' and
                coverage.get(name, {}).get('evidence') and coverage.get(name, {}).get('checked_at'))]
    if counts.get('confirmed_in_issuer_scope', 0) != len(known):
        missing.append('membership_rechecks')
    unresolved = []
    for c in inv['annual_candidates']:
        if area not in c['possible_regions'] or c['status'] == 'excluded_non_vehicle' or c['mapped_ids']:
            continue
        resolved = state.get('candidate_resolutions', {}).get(c['candidate_id'], {})
        if not (resolved.get('status') in ('linked', 'excluded_non_vehicle', 'duplicate') and
                resolved.get('evidence') and resolved.get('checked_at')):
            unresolved.append(c['candidate_id'])
    if unresolved:
        missing.append('annual_identities')
    return {'mapped_records_to_recheck': len(known), 'membership_check_status': dict(counts),
            'unresolved_annual_identities': len(unresolved),
            'missing_standard_checks': missing, 'standard_checks_complete': not missing,
            'scope': 'issuer-scoped rechecks; paper/QR/operator freshness not inferred'}


def sync_mapped_inventory(state, stations, fuel, order):
    """Newly published map identities join the next run's common denominator."""
    current = state.get('survey_inventory')
    if not current:
        return
    annual = {**current['annual_source'], 'rows': [c['row'] for c in current['annual_candidates']]}
    historic = {r['region']: r['historic_point_lookup'] for r in current['regions']}
    inventory = make_inventory(stations, fuel, annual, order, historic)
    install_survey(state, inventory, survey_jobs(inventory, fuel, order))
