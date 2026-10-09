"""Publish only public assets; never copy repository tooling or raw responses."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'
SITE.mkdir(exist_ok=True)
shutil.copyfile(ROOT / 'output' / 'map.html', SITE / 'index.html')
for name in ('favicon.svg', 'thumbnail.png'):
    shutil.copyfile(ROOT / name, SITE / name)
shutil.copytree(ROOT / 'assets', SITE / 'assets', dirs_exist_ok=True)
