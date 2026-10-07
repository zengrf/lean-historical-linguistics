"""Check the pinned, byte-for-byte Kiwari assets and local font dependencies."""

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "web/vendor/kiwari"


def verify():
    manifest = json.loads((THEME / "upstream.json").read_text())
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["commit"])
    actual = {str(p.relative_to(THEME)) for p in THEME.rglob("*") if p.is_file()}
    assert actual == set(manifest["files"]) | {"upstream.json"}
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((THEME / name).read_bytes()).hexdigest() == expected, name
    for relative in re.findall(
        r"url\(([^)]+)\)", (THEME / "lib/fonts.css").read_text()
    ):
        assert (THEME / "lib" / relative).is_file(), relative
    page = (ROOT / "web/index.html").read_text()
    for name in ["slides.css", "materials.css", "lib/fonts.css"]:
        assert f'href="/vendor/kiwari/{name}"' in page
    assert (THEME / "LICENSE").is_file()
    return dict(
        repository=manifest["repository"],
        commit=manifest["commit"],
        files=len(manifest["files"]),
    )


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
