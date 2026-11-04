"""Build the isolated mobile design-system review from the pinned Toss handoff.

Never writes deployed assets, map data, the .ait, or a collection queue.
"""
import argparse
import hashlib
import html as html_module
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / 'design/onnuri-fuel-v1'
DEFAULT_ARTIFACT = ROOT.parents[1] / 'output/apps-in-toss-review-20261103/candidate-e1f72f65/onnuri-fuel-map.ait'
EXPECTED_HASH = 'e1f72f65b654b4b5bc2bc7430261c5614a824697d4c85d91a8dc0b85faf63c7f'

COMPONENTS = [
 ('F01','foundation','글자 위계','제목20 / 본문16 / 메타14. 400·700 두 굵기를 사용한다.','type'),
 ('F02','foundation','버튼과 아이콘','주 행동·보조·닫기. 최소44px, 선 아이콘24px.','buttons'),
 ('F03','foundation','색과 표면','Sand 바탕·Indigo 정보·Jade 행동·Sage 선택. 일반 목록에 그림자 없음.','surfaces'),
 ('M01','map','토스 내비게이션 경계','실제 앱에서는 SDK 내비게이션을 유지한다. 웹 미리보기에서 재구현하지 않는다.','native'),
 ('M02','map','검색 입력과 지우기','입력16px. 검색과 지우기를 각각 이름 붙인 조작으로 제공한다.','search'),
 ('M03','map','지역 선택 버튼','현재 지역을 버튼에 표시하고 선택창으로 연결한다.','region_button'),
 ('M04','map','필터 버튼과 개수','적용된 결제수단·추가 조건은 접근성 이름과 배지로 표시한다.','filter_button'),
 ('M05','map','내 주변과 더보기','주요 탐색과 보조 메뉴를 구분한다. 처음에 위치 권한을 요구하지 않는다.','modes'),
 ('M06','map','조회 개수와 범위','전체 가맹점 수로 오해하지 않도록 현재 조건의 결과임을 구분한다.','count'),
 ('M07','map','지도 범위 조회','좌측 상단 단일 진입점. 결과창이 열리면 중복 버튼을 감춘다.','area'),
 ('M08','map','확대·축소와 내 위치','44px 확대 조작·48px 위치 조작. 지도 하단 좌우를 분리한다.','map_controls'),
 ('M09','map','지도 마커','온누리·지역화폐·중복의 색과 내부 도형을 구분한다. 상세에서 결제 범위를 다시 확인한다.','markers'),
 ('Q01','filters','지역 선택 팝업','모바일 아래 시트 / PC 중앙 팝업. 선택 지역과 닫기를 항상 구분한다.','region'),
 ('Q02','filters','검색 필터 팝업','결제수단→유형·유종→시군구. 지도 보기와 조건 초기화 제공.','filters'),
 ('Q03','filters','결제수단 선택','색과 체크를 함께 사용. 현재 선택은 배경·경계·문구로 구별한다.','segments'),
 ('Q04','filters','유형·유종·시군구 선택','기본 native select. 긴 선택값·키보드·확대 시 높이 증가 허용.','selects'),
 ('Q05','filters','초기화와 선택 요약','초기화는 낮은 우선순위. 선택값 자체를 화면에 보존한다.','reset'),
 ('R01','results','조회 결과 시트','지도 위에 독립된 목록. 제목·닫기·높이 조절과 본문 스크롤 구분.','results'),
 ('R02','results','범위·정렬·목록 높이','범위와 정렬은 짧은 두 선택. 내 위치가 없으면 거리 정렬 비활성.','sort'),
 ('R03','results','주유소 결과 행','상호→주소→결제 확인 범위→유가·날짜. 자동 높이, 긴 주소 줄바꿈.','row'),
 ('R04','results','추가 보기','현재 표시량과 추가 보기를 분리. 끝없이 자동 추가하지 않는다.','pagination'),
 ('R05','results','빈 결과와 복구','검색어 지우기·필터 초기화·지역 바꾸기 중 원인에 맞는 행동만 표시.','empty'),
 ('D01','detail','주유소 상세 시트','좌측 제목·주소와 우측44px 닫기. 지도 위치를 보존하고 원래 결과로 복귀.','detail'),
 ('D02','detail','결제 확인 배지','지류·디지털·KB국민카드 범위를 혼동하지 않는다. 현재 결제 보장 표현 없음.','badges'),
 ('D03','detail','확인일과 출처','가맹 확인일·유가 기준일을 나누고, 과거 자료는 상태와 함께 표시.','proof'),
 ('D04','detail','유가 행','유종과 숫자를 정렬. 가격 단위·자료 기준일을 숫자와 함께 제공.','prices'),
 ('D05','detail','유가 미확인','0원이나 실시간 최저가로 대체하지 않고 자료 부재를 표시한다.','no_price'),
 ('S01','support','더보기 메뉴','가격 순위·언어·사용 안내·업데이트. 보조 항목을 행으로 정리한다.','menu'),
 ('S02','support','가격 순위','서로 다른 날짜·가격 확보 범위를 표시. 작은 화면에서 가격을 다음 행에 배치.','rank'),
 ('S03','support','사용 안내','독립 정보 서비스·자료 한계·위치 거절 후 검색을 읽을 수 있게 제공.','help'),
 ('S04','support','업데이트·자료 상태','실제 데이터의 시각과 범위를 표시. 가맹 확인을 새로 한 것으로 표현하지 않음.','updates'),
 ('S05','support','언어 선택','한 번의 선택으로 변경. 상호·주소·사용자 입력의 원문은 보존한다.','language'),
]

