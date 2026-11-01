"""Build the same regional survey from versioned public inputs; no network."""
import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from incremental_collector import ROOT, POLICY, read
from survey_inventory import make_inventory, survey_jobs, load_compressed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=ROOT/'output/collector_plan.json')
    args = ap.parse_args()
    policy = read(POLICY)
    fuel = load_compressed('collector-fuel-index.json.gz')
    annual = load_compressed('collector-annual-baseline.json.gz')
    stations = read(ROOT/'output/gas_stations.json')
    previous = read(args.output) if args.output.exists() else {}
    historic = previous.get('regional_inventory', {})
    inventory = make_inventory(stations, fuel, annual, policy['region_order'], historic)
    jobs = survey_jobs(inventory, fuel, policy['region_order'])
    plan = {'id': 'regional-standard-survey-20261102-v2',
            'scope': inventory['scope'], 'region_order': policy['region_order'],
            'created_at': datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds'),
            'regional_inventory': historic,
            'cached_observations': previous.get('cached_observations', []),
            'reused_cache_queries': previous.get('reused_cache_queries', 0),
            'survey_inventory': inventory, 'jobs': jobs,
            'source_gaps': [{'gap_id': 'market-coverage:' + area, 'region': area,
                             'status': 'needs_source_inventory',
                             'reason': 'Latest designated-market membership/location coverage requires independent regional review'}
                            for area in policy['region_order']]}
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'jobs': len(jobs), 'mapped_rechecks': len(inventory['known_stations']),
                      'annual_candidates': len(inventory['annual_candidates']),
                      'regions': len(inventory['regions'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
