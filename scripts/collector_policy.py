"""Legacy network entry points must not bypass the persisted collector gate."""
import json
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / 'config/collector-policy.json'


def require_managed_collection(source):
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    setting = policy['sources'][source]
    raise PermissionError('Use the incremental collector; source=%s status=%s. No direct network request sent.' %
                          (source, setting['status']))
