"""Publish only public assets; never copy repository tooling or raw responses."""
import shutil
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'
SITE.mkdir(exist_ok=True)
html = (ROOT / 'output' / 'map.html').read_text(encoding='utf-8')
def version_asset(match):
    path = match.group(1)
    digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:12]
    return path + '?v=' + digest
html = re.sub(r'(assets/[\w.-]+\.(?:js|css))(?=")', version_asset, html)
(SITE / 'index.html').write_text(html, encoding='utf-8')
for name in ('favicon.svg', 'thumbnail.png'):
    shutil.copyfile(ROOT / name, SITE / name)
shutil.copytree(ROOT / 'assets', SITE / 'assets', dirs_exist_ok=True)
