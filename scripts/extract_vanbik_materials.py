"""Expanded VanBik numbered-entry extraction, derived from the M6 extractor.

Keep the frozen milestone extractor unchanged. Include the final entry page,
indented headers and the source's PPC/PSPC reconstruction levels. Sections 4.8
and 4.9 repeat earlier entries; they are not extra independent cognate sets.
"""
from bisect import bisect_right
import hashlib
import json
import re
from pypdf import PdfReader
from build_kuki_corpus import LANGUAGES, PDF, ROOT


def extract():
    lock = next(x for x in json.loads((ROOT / "bibliography/downloads.json").read_text()) if x["id"] == "vanbik2009")
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == lock["sha256"], "VanBik PDF changed"
    reader = PdfReader(PDF)
    pages = [reader.pages[i].extract_text() for i in range(92, 341)]
    offsets = []; offset = 0
    for t in pages:
        offsets.append(offset); offset += len(t) + 1
    text = "\n".join(pages)
    text = re.split(r"(?m)^4\.8\s+Allofamic Variation", text, maxsplit=1)[0]
    sections = list(re.finditer(r"(?m)^(4\.[\d .]+)\s+\*([^\n*-]+)\s*-", text))
    starts = [m.start() for m in sections]
    boundaries = [m.start() for m in re.finditer(r"(?m)^[ \t]*4\.\d+(?:\.\d+)*[ \t]+", text)]
    heads = list(re.finditer(r"(?m)^[ \t]*\[(\d+)\]\s+([^\n]+)", text))
    entries = []; omissions = []
    language = "|".join(re.escape(x).replace(r"\ ", r"\s+") for x in LANGUAGES)
    for i, h in enumerate(heads):
        end = heads[i+1].start() if i+1 < len(heads) else len(text)
        later = [s for s in boundaries if h.start() < s < end]
        if later: end = min(later)
        raw = text[h.start():end]
        header = re.match(r"(.+?)\s+(PKC|PCC|PNC|PMC|PPC|PSPC|PM)\s+(\*.+)", h[2])
        if not header:
            omissions.append(dict(entry_id=h[1], pdf_page=93+bisect_right(offsets,h.start())-1, reason="header-not-parsed"))
            continue
        body = text[h.end():end]
        # Slash-delimited discussions and unnumbered cross-references are not
        # additional reflex lists. Their locations and flags remain recorded.
        cut = re.search(r"\n\s*/|\n\s*[A-Z][A-Z /()0-9-]+\s+(?:PKC|PNC|PCC|PMC) ", body)
        reflex_body = body[:cut.start()] if cut else body
        records = []
        labels = list(re.finditer(r"("+language+r")\s+", reflex_body))
        continuation = reflex_body[:labels[0].start()].strip() if labels else ""
        proto = header[3].strip()
        if continuation.startswith("*"):
            proto += "\n" + continuation
        for j, m in enumerate(labels):
            alias = " ".join(m[1].split())
            chunk = reflex_body[m.end():labels[j+1].start() if j+1<len(labels) else len(reflex_body)]
            if "‘" not in chunk:
                omissions.append(dict(entry_id=h[1], language=alias, reason="no-opening-gloss-quote",
                    source_span=chunk.strip(), pdf_page=93+bisect_right(offsets,h.end()+m.start())-1)); continue
            form, remainder = chunk.split("‘",1)
            quote_closed = "’" in remainder
            gloss = remainder.split("’",1)[0] if quote_closed else remainder.rstrip(" ;.\n")
            lang_id, name, branch, subgroup = LANGUAGES[alias]
            # A missing closing quote must not absorb the next doculect.
            if re.search(r"(?:"+language+r")\s", form):
                omissions.append(dict(entry_id=h[1], language=alias, reason="overlapping-record-span")); continue
            page = 93 + bisect_right(offsets, h.end()+m.start()) - 1
            records.append(dict(id=f"vb-{h[1]}-{lang_id}-{j+1}", doculect_id="vb-"+lang_id,
                source_alias=alias, source_form=form.strip(), source_gloss=" ".join(gloss.split()),
                source_locator=dict(source_id="vanbik2009", pdf_page=page, printed_page=page-28, entry=h[1]),
                representation="source-transcription", attestation="recorded-form",
                branch=branch, subgroup=subgroup,
                extraction_issues=[] if quote_closed else ["source-gloss-closing-quote-absent"],
                transcription_review="pending-specialist-review"))
        section = sections[bisect_right(starts,h.start())-1]
        page = 93 + bisect_right(offsets,h.start()) - 1
        entries.append(dict(id=h[1], label=" ".join(header[1].split()), source_level=header[2],
            source_reconstruction=proto, initial_section=section[2].strip(),
            source_locator=dict(source_id="vanbik2009", pdf_page=page, printed_page=page-28, entry=h[1]),
            extraction=dict(entry_text_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                has_discussion=cut is not None, see_entries=re.findall(r"[Ss]ee\s+\[(\d+)\]", raw),
                additional_header=continuation if continuation and not continuation.startswith("*") else None,
                loan_mentioned=bool(re.search(r"borrow|loan",raw,re.I)),
                allofamy_markers=[c for c in ["⪤","↭","↮"] if c in raw],
                policy="Expanded chapter-4 extraction: indented entry headers and PPC/PSPC levels included; pypdf default extraction, surrounding whitespace removed from form spans; no glyph correction. Consult the numbered entry and its discussion in the PDF."),
            records=records))
    return lock, entries, omissions
