"""Run the Lean reconstruction CLI with an optional external process deadline.

An external timeout may occur before input validation or before a result is
serialized. It is always incomplete, never a completed empty inverse set.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_command(command, timeout=None):
    try:
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return dict(status="incomplete", complete=False, reason="process-timeout", input_valid=None,
                    no_candidate_in_scope=False, examined=None, scope_size=None, candidates=[],
                    limitation="The killed process supplied no complete result; found candidates and validation status are unknown."), 3
    except OSError as error:
        return dict(status="error", complete=False, reason="process-error", no_candidate_in_scope=False, error=str(error)), 2
    if process.returncode in {0, 1, 3}:
        try:
            report = json.loads(process.stdout)
            if (report["status"] != {0: "complete", 1: "invalid", 3: "incomplete"}[process.returncode]
                    or report["complete"] is not (process.returncode == 0)
                    or report["input_valid"] is not (process.returncode != 1)):
                raise ValueError("Inconsistent process status")
            if process.returncode == 0:
                if (not isinstance(report["candidates"], list)
                        or type(report["history_count"]) is not int
                        or report["history_count"] != len(report["candidates"])
                        or report["no_candidate_in_scope"] is not (not report["candidates"])
                        or type(report["examined"]) is not int or report["examined"] < 0
                        or type(report["scope_size"]) is not int
                        or report["examined"] != report["scope_size"]):
                    raise ValueError("Inconsistent complete result")
            elif report["no_candidate_in_scope"] is not False:
                raise ValueError("Only a complete result can establish an empty inverse set")
            return report, process.returncode
        except (ValueError, KeyError, TypeError):
            pass
    return dict(status="error", complete=False, reason="process-error", no_candidate_in_scope=False,
                returncode=process.returncode, error=process.stderr.strip()), 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--binary", type=Path, default=ROOT / "lean/.lake/build/bin/reconstruct")
    parser.add_argument("--timeout", type=float, help="Maximum process seconds; distinct from the cooperative Lean deadline")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error("--timeout must be finite and positive")
    result, code = run_command([str(args.binary.resolve()), "--file", str(args.input.resolve())], args.timeout)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.write_text(text)
    print(text, end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
