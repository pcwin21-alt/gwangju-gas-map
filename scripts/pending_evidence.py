"""Attach dated physical-identity evidence; never promote payment or routing."""


def annotate_pending(rows, evidence):
    result = []
    for original in rows:
        row = dict(original)
        if row.get('status') == 'needs_review' and row.get('show_pending'):
            matches = [e for e in evidence if all(
                row.get(k) == e.get(k) for k in ('candidate_id', 'name', 'market', 'region'))]
            if len(matches) == 1:
                item = matches[0]
                if (item.get('scope') == 'historical_physical_identity_only'
                        and item.get('sources') and item.get('address')
                        and item.get('historical_source_date') and item.get('commercial_source_date')):
                    row['identity_evidence'] = item
                    row['reason'] = (
                        f"주소 대조: {item['address']} "
                        f"(과거 가맹 명부 {item['historical_source_date']}, "
                        f"상권자료 {item['commercial_source_date']}). 현재 온누리 가맹 재확인 필요")
        result.append(row)
    return result
