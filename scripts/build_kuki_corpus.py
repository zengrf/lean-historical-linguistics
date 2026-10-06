"""Extract and freeze a stratified Kuki-Chin sample from VanBik (2009).

The PDF is the input, not a corrected wordlist. Retain extracted strings and
source locators; report parsing limitations separately from linguistic claims.
Selection and family grouping do not consult predictions.
"""
import argparse
from bisect import bisect_right
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader
from build_pie_corpus import ROOT, encoded, digest

DEST = ROOT / "data/kuki-chin"
PDF = ROOT / "library/open/vanbik2009.pdf"
SEED = "m6-vanbik-lexical-families-v1"
LANGUAGES = {
    "Mara": ("mara", "Mara", "Maraic", "Maraic"),
    "H. Lai": ("hakha-lai", "Hakha Lai", "Central", "Central"),
    "F. Lai": ("falam-lai", "Falam Lai (Zahao in VanBik's abbreviations)", "Central", "Central"),
    "Mizo": ("mizo", "Mizo (Lushai)", "Central", "Central"),
    "Tedim": ("tedim", "Tedim", "Peripheral", "Northern"),
    "Thado Kuki": ("thado-kuki", "Thado Kuki", "Peripheral", "Northern"),
    "Paite": ("paite", "Paite", "Peripheral", "Northern"),
    "Sizang": ("sizang", "Sizang", "Peripheral", "Northern"),
    "M. Cho": ("mindat-cho", "Mindat Cho", "Peripheral", "Southern-Plains"),
    "Daai": ("daai", "Daai", "Peripheral", "Southern-Plains"),
    "Asho": ("asho", "Asho as labelled by VanBik; dialect unspecified here", "Peripheral", "Southern-Plains"),
    "Khumi": ("khumi", "Khumi as labelled by VanBik", "Peripheral", "Southern-Plains"),
}


def extract():
    lock = next(x for x in json.loads((ROOT / "bibliography/downloads.json").read_text()) if x["id"] == "vanbik2009")
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == lock["sha256"], "VanBik PDF changed"
    reader = PdfReader(PDF)
    pages = [reader.pages[i].extract_text() for i in range(92, 340)]
    offsets = []; offset = 0
    for t in pages:
        offsets.append(offset); offset += len(t) + 1
    text = "\n".join(pages)
    sections = list(re.finditer(r"(?m)^(4\.[\d .]+)\s+\*([^\n*-]+)\s*-", text))
    starts = [m.start() for m in sections]
    heads = list(re.finditer(r"(?m)^\[(\d+)\]\s+([^\n]+)", text))
    entries = []; omissions = []
    language = "|".join(re.escape(x).replace(r"\ ", r"\s+") for x in LANGUAGES)
    for i, h in enumerate(heads):
        end = heads[i+1].start() if i+1 < len(heads) else len(text)
        later = [s for s in starts if h.start() < s < end]
        if later: end = min(later)
        raw = text[h.start():end]
        header = re.match(r"(.+?)\s+(PKC|PCC|PNC|PMC|PM)\s+(\*.+)", h[2])
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
                omissions.append(dict(entry_id=h[1], language=alias, reason="no-opening-gloss-quote")); continue
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
                policy="pypdf default extraction, surrounding whitespace removed from form spans; no glyph correction. Consult the numbered entry and its discussion in the PDF."),
            records=records))
    return lock, entries, omissions


def keys(value):
    """Conservative split grouping, not a phonological normalization."""
    value = "".join(c for c in unicodedata.normalize("NFD",value.lower()) if not unicodedata.combining(c))
    value = re.sub(r"-(?:iii|ii|i|inv)\b", "", value)
    return {re.sub(r"[^a-zɓɗŋʔθ]", "", x) for x in re.split(r"[,⪤↭↮/;\s-]+",value)} - {""}


