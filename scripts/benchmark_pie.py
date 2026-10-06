"""Measure 1,000 bounded source-fragment certificates in one fresh Lean process."""
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

from build_pie_corpus import ROOT,DEST,encoded,digest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",type=Path,default=ROOT/"reports/pie-benchmark-local.json");a=p.parse_args()
    d=json.loads((DEST/"diagnostic-input.json").read_text());package=d["packages"][0];template=d["forward"][0]
    jobs=[]
    for i in range(1000):
        j=deepcopy(template);j["id"]="benchmark-"+str(i);jobs.append(j)
    req=dict(schema_version="1.0.0",id="pie-1000-certificates",packages=[package],forward=jobs,inverse=[])
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/"request.json";path.write_bytes(encoded(req))
        started=time.perf_counter()
        result=subprocess.run([str(ROOT/"lean/.lake/build/bin/pie_check"),"--batch",str(path)],capture_output=True,text=True,timeout=65)
        elapsed=time.perf_counter()-started
    assert result.returncode==0,result.stderr
    out=json.loads(result.stdout)
    assert len(out["forward"])==1000 and all(r["certificate_accepted"] and r["exact"] for r in out["forward"])
    peak=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    if platform.system()!="Darwin":peak*=1024
    report=dict(certificates=1000,word_length=3,rules_per_certificate=len(package["laws"]),elapsed_seconds=elapsed,
                peak_resident_bytes=peak,seconds_limit=60,memory_limit_bytes=2*1024**3,
                passed=elapsed<60 and peak<2*1024**3,platform=dict(system=platform.system(),release=platform.release(),machine=platform.machine()),
                scope="One fresh Lean process, including JSON parsing, package validation, trace generation, checking and serialization. This is a bounded engineering control, not a historical-accuracy metric.",
                request_sha256=digest(req),input_hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
                    ["lean/PieCheck.lean","lean/Historical/Batch.lean","lean/Historical/CaseStudy.lean","scripts/benchmark_pie.py","data/pie/diagnostic-input.json"]})
    a.output.write_bytes(encoded(report));print(json.dumps(report,sort_keys=True))
    if not report["passed"]:raise SystemExit(1)


if __name__=="__main__":main()
