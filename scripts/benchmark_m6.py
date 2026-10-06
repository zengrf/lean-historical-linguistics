"""Measure 1,000 certificates from the largest M6 lexical rule package."""
import argparse
from copy import deepcopy
import hashlib
import json
import platform
import resource
import subprocess
import tempfile
import time
from pathlib import Path

from build_pie_corpus import ROOT, encoded, digest
from build_kuki_corpus import DEST


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",type=Path,default=ROOT/"reports/sino-tibetan-benchmark-local.json");a=p.parse_args()
    data=json.loads((DEST/"lexical-input.json").read_text());by={p["id"]:p for p in data["batch"]["packages"]}
    template=max(data["batch"]["forward"],key=lambda j:(len(by[j["package_id"]]["laws"]),len(j["input"]),j["id"]))
    pack=by[template["package_id"]];binding=next(s for s in data["package_scopes"] if s["package_id"]==pack["id"])
    jobs=[]
    for i in range(1000):
        j=deepcopy(template);j["id"]="benchmark-"+str(i);jobs.append(j)
    request=dict(schema_version="1.0.0",nodes=[binding["ancestor"],binding["descendant"]],package_scopes=[binding],query_scopes=[],
        batch=dict(schema_version="1.0.0",id="m6-1000-certificates",packages=[pack],forward=jobs,inverse=[]))
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"request.json";path.write_bytes(encoded(request));start=time.perf_counter()
        result=subprocess.run([str(ROOT/"lean/.lake/build/bin/sino_tibetan_check"),"--batch",str(path)],capture_output=True,text=True,timeout=65)
        elapsed=time.perf_counter()-start
    assert result.returncode==0,(result.stdout[:200],result.stderr)
    out=json.loads(result.stdout);assert out["scope_valid"] and len(out["result"]["forward"])==1000
    assert all(j["certificate_accepted"] for j in out["result"]["forward"])
    peak=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    if platform.system()!="Darwin":peak*=1024
    names=["lean/Historical/Batch.lean","lean/Historical/SourceScope.lean","lean/SinoTibetanCheck.lean","scripts/benchmark_m6.py","data/kuki-chin/lexical-input.json"]
    report=dict(certificates=1000,word_length=len(template["input"]),rules_per_certificate=len(pack["laws"]),elapsed_seconds=elapsed,peak_resident_bytes=peak,
        seconds_limit=60,memory_limit_bytes=2*1024**3,passed=elapsed<60 and peak<2*1024**3,
        platform=dict(system=platform.system(),release=platform.release(),machine=platform.machine()),request_sha256=digest(request),
        scope="Fresh Lean process including strict decoding, scope and package validation, trace generation, certificate checking and serialization; timing is not a linguistic accuracy measure.",
        input_hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names})
    a.output.write_bytes(encoded(report));print(json.dumps(report))
    if not report["passed"]:raise SystemExit(1)


if __name__=="__main__":main()
