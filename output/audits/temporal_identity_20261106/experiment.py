"""Offline Jeonnam temporal identity pilot; never makes source requests or writes state."""
import collections
import datetime
import gzip
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
STATE_REF = "ad0b62dfd33626bcc174bc9c7e6ad3ab7c7c3c13"
BASE = ROOT / "output/audits/full_region_crosscheck_20261103/issuer_merchant_versions.json.gz"
FIELDS = ("title", "category", "tel", "address")


def git_bytes(path):
    return subprocess.check_output(["git", "show", f"{STATE_REF}:{path}"], cwd=ROOT)


def main():
    state_raw = git_bytes("state.json")
    state = json.loads(state_raw)
    jobs = {j["id"]: j for j in state["jobs"]}
    observations = json.loads(gzip.decompress(BASE.read_bytes()))
    baseline_count = len(observations)
    response_refs = []
    for attempt in state["attempts"]:
        if attempt.get("source") != "kbcard" or jobs.get(attempt["job_id"], {}).get("region") != "전남":
            continue
        path = f"responses/{attempt['id']}.json"
        raw = git_bytes(path)
        payload = json.loads(raw)
        for row in payload.get("rows", []):
            observations.append({**row, "checked_at": payload["checked_at"]})
        response_refs.append({"path": path, "sha256": hashlib.sha256(raw).hexdigest(),
                              "checked_at": payload.get("checked_at"), "rows": len(payload.get("rows", []))})

    grouped = collections.defaultdict(dict)
    rejected_regions = 0
    for row in observations:
        content = row["content"]
        if not content.get("address", "").startswith("전남 "):
            rejected_regions += 1
            continue
        values = tuple(content.get(field, "") for field in FIELDS)
        point = (row.get("location", {}).get("lat"), row.get("location", {}).get("lng"))
        key = (row["checked_at"], values, point)
        grouped[content["franchiseNo"]][key] = row

    changes = []
    comparable = []
    physical_path = ROOT / "output/audits/full_region_crosscheck_20261103/physical_fuel_records.json.gz"
    physical = json.loads(gzip.decompress(physical_path.read_bytes()))
    def normalized(value):
        return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())
    for bank_id, keyed in grouped.items():
        rows = list(keyed.values())
        if len({r["checked_at"] for r in rows}) < 2:
            continue
        comparable.append(bank_id)
        deltas = {field: sorted({r["content"].get(field, "") for r in rows})
                  for field in FIELDS if len({r["content"].get(field, "") for r in rows}) > 1}
        if deltas:
            names = {normalized(r["content"].get("title")) for r in rows}
            phones = {re.sub(r"\D", "", r["content"].get("tel", "")) for r in rows} - {""}
            physical_matches = [r["source_id"] for r in physical
                                if normalized(r.get("name")) in names
                                or (re.sub(r"\D", "", r.get("phone") or "") in phones)]
            changes.append({"bank_id": bank_id, "field_changes": deltas,
                            "observations": [{"checked_at": r["checked_at"],
                                              "title": r["content"].get("title"),
                                              "category": r["content"].get("category"),
                                              "address": r["content"].get("address"),
                                              "location": r.get("location")} for r in sorted(rows, key=lambda x: x["checked_at"])],
                            "independent_fuel_exact_name_or_phone_source_rows": physical_matches,
                            "disposition": "No independent fuel name/phone link; displayed title difference is not a verified legal rename or vehicle-fuel identity." if not physical_matches
                                           else "Review-only independent leads; no automatic membership transfer."})

    samples = []
    for bank_id, role in [
        ("000000094538059", "unresolved_independent_premise:baekdong"),
        ("000000069335783", "unresolved_lpg_operator_link:manjae"),
        ("000000100747978", "existing_station_alternative_wash_terminal:not_new_station"),
        ("000000004645863", "previously_linked_control:hyundai"),
        ("000000055922363", "previously_linked_control:samhak"),
    ]:
        rows = list(grouped.get(bank_id, {}).values())
        dates = sorted({r["checked_at"] for r in rows})
        samples.append({"bank_id": bank_id, "role": role, "observations": len(rows),
                        "distinct_observation_times": len(dates), "observed_dates": dates,
                        "names": sorted({r["content"]["title"] for r in rows}),
                        "categories": sorted({r["content"]["category"] for r in rows}),
                        "variant_counts": {f: len({r["content"].get(f, "") for r in rows}) for f in FIELDS},
                        "result": "no_historical_alias_in_cached_window" if len(dates) > 1
                                  else "insufficient_repeated_observations",
                        "fresh_membership_check": False})

    dates = sorted({row["checked_at"] for rows in grouped.values() for row in rows.values()})
    report = {
        "reviewed_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds"),
        "region": "전남", "method": "stable_issuer_id_temporal_metadata_comparison",
        "hypothesis": "Historical names/categories on the exact same issuer terminal ID may expose a missed fuel identity.",
        "selection": {
            "priority_permit_change_history": "Public blank form located previously; no actual dated Jeonnam register obtained. Official guide retrieval timed out today. Not executed as a record linkage.",
            "chosen_cached_issuer_versions": "Previously saved versions existed, but prior report used latest-by-ID and static matching. Compare exact ID across dates, not a broader keyword or location retry.",
            "corporate_branch_history": "Public recruitment descriptions have historical corporate splits, but no primary current branch/operator continuity; not accepted as membership or permit evidence.",
        },
        "sources": {"baseline_path": str(BASE.relative_to(ROOT)),
                    "baseline_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
                    "physical_path": str(physical_path.relative_to(ROOT)),
                    "physical_sha256": hashlib.sha256(physical_path.read_bytes()).hexdigest(),
                    "state_ref": STATE_REF, "state_sha256": hashlib.sha256(state_raw).hexdigest(),
                    "managed_cached_responses": response_refs},
        "counts": {"baseline_observation_rows": baseline_count,
                   "managed_response_files_read": len(response_refs),
                   "managed_cached_rows_read": sum(r["rows"] for r in response_refs),
                   "observation_rows_before_deduplication": len(observations),
                   "observation_rows_after_deduplication": sum(len(v) for v in grouped.values()),
                   "excluded_non_jeonnam_rows": rejected_regions, "distinct_issuer_ids": len(grouped),
                   "ids_with_multiple_observation_times": len(comparable),
                   "ids_with_changed_identity_fields": len(changes), "pilot_samples": len(samples),
                   "changed_ids_crosschecked_against_physical_inventory": len(changes),
                   "physical_source_rows_compared_per_changed_id": len(physical),
                   "changed_ids_with_independent_fuel_name_or_phone_lead": sum(bool(c["independent_fuel_exact_name_or_phone_source_rows"]) for c in changes),
                   "live_merchant_source_requests": 0, "new_membership_confirmations": 0,
                   "existing_stations_freshly_reconfirmed": 0, "map_additions": 0},
        "observation_window": {"first": dates[0], "last": dates[-1]},
        "identity_changes": changes, "samples": samples,
        "success_criterion": "At least one changed identity field on an exact repeated ID plus independently dated same-business fuel evidence; otherwise do not add or resolve.",
        "limitations": [
            "Observation timestamps are retrieval times, not legal effective/change dates.",
            "An issuer ID identifies a merchant/terminal observation, not necessarily a unique physical station or continuing operator.",
            "No changes in this short window cannot exclude older renames, closed businesses, missing merchants, or future changes.",
            "Same-name/nearby/phone-only relationships never transfer membership between operators or businesses.",
            "This is archived-data crosschecking, not a new live collection or current census; original paper/QR/issuer dates remain unchanged.",
        ],
        "result": "no_independently_linked_new_fuel_identity_in_cached_window" if not any(c["independent_fuel_exact_name_or_phone_source_rows"] for c in changes)
                  else "changed_fields_require_manual_independent_review",
        "state_changed": False, "queue_changed": False, "map_changed": False, "deployment": "not_required_no_service_or_map_change",
        "next_candidate": "Locate a dated public municipal operator/brand transfer notice for one unresolved Jeonnam fuel premise. Require stable public facility key and effective date before testing any old-name link; stop if only blank forms or current snapshots exist.",
    }
    (OUT / "findings.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": report["counts"], "window": report["observation_window"],
                      "sample_results": [{"name": x["names"], "times": x["distinct_observation_times"], "result": x["result"]} for x in samples],
                      "result": report["result"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
