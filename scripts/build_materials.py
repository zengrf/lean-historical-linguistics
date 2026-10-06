"""Extract all parseable VanBik initial-chapter entries and audit source coverage."""
import argparse
from extract_vanbik_materials import extract
from build_pie_corpus import encoded
from materials import DEST, coverage


def generate():
    lock, entries, omissions = extract()
    assert [e["id"] for e in entries] == [str(i) for i in range(1, 1356)], "A numbered VanBik entry is missing or duplicated"
    return dict(schema_version="1.0.0", source_id="vanbik2009", source_sha256=lock["sha256"],
        scope="VanBik (2009), numbered comparative entries [1]–[1355] in chapter 4, PDF pages 93–341. All reconstruction levels are retained. Sections 4.8–4.9 relist earlier entries and are not counted as extra sets. Chapters 5–6 (rhymes and tones) are not structurally transcribed.",
        entries=entries, omissions=omissions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = DEST / "vanbik-initials.json"
    data = encoded(generate())
    if args.check:
        assert path.read_bytes() == data, "Stale VanBik extraction"
    else:
        path.write_bytes(data)
    path = DEST / "coverage.json"
    data = encoded(coverage())
    if args.check:
        assert path.read_bytes() == data, "Stale coverage report"
    else:
        path.write_bytes(data)
    print("Complete source snapshots and VanBik extraction checked.")


if __name__ == "__main__":
    main()
