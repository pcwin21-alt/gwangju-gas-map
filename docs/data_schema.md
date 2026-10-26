# gas_stations.json 스키마 정의

## 파일 위치
`/output/gas_stations.json`

## 최상위 구조
JSON Array — 각 원소가 주유소 1개.

## 카드사 교차확인 보완 자료

`source: ["kb_onnuri"]`, `verification.onnuri.provider: "kbcard"`는 온누리 운영사 검색과 별개의 KB국민카드 공개 사용처 조회 근거다. ID는 `onnuri:kb:<카드사 가맹점 ID>`로 분리한다. 카드사의 온누리 표시·차량 연료 업종·상호·주소권역·좌표와 공식 상권자료의 상세주소를 함께 확인한 경우에만 추가한다. 현재 운영사 확정 기록이 같은 장소에 있으면 그것을 유지한다.

`onnuri_methods.card/digital`은 true, `paper/qr`은 미확인을 뜻하는 null이다. 지류·QR·다른 카드사의 사용 가능 여부를 추정하지 않는다. `issuer_scope: ["KB국민카드"]` 및 조회일을 화면에 구분한다. 카드사 데이터의 원천 기준일은 알 수 없어 `source_date`는 null이며, `checked_at`만 기록한다. 30일 경과하면 stale로 표시하고 경유 추천에서 제외한다.

`output/supplemental_onnuri_evidence.json`이 검토된 근거 정본이다. 재갱신·실패 시 기존 온누리 검색 스냅샷을 덮어쓰지 않고 별도로 합친다. 발견용 전체 조회 결과를 자동 승격하지 않는다.

## 필드 정의

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `name` | string | ✅ | 주유소 상호명 |
| `address` | string | ✅ | 주소 (도로명 또는 지번) |
| `lat` | number\|null | ✅ | 위도 (WGS84) |
| `lng` | number\|null | ✅ | 경도 (WGS84) |
| `payment_types` | string[] | ✅ | 사용 가능한 결제수단 목록 |
| `source` | string[] | ✅ | 원본 데이터 출처 |

### `payment_types` 가능한 값

| 값 | 의미 | 지도 마커 색상 |
|----|------|--------------|
| `["saengsaeng"]` | 광주상생카드만 | 파란색 (#3B82F6) |
| `["onnuri"]` | 온누리상품권만 | 노란색 (#F59E0B) |
| `["saengsaeng", "onnuri"]` | 둘 다 가능 | 진홍색 (#DC2626) |

### `source` 가능한 값

| 값 | 의미 |
|----|------|
| `"saengsaeng"` | gwangju.go.kr API 또는 공공데이터포털 상생카드 CSV |
| `"onnuri"` | 공공데이터포털 온누리상품권 REST API (전통시장 한정) |
| `"onnuri_place"` | onnuri.gift 내부 API — 주력 소스, 주소+좌표 포함 |

## 예시

```json
[
  {
    "name": "광주주유소",
    "address": "광주광역시 북구 용봉로 123",
    "lat": 35.1765,
    "lng": 126.9123,
    "payment_types": ["saengsaeng", "onnuri"],
    "source": ["saengsaeng", "onnuri"]
  },
  {
    "name": "GS칼텍스 무등주유소",
    "address": "광주광역시 동구 무등로 45",
    "lat": 35.1453,
    "lng": 126.9231,
    "payment_types": ["onnuri"],
    "source": ["onnuri"]
  },
  {
    "name": "북구주유소",
    "address": "광주광역시 북구 신안로 78",
    "lat": 35.1842,
    "lng": 126.8965,
    "payment_types": ["saengsaeng"],
    "source": ["saengsaeng"]
  }
]
```

## 중간 파일 스키마

### `/output/raw_onnuri_place.json` ⭐ 주력 온누리 소스
onnuri.gift 내부 API 격자 스캔 결과. 주요 필드:
- `frCd`: 가맹점 고유 코드 (중복 제거 기준)
- `frcsNm`: 가맹점명
- `frcsAddr`: 도로명 주소
- `latitude`, `longitude`: 좌표 (WGS84)
- `paperYn`, `cardYn`, `qrYn`: 지류/카드/QR 결제 가능 여부

### `/output/raw_onnuri.json`
공공데이터포털 API 원본 응답 배열 (전통시장 한정, 주소 없음). 필드명은 API 응답에 따라 다름.

### `/output/raw_sangsaeng.json`
gwangju.go.kr API 원본 응답 배열. 주요 필드:
- `storeNm`: 가맹점명
- `storeCtgy`: 업종분류
- `storeAddr`: 주소
- `lot`: 위도
- `lalt`: 경도

### `/output/filtered_onnuri.json` / `/output/filtered_sangsaeng.json`
주유소만 필터링된 배열. 원본 필드 유지.

### `/output/dedup_result.json`
```json
{
  "cleaned_onnuri": [...],
  "updated_sangsaeng": [...],
  "judged_pairs": [...],
  "stats": {
    "original_onnuri": 10,
    "original_sangsaeng": 15,
    "removed_onnuri_duplicates": 3,
    "confidence_threshold": 0.85
  }
}
```

### `/output/merged_stations.json`
`gas_stations.json`과 동일한 스키마. geocode.py 입력용.
