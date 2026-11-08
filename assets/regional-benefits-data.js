/* Official regional policy records. Merchant verification and fuel prices are separate. */
(function (root) {
  'use strict';
  const policies = {
    saengsaeng: {
      name: '광주상생카드',
      official: 'https://www.gwangju.go.kr/economy/boardList.do?boardId=BD_0802013200&pageId=economy132',
      checkedOn: '2026-11-08',
      base: {
        label: '기본 혜택 10%',
        detail: '선불카드는 구매할 때 할인되고, 체크카드는 충전한 금액 중 사용액에 대해 다음 달 캐시백을 받아요. 체크·선불 통합 월 50만 원 한도이며 법인은 제외돼요.',
        startsOn: '2026-09-03',
        source: 'https://www.gwangju.go.kr/economy/contentsView.do?pageId=economy125',
      },
      notices: [{
        title: '추석 15% 특별할인 종료, 기본 10% 전환',
        publishedOn: '2026-09-03',
        endedOn: '2026-09-03',
        detail: '특별할인 한도 소진으로 9월 3일부터 기본 혜택으로 돌아왔어요.',
        source: 'https://www.gwangju.go.kr/economy/boardView.do?pageId=economy132&boardId=BD_0802013200&seq=19',
      }],
    },
    'incheon-eum': {
      name: '인천e음',
      official: 'https://www.incheon.go.kr/eco/ECO050101/list?srchKey=srchSj&srchWord=%EC%9D%B8%EC%B2%9Ce%EC%9D%8C',
      checkedOn: '2026-11-08',
      base: {
        label: '기본 캐시백 10%',
        detail: '10~12월 기본 혜택은 월 결제 50만 원까지 적용돼요.',
        startsOn: '2026-10-01',
        endsOn: '2026-12-31',
        source: 'https://www.incheon.go.kr/eco/ECO050101/view?nttNo=2046197',
      },
      notices: [{
        title: '코리아 그랜드 페스티벌 캐시백 상향',
        label: '한시 캐시백 15%',
        publishedOn: '2026-10-27',
        startsOn: '2026-10-29',
        endsOn: '2026-11-15',
        detail: '연매출 30억 원 이하 가맹점 결제에 월 50만 원 한도로 적용돼요. 착한가격업소는 20%, 강화·옹진군은 20%(해당 지역 착한가격업소 25%)예요. 예산 소진 시 조기 종료돼요.',
        source: 'https://www.incheon.go.kr/IC010101/view?nttNo=2046317',
      }],
    },
    'busan-dongbaek': {
      name: '동백전',
      official: 'https://busandong100.kr/cs/notice',
      checkedOn: '2026-11-08',
      base: {
        label: '기본 캐시백 8~10%',
        detail: '가맹점 연매출 10억 원 이하는 10%, 10억 원 초과 30억 원 이하는 8%예요. 30억 원을 초과하면 기본 캐시백이 없어요.',
        startsOn: '2026-01-01',
        source: 'https://www.busandong100.kr/cs/faq?category=0',
      },
      notices: [{
        title: '코리아 그랜드 페스티벌 추가 5% 조기 종료',
        publishedOn: '2026-11-04',
        endedOn: '2026-11-04',
        detail: '동백전 운영사가 추가 캐시백 조기 종료를 공지했어요. 기본 캐시백은 가맹점 매출에 따라 달라요.',
        source: 'https://busandong100.kr/cs/notice',
      }],
    },
    'gangwon-gift': {
      name: '강원상품권',
      official: 'https://gwgc.gwd.go.kr/site/board/selectBoardList.do?bbsId=BBSMSTR_000000000001',
      checkedOn: '2026-11-08',
      base: {
        label: '모바일 구매할인 5%',
        detail: '1인당 월 20만 원 한도로, 11월 발행은 11월 2일 오전 9시로 안내됐어요. 월 발행액이 소진되면 구매할 수 없어요. 지류형은 개인에게 판매하지 않아요.',
        startsOn: '2026-11-02',
        endsOn: '2026-11-30',
        source: 'https://gwgc.gwd.go.kr/site/board/selectBoardArticle.do?bbsId=BBSMSTR_000000000001&nttId=2101&bbsTyCode=BBST03&bbsAttrbCode=BBST03',
      },
    },
    'jeju-tamna': {
      name: '탐나는전',
      official: 'https://www.jeju.go.kr/news/bodo/list.htm?q=%ED%83%90%EB%82%98%EB%8A%94%EC%A0%84&searchType=title',
      checkedOn: '2026-11-08',
      base: {
        label: '기본 적립 10%',
        detail: '연매출 10억 원 이하 가맹점에서 결제하면 월 결제액 100만 원까지 10%를 적립해요. 예산 상황에 따라 달라질 수 있어요.',
        startsOn: '2026-11-01',
        endsOn: '2026-12-31',
        source: 'https://www.jeju.go.kr/news/bodo/list.htm?act=view&seq=2039869',
      },
      notices: [{
        title: '코리아 그랜드 페스티벌 추가 적립',
        label: '최대 적립 15%',
        publishedOn: '2026-10-30',
        startsOn: '2026-11-01',
        endsOn: '2026-11-15',
        detail: '적립 대상 결제 중 행사 기간 35만 원까지 기본 10%에 5%가 추가돼요. 추가 적립은 예산 소진 시 조기 종료될 수 있어요.',
        source: 'https://www.jeju.go.kr/news/bodo/list.htm?act=view&seq=2039869',
      }],
    },
    'daegu-ropay': {
      name: '대구로페이',
      official: 'https://www.daegu.go.kr/index.do?menu_id=00000854&menu_link=%2Ficms%2Fbbs%2FselectBoardList.do&bbsId=BBS_00029&searchCnd=0&searchWrd=%EB%8C%80%EA%B5%AC%EB%A1%9C%ED%8E%98%EC%9D%B4',
      checkedOn: '2026-11-08',
      pending: '할인 판매는 차수별 물량과 판매처에 따라 달라요. 지금 할인 충전이 가능한지는 대구시 공지와 iM샵에서 확인하세요.',
      notices: [{
        title: '코리아 그랜드 페스티벌 결제 캐시백',
        label: '한시 캐시백 5%',
        publishedOn: '2026-10-26',
        startsOn: '2026-10-29',
        endsOn: '2026-11-15',
        detail: '행사 기간 결제에 5%를 돌려줘요. 일반 충전 잔액도 대상이며 착한가격업소 추가분은 별도예요. 예산 소진 시 조기 종료되고 10% 할인 충전은 판매처 잔여 물량을 확인해야 해요.',
        source: 'https://www.daegu.go.kr/index.do?menu_id=00000854&menu_link=%2Ficms%2Fbbs%2FselectBoardArticle.do&bbsId=BBS_00029&nttId=828698',
      }, {
        title: '하반기 10% 할인 판매 안내',
        publishedOn: '2026-09-14',
        startsOn: '2026-09-21',
        detail: '9월 발행 공고의 할인율은 10%, 구매 한도는 월 30만 원이었어요. 현재 구매 가능 여부는 판매처의 잔여 물량을 확인해야 해요.',
        source: 'https://www.daegu.go.kr/index.do?menu_id=00000854&menu_link=%2Ficms%2Fbbs%2FselectBoardArticle.do&bbsId=BBS_00029&nttId=823438',
      }],
    },
    'ulsan-pay': {
      name: '울산페이',
      official: 'https://www.ulsan.go.kr/u/economy/bbs/list.do?bbsId=BBS_0000000000000069&mId=001007004002003000',
      checkedOn: '2026-11-08',
      base: {
        label: '캐시백 13%',
        detail: '일반 결제 캐시백은 11월 30일까지 월 이용액 50만 원 한도로 안내됐어요.',
        startsOn: '2026-11-06',
        endsOn: '2026-11-30',
        source: 'https://www.ulsan.go.kr/u/rep/bbs/view.do?bbsId=BBS_0000000000000003&dataId=185001&mId=001004001001000000',
      },
      notices: [{
        title: '코리아 그랜드 페스티벌 추가 캐시백 조기 종료',
        publishedOn: '2026-11-06',
        endedOn: '2026-11-06',
        detail: '행사 추가 5%가 예산 소진으로 종료됐어요. 울산시는 기존 13%와 월 이용액 50만 원 조건을 11월 30일까지 유지한다고 안내했어요.',
        source: 'https://www.ulsan.go.kr/u/rep/bbs/view.do?bbsId=BBS_0000000000000003&dataId=185001&mId=001004001001000000',
      }],
    },
    yeominjeon: {
      name: '여민전',
      official: 'https://ddv.konacard.co.kr/total-guide/card-application?aspId=000193000000000&kaId=410307830187801&konaLangCd=ko&useAppLinkBtn=false&useChatbot=false',
      pending: '운영사 안내에 따라 이번 달 결제 캐시백률과 한도는 여민전 앱 홈 또는 공지사항에서 확인하세요.',
    },
  };

  function context(region, payment, currencies) {
    if (payment === 'onnuri') return null;
    if (Object.hasOwn(policies, payment)) return payment;
    return Object.keys(policies).find(id => currencies.product(id)?.region === region) ||
      (payment === 'local' ? 'local' : null);
  }

  function noticeState(notice, today) {
    if (notice.endedOn && today >= notice.endedOn) return '종료';
    if (notice.startsOn && today < notice.startsOn) return '예정';
    if (notice.endsOn && today > notice.endsOn) return '기간 종료';
    return notice.endsOn ? '기간 한정 공지' : '공식 소식';
  }

  function snapshot(id, today) {
    if (!Object.hasOwn(policies, id)) return null;
    const policy = policies[id];
    const age = (Date.parse(today) - Date.parse(policy.checkedOn)) / 86400000;
    const fresh = age >= 0 && age <= 7;
    const active = entry => entry?.startsOn && entry.startsOn <= today &&
      (!entry.endsOn || today <= entry.endsOn) && (!entry.endedOn || today < entry.endedOn);
    const base = fresh && active(policy.base) ? policy.base : null;
    const notices = (policy.notices || []).filter(n => n.publishedOn <= today)
      .sort((a,b) => b.publishedOn.localeCompare(a.publishedOn))
      .map(n => ({...n, state: noticeState(n, today)}));
    const promotion = fresh ? notices.find(n => n.label && active(n)) : null;
    return {...policy, base, notices, promotion, current: promotion || base};
  }

  const api = { policies, context, snapshot };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GasRegionalBenefits = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