def group_families(entries):
    parent = {s["id"]:s["id"] for s in entries}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        if a in parent and b in parent:
            a,b=find(a),find(b)
            if a!=b:
                lo,hi=sorted([a,b],key=int);parent[hi]=lo
    roots={};surfaces={}
    for s in entries:
        for target in s["extraction"]["see_entries"]:union(s["id"],target)
        for k in keys(s["source_reconstruction"]):
            if len(k)<2:continue
            # Even stems and compound components that may be homonyms stay
            # together. A shared spelling is not a new cognacy judgment.
            if k in roots:union(s["id"],roots[k])
            roots[k]=s["id"]
        for r in s["records"]:
            k=(r["doculect_id"],unicodedata.normalize("NFC"," ".join(r["source_form"].split())))
            if k in surfaces:union(s["id"],surfaces[k])
            surfaces[k]=s["id"]
    return {s["id"]:"vb-family-"+find(s["id"]) for s in entries}


def make_evidence(corpus):
    records=[]
    for s in corpus["sets"]:
        for r in s["records"]:
            form=r["source_form"]
            records.append(dict(id=r["id"],doculect_id=r["doculect_id"],meaning_ids=["meaning-"+s["id"]],
                representation="orthographic",attestation="attested",evidence_state="present",analysis_id=None,proto_node_id=None,
                citations=[dict(source_id="vanbik2009",locator=f"PDF {r['source_locator']['pdf_page']}, entry [{s['id']}]")],
                readings=[dict(id="pdf-transcription",original=form,normalized=form,cells=[dict(kind="segment",value=c) for c in form],
                    normalization=[dict(method_id="pdf-display",method_version="1",input=form,output=form,reason="Preserve the extracted display string; character cells do not identify phonemes")],choices=[])],
                uncertain=True,uncertainty_note="PDF extraction and source analysis await specialist review. Source diacritics, alternatives and stem labels remain in the display string.",
                imported_from=None))
    return dict(schema_version="1.0.0",id="kuki-chin-m6-evidence",description="Lossless character-cell projection of extracted source transcriptions; phonological analysis is separate.",
        sources=[dict(id="vanbik2009",title="Ken VanBik: Proto-Kuki-Chin",url=corpus["source"]["url"],version="2009",license=corpus["source"]["license"],kind="publication",sha256=corpus["source"]["sha256"])],
        doculects=[dict(id="vb-"+v[0],name=v[1],family="Kuki-Chin",stage="Variety and notation as recorded in VanBik (2009); no cross-source identity inferred",kind="attested",date_range=None) for v in LANGUAGES.values()],
        meanings=[dict(id="meaning-"+s["id"],label=s["label"]) for s in corpus["sets"]],analyses=[],
        normalization_methods=[dict(id="pdf-display",version="1",description="Identity of PDF display strings, including tone marks and stem labels")],choice_groups=[],records=records)


