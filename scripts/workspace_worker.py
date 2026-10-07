"""One isolated, cancellable native reconstruction job."""

import hashlib
import json
from pathlib import Path
import sys
import os
import signal
import threading
import time

from build_pie_corpus import encoded
from explore_reconstructions import strict_read
from lexicon import BIN, reconstruct, save
from m7_solver import IncompleteSearch
from workspace_evaluation import evaluate


def main():
    directory = Path(sys.argv[1])
    # Lean 4.34 reserves a 1 GiB stack for each runtime thread by default.
    # Bound native concurrency and stack reservations inside the worker's
    # address-space budget; these checks do not use parallel Lean tasks.
    os.environ["LEAN_NUM_THREADS"] = "1"
    os.environ["LEAN_STACK_SIZE_KB"] = "65536"
    if sys.platform.startswith("linux"):
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    payload = strict_read(directory / "input.json")
    if os.name == "posix" and os.getpgrp() == os.getpid():

        def watch_parent():
            while True:
                time.sleep(1)
                if os.getppid() != payload.get("parent_pid"):
                    os.killpg(os.getpgrp(), signal.SIGTERM)
                    return

        threading.Thread(target=watch_parent, daemon=True).start()
    try:
        if hashlib.sha256(BIN.read_bytes()).hexdigest() != payload["engine_sha256"]:
            raise ValueError(
                "The Lean executable changed after this analysis was queued; submit it again"
            )
        result = reconstruct(payload["request"], **payload["limits"])
        evaluation = encoded(
            evaluate(
                payload["request"],
                payload.get("evaluation_annotations", {}),
                result["summary"],
            )
        )
        (directory / "evaluation.json").write_bytes(evaluation)
        result["summary"]["evaluation_sha256"] = hashlib.sha256(evaluation).hexdigest()
        save(result, directory)
        outcome = dict(status="complete", summary=result["summary"], error=None)
    except IncompleteSearch as error:
        outcome = dict(status="incomplete", summary=None, error=str(error))
    except Exception as error:
        outcome = dict(status="failed", summary=None, error=str(error)[:2000])
    temporary = directory / "outcome.tmp"
    temporary.write_bytes(encoded(outcome))
    temporary.replace(directory / "outcome.json")


if __name__ == "__main__":
    main()
