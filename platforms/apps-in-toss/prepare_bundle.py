"""Prepare an information-only Toss test build without changing the public website.

Exclude legacy donation/report/reaction/analytics code and trial routing before
packaging. Domain permissions and actual Toss runtime behavior still need testing.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def between(text, start, end):
    a = text.index(start)
    b = text.index(end, a)
    return text[:a] + text[b:]


def prepare(html):
    html = re.sub(r'<script>\s*window.goatcounter[\s\S]*?</script>', '', html, count=1)
    html = re.sub(r'<script data-goatcounter=[\s\S]*?</script>', '', html, count=1)
    html = between(html, '// ── 제보 기능', '// 도움말 모달')
    html = between(html, '// 최초 방문 시 자동 오픈', '// 반응 패널')
    a = html.index('// 반응 패널')
    b = html.index('</script>', a)
    html = html[:a] + html[b:]
    for name in ['route-core', 'route-map', 'route-planner', 'route-window', 'theme']:
        html = html.replace(f'<script src="assets/{name}.js"></script>', '')
    html = html.replace('navigator.geolocation.getCurrentPosition(', 'window.GasToss.getCurrentPosition(')
    html = re.sub(r'function getNaverFallbackUrl\(station\) \{[\s\S]*?\n\}', "function getNaverFallbackUrl(station) { return ''; }", html, count=1)
    html = html.replace('if (!navigator.geolocation)', 'if (!window.GasToss)')
    html = html.replace("alert('위치 정보를 가져올 수 없습니다.\\n브라우저 위치 권한을 허용해 주세요.');", "alert(err?.message || '위치를 확인하지 못했어요. 지역·주소 검색을 이용해 주세요.');")
    # Donation QR and feedback image elements must not cause background requests.
    html = re.sub(r'<img\b[^>]*\bsrc="[^"]+"[^>]*>', lambda m: '' if any(term in m.group(0).lower() for term in ['kakaopay', 'qr.kakao', 'coffee']) else m.group(0), html)
    html = re.sub(r'<meta[^>]+(?:og:url|og:image|twitter:image)[^>]*>', '', html)
    html = html.replace('<html lang="ko">', '<html lang="ko" data-theme="light" style="color-scheme:light">')
    html = html.replace('content="light dark"', 'content="light"')
    html = re.sub(r'<title>.*?</title>', '<title>온누리 주유소 지도</title>', html, count=1)
    # The native navigation replaces the public header; keep its menu reachable.
    menu = re.search(r'<button\b[^>]*\bid="toolsOpenBtn"[^>]*>[\s\S]*?</button>', html)
    if not menu:
        raise ValueError('Shared menu button missing; review the platform navigation.')
    html = html[:menu.start()] + html[menu.end():]
    html, count = re.subn(r'(<nav class="search-modes"[^>]*>[\s\S]*?)(</nav>)', lambda m: m[1] + menu[0] + m[2], html, count=1)
    if count != 1:
        raise ValueError('Shared search tools missing; menu cannot be exposed.')
    style = '''<style>
      .header,.theme-picker,#routeModeBtn,#tripLauncher,#tripPanel,.station-via,.info-overlay .route-actions,
      #coffeeBtn,#coffeeModal,#reportTriggerBtn,#reportPanel,#reportBanner,
      #reactFloatBtn,#reactPanel,.react-banner,.react-footer,.header-stats,
      #nearbyBtn,.tools-contact {display:none!important}
    </style>'''
    html = html.replace('</head>', style + '\n<link rel="stylesheet" href="assets/information-ui.css">\n</head>')
    html = html.replace('<script src="assets/nationwide-ui.js"></script>', '<script src="assets/information-ui.js"></script>\n<script src="assets/nationwide-ui.js"></script>')
    html = html.replace('</body>', '<script type="module" src="assets/toss-adapter.js"></script>\n</body>')
    # Help must describe only actions included in this candidate.
    html = re.sub(r'<div class="help-item">[\s\S]*?</div>', lambda m: '' if any(term in m[0] for term in ['경유 주유소 찾기', '<b>길찾기</b>', '<b>주변 내보내기</b>']) else m[0], html)
    html = re.sub(r'<div class="help-section">\s*<div class="help-section-title">누락·오류 제보</div>[\s\S]*?(?=<div class="help-section">)', '', html, count=1)
    html = html.replace('가격 순위·언어·사용법·제보 등 보조 기능', '가격 순위·언어·사용법 등 보조 기능')
    html = html.replace('브라우저 위치 권한 필요', '토스 위치 권한 허용 필요')
    html = html.replace('결제 가능 수단, 현재 유가', '결제 확인 범위, 자료 기준일의 유가')
    html = html.replace('온누리: 소상공인시장진흥공단 공식 파일', '온누리: 공식 검색·공식 파일·KB국민카드 가맹점 조회')
    html = html.replace('유가와 가맹점 확인일은 별개입니다.', '유가와 가맹점 확인일은 별개입니다. 발행사·운영사의 공식 앱이 아니며, 전국 모든 가맹점이나 방문 시 결제를 보장하지 않습니다.')
    # Fail closed if legacy network/payment integrations leaked back into this build.
    for token in ['BIN_KEY', 'X-Master-Key', 'formspree.io', 'qr.kakaopay.com', 'goatcounter.com', 'gc.zgo.at', 'apps.apple.com', 'navigator.geolocation.getCurrentPosition']:
        if token in html:
            raise ValueError('Excluded integration remains in the platform build: ' + token)
    return html


def prepare_results(js):
    old = "const station=row.item.station,node=document.createElement(hasMap?'button':'a');"
    if old not in js:
        raise ValueError('Result row contract changed; review the information-only fallback.')
    js = js.replace(old, "const station=row.item.station,node=document.createElement('button');")
    js, count = re.subn(r"if\(hasMap\)node.type='button';else\{node.href=[^\n]+\}", "node.type='button';", js, count=1)
    if count != 1:
        raise ValueError('External fallback link contract changed.')
    anchor = "    if(hasMap)node.setAttribute('aria-pressed',String(selectedId===station.id));"
    if js.count(anchor) != 1:
        raise ValueError('Station selection contract changed; review the fallback detail action.')
    js = js.replace(anchor, "    if(!hasMap)node.addEventListener('click',()=>window.GasTossUI.showStationDetails(station,node));\n" + anchor)
    return js.replace('목록에서 주소와 길찾기를 확인하세요.', '목록에서 주유소 정보를 확인하세요.')


def copy_assets(html, dist):
    """Package only referenced assets; old trial scripts must not survive rebuilds."""
    dist = dist.resolve()
    if dist != HERE.resolve() / 'dist':
        raise ValueError('Unexpected build output directory')
    assets = dist / 'assets'
    if assets.is_symlink() or assets.resolve() != assets:
        raise ValueError('Unexpected linked asset directory')
    assets.mkdir(exist_ok=True)
    references = set(re.findall(r'(?:src|href)="(assets/[^"?#]+)"', html))
    for relative in references:
        target = dist / relative
        if target.is_symlink() or not target.resolve().is_relative_to(assets):
            raise ValueError('Asset path escapes output directory')
        if relative == 'assets/toss-adapter.js':
            continue  # Vite builds this after the static copy.
        source = HERE / 'src' / target.name if target.name.startswith('information-ui.') else ROOT / relative
        if relative == 'assets/nationwide-ui.js':
            target.write_text(prepare_results(source.read_text(encoding='utf-8')), encoding='utf-8')
        elif relative == 'assets/i18n.js':
            translated = source.read_text(encoding='utf-8').replace('전국 주유소 할인 지도', '온누리 주유소 지도').replace('Korea Fuel Discount Map', 'Onnuri FuelMap')
            target.write_text(translated, encoding='utf-8')
        elif relative == 'assets/ux-fixes.js':
            keyboard = source.read_text(encoding='utf-8').replace("event.key==='Escape'&&typeof activeOverlay", "event.key==='Escape'&&window.kakao?.maps&&typeof activeOverlay")
            target.write_text(keyboard, encoding='utf-8')
        else:
            shutil.copyfile(source, target)
    for path in assets.rglob('*'):
        if path.is_symlink() or not path.resolve().is_relative_to(assets):
            raise ValueError('Unexpected asset symlink or path')
        if path.is_file() and path.relative_to(dist).as_posix() not in references:
            path.unlink()
    return sorted(references)


def main():
    source = (ROOT / 'output/map.html').read_text(encoding='utf-8')
    html = prepare(source)
    dist = HERE / 'dist'
    dist.mkdir(exist_ok=True)
    references = copy_assets(html, dist)
    # Shared filenames can otherwise keep an older script after a new deployment.
    inputs = [ROOT / 'output/map.html', ROOT / 'favicon.svg', HERE / 'prepare_bundle.py',
              HERE / 'package.json', HERE / 'package-lock.json', HERE / 'apps-in-toss.config.ts', HERE / 'vite.config.js']
    inputs += sorted((HERE / 'src').glob('*'))
    inputs += [ROOT / relative for relative in references
               if not Path(relative).name.startswith('information-ui.') and relative != 'assets/toss-adapter.js']
    hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    version = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode('utf-8')).hexdigest()[:12]
    html = re.sub(r'((?:src|href)="assets/[^"?#]+)(")', rf'\1?v={version}\2', html)
    shutil.copyfile(ROOT / 'favicon.svg', dist / 'favicon.svg')
    (dist / 'index.html').write_text(html, encoding='utf-8')
    for key in ['STATIONS', 'PRICES', 'PRICE_INFO', 'MERCHANT_STATUS', 'NATIONAL_PENDING']:
        pattern = rf'^(?:const|let) {key} = (.+);$'
        assert re.search(pattern, source, re.M).group(1) == re.search(pattern, html, re.M).group(1), key
    # The static network inventory contains hosts, not coordinates or credentials.
    hosts = sorted(set(re.findall(r'https?://([\w.-]+)', html)))
    (dist / 'test-build-manifest.json').write_text(json.dumps({
        'appName': 'onnuri-fuel-map', 'buildKind': 'information_only_test_candidate',
        'runtimeVerified': False, 'externalHostsInHtml': hosts,
        'referencedAssets': references,
        'buildInputs': hashes, 'assetVersion': version,
        'sharedPalette': {'path': 'assets/theme.css', 'sha256': hashlib.sha256((dist / 'assets/theme.css').read_bytes()).hexdigest()},
        'sourceHtmlSha256': hashlib.sha256(source.encode('utf-8')).hexdigest(),
        'excluded': ['donations', 'legacy_reporting', 'legacy_reactions', 'legacy_analytics', 'trial_routing', 'external_navigation_actions'],
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Prepared Toss information-only candidate; 5 embedded datasets preserved.')


if __name__ == '__main__':
    main()
