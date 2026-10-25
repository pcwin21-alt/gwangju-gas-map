"""Resolve a review candidate's province, never its address or membership."""
import re
try:
    from nationwide import region
except ModuleNotFoundError:
    from scripts.nationwide import region


def market_key(value):
    # Do not erase legal names, parentheses or reorder words to invent aliases.
    return re.sub(r'\s+', '', value or '')


def resolve_pending_regions(rows, evidence):
    result = []
    for original in rows:
        row = dict(original)
        source_region = row.get('source_region', row.get('region'))
        if source_region != '전남광주' or row.get('status') != 'needs_review':
            result.append(row)
            continue
        matches = [e for e in evidence if market_key(e.get('market')) == market_key(row.get('market'))]
        areas = {region(e.get('reference_address')) for e in matches}
        registry = any(e.get('source_kind') == 'official_market_registry' for e in matches)
        places = {e.get('source_id') for e in matches if e.get('source_kind') == 'official_place_search' and e.get('source_id')}
        supported = len(areas) == 1 and areas <= {'전남', '광주'} and (registry or len(places) >= 2)
        row['source_region'] = source_region
        row['region'] = next(iter(areas)) if supported else '지역 미확정'
        row['region_resolution'] = {
            'status': 'resolved' if supported else 'unresolved',
            'match_basis': 'exact_market_name_consistent_region' if supported else 'insufficient_or_conflicting_market_evidence',
            'evidence': matches,
            'scope': 'province_only_no_station_address_or_membership_inference',
        }
        result.append(row)
    return result
