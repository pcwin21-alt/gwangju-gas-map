/* Region benefit information uses the map filters, with independent dialog selection. */
(() => {
  'use strict';
  const data = GasRegionalBenefits;
  const byId = id => document.getElementById(id);
  const button = byId('regionalBenefitsOpen');
  const menu = byId('regionalBenefitsMenu');
  const dialog = byId('regionalBenefitsDialog');
  const choice = byId('regionalBenefitsChoice');
  const content = byId('regionalBenefitsContent');
  let selected = null, nationwide = false, returnFocus, renderedDay;
  const make = (tag, value, cls) => {
    const element = document.createElement(tag);
    element.textContent = value;
    if (cls) element.className = cls;
    return element;
  };
  const link = (label, url) => {
    const anchor = make('a', label + ' ↗');
    anchor.href = url;
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    return anchor;
  };
  function renderOverview(today) {
    const list = make('ul', '', 'regional-news-list');
    for (const id of Object.keys(data.policies)) {
      const view = data.snapshot(id, today);
      const region = GasRegionalCurrency.product(id).region;
      const latest = view.notices[0];
      const row = make('li', '');
      const action = make('button', '', 'regional-news-row');
      action.type = 'button';
      action.append(
        make('strong', region + ' · ' + view.name),
        make('span', view.current?.label || '공식 안내 확인', 'regional-news-rate')
      );
      if (latest) {
        action.append(make('span', latest.title, 'regional-news-title'));
        action.append(make('span', latest.publishedOn + ' · ' + latest.state, 'policy-meta'));
      }
      action.addEventListener('click', () => {
        choice.value = id;
        render(today);
        choice.focus();
      });
      row.append(action);
      list.append(row);
    }
    content.replaceChildren(list);
  }

  function render(today) {
    renderedDay = today;
    const view = data.snapshot(choice.value, today);
    if (!view) {
      renderOverview(today);
      return;
    }
    const current = view.current;
    content.replaceChildren(make('h3', current?.label || '현재 적용률 확인'));
    content.append(make('p', current?.detail || view.pending ||
      '최근 확인한 자료로는 현재 적용률을 표시하기 어려워요. 공식 공지에서 확인하세요.'));
    if (view.checkedOn) content.append(make('p', '공식 자료 확인 ' + view.checkedOn, 'policy-meta'));
    if (current) {
      content.append(link('혜택 조건 원문', current.source));
      if (view.promotion && view.base) {
        content.append(make('p', view.base.label + ' · 일반 운영 기준', 'policy-meta'));
      }
    }
    content.append(link(view.name + ' 공식 최신 안내', view.official));
    content.append(make('p', '실제 혜택은 주유소별 적용 조건과 남은 한도에 따라 달라요.', 'policy-meta'));
    if (!view.notices.length) return;
    const news = make('section', '', 'policy-news-item');
    news.append(make('h3', '최근 정책 소식'));
    for (const notice of view.notices) {
      const item = make('article', '');
      item.append(make('span', notice.state, 'policy-state'), make('h4', notice.title));
      const timing = notice.startsOn && notice.endsOn ? ' · 적용 ' + notice.startsOn + ' ~ ' + notice.endsOn : '';
      item.append(make('p', '공지 ' + notice.publishedOn + timing, 'policy-meta'), make('p', notice.detail));
      if (notice.source !== current?.source) item.append(link('공지 원문', notice.source));
      news.append(item);
    }
    content.append(news);
  }

  function update() {
    const today = GasOnnuriPolicy.koreanDay();
    const params = new URL(location.href).searchParams;
    const region = params.get('region');
    selected = data.context(region, params.get('payment'), GasRegionalCurrency);
    nationwide = GasNational.regionFromURL(region) === 'all';
    byId('policyOpen').hidden = !nationwide && Boolean(selected);
    button.hidden = !nationwide && !selected;
    const view = nationwide ? null : data.snapshot(selected, today);
    byId('regionalBenefitsLabel').textContent = view ?
      view.name + ' ' + (view.current?.label || '혜택') : '지역화폐 소식';
    if (dialog.open && renderedDay !== today) render(today);
  }

  function show(event) {
    returnFocus = event.currentTarget;
    choice.value = !nationwide && Object.hasOwn(data.policies, selected) ? selected : '';
    dialog.querySelector('.policy-body').scrollTop = 0;
    render(GasOnnuriPolicy.koreanDay());
    dialog.showModal();
  }

  choice.add(new Option('전체 지역 소식', ''));
  for (const [id, policy] of Object.entries(data.policies)) choice.add(new Option(policy.name, id));
  choice.addEventListener('change', () => render(GasOnnuriPolicy.koreanDay()));
  button.addEventListener('click', show);
  menu.addEventListener('click', show);
  byId('regionalBenefitsClose').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    const target = returnFocus?.getClientRects().length ? returnFocus : byId('toolsOpenBtn');
    target?.focus({preventScroll:true});
  });
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
  });
  window.GasRegionalBenefitsUI = { update };
  document.addEventListener('visibilitychange', () => { if (!document.hidden) update(); });
  setInterval(update, 60000);
  update();
})();
