"""Extract all parseable VanBik initial-chapter entries and audit source coverage."""
import argparse
from build_kuki_corpus import extract
from build_pie_corpus import encoded
from materials import DEST, coverage


def generate():
    lock, entries, omissions = extract()
    return dict(schema_version="1.0.0", source_id="vanbik2009", source_sha256=lock["sha256"],
        scope="VanBik (2009), chapter 4, PDF pages 93–340: every entry parsed by the retained extractor, including PKC and lower reconstruction levels. This is not a transcription of chapters 5–6 (rhymes and tones).",
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