ICON_PATHS = {
 'search':'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
 'close':'<path d="m6 6 12 12M18 6 6 18"/>',
 'arrow':'<path d="M5 12h14m-5-5 5 5-5 5"/>',
 'chevron':'<path d="m9 5 7 7-7 7"/>',
 'location':'<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/>',
 'plus':'<path d="M12 5v14M5 12h14"/>',
 'minus':'<path d="M5 12h14"/>',
 'filter':'<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="2"/><circle cx="15" cy="17" r="2"/>',
 'check':'<path d="m5 12 4 4L19 6"/>',
 'more':'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
}


def icon(name):
    return f'<svg class="fu-icon" aria-hidden="true" viewBox="0 0 24 24">{ICON_PATHS[name]}</svg>'


def button(label, kind='', extra=''):
    return f'<button type="button" class="fu-button {kind}" {extra}>{label}</button>'


def select(label, options, disabled=False):
    return '<label class="fu-field">'+label+f'<select class="fu-select" {"disabled" if disabled else ""}>'+''.join(f'<option>{x}</option>' for x in options)+'</select></label>'


def marker(kind='', label='온누리'):
    middle='<circle cx="16" cy="16" r="5" fill="white"/>'
    if kind=='currency': middle='<path d="m16 10 6 6-6 6-6-6z" fill="white"/>'
    elif kind=='both': middle='<circle cx="12" cy="16" r="3.5" fill="white"/><circle cx="20" cy="16" r="3.5" fill="white"/>'
    return f'<svg class="fu-marker {kind}" viewBox="0 0 32 42" role="img" aria-label="{label}"><path d="M16 1C7.7 1 1 7.7 1 16c0 10 15 24 15 24s15-14 15-24C31 7.7 24.3 1 16 1Z" fill="currentColor" stroke="white" stroke-width="2"/>{middle}</svg>'


