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
    style = '''<style>
      .header,.theme-picker,#tripLauncher,#tripPanel,.station-via,.info-overlay .route-actions,
      #coffeeBtn,#coffeeModal,#reportTriggerBtn,#reportPanel,#reportBanner,
      #reactFloatBtn,#reactPanel,.react-banner,.react-footer,.header-stats,
      #nearbyBtn,.tools-contact {display:none!important}
      .station-list-row:not(button) {cursor:default}
    </style>'''
    html = html.replace('</head>', style + '\n</head>')
    html = html.replace('</body>', '<script type="module" src="assets/toss-adapter.js"></script>\n</body>')
    # Fail closed if legacy network/payment integrations leaked back into this build.
    for token in ['BIN_KEY', 'X-Master-Key', 'formspree.io', 'qr.kakaopay.com', 'goatcounter.com', 'gc.zgo.at', 'apps.apple.com', 'navigator.geolocation.getCurrentPosition']:
        if token in html:
            raise ValueError('Excluded integration remains in the platform build: ' + token)
    return html


def prepare_results(js):
    old = "const station=row.item.station,node=document.createElement(hasMap?'button':'a');"
    if old not in js:
        raise ValueError('Result row contract changed; review the information-only fallback.')
    js = js.replace(old, "const station=row.item.station,node=document.createElement(hasMap?'button':'div');")
    js, count = re.subn(r"if\(hasMap\)node.type='button';else\{node.href=[^\n]+\}", "if(hasMap)node.type='button';", js, count=1)
    if count != 1:
        raise ValueError('External fallback link contract changed.')
    return js.replace('목록에서 주소와 길찾기를 확인하세요.', '목록에서 주유소 정보를 확인하세요.')


def main():
    source = (ROOT / 'output/map.html').read_text(encoding='utf-8')
    html = prepare(source)
    dist = HERE / 'dist'
    dist.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'assets', dist / 'assets', dirs_exist_ok=True)
    results = (ROOT / 'assets/nationwide-ui.js').read_text(encoding='utf-8')
    (dist / 'assets/nationwide-ui.js').write_text(prepare_results(results), encoding='utf-8')
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
        'sharedPalette': {'path': 'assets/theme.css', 'sha256': hashlib.sha256((dist / 'assets/theme.css').read_bytes()).hexdigest()},
        'sourceHtmlSha256': hashlib.sha256(source.encode('utf-8')).hexdigest(),
        'excluded': ['donations', 'legacy_reporting', 'legacy_reactions', 'legacy_analytics', 'trial_routing', 'external_navigation_actions'],
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Prepared Toss information-only candidate; 5 embedded datasets preserved.')


if __name__ == '__main__':
    main()
