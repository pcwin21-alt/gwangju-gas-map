"""Offline, station-targeted sampling plan. Does not make network requests.

This supplements the geographic grid; it cannot establish regional completeness.
"""
import argparse
import json
from pathlib import Path
from grid_search import distance_km, check_tile

OUT = Path(__file__).resolve().parents[1] / 'output'


def cover(points, completed, radius=1.8):
    if not 0 < radius <= 1.8:
        raise ValueError('Keep at least 200 m margin inside the public 2 km radius')
    pending = {i for i, p in enumerate(points)
               if not any(distance_km(p, c) <= radius for c in completed)}
    reused = len(points) - len(pending)
    neighbors = [{j for j in pending if distance_km(p, points[j]) <= radius} for p in points]
    queries = []
    while pending:
        best = max(range(len(points)), key=lambda i: (len(neighbors[i] & pending), -i))
        covered = sorted(neighbors[best] & pending)
        if not covered:
            raise ValueError('Uncovered fuel locations remain')
        queries.append({'center':points[best], 'covered_point_indices':covered})
        pending.difference_update(covered)
    return reused, queries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    source = json.loads((OUT/'alternatives/vehicle_fuel_index_20261026.json').read_text(encoding='utf-8'))
    rows = [r for r in source['rows'] if r['region'] == '전남']
    places = {}
    for r in rows:
        point = tuple(round(float(r[k]), 6) for k in ('위도','경도'))
        if not (32 < point[0] < 40 and 124 < point[1] < 132):
            raise ValueError('Invalid fuel coordinate')
        places.setdefault(point, []).append({'id':r['상가업소번호'], 'name':r['상호명'], 'address':r['도로명주소']})
    points = sorted(places)
    grid = json.loads((OUT/'grid_search/jeonnam_plan_20261025.json').read_text(encoding='utf-8'))
    tiles = {t['id']:t for t in grid['tiles']}
    completed = []
    for path in sorted((OUT/'grid_cache/jeonnam_20261025').glob('*.json')):
        tile = json.loads(path.read_text(encoding='utf-8'))
        if tile.get('query',{}).get('status') != 'complete':
            continue
        check_tile(tiles[tile['tile_id']], tile)
        completed.append(tile['query']['center'])
    reused, queries = cover(points, completed)
    result = {'scope':'future_station_sampling_not_region_census', 'region':'전남',
        'status':'planned_not_executed', 'live_requests':0, 'radius_km':2,
        'coverage_margin_radius_km':1.8, 'keyword':'',
        'commercial_source':{k:v for k,v in source.items() if k!='rows'},
        'fuel_records':len(rows), 'distinct_coordinate_points':len(points),
        'complete_cached_tiles':len(completed), 'points_within_cached_radius':reused,
        'points_needing_queries':len(points)-reused, 'additional_query_centers':len(queries),
        'limitations':['Coordinates are commercial candidates, not confirmed Onnuri merchants.',
            'Reusing old results is historical coverage, not current membership verification.',
            'Missing/mislocated commercial records and new stations remain outside this plan.',
            'Each center may require several paginated requests; server availability is still required.'],
        'points':[{'coordinate':p, 'businesses':places[p]} for p in points], 'queries':queries}
    with args.output.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('points','queries','commercial_source','limitations')},ensure_ascii=False))


if __name__ == '__main__':
    main()
