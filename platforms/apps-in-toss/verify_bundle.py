"""Audit the actual .ait candidate without console access or device certification."""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def audit():
    bundle, dist = HERE / 'onnuri-fuel-map.ait', HERE / 'dist'
    checks = []

    def passed(name, evidence):
        checks.append({'name': name, 'status': 'passed', 'evidence': evidence})

    with zipfile.ZipFile(bundle) as archive:
        assert archive.testzip() is None, 'Archive checksum failed'
        expanded = sum(info.file_size for info in archive.infolist())
        assert expanded < 100 * 1024 * 1024, 'Expanded bundle exceeds 100 MiB'
        passed('archive_integrity_and_size', {'compressedBytes': bundle.stat().st_size, 'expandedBytes': expanded})
        sources = {name[8:]: archive.read(name) for name in archive.namelist() if name.startswith('sources/') and not name.endswith('/')}
    for name, content in sources.items():
        path = dist / name
        assert path.resolve().is_relative_to(dist.resolve()), 'Unsafe source path'
        assert content == path.read_bytes(), f'Archive differs from build: {name}'
    passed('archive_matches_built_files', len(sources))
    html = sources['index.html'].decode('utf-8')
    manifest = json.loads(sources['test-build-manifest.json'])
    for name, digest in manifest['buildInputs'].items():
        path = ROOT / name
        assert path.resolve().is_relative_to(ROOT.resolve()), 'Unsafe input path'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f'Input changed since build: {name}'
    passed('all_build_inputs_current', len(manifest['buildInputs']))
    references = set(re.findall(r'(?:src|href)="(assets/[^"?#]+)', html))
    assert references == set(manifest['referencedAssets'])
    assert set(name for name in sources if name.startswith('assets/')) == references, 'Missing or leftover asset'
    passed('all_references_packaged_without_stale_assets', len(references))
    excluded = ['route-core.js', 'route-map.js', 'route-planner.js', 'route-window.js', 'theme.js']
    assert all('assets/' + name not in sources for name in excluded)
    passed('excluded_trial_scripts_absent', len(excluded))
    for token in ['X-Master-Key', 'BIN_KEY', 'formspree.io', 'qr.kakaopay.com', 'goatcounter.com', 'gc.zgo.at', 'apps.apple.com', 'navigator.geolocation.getCurrentPosition']:
        assert token not in html, f'Legacy integration in HTML: {token}'
    passed('legacy_endpoints_and_browser_gps_removed', True)
    original = (ROOT / 'output/map.html').read_text(encoding='utf-8')
    for key in ['STATIONS', 'PRICES', 'PRICE_INFO', 'MERCHANT_STATUS', 'NATIONAL_PENDING']:
        pattern = rf'^(?:const|let) {key} = (.+);\r?$'
        assert re.search(pattern, original, re.M).group(1).strip() == re.search(pattern, html, re.M).group(1).strip(), key
    stations = json.loads(re.search(r'^const STATIONS = (.+);\r?$', html, re.M).group(1))
    passed('five_datasets_preserved', {'allRecords': len(stations), 'onnuriTaggedRecords': sum('onnuri' in station.get('payment_types', []) for station in stations)})
    scripts = [(name, content.decode('utf-8')) for name, content in sources.items() if name.endswith('.js')]
    scripts += [('inline', body) for body in re.findall(r'<script(?:\s[^>]*)?>([\s\S]*?)</script>', html) if body.strip()]
    for name, body in scripts:
        result = subprocess.run(['node', '--check', '--input-type=module'], input=body, encoding='utf-8', capture_output=True)
        assert result.returncode == 0, f'{name}: {result.stderr}'
    passed('javascript_syntax', len(scripts))
    versions = re.findall(r'(?:src|href)="assets/[^"?#]+\?v=([^"&]+)', html)
    assert len(versions) == len(references) and set(versions) == {manifest['assetVersion']}
    passed('asset_cache_version', manifest['assetVersion'])
    return {
        'checkedAt': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        'scope': 'local_artifact_audit_not_toss_device_certification',
        'artifactSha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
        'checks': checks, 'readyForSubmission': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    report = json.dumps(audit(), ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding='utf-8')
        print(f'Saved artifact audit: {args.out}')
    else:
        print(report, end='')
