"""Detect stale native builds before a workspace analysis is submitted."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "lean/.lake/build/bin/lexicon_check"

STAMP = ROOT / "lean/.lake/build/workspace-build.json"


def sources():
    files = [p for p in (ROOT / "lean").rglob("*.lean") if ".lake" not in p.parts]
    files += [ROOT / "lean/lakefile.toml"]
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(files)
    }


def record_build(toolchain):
    stamp = dict(
        toolchain=toolchain,
        sources=sources(),
        binary_sha256=hashlib.sha256(BIN.read_bytes()).hexdigest(),
    )
    STAMP.write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n")
    return stamp


def identity():
    if not BIN.is_file() or not STAMP.is_file():
        raise ValueError(
            "Build the workspace engine with ./workbench setup before running an analysis"
        )
    stamp = json.loads(STAMP.read_text())
    if (
        stamp["sources"] != sources()
        or stamp["binary_sha256"] != hashlib.sha256(BIN.read_bytes()).hexdigest()
    ):
        raise ValueError(
            "The Lean source or executable changed after the recorded build. Run ./workbench setup to rebuild it."
        )
    return stamp


def readiness():
    try:
        stamp = identity()
        return dict(
            ready=True,
            toolchain=stamp["toolchain"],
            binary_sha256=stamp["binary_sha256"],
        )
    except (OSError, ValueError, KeyError) as error:
        return dict(ready=False, error=str(error))
