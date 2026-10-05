"""Generate the closed v1 interchange schema. Semantic checks also run in Lean."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = {"type": "string"}
TEXT = {"type": "string", "minLength": 1}
ID = {"type": "string", "pattern": "^[A-Za-z0-9_.:-]+$"}


def enum(*values): return {"type": "string", "enum": list(values)}
def ref(name): return {"$ref": "#/$defs/" + name}
def opt(value): return {"anyOf": [value, {"type": "null"}]}
def arr(value, minimum=0): return {"type": "array", "items": value, "minItems": minimum}
def obj(**fields):
    return {"type": "object", "additionalProperties": False,
            "required": list(fields), "properties": fields}


def schema():
    defs = {
        "source": obj(id=ID, title=TEXT, url=TEXT, version=TEXT, license=TEXT,
                      kind=enum("publication", "dataset", "synthetic"),
                      sha256=opt({"type": "string", "pattern": "^[0-9a-f]{64}$"})),
        "citation": obj(source_id=ID, locator=TEXT),
        "date_range": obj(earliest={"type": "integer"}, latest={"type": "integer"},
                          convention={"const": "astronomical-year"}),
        "doculect": obj(id=ID, name=TEXT, family=TEXT, stage=TEXT,
                        kind=enum("attested", "proto"), date_range=opt(ref("date_range"))),
        "meaning": obj(id=ID, label=TEXT),
        "analysis": obj(id=ID, description=TEXT, source_ids=arr(ID, 1), proto_node_id=ID),
        "method": obj(id=ID, version=TEXT, description=TEXT),
        "step": obj(method_id=ID, method_version=TEXT, input=S, output=S, reason=TEXT),
        "cell": {"oneOf": [obj(kind=enum("segment", "boundary", "unknown"), value=TEXT),
                            obj(kind=enum("missing", "gap"), value={"type": "null"})]},
        "choice_group": obj(id=ID, options={**arr(ID, 2), "uniqueItems": True}, description=TEXT),
        "binding": obj(group_id=ID, option_id=ID),
        "reading": obj(id=ID, original=S, normalized=S, cells=arr(ref("cell"), 1),
                       normalization=arr(ref("step"), 1), choices=arr(ref("binding"))),
        "raw_column": obj(name=TEXT, value=S),
        "import_origin": obj(dataset_id=ID, table=TEXT, row_id=TEXT, id_column=TEXT,
                             original_column=TEXT, raw_columns=arr(ref("raw_column"), 1)),
        "record": obj(id=ID, doculect_id=ID, meaning_ids={**arr(ID, 1), "uniqueItems": True},
                      representation=enum("orthographic", "phonetic", "phonemic", "mixed"),
                      attestation=enum("attested", "reconstructed"),
                      evidence_state=enum("present", "missing", "unknown"),
                      analysis_id=opt(ID), proto_node_id=opt(ID), citations=arr(ref("citation"), 1),
                      readings=arr(ref("reading"), 1), uncertain={"type": "boolean"},
                      uncertainty_note=opt(TEXT), imported_from=opt(ref("import_origin"))),
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://zengrf.github.io/lean-historical-linguistics/schema/v1/dossier.schema.json",
        "title": "Historical linguistic evidence dossier v1.0.0",
        "$comment": "The $id is an identifier, not a claim that GitHub Pages is deployed. Cross-reference and normalization-chain checks are implemented in Lean.",
        **obj(schema_version={"const": "1.0.0"}, id=ID, description=TEXT,
              sources=arr(ref("source"), 1), doculects=arr(ref("doculect"), 1),
              meanings=arr(ref("meaning"), 1), analyses=arr(ref("analysis")),
              normalization_methods=arr(ref("method"), 1), choice_groups=arr(ref("choice_group")),
              records=arr(ref("record"), 1)),
        "$defs": defs,
    }


if __name__ == "__main__":
    path = ROOT / "schema/v1/dossier.schema.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema(), ensure_ascii=False, indent=2) + "\n")
    print("Generated", path.relative_to(ROOT))
