"""Build the map's interior 시·군·구 lines from an admdongkor GeoJSON export.

Usage: python scripts/build_municipal_boundaries.py PATH_TO_GEOJSON
Build dependencies: shapely 2.1+, pyproj 3.x. No runtime dependencies.
"""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from pyproj import Transformer
from shapely import STRtree, line_merge, make_valid, transform, union_all
from shapely.geometry import shape


SOURCE = {
    "date": "2026-10-01",
    "url": "https://github.com/vuski/admdongkor/blob/d5d5a821c8de6cc337d47eeca604d7af76271c9b/ver20261001/HangJeongDong_ver20261001.geojson",
    "sha256": "843ece3a0b3429742cd4a1b699cc13987a88b5e5401f382e7fdaaa194ea5e605",
    "original": "Statistics Korea SGIS (https://sgis.kostat.go.kr), KOGL Type 1",
    "adaptedBy": "vuski/admdongkor",
    "license": "https://creativecommons.org/licenses/by/4.0/",
}
OUTPUT = Path(__file__).resolve().parents[1] / "assets/municipal-boundary-lines.json"


def parts(geometry, kind):
    if geometry.is_empty:
        return
    if geometry.geom_type == kind:
        yield geometry
    elif hasattr(geometry, "geoms"):
        for item in geometry.geoms:
            yield from parts(item, kind)


def build(source_path):
    raw = source_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE["sha256"]:
        raise ValueError("Review the input revision and update SOURCE before building.")

    groups = defaultdict(list)
    to_meters = Transformer.from_crs(4326, 5179, always_xy=True).transform
    to_degrees = Transformer.from_crs(5179, 4326, always_xy=True).transform
    for feature in json.loads(raw.decode("utf-8-sig"))["features"]:
        polygon = transform(shape(feature["geometry"]), to_meters, interleaved=False)
        groups[feature["properties"]["sgg"]].extend(parts(make_valid(polygon), "Polygon"))

    codes = sorted(groups)
    polygons = [union_all(groups[code], grid_size=0.1) for code in codes]
    index = STRtree(polygons)
    lines = []
    touched = set()
    for i, polygon in enumerate(polygons):
        for j in sorted(index.query(polygon)):
            if j <= i:
                continue
            common = polygon.boundary.intersection(polygons[j].boundary, grid_size=0.1)
            for line in parts(line_merge(common), "LineString"):
                if line.length < 5:
                    continue
                simplified = transform(line.simplify(5), to_degrees, interleaved=False)
                coordinates = [[round(x, 5), round(y, 5)] for x, y in simplified.coords]
                bounds = [round(value, 5) for value in simplified.bounds]
                lines.append([bounds, coordinates])
                touched.update((codes[i], codes[j]))

    data = {"source": SOURCE, "districtCount": len(codes), "lines": lines}
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as file:
        file.write('{"source":' + json.dumps(data["source"], separators=(",", ":")) + ',\n')
        file.write(f'"districtCount":{data["districtCount"]},\n"lines":[\n')
        file.write(",\n".join(json.dumps(line, separators=(",", ":")) for line in lines))
        file.write("\n]}\n")
    print(f"{len(codes)} districts, {len(touched)} with land borders, {len(lines)} line parts")
    print("Districts without land borders:", ", ".join(sorted(set(codes) - touched)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geojson", type=Path)
    build(parser.parse_args().geojson)
