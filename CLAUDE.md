# 광주 주유소 결제 가능 지도 에이전트

## 프로젝트 개요

광주광역시에서 **온누리상품권**과 **광주상생카드**를 사용할 수 있는 주유소를 수집하여
`/output/gas_stations.json`으로 저장하고, 카카오맵 기반 `map.html` 지도 파일을 생성하는 단일 에이전트.

- 에이전트 구조: 단일 CLAUDE.md 오케스트레이터 + 3개 스킬 (data-fetcher, gas-filter, map-builder)
- 스킬 간 통신: `/output/` 파일 기반 전달 (직접 데이터 전달 없음)

---

## 환경 설정

### API 키 확인

프로젝트 루트에 `.env` 파일이 있어야 합니다. 없으면 `env.example`을 복사하여 작성 요청.

| 환경변수 | 용도 | 필수 여부 |
|---------|------|---------|
| `ONNURI_API_KEY` | 공공데이터포털 온누리상품권 REST API | 필수 |
| `KAKAO_REST_API_KEY` | 카카오 Local API (주소→좌표) | 조건부 (좌표 누락 시) |
| `KAKAO_MAPS_APP_KEY` | 카카오맵 JavaScript SDK | 필수 (Step 6) |

**키가 없으면 해당 스킬 실행 전 즉시 에스컬레이션하여 사용자에게 키를 요청하라.**

---

## 업종 키워드

스크립트(`filter_gas.py`)는 이 섹션을 파싱하여 주유소를 필터링한다.
섹션명과 키워드 형식을 변경하지 말 것.

### 온누리상품권 필터 키워드
주유소, 주유, 석유, oil, 유류, 휘발유, 경유

### 광주상생카드 필터 키워드 (storeCtgy 값)
주유소, 주유, 가스충전, 유류
<!-- 실제 확인된 storeCtgy: GS주유소, SK주유소, 쌍용S-oil주유소, 현대정유오일뱅크, 주 유 소, SK가스충전소, GS가스충전소 등. fetch_sangsaeng.py는 서버 측 업종 검색으로 수집. -->

---

## 워크플로우

### 전체 실행 순서
Step 1 → 변동 감지 → Step 2 → Step 3 → Step 4(조건부) → Step 5 → Step 6

### 변동 감지 로직 (재실행 시)

```
1. Step 1 항상 실행 (최신 raw 데이터 수집)
2. raw 데이터에서 주유소 이름+주소 Set 추출
3. /output/gas_stations.json 존재 여부 확인
   - 없으면: Step 2~6 전체 실행
   - 있으면: 기존 이름+주소 Set과 비교
     - Set 동일: Step 2~6 스킵, "데이터 변동 없음" 메시지 출력 후 종료
     - Set 다름: Step 2~6 전체 실행
```

---

### [Step 1] 데이터 수집 — `data-fetcher` 스킬

트리거: 워크플로우 시작 시 가장 먼저 호출

#### Step 1-A: 온누리상품권 공공데이터 (보조, 전통시장 한정)

- 스크립트: `.claude/skills/data-fetcher/scripts/fetch_onnuri.py`
- `ONNURI_API_KEY` 없으면 즉시 에스컬레이션
- 공공데이터포털 REST API 호출, 광주광역시 필터 파라미터 사용
- **한계**: 전통시장·골목형 상점가 소속 가맹점만 포함, 주소 필드 없음 → Step 1-B가 주력
- API 참조: `.claude/skills/data-fetcher/references/api_guide.md` §1
- 결과 저장: `/output/raw_onnuri.json`
- 성공 기준: 레코드 1건 이상
- 실패 시: 자동 재시도 최대 3회 → 에스컬레이션

#### Step 1-B: 온누리 플레이스 (onnuri.gift 내부 API) ⭐ 주력 소스

- 스크립트: `.claude/skills/data-fetcher/scripts/fetch_onnuri_place.py`
- **비공개 내부 API** — onnuri.gift 사이트가 내부적으로 사용하는 엔드포인트
  (`POST https://onnuri.gift/api/v1/place/search`)
- 반경 1km 고정이므로 광주 전체를 1.5km 격자(~300점)로 스캔
- `frCd` 기준 중복 제거
- 결과 저장: `/output/raw_onnuri_place.json`
- 성공 기준: 50건 이상 (광주 기준 100건 내외 정상)
- API 구조 변경 감지 시: 에스컬레이션 후 DevTools 재추적 필요
- API 참조: `.claude/skills/data-fetcher/references/api_guide.md` §4

#### Step 1-C: 광주상생카드

- 스크립트: `.claude/skills/data-fetcher/scripts/fetch_sangsaeng.py`
- **1차**: `https://www.gwangju.go.kr/pg/getGjCardList.do` (POST)
  - 응답에서 `storeCtgy` 값 목록 확인 → 광주상생카드 필터 키워드 섹션 업데이트
  - 응답에 `lot`, `lalt` 좌표 필드 포함 여부 확인하여 로그에 기록
- **1차 실패**(3회 재시도 후): 공공데이터포털 상생카드 CSV fallback
- 결과 저장: `/output/raw_sangsaeng.json`
- 성공 기준: 레코드 1건 이상