def render_gallery(sample, prices, checked, price_date, count):
    name=html_module.escape(sample['name']); address=html_module.escape(sample['address'])
    price_rows=''.join(f'<div class="fu-price-row"><span>{html_module.escape(fuel)}</span><strong>{value:,.0f}<small>원/L</small></strong></div>' for fuel,value in prices.items() if fuel in ('휘발유','경유'))
    price_box=f'<div class="fu-price-group">{price_rows}</div><p class="fu-meta">Opinet {price_date} 기준</p>'
    row=f'<button type="button" class="fu-row" data-demo-detail><strong>{name}</strong><span class="address">{address}</span><span class="fu-badge">온누리 지류·디지털</span><span>휘발유 {prices["휘발유"]:,.0f}원/L · 경유 {prices["경유"]:,.0f}원/L</span><span class="fu-meta">유가 {price_date} 기준</span></button>'
    close_button=button(icon('close'),'icon','aria-label="주유소 상세 닫기" data-demo-close')
    clear_button=button(icon('close'),'icon','aria-label="검색어 지우기" data-demo-clear')
    header=f'<div class="fu-sheet-head"><h3>{name}</h3>{close_button}</div>'
    detail=f'{header}<div class="fu-sheet-body"><p>{address}</p><div><span class="fu-badge">온누리 지류·디지털</span><p class="fu-meta" style="margin-top:.5rem">{checked} 가맹 확인</p></div>{price_box}</div>'
    segment='<div class="fu-segments" data-demo-segments><button type="button" aria-pressed="false">전체</button><button type="button" aria-pressed="true">온누리</button><button type="button" aria-pressed="false">지역화폐</button></div>'
    fields='<div class="fu-split">'+select('온누리 유형',['전체','지류','디지털'])+select('유종',['전체','휘발유·경유','LPG'])+'</div>'+select('시·군·구',['전체 시·군·구','광산구','남구','동구','북구','서구'])
    menu=''.join(f'<button type="button" class="fu-menu-row" data-demo-open="{target}"><span>{label}</span>{icon("chevron")}</button>' for label,target in [('가격 순위','rank'),('언어','language'),('사용 안내','help'),('업데이트 내역','updates')])
    demos={
      'type':f'<div class="fu-stack"><h3 class="fu-title">{name}</h3><p class="fu-body">{address}</p><p class="fu-meta">{checked} 확인 · 자료 기준일을 구분해요</p></div>',
      'buttons':'<div class="fu-inline">'+button('지도 보기','primary')+button('지역 바꾸기','secondary')+button('초기화','quiet')+button(icon('close'),'icon','aria-label="닫기"')+button('위치 확인 중','', 'disabled aria-busy="true"')+'</div><div class="fu-inline" style="margin-top:1rem">'+''.join(icon(k) for k in ICON_PATHS)+'</div>',
      'surfaces':'<div class="fu-stack"><div class="fu-notice">선택은 Sage 면, 오류는 별도 상태색을 사용해요.</div><div class="fu-inline"><span class="fu-badge">선택됨</span><span class="fu-badge warning">과거 확인 자료</span><span class="fu-badge neutral">유가 미확인</span></div></div>',
      'native':'<div class="native-slot">토스에서 제공하는 내비게이션 영역</div><p class="fu-meta" style="margin-top:1rem">웹 검토 화면에는 자체 닫기·가짜 토스 탭을 추가하지 않아요.</p>',
      'search':f'<label class="fu-search">{icon("search")}<input type="search" aria-label="주유소명 또는 주소 검색" placeholder="주유소명 · 주소 검색" autocomplete="off">{clear_button}</label>',
      'region_button':button('광주 ▾','secondary','data-demo-open="region" aria-haspopup="dialog"'),
      'filter_button':button(icon('filter')+'온누리 <span class="fu-badge">1</span>','secondary','data-demo-open="filters" aria-haspopup="dialog"'),
      'modes':'<div class="fu-inline">'+button(icon('location')+'내 주변','quiet','data-location-demo')+button('더보기 '+icon('more'),'quiet','data-demo-open="menu" aria-haspopup="dialog"')+'</div><p class="fu-meta" data-location-result></p>',
      'count':f'<div class="fu-inline"><strong>{count}곳</strong><span class="fu-meta">광주 · 온누리 조건 결과</span></div>',
      'area':button(icon('search')+'현재 지도에서 주유소 찾기','secondary','data-demo-open="results"'),
      'map_controls':'<div class="fu-inline">'+button(icon('plus'),'secondary icon','aria-label="지도 확대"')+button(icon('minus'),'secondary icon','aria-label="지도 축소"')+button(icon('location'),'secondary icon','aria-label="내 위치로 이동" data-location-demo')+'</div>',
      'markers':'<div class="marker-gallery">'+''.join('<div>'+marker(k,l)+'<span class="fu-meta">'+l+'</span></div>' for k,l in [('', '온누리'),('currency','지역화폐'),('both','두 수단'),('selected','선택')])+'</div>',
      'region':'<div class="fu-grid" data-demo-single>'+''.join(button(n,'secondary',f'aria-pressed="{str(n=="광주").lower()}"') for n in ['광주','전국','전남','전북','서울','경기','인천','충남','강원'])+'</div>',
      'filters':'<div class="fu-stack">'+segment+fields+'<div class="fu-inline">'+button('조건 초기화','quiet','data-demo-reset')+button('지도 보기','primary','data-demo-open="filters"')+'</div></div>',
      'segments':segment,
      'selects':'<div class="fu-stack">'+fields+'</div>',
      'reset':'<div class="fu-inline"><span class="fu-badge">온누리</span><span class="fu-badge">지류</span>'+button('조건 초기화','quiet','data-demo-reset')+'</div>',
      'results':'<div class="fu-sheet-head"><h3>조회 결과 <span class="fu-meta">1곳</span></h3>'+button(icon('close'),'icon','aria-label="조회 결과 닫기"')+'</div>'+row,
      'sort':'<div class="fu-split">'+select('범위',['찾은 범위','선택 지역'])+select('정렬',['이름순','가까운 순'])+'</div>'+button('목록 펼치기','quiet','aria-label="목록 전체로 펼치기"'),
      'row':row,
      'pagination':'<div class="fu-stack"><span class="fu-meta">20곳 표시 중</span>'+button('더 보기','secondary','data-pagination-demo')+'<span class="fu-meta" data-pagination-result></span></div>',
      'empty':'<div class="fu-empty"><strong>조건에 맞는 주유소가 없어요</strong><p>검색어를 지우거나 선택한 지역을 바꿔보세요.</p><div class="fu-inline">'+button('검색어 지우기','primary','data-demo-toast="검색어를 지웠어요"')+button('지역 바꾸기','secondary','data-demo-open="region"')+'</div></div>',
      'detail':'<div class="fu-sheet">'+detail+'</div>',
      'badges':'<div class="fu-stack"><div class="fu-inline"><span class="fu-badge">온누리 지류·디지털</span><span class="fu-badge info">지역화폐</span></div><span class="fu-badge">온누리 KB국민카드</span><p class="fu-meta">카드사 확인은 해당 카드사 범위로 표시해요. 지류·QR을 함께 재확인한 뜻이 아니에요.</p></div>',
      'proof':f'<div class="fu-stack"><p class="fu-meta">가맹 확인 · {checked}</p><p class="fu-meta">유가 기준 · {price_date}</p><div class="fu-notice warning"><strong>과거 확인 자료</strong><p>확인일 이후 상태가 바뀔 수 있어요. 방문 전에 주유소에 확인해 주세요.</p></div></div>',
      'prices':price_box,
      'no_price':'<div class="fu-notice"><strong>확보된 유가 정보가 없어요</strong><p>주소와 결제 확인 범위는 계속 볼 수 있어요.</p></div>',
      'menu':menu,
      'rank':f'<div class="fu-inline"><span class="fu-badge">휘발유</span><span class="fu-meta">확보된 가격 중 · {price_date}</span></div><div class="fu-row"><strong>{name}</strong><span>{address}</span><div class="fu-price-row"><span>휘발유</span><strong>{prices["휘발유"]:,.0f}<small>원/L</small></strong></div></div><p class="fu-meta">순위 예시의 한 행이에요. 이 지점이 전국 최저가라는 뜻은 아니에요.</p>',
      'help':'<details class="fu-accordion" open><summary>결제 확인 범위</summary><p>발행사·운영사의 공식 앱이 아니며, 전국 모든 가맹점이나 방문 시 결제를 보장하지 않아요.</p></details><details class="fu-accordion"><summary>내 위치를 허용하지 않았어요</summary><p>지역을 선택하거나 주유소명·주소를 검색할 수 있어요.</p></details>',
      'updates':f'<div class="fu-stack"><div><h3 class="fu-title">자료 기준</h3><p class="fu-meta" style="margin-top:.5rem">이 시안은 보관된 20261103-1 인계본을 사용해요.</p></div><div class="fu-notice"><p>가격과 가맹 확인일은 별개예요. 웹 갱신이 이 보관본을 바꾸지는 않아요.</p></div><p>유가 자료 중 가장 최근 기준일 · {price_date}</p></div>',
      'language':'<div class="fu-segments" data-demo-segments><button type="button" aria-pressed="true">한국어</button><button type="button" aria-pressed="false">English</button></div><p class="fu-meta" style="margin-top:1rem">상호·주소와 입력한 문구는 원문을 유지해요.</p>',
    }
    sections=[]
    for code,group,title,spec,demo in COMPONENTS:
        sections.append(f'<article class="component" data-group="{group}" id="{code}"><header><span class="component-id">{code}</span><h3>{title}</h3></header><p class="component-spec">{spec}</p><div class="demo fuel-ui">{demos[demo]}</div></article>')
    states=[
      ('기본·선택·비활성','<div class="fu-inline">'+button('지역 바꾸기','secondary')+button('온누리 ✓','primary')+button('가까운 순','', 'disabled')+'</div>'),
      ('키보드 초점','<p>아래 버튼으로 Tab 이동해 초점 표시를 확인해요.</p>'+button('지도 보기','secondary','data-focus-example')),
      ('입력 유지·빈 결과',demos['empty']),
      ('지도 표시 실패','<div class="fu-notice error"><strong>지도를 불러오지 못했어요</strong><p>목록에서 주유소 정보를 확인해 주세요.</p></div>'+row),
      ('위치 거절','<div class="fu-notice warning"><strong>내 위치를 확인하지 못했어요</strong><p>지역을 선택하거나 주소를 검색해 주세요.</p></div>'+button('지역 바꾸기','secondary','data-demo-open="region"')),
      ('위치 확인 중','<div class="fu-inline" aria-busy="true">'+button('위치 확인 중','', 'disabled')+'<span>검색은 계속 사용할 수 있어요.</span></div>'),
      ('목록 로딩','<div aria-label="목록 불러오는 중" aria-busy="true"><div class="fu-skeleton big"></div><div class="fu-skeleton"></div><div class="fu-skeleton short"></div></div>'),
      ('짧은 피드백','<div class="fu-toast" role="status">'+icon('check')+'선택한 조건을 초기화했어요</div>'),
      ('긴 이름·주소',f'<div class="fu-row"><strong>(주)대창석유 직영 국일충전소</strong><span class="address">광주광역시 북구 탁영로 11 (두암동)</span><span class="fu-badge">온누리 지류·디지털 · LPG 충전소</span></div><p class="fu-meta">실제 상호·주소의 줄바꿈 예시예요.</p>'),
    ]
    state_html=''.join(f'<article class="state-demo"><h3>{title}</h3><div class="demo fuel-ui">{body}</div></article>' for title,body in states)
    dialogs={'detail':detail,'region':'<h2 class="fu-title" style="margin-bottom:1rem">지역 선택</h2>'+demos['region'],'filters':'<h2 class="fu-title" style="margin-bottom:1rem">검색 필터</h2>'+demos['filters'],'menu':demos['menu'],'results':demos['results'],'rank':demos['rank'],'help':demos['help'],'updates':demos['updates'],'language':demos['language']}
    templates=''.join(f'<template id="template-{key}">{value}</template>' for key,value in dialogs.items())
    css='''
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0}button{font:inherit}header.review-head{max-width:1280px;margin:auto;padding:32px 32px 24px;border-bottom:1px solid var(--fuel-line)}.review-head h1{font-size:28px;margin:8px 0 12px}.review-top{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}.review-nav{display:flex;gap:24px;padding-top:24px;flex-wrap:wrap}.review-nav a{text-decoration:none;font-weight:700}.review-main{max-width:1280px;margin:auto;padding:40px 32px}.review-intro{display:grid;grid-template-columns:1.2fr 1fr;gap:48px;padding-bottom:40px;border-bottom:1px solid var(--fuel-line)}.review-intro h2{font-size:24px;margin-bottom:16px}.review-note{max-width:680px;color:var(--fuel-muted);font-size:16px;line-height:1.7}.review-meta{margin-bottom:16px;font-size:14px;color:var(--fuel-muted)}.review-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}.review-summary strong{font-size:28px;line-height:1.2;display:block}.review-summary span{font-size:14px;color:var(--fuel-muted);display:block;margin-top:8px}.section-title{font-size:24px;margin:40px 0 16px}.section-note{color:var(--fuel-muted);margin-bottom:24px}.group-filter{display:flex;gap:8px;flex-wrap:wrap;padding:16px 0 24px}.component-grid,.state-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 40px}.component,.state-demo{padding:28px 0 32px;border-top:1px solid var(--fuel-line);min-width:0}.component header{display:flex;align-items:baseline;gap:12px}.component h3,.state-demo h3{font-size:18px;margin:0}.component-id{font-size:14px;color:var(--fuel-muted);font-variant-numeric:tabular-nums}.component-spec{font-size:14px;line-height:1.6;color:var(--fuel-muted);margin:10px 0 20px!important}.demo{padding:20px;background:var(--fuel-panel);border-radius:16px;min-width:0;overflow-wrap:anywhere}.state-demo .demo{margin-top:20px}.marker-gallery{display:flex;gap:32px;flex-wrap:wrap;align-items:center}.marker-gallery>div{display:flex;flex-direction:column;align-items:center;gap:12px}.native-slot{border-block:1px dashed var(--fuel-control-line);padding:16px;text-align:center;color:var(--fuel-muted);font-size:14px}.theme-selector{display:flex;align-items:center;gap:12px;font-size:14px}.theme-selector select{font:inherit;min-height:44px;border-radius:12px;padding:8px;border:1px solid var(--fuel-control-line);color:var(--fuel-ink);background:var(--fuel-panel)}.review-footer{margin-top:40px;padding:24px 0;border-top:1px solid var(--fuel-line);font-size:14px;color:var(--fuel-muted)}#demoToast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);max-width:calc(100% - 32px);z-index:10}[hidden]{display:none!important}dialog .dialog-close{margin-bottom:16px;display:flex;justify-content:flex-end}.component .fu-sheet{box-shadow:none}.reference-notes{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}.reference-notes h3{font-size:18px;margin-bottom:12px}.reference-notes p{font-size:16px;line-height:1.7}@media(max-width:700px){header.review-head{padding:24px 16px}.review-main{padding:24px 16px}.review-intro{grid-template-columns:1fr;gap:24px}.component-grid,.state-grid,.reference-notes{grid-template-columns:1fr}.review-summary{gap:16px}.component-spec{font-size:14px}.demo{padding:16px}.review-head h1{font-size:24px}.marker-gallery{gap:20px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}'''
    document=f'''<!doctype html><html lang="ko" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>온누리 주유소 지도 · 디자인 체계 v1</title><link rel="stylesheet" href="system/tokens.css"><link rel="stylesheet" href="system/components.css"><style>{css}</style></head>
<body class="fuel-ui"><header class="review-head"><div class="review-top"><span class="fu-meta">온누리 주유소 지도 · 디자인 검토 v1 · 2026.11.04</span><label class="theme-selector">시트 테마<select id="sheetTheme"><option value="light">라이트</option><option value="dark">다크</option></select></label></div><h1>지도·메뉴·팝업을 하나의 기준으로</h1><p class="review-note">디자인 시안이에요. 실제 토스 출시 버전은 바뀌지 않았어요.</p><nav class="review-nav" aria-label="디자인 검토"><a href="#components">구성요소</a><a href="#states">상태와 복구</a><a href="#principles">적용 원칙</a><a href="app/?region=광주&payment=onnuri">실제 지도 시안 ↗</a><a href="screens.html">대표 화면 모음 ↗</a></nav></header>
<main class="review-main"><section class="review-intro"><div><p class="review-meta">Sand / Indigo / Jade / Sage</p><h2>지도는 넓게, 정보는 읽는 순서대로</h2><p class="review-note">기존 색상과 검증 정보를 유지하면서 검색·선택·조회·상세의 형태와 간격을 맞췄어요. 아래 요소는 같은 토큰과 컴포넌트 CSS를 사용해요.</p><div class="fu-inline" style="margin-top:24px"><a class="fu-button primary" href="app/?region=광주&payment=onnuri">지도 시안 열기 {icon('arrow')}</a><a class="fu-button secondary" href="app/?region=광주&payment=onnuri&view=detail">상세 화면 보기</a></div></div><div class="review-summary"><div><strong>{len(COMPONENTS)}</strong><span>구성요소</span></div><div><strong>{len(states)}</strong><span>상태·변형 예시</span></div><div><strong>16px</strong><span>본문·입력 기준</span></div></div></section>
<section id="components"><h2 class="section-title">구성요소</h2><p class="section-note">팝업 버튼과 선택 조작은 이 시트 안에서 동작해요. 위치·전송·결제는 호출하지 않아요.</p><div class="group-filter" role="group" aria-label="요소 분류">{''.join(button(label,'secondary',f'data-filter-group="{key}" aria-pressed="{str(key=="all").lower()}"') for key,label in [('all','전체'),('foundation','기본'),('map','지도'),('filters','지역·필터'),('results','목록'),('detail','상세'),('support','보조 메뉴')])}</div><div class="component-grid">{''.join(sections)}</div></section>
<section id="states"><h2 class="section-title">상태와 복구</h2><p class="section-note">오류·대기·복구의 디자인 예시예요. 실제 서버 요청 결과가 아니에요.</p><div class="state-grid">{state_html}</div></section>
<section id="principles"><h2 class="section-title">적용 원칙</h2><div class="reference-notes"><div><h3>연구소에서 가져온 과정</h3><p>실제 참고 화면 확인→역할별 토큰→전체 요소와 상태→대표 렌더→작은 화면·키보드 검수.</p></div><div><h3>지도 앱에 맞춘 형태</h3><p>목록은 열린 행과 구분선, 지도 조작은 작은 플로팅 면, 지역·필터·상세는 독립 시트로 구분해요.</p></div><div><h3>정보의 확인 범위</h3><p>가맹 확인일·카드사 범위·유가 기준일을 보존해요. 방문·결제 가능이나 전국 전수를 보장하지 않아요.</p></div></div></section><footer class="review-footer">이 시트와 지도 시안은 별도 로컬 검토본이에요. 토스는 기존 라이트 모드·SDK 내비게이션을 유지하며, 다크 시트는 웹 변형 검토용이에요. 자료는 보관된 20261103-1 인계본, 새 가맹점 조사 없음. Pretendard 원본·OFL 라이선스 포함.</footer></main>
<dialog id="componentDialog" class="fu-sheet fu-dialog" aria-label="구성요소 팝업 예시"><div class="dialog-close">{button('닫기','quiet','data-dialog-close')}</div><div id="dialogBody"></div></dialog>{templates}<div id="demoToast" class="fu-toast" role="status" hidden></div><script src="gallery.js"></script></body></html>'''
    document=document.replace('<select id="sheetTheme">','<select id="sheetTheme" aria-label="시트 테마">')
    document=document.replace('</style>','[data-filter-group][aria-pressed="true"]{background:var(--fuel-primary);color:var(--fuel-on-primary);border-color:var(--fuel-primary)}</style>')
    return document


