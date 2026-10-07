"""Local UI operations for checked, reflex-only protolexicon search."""

from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
import secrets
import tempfile
import threading

from build_pie_corpus import ROOT
from explore_reconstructions import strict_read
from lexicon import reconstruct, native, constrain, page, read_tsv, to_tsv, save, load

EXAMPLES = {
    "merger": "Two mergers · whole-lexicon example",
    "kuki": "Kuki-Chin · ARM reflexes",
    "pie": "Indo-European · LEG reflexes (fitted baseline)",
    "deletion": "Deletion and unknown segments",
    "contextual": "Context-sensitive sound change",
    "conflict": "Incompatible global models",
    "scaling": "1,000 cognate sets · scale demonstration",
}
CACHE = OrderedDict()
LOCK = threading.Lock()


def example(key):
    if key not in EXAMPLES:
        raise ValueError("Unknown reflex-table example")
    spec = strict_read(ROOT / "data/lexicon" / (key + ".json"))
    return dict(request=spec, tsv=to_tsv(spec), examples=EXAMPLES)


def execute(operation, body):
    if not isinstance(body, dict):
        raise ValueError("Expected a JSON object")
    if operation == "table":
        if set(body) != {"request", "tsv", "source_ref"}:
            raise ValueError("Provide request, tsv and source_ref")
        spec = deepcopy(body["request"])
        spec["entries"] = read_tsv(body["tsv"], spec["languages"], body["source_ref"])
        native("--validate", spec)
        return dict(request=spec, tsv=to_tsv(spec))
    if operation == "run":
        if set(body) != {
            "request",
            "analyses",
            "languages",
            "node_budget",
            "time_limit",
        }:
            raise ValueError(
                "Provide request, analyses, languages, node_budget and time_limit"
            )
        # Validate before Python indexing or changing the selected constraints.
        native("--validate", body["request"])
        spec = constrain(body["request"], body["analyses"], body["languages"])
        result = reconstruct(
            spec, node_budget=body["node_budget"], time_limit=body["time_limit"]
        )
        directory = tempfile.TemporaryDirectory(prefix="m7-ui-")
        save(result, Path(directory.name))
        token = secrets.token_urlsafe(24)
        with LOCK:
            CACHE[token] = directory
            while len(CACHE) > 4:
                _, old = CACHE.popitem(last=False)
                old.cleanup()
        return dict(token=token, summary=result["summary"], request=spec)
    if operation not in {"page", "export"}:
        raise ValueError("Unknown lexicon operation")
    allowed = (
        {"token"}
        if operation == "export"
        else {"token", "analysis_id", "entry_id", "offset", "limit"}
    )
    if set(body) != allowed or not isinstance(body["token"], str):
        raise ValueError("Invalid saved-result request")
    with LOCK:
        directory = CACHE.get(body["token"])
        if directory is None:
            raise ValueError("This result has expired; run the search again")
        # Read under the cache lock so eviction cannot race a page request.
        result = dict(
            forest=strict_read(Path(directory.name) / "forest.json"),
            summary=strict_read(Path(directory.name) / "summary.json"),
        )
    if operation == "export":
        return result
    return page(
        result,
        body["analysis_id"],
        entry_id=body["entry_id"],
        offset=body["offset"],
        limit=body["limit"],
    )