---

### [Step 2] 주유소 필터링 — `gas-filter` 스킬

트리거: `raw_onnuri.json`과 `raw_sangsaeng.json`이 모두 존재할 때

- 스크립트: `.claude/skills/gas-filter/scripts/filter_gas.py`
- CLAUDE.md 업종 키워드 섹션을 파싱하여 필터링 기준으로 사용
- 온누리: 업종명/코드 필드를 키워드 목록과 매칭
- 상생카드: `storeCtgy` 필드를 키워드 목록과 매칭
- 결과 저장: `/output/filtered_onnuri.json`, `/output/filtered_sangsaeng.json`
- 성공 기준: 두 소스 합산 1건 이상
- 0건 시: 에스컬레이션 (업종 필드명/값 확인 요청)

---

### [Step 3] 데이터 통합 및 중복 제거 — `gas-filter` 스킬 (계속)

#### Step 3-A: 중복 판단

- 스크립트: `.claude/skills/gas-filter/scripts/dedup.py`
- 두 소스에서 상호명 또는 주소가 유사한 쌍을 후보로 추출
- LLM에게 상호명+주소 쌍 제시, `confidence` 0~1 점수 요청
- confidence ≥ 0.85: 중복으로 판단
  - 상생카드 항목 유지 (좌표 포함), 온누리 태그 복사 후 온누리 항목 삭제
- confidence < 0.85: 별개 항목으로 유지

#### Step 3-B: 통합 및 태그 부여

- 스크립트: `.claude/skills/gas-filter/scripts/merge.py`
- 중복 제거 후 두 소스 병합
- `payment_types` 태그 부여: `["saengsaeng"]` / `["onnuri"]` / `["saengsaeng", "onnuri"]`
- `source` 태그 부여: 원본 데이터 출처 기록
- 결과 저장: `/output/merged_stations.json`

---

### [Step 4] 좌표 보완 (조건부) — `map-builder` 스킬

트리거: `merged_stations.json`에 `lat`/`lng` 없는 항목이 1건 이상 존재할 때만 실행.
**두 API 모두 좌표 제공이 확인된 경우 이 단계 전체 스킵.**

- 스크립트: `.claude/skills/map-builder/scripts/geocode.py`
- `KAKAO_REST_API_KEY` 없으면 에스컬레이션
- 좌표 없는 항목의 주소로 카카오 주소검색 API 호출
- 실패 항목: `output/error.log`에 기록 후 목록에서 제외
- 성공 기준: 전체 항목의 80% 이상 좌표 보유
- 80% 미달 시: 에스컬레이션

---

### [Step 5] JSON 저장

트리거: 통합(+좌표) 데이터 준비 완료 후

- `/output/gas_stations.json` 저장
- 스키마: `docs/data_schema.md` 참조
- 성공 기준: 파일 생성 + 유효한 JSON + 레코드 1건 이상
- 실패 시: 자동 재시도 1회

---

### [Step 6] 웹 지도 생성 — `map-builder` 스킬

트리거: `/output/gas_stations.json` 생성 후

- 스크립트: `.claude/skills/map-builder/scripts/build_map.py`
- `KAKAO_MAPS_APP_KEY` 없으면 에스컬레이션
- `/output/map.html` 생성
- LLM 자기 검증 (생성 후 반드시 수행):
  1. Kakao Maps API 코드 패턴 유효성
  2. 마커 수 = `gas_stations.json` 레코드 수 일치
  3. 필터 토글 (전체/상생카드/온누리) 동작 로직
  4. 주유소명 텍스트 검색 동작 로직
- 검증 실패 시: 자동 재시도 1회 (코드 수정 후 재생성)
- 성공 기준: 브라우저에서 렌더링 가능한 HTML

---

## 에스컬레이션 기준

| 상황 | 조치 |
|------|------|
| API 키 없음 | 즉시 에스컬레이션, 사용자에게 키 요청 |
| API 호출 3회 실패 | 에스컬레이션, 오류 내용 포함 |
| 주유소 0건 추출 | 에스컬레이션, 업종 필드 구조 확인 요청 |
| gwangju.go.kr 구조 변경 감지 | 에스컬레이션, fallback 전환 안내 |
| Geocoding 성공률 80% 미달 | 에스컬레이션, 데이터 품질 확인 요청 |

---

## 산출물 파일

| 파일 | 경로 | 설명 |
|------|------|------|
| 온누리 원본 | `/output/raw_onnuri.json` | Step 1-A 원본 응답 |
| 상생카드 원본 | `/output/raw_sangsaeng.json` | Step 1-B 원본 응답 |
| 필터링 결과 | `/output/filtered_onnuri.json` | Step 2 결과 |
| 필터링 결과 | `/output/filtered_sangsaeng.json` | Step 2 결과 |
| 통합 데이터 | `/output/merged_stations.json` | Step 3 결과 |
| 최종 데이터 | `/output/gas_stations.json` | Step 5 최종 산출물 |
| 지도 페이지 | `/output/map.html` | Step 6 최종 산출물 |
| 오류 로그 | `/output/error.log` | 에러 기록 |
