# gas_stations.json 스키마 정의

## 파일 위치
`/output/gas_stations.json`

## 최상위 구조
JSON Array — 각 원소가 주유소 1개.

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
| `"onnuri"` | 공공데이터포털 온누리상품권 REST API |

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

### `/output/raw_onnuri.json`
공공데이터포털 API 원본 응답 배열. 필드명은 API 응답에 따라 다름.

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