def build(out, artifact):
    out=out.resolve()
    if out == ROOT or not out.is_relative_to(ROOT/'output') or '_site' in out.parts:
        raise ValueError('Review output must be an isolated directory under output.')
    digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
    if digest != EXPECTED_HASH: raise ValueError('Unexpected artifact; preserve the pinned handoff.')
    out.mkdir(parents=True,exist_ok=True);app=out/'app';app.mkdir(exist_ok=True)
    with zipfile.ZipFile(artifact) as archive:
        if archive.testzip() is not None: raise ValueError('Invalid archive')
        for name in archive.namelist():
            if not name.startswith('sources/') or name.endswith('/'): continue
            target=(app/name[8:]).resolve()
            if not target.is_relative_to(app): raise ValueError('Invalid archive path')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
    original=(app/'index.html').read_text(encoding='utf-8');html=original
    if html.count('<div class="app">')!=1: raise ValueError('App root contract changed')
    html=html.replace('<div class="app">','<div class="app" id="fuelDesignApp">',1)
    html=html.replace('</head>','<link rel="stylesheet" href="../system/tokens.css"><link rel="stylesheet" href="../system/components.css"><link rel="stylesheet" href="../system/prototype.css"></head>')
    html=html.replace('</body>','<script src="../system/prototype.js"></script></body>')
    html,count=re.subn(r'<section([^>]*id="mapFilters"[^>]*)>(.*?)</section>',r'<dialog\1>\2</dialog>',html,count=1,flags=re.S)
    if count!=1: raise ValueError('Filter panel contract changed')
    html=html.replace("saengsaeng: '#3B82F6'","saengsaeng: '#3E50A0'").replace("onnuri:     '#F59E0B'","onnuri:     '#1D3B31'").replace("both:       '#DC2626'","both:       '#6851A2'")
    old='<circle cx="14" cy="14" r="5" fill="#fff"/>'
    new='${color === COLOR.saengsaeng ? \'<path d="m14 8 6 6-6 6-6-6z" fill="#fff"/>\' : color === COLOR.both ? \'<circle cx="10" cy="14" r="3" fill="#fff"/><circle cx="18" cy="14" r="3" fill="#fff"/>\' : \'<circle cx="14" cy="14" r="5" fill="#fff"/>\'}'
    if html.count(old)!=1: raise ValueError('Marker contract changed')
    html=html.replace(old,new)
    html=html.replace("const icons = ['👑','2','3','4','5'];","const icons = ['1','2','3','4','5'];")
    html=html.replace('new kakao.maps.Size(18, 23), { offset: new kakao.maps.Point(9, 23) }','new kakao.maps.Size(24, 31), { offset: new kakao.maps.Point(12, 31) }')
    for key in ['STATIONS','PRICES','PRICE_INFO','MERCHANT_STATUS','NATIONAL_PENDING']:
        pattern=rf'^(?:const|let) {key} = (.+);$'
        if re.search(pattern,original,re.M)[1]!=re.search(pattern,html,re.M)[1]: raise ValueError('Data changed: '+key)
    (app/'index.html').write_text(html,encoding='utf-8')
    system=out/'system';system.mkdir(exist_ok=True)
    for name in ['tokens.css','components.css','prototype.css','prototype.js']:
        shutil.copyfile(DESIGN/name,system/name)
    shutil.copytree(DESIGN/'fonts',system/'fonts',dirs_exist_ok=True)
    gallery_js=(DESIGN/'gallery.js').read_text(encoding='utf-8')
    (out/'gallery.js').write_text(gallery_js,encoding='utf-8')
    data=lambda key:json.loads(re.search(rf'^(?:const|let) {key} = (.+);$',original,re.M)[1])
    stations=data('STATIONS');sample=next(s for s in stations if s['name']=='서양새마을금고 주유소')
    prices=data('PRICES')[sample['id']];checked=sample['verification']['onnuri']['checked_at'][:10]
    day=max(data('PRICE_INFO')[sample['id']]['source_dates']);price_date=day[:4]+'-'+day[4:6]+'-'+day[6:]
    count=sum(s['region']=='광주' and 'onnuri' in s['payment_types'] for s in stations)
    (out/'index.html').write_text(render_gallery(sample,prices,checked,price_date,count),encoding='utf-8')
    (out/'screens.html').write_text('''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>온누리 지도 · 대표 화면</title><link rel="stylesheet" href="system/tokens.css"><style>*{box-sizing:border-box}body{margin:0;background:#f1f0ef;color:#1f2d5c;font:400 16px/1.6 var(--fuel-font)}main{max-width:1320px;margin:auto;padding:32px}h1{font-size:28px;margin:0 0 8px}p{margin:0 0 24px;color:#60646c}.screens{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}figure{margin:0;min-width:0}figcaption{font-weight:700;margin-bottom:12px}iframe{border:1px solid #cfceca;border-radius:20px;display:block;width:100%;height:780px;background:white}a{color:#1d3b31}@media(max-width:850px){.screens{grid-template-columns:1fr}main{padding:20px}iframe{max-width:390px;margin:auto}figure{margin-bottom:24px}}</style></head><body><main><h1>온누리 주유소 지도 · 디자인 시안</h1><p>실제 지도와 보관 자료를 사용하는 로컬 검토본 · 토스 내비게이션은 실제 앱에서 SDK가 제공합니다. <a href="index.html">전체 구성요소 보기</a></p><div class="screens"><figure><figcaption>01 지도·검색</figcaption><iframe title="지도·검색 시안" src="app/?region=광주&payment=onnuri"></iframe></figure><figure><figcaption>02 검색 필터</figcaption><iframe title="검색 필터 시안" src="app/?region=광주&payment=onnuri&view=filters"></iframe></figure><figure><figcaption>03 주유소 상세</figcaption><iframe title="상세 정보 시안" src="app/?region=광주&payment=onnuri&view=detail"></iframe></figure></div></main></body></html>''',encoding='utf-8')
    version=hashlib.sha256(b''.join((DESIGN/name).read_bytes() for name in ['tokens.css','components.css','prototype.css','prototype.js','gallery.js'])).hexdigest()[:12]
    for page in [app/'index.html',out/'index.html',out/'screens.html']:
        content=page.read_text(encoding='utf-8')
        content=re.sub(r'((?:src|href)="(?:\.\./)?system/[^"?]+)(")',rf'\1?v={version}\2',content)
        content=content.replace('src="gallery.js"',f'src="gallery.js?v={version}"')
        page.write_text(content,encoding='utf-8')
    inventory=[{'id':code,'family':group,'name':name,'contract':spec,'demo':demo} for code,group,name,spec,demo in COMPONENTS]
    (DESIGN/'inventory.json').write_text(json.dumps({'status':'design_proposal_not_deployed','components':inventory,'count':len(inventory)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'manifest.json').write_text(json.dumps({'status':'local_design_review_not_release','pinnedArtifactSha256':digest,'datasetsPreserved':5,'components':len(inventory),'stateExamples':9,'sourceFiles':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DESIGN.glob('*') if p.is_file()},'previewUsesActualMap':True,'realPhoneVerified':False,'dataCollectionAdded':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(out),'components':len(inventory),'stateExamples':9,'datasetsPreserved':5},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'output/design-system-20261104/site')
    parser.add_argument('--artifact',type=Path,default=DEFAULT_ARTIFACT)
    args=parser.parse_args();build(args.out,args.artifact)
