"""Build a local-only layout fixture from the real HTML/CSS; never calls a service.

The preview deliberately omits production JS and is not a functional map test.
Its output directory must be outside the public _site directory.
"""
import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(destination):
    destination = Path(destination).resolve()
    if destination == ROOT / '_site' or ROOT / '_site' in destination.parents:
        raise ValueError('The UI fixture must not be published in _site')
    destination.mkdir(parents=True, exist_ok=True)
    html = (ROOT / 'output/map.html').read_text(encoding='utf-8')
    html = re.sub(r'<script\b[^>]*>[\s\S]*?</script>', '', html)
    html = re.sub(r'<title>[^<]*</title>', '<title>UI 검수 전용 — 실제 지도·전송 없음</title>', html, count=1)
    fixture = r'''
<script>
const args=new URLSearchParams(location.search),screen=args.get('screen')||'home';
if(args.get('large')==='1')document.documentElement.style.fontSize='200%';
document.documentElement.dataset.theme=args.get('theme')==='dark'?'dark':'light';
document.documentElement.style.setProperty('--app-height','100dvh');
const byId=id=>document.getElementById(id);
// Controlled UI-only integration: no browser GPS, place search, or road service.
window.kakao={maps:{LatLng:class{constructor(lat,lng){this.lat=lat;this.lng=lng;}}}};
const map={setCenter(){},setLevel(){}};
function locateUser(){return args.get('gps')==='denied'?Promise.reject(Error('fixture denied')):Promise.resolve({lat:35.16,lng:126.85});}
function closeStationOverlay(){byId('stationDetails').hidden=true;byId('stationDetails').replaceChildren();}
window.GasResultsPanel={showNearby(){byId('nationalResults').open=true;byId('listScope').textContent='광주 조건 결과 · 내 위치 가까운 순 · 검수용 예시';}};
const longName='가나다라마바사 에너지 직영 산업단지 제2 셀프주유소';
const longAddress='전라남도 무안군 삼향읍 남악리 아주긴도로명123번길 123-45 (산업단지 제2동)';
const longToken='LongMerchantNameWithoutSpaces0123456789'.repeat(3);
byId('map').textContent='지도 영역 — UI 배치 검수용';
byId('countBadge').textContent='131곳';byId('listCount').textContent='전체 131곳';
if(screen==='filters')byId('mapFilters').hidden=false;
if(screen==='region'){
  for(const name of ['광주','전남','서울','경기','세종','전북','충남','전국']){
    const b=document.createElement('button');b.textContent=name;byId('regionOptions').append(b);
  }
  byId('regionDialog').showModal();
}
if(screen==='tools')byId('mapTools').showModal();
if(screen==='updates')byId('updatesDialog').showModal();
const panels={rank:'rankModal',report:'reportPanel',nearby:'nearbyPanel',help:'helpModal',reaction:'reactPanel',coffee:'coffeeModal'};
if(panels[screen])byId(panels[screen]).classList.add('open');
if(screen==='rank'){
  byId('rankList').innerHTML=Array.from({length:5},(_,i)=>`<button type="button" class="rank-item"><span class="rank-badge">${i+1}</span><span class="rank-info"><span class="rank-name">${i===0?longToken:longName}</span><span class="rank-addr">${longAddress}</span></span><span class="rank-price"><span class="effective-price"><del>1,999원/L</del><b>1,799.1원/L</b><small>상생 10% 적용 체감가</small></span></span></button>`).join('');
}
if(screen==='nearby')byId('nearbyList').innerHTML=`<button class="nearby-item"><span class="nearby-dist">1.25km</span><span class="nearby-info"><span class="nearby-name">${longToken}</span><span class="nearby-addr">${longAddress}</span></span></button>`;
if(screen==='report'){
  byId('reportLocDisplay').textContent=longAddress;byId('reportName').value=longName;
  byId('reportFileName').style.display='block';byId('reportFileName').textContent=longToken+'.jpg';
}
if(screen==='reaction'){
  byId('reactClist').innerHTML=`<div class="react-clist-item"><div class="react-clist-body"><div class="react-clist-nick-row"><span class="react-clist-nick">${longToken}</span><button class="react-del-btn">삭제</button></div><p class="react-clist-text">${longToken}</p><p class="react-clist-meta">2026-11-02 검수용 예시</p></div></div>`;
}
if(screen==='trip'){
  byId('tripPanel').open=true;byId('tripSettings').open=true;byId('tripCriteria').open=true;
  byId('tripLauncher').hidden=true;byId('tripPanel').style.setProperty('--trip-window-height','min(620px,calc(100dvh - 200px))');
  byId('tripDestinationSelected').textContent=longAddress;byId('tripStartSelected').textContent=longToken;
  byId('tripChoices').innerHTML=`<button class="trip-choice">${longName}<br>${longAddress}</button>`;
}
if(screen==='station'){
  byId('stationDetails').hidden=false;
  byId('stationDetails').innerHTML=`<div class="info-overlay"><div class="info-heading"><div class="copy-row name"><span>${longToken}</span></div><button class="station-close">×</button></div><div class="copy-row address">${longAddress}</div><div class="tags"><span class="station-payment-label">온누리 지류·디지털 / 광주상생카드</span><span class="station-check">2026-11-02 확인</span></div><div class="prices"><span class="price-item"><span class="fuel-label">휘발유</span><span class="effective-price"><del>1,999원/L</del><b>1,799.1원/L</b></span></span></div><div class="route-actions"><a class="route-btn kakao">카카오맵</a><a class="route-btn naver">네이버지도</a></div><button class="route-btn station-via">이 주유소 경유</button></div>`;
}
if(screen==='list'){
  byId('nationalResults').open=true;
  const areaHeight=document.querySelector('.map-area').clientHeight;
  byId('nationalResults').style.setProperty('--results-available',Math.max(100,areaHeight-88)+'px');
  byId('nationalResults').style.setProperty('--results-body-height',Math.max(88,areaHeight*.65-60)+'px');
  byId('stationList').innerHTML=Array.from({length:3},()=>`<button class="station-list-row"><strong>${longName}</strong><span class="station-address">${longAddress}</span><span class="station-payment">온누리 지류·디지털 / 광주상생카드</span><span class="station-price">휘발유 1,999원/L · 경유 1,899원/L</span></button>`).join('');
}
document.querySelectorAll('form').forEach(form=>form.addEventListener('submit',e=>e.preventDefault()));
</script>'''
    # Run only the actual route-window sizing/gestures module. It has no network
    # or merchant-data behavior, and lets layout tests catch native details sizing.
    modules = '''\n<script src="assets/route-window.js"></script><script src="assets/search-flow.js"></script><script src="assets/i18n.js"></script>
<script>if((document.documentElement.lang==='en')!==(args.get('lang')==='en'))document.getElementById('languageBtn').click();document.title='UI 검수 전용 — 실제 지도·전송 없음';</script>'''
    (destination / 'index.html').write_text(html.replace('</body>', fixture + modules + '\n</body>'), encoding='utf-8')
    shutil.copytree(ROOT / 'assets', destination / 'assets', dirs_exist_ok=True)
    for name in ('favicon.svg', 'thumbnail.png'):
        shutil.copyfile(ROOT / name, destination / name)
    print(f'Local layout fixture: {destination}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    build(parser.parse_args().output)
