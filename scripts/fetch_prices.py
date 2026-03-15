"""
Opinet 유가정보 수집 (하이브리드 방식)
1단계: aroundAll — 구별 중심점 15회 호출로 광주 전체 수집
2단계: detailById — 1단계 미매칭 중 캐시에 UNI_ID 있는 것만 보완

총 호출: 15 + 미매칭캐시수 (최초 실행 이후 점진적으로 줄어듦)

실행: python scripts/fetch_prices.py
출력: output/gas_prices.json
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

OUTPUT_FILE = ROOT / "output" / "gas_prices.json"

API_KEY = os.getenv("OPINET_API_KEY")
BASE = "https://www.opinet.co.kr/api"

# 광주 5개 구 중심 KATEC 좌표
GU_CENTERS = {
    "광산구": (287723, 276570),
    "남구":   (293641, 276515),
    "북구":   (302952, 286259),
    "서구":   (293078, 279735),
    "동구":   (302761, 281296),
}

FUELS = [("B027", "휘발유"), ("B034", "경유"), ("D047", "LPG")]
RADIUS = 15000


def normalize(s: str) -> str:
    return (s.lower()
            .replace(" ", "")
            .replace("(주)", "").replace("㈜", "")
            .replace("(유)", "").replace("유한회사", "")
            .replace("주식회사", "").replace("(주)", ""))


def fetch_around(x, y, prodcd) -> list:
    resp = requests.get(f"{BASE}/aroundAll.do", params={
        "code": API_KEY, "out": "json",
        "x": x, "y": y, "radius": RADIUS, "prodcd": prodcd, "sort": 1,
    }, timeout=10)
    resp.raise_for_status()
    return resp.json().get("RESULT", {}).get("OIL", [])


def fetch_detail(uni_id: str) -> dict:
    resp = requests.get(f"{BASE}/detailById.do",
        params={"code": API_KEY, "out": "json", "id": uni_id}, timeout=10)
    resp.raise_for_status()
    oils = resp.json().get("RESULT", {}).get("OIL", [])
    if not oils:
        return {}
    return {
        p["PRODCD"]: p["PRICE"]
        for p in oils[0].get("OIL_PRICE", [])
        if p["PRODCD"] in ("B027", "B034", "D047")
    }


PRODCD_NAME = {"B027": "휘발유", "B034": "경유", "D047": "LPG"}


def main():
    if not API_KEY:
        print("[ESCALATE] OPINET_API_KEY가 .env에 없습니다.")
        sys.exit(1)

    with open(ROOT / "output" / "gas_stations.json", encoding="utf-8") as f:
        stations = json.load(f)

    # opinet_cache.json(searchByName으로 구축한 UNI_ID 맵) 로드
    cache_file = ROOT / "output" / "opinet_cache.json"
    cached_ids: dict[str, str] = {}  # station_name → UNI_ID
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            cache_data = json.load(f)
        for name, v in cache_data.items():
            if v.get("uni_id"):
                cached_ids[name] = v["uni_id"]
        print(f"캐시 로드: {len(cached_ids)}건의 UNI_ID")

    # ── 1단계: aroundAll ──────────────────────────────────
    print("\n[1단계] aroundAll 수집...")
    collected: dict[str, dict] = {}  # UNI_ID → {OS_NM, prices}
    calls = 0

    for gu, (x, y) in GU_CENTERS.items():
        for prodcd, fuel_name in FUELS:
            try:
                oils = fetch_around(x, y, prodcd)
                calls += 1
                for o in oils:
                    uid = o["UNI_ID"]
                    if uid not in collected:
                        collected[uid] = {"OS_NM": o["OS_NM"], "prices": {}}
                    if o.get("PRICE"):
                        collected[uid]["prices"][fuel_name] = o["PRICE"]
            except Exception as e:
                print(f"  [{gu} {fuel_name}] 오류: {e}")
            time.sleep(0.15)

    print(f"  → {calls}회 호출, {len(collected)}개 주유소 수집")

    # 이름 인덱스
    opinet_idx = {normalize(v["OS_NM"]): uid for uid, v in collected.items()}

    def match_by_name(name: str) -> str | None:
        key = normalize(name)
        uid = opinet_idx.get(key)
        if not uid:
            for okey, ouid in opinet_idx.items():
                if key and okey and (key in okey or okey in key):
                    uid = ouid
                    break
        return uid

    # ── 2단계: detailById 보완 ────────────────────────────
    # 1단계에서 매칭 안 됐지만 캐시에 UNI_ID 있는 것
    need_detail = []
    for st in stations:
        name = st["name"]
        if not match_by_name(name) and name in cached_ids:
            need_detail.append((name, cached_ids[name]))

    if need_detail:
        print(f"\n[2단계] detailById 보완 ({len(need_detail)}건)...")
        for name, uid in need_detail:
            try:
                raw = fetch_detail(uid)
                prices = {PRODCD_NAME[k]: v for k, v in raw.items()}
                collected[uid] = {"OS_NM": name, "prices": prices}
                opinet_idx[normalize(name)] = uid
                calls += 1
            except Exception as e:
                print(f"  {name}: 오류 {e}")
            time.sleep(0.15)
        print(f"  → 보완 완료")

    # ── 최종 매칭 ─────────────────────────────────────────
    results = {}
    matched = 0
    for st in stations:
        name = st["name"]
        uid = match_by_name(name)
        if uid and collected.get(uid, {}).get("prices"):
            results[name] = {
                "uni_id": uid,
                "matched_name": collected[uid]["OS_NM"],
                "prices": collected[uid]["prices"],
            }
            matched += 1
        else:
            results[name] = {
                "uni_id": uid or cached_ids.get(name),
                "matched_name": None,
                "prices": {},
            }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {matched}/{len(stations)}건 매칭")
    print(f"API 사용량: {calls}회 / 일 1500회 한도")


if __name__ == "__main__":
    main()