def generate():
    lock,entries,omissions=extract(); groups=group_families(entries)
    sections=list(dict.fromkeys(s["initial_section"] for s in entries))
    eligible=[s for s in entries if s["source_level"]=="PKC" and len({r['doculect_id'] for r in s["records"]})>=3 and len({r["branch"] for r in s["records"]})>=2]
    by_section={k:[s for s in eligible if s["initial_section"]==k] for k in sections}
    selected=[];rank=0
    while len(selected)<100:
        for k in sections:
            if rank<len(by_section[k]) and len(selected)<100:selected.append(by_section[k][rank])
        rank+=1
        assert rank<100,"Insufficient eligible source entries"
    core=[s["id"] for s in selected[:50]]
    selected=sorted(selected,key=lambda s:int(s["id"]))
    families=sorted({groups[s["id"]] for s in selected},key=lambda f:hashlib.sha256((SEED+":"+f).encode()).hexdigest())
    cuts=round(.6*len(families)),round(.8*len(families))
    assignment={f:"train" if i<cuts[0] else "development" if i<cuts[1] else "test" for i,f in enumerate(families)}
    selection=dict(schema_version="1.0.0",source_pdf_sha256=lock["sha256"],core_set_ids=core,set_ids=[s["id"] for s in selected],
        policy="Round-robin by printed initial-consonant subsection, retaining source entry order within each section. First 100 eligible PKC entries; first 50 in that order form the review core. At least three distinct source doculects in at least two of VanBik's Peripheral, Central and Maraic groups. No model outcome is consulted.",
        counts=dict(parsed_entries=len(entries),eligible_entries=len(eligible)),
        section_counts={k:sum(s["initial_section"]==k for s in selected) for k in sections},
        extraction_omissions=omissions,
        unselected=[dict(id=s["id"],reason="outside-stratified-sample" if s in eligible else "not-PKC-or-insufficient-parsed-coverage") for s in entries if s not in selected])
    splits=dict(schema_version="1.0.0",seed=SEED,selection_sha256=digest(selection),
        evaluation_kind="retrospective grouped baseline evaluation, not blind historical discovery",
        grouping="Transitive closure across all parsed entries in chapter 4: explicit See-entry links, equal accent-stripped reconstructed stems or compound components (including possible homonyms and across source levels), and identical source strings within a doculect. Unrecorded lexical relations require specialist review.",
        assignments=[dict(set_id=s["id"],family_id=groups[s["id"]],split=assignment[groups[s["id"]]]) for s in selected],
        family_counts={p:sum(x==p for x in assignment.values()) for p in ["train","development","test"]})
    for s in selected:
        s.update(core=s["id"] in core,family_id=groups[s["id"]],split=assignment[groups[s["id"]]],
            node_id="vanbik-2009-PKC",tone_reconstruction=None,
            tone_scope="Chapter 4 initial-consonant entry: no proto-tone supplied here. Chapter 6 tone analyses are a separate source claim.",
            absent_doculects=["vb-"+v[0] for v in LANGUAGES.values() if "vb-"+v[0] not in {r["doculect_id"] for r in s["records"]}],
            morphology="Form I/II/III and INV labels, compounds and allofams remain verbatim. No automatic equivalence between stem cells or independent recombination of their alternatives.")
    corpus=dict(schema_version="1.0.0",id="vanbik-chapter4-100-v1",source_kind="sourced",
        source=dict(id="vanbik2009",path=str(PDF.relative_to(ROOT)),sha256=lock["sha256"],
            url="https://stedt.berkeley.edu/pubs_and_prods/STEDT_Monograph8_Proto-Kuki-Chin.pdf",
            license="Source PDF retained unmodified under STEDT's academic non-commercial permission; lexical facts and locators extracted here."),
        selection_sha256=digest(selection),splits_sha256=digest(splits),
        limitations=["This extraction has not received independent transcription or etymological review.",
            "Quoted reflex lists are parsed; source discussions, footnotes and unparsed portions remain accessible by PDF locator and are not silently treated as additional observations.",
            "A source-level cognacy claim is retained as a claim. Inclusion does not establish its correctness."],sets=selected)
    assert len(selected)==100 and len(core)==50 and sum(len(s["records"]) for s in selected)>=300
    return {"selection.json":selection,"splits.json":splits,"corpus.json":corpus,"evidence.json":make_evidence(corpus)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--check",action="store_true");a=p.parse_args()
    files=generate();DEST.mkdir(parents=True,exist_ok=True)
    for name,obj in files.items():
        path=DEST/name;data=encoded(obj)
        if a.check:assert path.read_bytes()==data,"Frozen Kuki-Chin input changed: "+name
        else:
            if path.exists() and path.read_bytes()!=data:raise ValueError("Create an explicitly versioned study to change frozen inputs: "+name)
            path.write_bytes(data)
    print("Kuki-Chin:",len(files["corpus.json"]["sets"]),"sets;",len(files["evidence.json"]["records"]),"reflex records;",files["splits.json"]["family_counts"])


if __name__=="__main__":main()
