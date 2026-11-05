"""Promote the approved UI over the current map, never a pinned review dataset."""
import hashlib
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_KEYS = ('STATIONS', 'PRICES', 'PRICE_INFO', 'MERCHANT_STATUS', 'NATIONAL_PENDING')


def datasets(html):
    return {key: re.search(rf'^(?:const|let) {key} = (.+);$', html, re.M)[1] for key in DATA_KEYS}


def promote(html):
    if 'id="fuelDesignApp"' in html:
        return html
    before = datasets(html)
    html = html.replace('<div class="app">', '<div class="app" id="fuelDesignApp">', 1)
    html, count = re.subn(r'<section([^>]*id="mapFilters"[^>]*)>(.*?)</section>', r'<dialog\1>\2</dialog>', html, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Filter panel contract changed')
    html, count = re.subn(r'<button\b[^>]*id="languageBtn"[^>]*>.*?</button>', '', html, flags=re.S)
    if count != 1:
        raise ValueError('Language control contract changed')
    html = re.sub(r'<script src="assets/i18n\.js(?:\?[^\"]*)?"></script>', '', html)
    html = html.replace('가격 순위·언어·사용법', '가격 순위·사용법')
    # Match the review's information-only surface; do not revive legacy
    # reporting, payment links or reaction-service credentials on promotion.
    html = re.sub(r'// ── 제보 기능[\s\S]*?(?=// 도움말 모달)', '// ── 제보 기능 (정보 UI에서 제외)\n', html, count=1)
    html = re.sub(r'// 최초 방문 시 자동 오픈[\s\S]*?(?=// 반응 패널)', '', html, count=1)
    html = re.sub(r'// 반응 패널[\s\S]*?(?=</script>)', '// 반응 패널 (정보 UI에서 제외)\n', html, count=1)
    html = re.sub(r'<script>\s*window.goatcounter[\s\S]*?</script>', '', html, count=1)
    html = re.sub(r'<script data-goatcounter=[\s\S]*?</script>', '', html, count=1)
    html = re.sub(r'<img\b[^>]*\bsrc="[^\"]+"[^>]*>', lambda m: '' if any(term in m[0].lower() for term in ['qr.kakao', 'qrserver.com', 'coffee']) else m[0], html)
    html = re.sub(r'<div class="help-item">[\s\S]*?</div>', lambda m: '' if any(term in m[0] for term in ['경유 주유소 찾기', '<b>주변 내보내기</b>']) else m[0], html)
    html = re.sub(r'<div class="help-section">\s*<div class="help-section-title">누락·오류 제보</div>[\s\S]*?(?=<hr class="help-divider">)', '', html, count=1)
    menu = re.search(r'<button\b[^>]*id="toolsOpenBtn"[^>]*>.*?</button>', html, re.S)
    html = html[:menu.start()] + html[menu.end():]
    html, count = re.subn(r'(<nav class="search-modes"[^>]*>.*?)(</nav>)', lambda m: m[1] + menu[0] + m[2], html, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Search tools contract changed')
    css = ['tokens', 'components', 'prototype', 'reference', 'journey', 'web']
    html = html.replace('</head>', ''.join(f'<link rel="stylesheet" href="assets/fuel-ui/{name}.css">' for name in css) + '<link rel="stylesheet" href="assets/onnuri-palette.css">\n</head>', 1)
    journey = (ROOT / 'design/onnuri-fuel-v2/journey.html').read_text(encoding='utf-8')
    html = html.replace('<div class="map-area">', '<div class="map-area">' + journey, 1)
    js = '<script src="assets/fuel-ui/prototype.js"></script><script src="assets/onnuri-pin-themes.js"></script><script src="assets/fuel-ui/reference.js"></script>'
    # A public route gateway has not been connected. Never point visitors at
    # localhost or the development fixture; navigation/copy remain available.
    js += '<script>window.GasJourneyConfig={endpoint:"",externalNavigationEnabled:true};</script><script src="assets/fuel-journey-core.js"></script><script src="assets/fuel-ui/journey.js"></script>'
    html = html.replace('</body>', js + '\n</body>', 1)
    html = re.sub(r'(?m)^[ \t]+$', '', html)
    if before != datasets(html):
        raise ValueError('UI promotion changed map data')
    for token in ['BIN_KEY', 'X-Master-Key', 'formspree.io', 'qr.kakaopay.com', 'goatcounter.com']:
        if token in html:
            raise ValueError('Review-excluded integration remains: ' + token)
    return html


def main():
    target = ROOT / 'assets/fuel-ui'
    target.mkdir(exist_ok=True)
    for name in ['tokens.css', 'components.css', 'prototype.css', 'prototype.js']:
        shutil.copyfile(ROOT / 'design/onnuri-fuel-v1' / name, target / name)
    shutil.copytree(ROOT / 'design/onnuri-fuel-v1/fonts', target / 'fonts', dirs_exist_ok=True)
    for name in ['reference.css', 'reference.js', 'journey.css', 'journey.js']:
        shutil.copyfile(ROOT / 'design/onnuri-fuel-v2' / name, target / name)
    path = ROOT / 'output/map.html'
    original = path.read_text(encoding='utf-8')
    result = promote(original)
    path.write_text(result, encoding='utf-8')
    print('UI v2 applied; five current map datasets preserved:', hashlib.sha256(str(datasets(result)).encode()).hexdigest()[:12])


if __name__ == '__main__':
    main()
