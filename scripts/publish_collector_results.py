"""Publish only independent exact identity evidence; retain prior map records."""
import argparse
import copy
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from incremental_collector import ROOT, read
    from nationwide import name_key, region
    from supplemental_onnuri import station_from_evidence, apply_evidence, reconcile_ledger
    from refresh_merchants import save, sync_map
except ModuleNotFoundError:
    from scripts.incremental_collector import ROOT, read
    from scripts.nationwide import name_key, region
    from scripts.supplemental_onnuri import station_from_evidence, apply_evidence, reconcile_ledger
    from scripts.refresh_merchants import save, sync_map


def reached_regions(state):
    order = state.get('region_order')
    active = state.get('summary', {}).get('active_region')
    return set(order[:order.index(active)+1] if active else order) if order else None


def attach_rechecks(stations, state):
    stations = copy.deepcopy(stations)
    areas = reached_regions(state)
    for station in stations:
        check = state.get('membership_rechecks', {}).get(station['id'])
        if not check or areas is not None and station.get('region') not in areas:
            continue
        verification = station.get('verification', {}).get('onnuri')
        if verification is not None:
            verification.setdefault('issuer_checks', {})['kbcard'] = check
    return stations


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state-dir', type=Path, required=True)
    args = ap.parse_args()
    state = read(args.state_dir/'state.json')
    old = read(ROOT/'output/gas_stations.json')
    previous = read(ROOT/'output/supplemental_onnuri_evidence.json')
    as_of = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
    merged = {e['bank_record']['content']['franchiseNo']: e for e in previous['rows']}
    areas = reached_regions(state)
    for evidence in state['evidence']:
        if areas is not None and region(evidence['bank_record']['content']['address']) not in areas:
            continue
        station_from_evidence(evidence, as_of)
        fid = evidence['bank_record']['content']['franchiseNo']
        prior = merged.get(fid)
        if prior:
            # Curated special identities must not be replaced by generic source
            # matching. A current exact identity may refresh only the same ID.
            if prior.get('municipal_record') or prior.get('opinet_record') or prior.get('correct_existing_location'):
                continue
            if evidence['checked_at'] <= prior['checked_at']:
                continue
            if name_key(prior['bank_record']['content']['title']) != name_key(evidence['bank_record']['content']['title']):
                continue
            evidence = {**evidence, 'annual_candidate_ids': prior.get('annual_candidate_ids', [])}
        merged[fid] = evidence
    review = read(ROOT/'output/merchant_review.json')
    stations, review, meta = apply_evidence(old, review, list(merged.values()), as_of)
    # The generic supplement re-evaluates stale entries; a failed/empty query
    # must not mutate existing map records. Only genuinely new identities are
    # eligible here. Freshness changes need their own successful-ID evidence.
    old_by_id = {s['id']: s for s in old}
    stations = [old_by_id.get(s['id'], s) for s in stations]
    old_ids = set(old_by_id)
    if not old_ids <= {s['id'] for s in stations}:
        raise ValueError('Collector publication would lose previous station IDs')
    stations = attach_rechecks(stations, state)
    status = read(ROOT/'output/merchant_status.json')
    status['incremental_collection'] = {**state['summary'], 'checked_at': state['last_run']['checked_at'],
                                       'scope': state['scope'], 'new_station_count': sum(s['id'] not in old_ids for s in stations)}
    status['supplemental_onnuri'] = meta
    all_onnuri = [s for s in stations if 'onnuri' in s.get('payment_types', [])]
    status['onnuri']['record_counts'] = {
        'mapped_records': len(all_onnuri),
        'confirmed_history': sum(s['verification']['onnuri'].get('status') == 'confirmed' for s in all_onnuri),
        'stale_history': sum(s['verification']['onnuri'].get('status') == 'stale' for s in all_onnuri),
        'scope': 'historical map records; not all currently valid nationwide merchants'}
    status['onnuri']['pending_count'] = len({r['candidate_id'] for r in review if r.get('show_pending') and r.get('candidate_id')})
    ledger = read(ROOT/'output/nationwide_candidates.json')
    ledger['rows'] = reconcile_ledger(ledger['rows'], stations)
    previous['rows'] = list(merged.values())
    save('supplemental_onnuri_evidence.json', previous)
    save('gas_stations.json', stations); save('merchant_review.json', review)
    save('merchant_status.json', status); save('nationwide_candidates.json', ledger)
    sync_map(stations, status)
    print('Added stations:', sum(s['id'] not in old_ids for s in stations))


if __name__ == '__main__':
    main()
