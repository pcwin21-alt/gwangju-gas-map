"""Collect geographic grids sequentially, Jeonnam first and Seoul last.

Collection alone never publishes a map. Completed regional snapshots are ready
for identity/industry review and augmentation of the existing national data.
Run again with the same folder to resume; failures stop the regional sequence.
"""
import argparse
import json
from pathlib import Path

try:
    from grid_search import OUT, write, now, run, summarize, digest
    from live_merchants import address_key
    from refresh_regions import ORDER
except ModuleNotFoundError:
    from scripts.grid_search import OUT, write, now, run, summarize, digest
    from scripts.live_merchants import address_key
    from scripts.refresh_regions import ORDER


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default=str(OUT/'grid_search/region_order.json'))
    parser.add_argument('--cache-root', default=str(OUT/'grid_cache'))
    parser.add_argument('--fuel-addresses', default=str(OUT/'grid_search/fuel_addresses_202606.json'))
    parser.add_argument('--stop-after', choices=ORDER, default='서울')
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    if manifest['order'] != ORDER or [r['region'] for r in manifest['plans']] != ORDER:
        raise ValueError('Expected Jeonnam-first, Seoul-last plan order')
    annual = json.loads((OUT/'onnuri_official_snapshot.json').read_text(encoding='utf-8'))['rows']
    known = {address_key(a) for a in json.loads(Path(args.fuel_addresses).read_text(encoding='utf-8'))}
    for filename in ('station_locations.json', 'lpg_locations.json'):
        known.update(address_key(r.get('LCTN_ROAD_NM')) for r in json.loads((OUT/filename).read_text(encoding='utf-8'))['rows'])
    known.discard(None)
    folder = Path(args.manifest).resolve().parent
    completed = []
    for entry in manifest['plans']:
        area = entry['region']
        plan = json.loads((OUT.parent/entry['plan']).read_text(encoding='utf-8'))
        if plan['region'] != area or plan['tile_count'] != entry['planned_tiles']:
            raise ValueError('Plan metadata mismatch')
        suffix = 'jeonnam' if area == '전남' else area
        stamp = plan['created_at'][:10].replace('-', '')
        path = folder / f'{suffix}_snapshot_{stamp}.json'
        if path.exists():
            snapshot = json.loads(path.read_text(encoding='utf-8'))
            if (snapshot['status'] != 'complete' or snapshot['plan_sha256'] != digest(plan) or
                    snapshot['completed_tiles'] != plan['tile_count']):
                raise ValueError('Existing snapshot is incomplete or belongs to another plan')
        else:
            cache = Path(args.cache_root)/f'{suffix}_{stamp}'
            write(folder/'progress.json', {'status':'running', 'updated_at':now(), 'order':ORDER,
                  'completed':completed, 'current_region':area, 'current_cache':str(cache.resolve()),
                  'remaining':ORDER[len(completed):], 'publication':'requires_evidence_review'})
            try:
                results = run(plan, cache, pause=1, workers=1)
                snapshot = summarize(plan, results, annual, known)
                write(path, snapshot)
            except Exception as error:
                write(folder/'progress.json', {'status':'blocked' if isinstance(error, PermissionError) else 'failed', 'updated_at':now(), 'order':ORDER,
                      'completed':completed, 'current_region':area, 'current_cache':str(cache.resolve()),
                      'remaining':ORDER[len(completed):], 'error':type(error).__name__, 'message':str(error)[:400]})
                raise
        completed.append(area)
        write(folder/'progress.json', {'status':'complete' if completed == ORDER else 'partial',
              'updated_at':now(), 'order':ORDER, 'completed':completed, 'remaining':ORDER[len(completed):],
              'publication':'requires_evidence_review'})
        print(f'{area}: completed {snapshot["completed_tiles"]} tiles, {len(snapshot["rows"])} candidates', flush=True)
        if area == args.stop_after:
            break


if __name__ == '__main__':
    main()
