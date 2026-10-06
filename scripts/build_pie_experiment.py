"""Reproduce M5 baselines and the specified fragments of published analyses.

The lexical models are baselines, not published complete PIE-to-daughter laws.
The separate diagnostics encode source-defined fragments with exact scope.
"""
import argparse
from collections import Counter, defaultdict
import json
import re
import unicodedata

from build_pie_corpus import ROOT, DEST, encoded, digest
from build_m2_fixtures import rule

FREEZE_COMMIT = "83adff4"


def proto_tokens(raw):
    """All explicit comma/tilde alternatives, or an explicit unsupported result.

    Unknown laryngeals, optional segments and opaque notation are not guessed.
    The baseline drops lexical accent and morphological hyphens explicitly.
    """
    words = []
    for alternative in re.split(r"[,~]", raw):
        s = unicodedata.normalize("NFC", alternative.strip().lstrip("*").strip())
        s = s.replace("u̯", "w").replace("i̯", "j").replace("k̑", "ḱ").replace("g̑", "ǵ")
        s = s.replace("₁", "1").replace("₂", "2").replace("₃", "3").replace("-", "")
        for a,b in {"á":"a", "é":"e", "í":"i", "ó":"o", "ú":"u", "ḗ":"ē", "ṓ":"ō"}.items(): s=s.replace(a,b)
        tokens = re.findall(r"h[123]|[a-zḱǵāēīōū][ʰʷ]*[\u0325\u032f\u0301]*", s)
        if not tokens or "".join(tokens) != s:
            return None
        words.append(tokens)
    return [list(w) for w in dict.fromkeys(tuple(w) for w in words)]


def observed_tokens(record):
    tokens = record["normalization"]["tokens"]
    if not tokens or any(not t or any(c.isspace() for c in t) or any(c in t for c in "/?*#_") for t in tokens):
        return None
    return tokens


def align(left, right):
    """Unit edit alignment; ties choose diagonal, deletion, then insertion."""
    dp = [[0] * (len(right)+1) for _ in range(len(left)+1)]
    for i in range(len(left)+1): dp[i][0] = i
    for j in range(len(right)+1): dp[0][j] = j
    for i,a in enumerate(left,1):
        for j,b in enumerate(right,1):
            dp[i][j] = min(dp[i-1][j-1] + (a != b), dp[i-1][j]+1, dp[i][j-1]+1)
    pairs=[]; i,j=len(left),len(right)
    while i or j:
        if i and j and dp[i][j] == dp[i-1][j-1] + (left[i-1] != right[j-1]):
            pairs.append((left[i-1],right[j-1])); i-=1; j-=1
        elif i and dp[i][j] == dp[i-1][j]+1:
            pairs.append((left[i-1],None)); i-=1
        else:
            pairs.append((None,right[j-1])); j-=1
    return pairs[::-1]


def package(name, rules, inventory, description, initial="published-root"):
    return dict(id=name, version="1.0.0", description=description,
                inventory=sorted(set(inventory)), initial_stage=initial,
                final_stage=initial if not rules else name+"-stage-"+str(len(rules)),
                laws=[dict(id=name+"-law-"+str(i+1), input_stage=initial if i==0 else name+"-stage-"+str(i),
                           output_stage=name+"-stage-"+str(i+1), rule=r) for i,r in enumerate(rules)])


def fit_correspondences(sets):
    counts=defaultdict(lambda:defaultdict(Counter)); training=[]; ignored_insertions=0
    for s in sets:
        if s["split"] != "train": continue
        roots=proto_tokens(s["reconstruction"]["original"])
        if roots is None or len(roots)!=1 or s["loans"]: continue
        for r in s["records"]:
            target=observed_tokens(r)
            if target is None or "+" in target: continue
            lang=r["raw_form"]["Language_ID"]
            training.append(dict(set_id=s["id"], family_id=s["family_id"], record_id=r["id"],
                                 input=roots[0], output=target, doculect_id=lang))
            for a,b in align(roots[0],target):
                if a is None: ignored_insertions+=1
                else: counts[lang][a][b]+=1
    maps={lang:{a:sorted(c, key=lambda b:(-c[b], b!=a, "" if b is None else b))[0] for a,c in alphabet.items()}
          for lang,alphabet in counts.items()}
    return maps,training,ignored_insertions


def compile_map(name, mapping, inventory):
    # Fresh temporary atoms implement simultaneous one-token substitutions and
    # deletions without accidentally feeding another learned substitution.
    changed=[(a,b) for a,b in sorted(mapping.items()) if a!=b]
    markers=[f"MAP{i}" for i in range(len(changed))]
    assert not set(markers)&set(inventory)
    rs=[rule([a],marker) for (a,_),marker in zip(changed,markers)]
    rs += [rule([marker],b) for (_,b),marker in zip(changed,markers)]
    return package(name,rs,inventory+markers,"Train-only unit-edit correspondence baseline; substitution/deletion only, with no morphological or chronological interpretation.")


def lexical_experiment(corpus):
    sets=corpus["sets"]; roots={s["id"]:proto_tokens(s["reconstruction"]["original"]) for s in sets}
    pool=[list(w) for w in dict.fromkeys(tuple(w) for ws in roots.values() if ws for w in ws)]
    inventory=sorted({a for w in pool for a in w}|{a for s in sets for r in s["records"] for a in (observed_tokens(r) or []) if a!="+"})
    maps,training,ignored=fit_correspondences(sets)
    docs=sorted({r["raw_form"]["Language_ID"] for s in sets for r in s["records"]},key=int)
    packages=[package("identity",[],inventory,"No-change baseline; not a historical derivation.")]
    packages += [compile_map("correspondence-"+doc,maps.get(doc,{}),inventory) for doc in docs]
    forwards=[]; inverses=[]; outcomes=[]
    for s in sets:
        ws=roots[s["id"]]; available=[]
        for r in s["records"]:
            obs=observed_tokens(r); ids=[]
            why = "unsupported-proto-notation" if ws is None else "missing-or-unsupported-phonemic-segmentation" if obs is None else None
            if why is None:
                available.append((r,obs))
                for model in ["identity","correspondence"]:
                    pid="identity" if model=="identity" else "correspondence-"+r["raw_form"]["Language_ID"]
                    for i,w in enumerate(ws):
                        jid=f"set-{s['id']}-{r['id']}-{model}-a{i}"
                        forwards.append(dict(id=jid,package_id=pid,input=w,expected=obs));ids.append(jid)
            outcomes.append(dict(set_id=s["id"],record_id=r["id"],split=s["split"],core=s["core"],branch=r["branch"],
                                 source_locator=r["source_locator"],source_loan=bool(s["loans"]),
                                 status="scheduled" if why is None else "unsupported",failure_category=why,forward_job_ids=ids,
                                 source_root_is_stem=s["reconstruction"]["original"].rstrip().endswith("-"),
                                 morphology="unmodeled-root-to-lexeme-difference",source_uncertainty=r["uncertainty"]))
        if ws and len({r['branch'] for r,_ in available})>=2:
            for model in ["identity","correspondence"]:
                bs=[dict(doculect_id=r["id"],package_id="identity" if model=="identity" else "correspondence-"+r["raw_form"]["Language_ID"],expected=obs) for r,obs in available]
                inverses.append(dict(id=f"set-{s['id']}-{model}",pool=pool,branches=bs,reference=ws))
    request=dict(schema_version="1.0.0",id="pie-lexical-baselines-v1",packages=packages,forward=forwards,inverse=inverses)
    design=dict(schema_version="1.0.0",freeze_commit=FREEZE_COMMIT,corpus_sha256=digest(corpus),
                normalization=dict(root_policy="Remove reconstruction star and morpheme hyphens; u̯/i̯ become w/j; subscript laryngeal numbers become ASCII; acute lexical accent is dropped. Retain length, palatal and aspiration distinctions. Parse all explicit comma/tilde alternatives or reject the entire expression. Unspecified H and optional segments remain unsupported.",
                                   reflex_policy="Use the source Phonemic_Segments column verbatim; no orthographic-to-phonetic inference. Reject opaque aliases/uncertainty tokens. Raw columns remain in corpus.json.",
                                   dropped_accent_limitation="These baselines cannot model Verner conditioning and must not be described as doing so."),
                baselines=["identity", "train-only-edit-correspondence"],models=maps,training_examples=training,
                training_sha256=digest(training),ignored_training_insertions=ignored,
                root_pool=pool,reference_pool_scope="All parsable published roots in the frozen sample, including test references. This is declared closed-set retrieval, not generation of previously unknown ancestors.",
                fixed_inventory=inventory,vocabulary_policy="The frozen corpus defines a shared symbol inventory; no held-out token frequencies or correspondences are fitted.",
                split_policy="No development/test pairs fit mappings. Published sources and model training may already contain these etymologies; no blind-discovery claim.",
                expected_failure_policy="Roots are often stems whereas reflexes are inflected lexemes. Exact-word failures are retained; learned alignments and certificate validity do not supply missing morphology.",
                outcomes=outcomes)
    return request,design


def source_diagnostics():
    # Ringe's seven-change chronology, encoded only where the M2 two-token
    # context can express the source condition exactly.
    inv=["a","á","e","é","i","í","o","ó","u","ú","p","t","k","kʷ","b","d","g","gʷ",
         "bʰ","dʰ","gʰ","gʷʰ","f","θ","x","xʷ","β","ð","ɣ","ɣʷ","s","z","m","n","l","r","w","j"]
    non_obstruents=["a","á","e","é","i","í","o","ó","u","ú","m","n","l","r","w","j"]
    shifts=[]
    for a,b in [("p","f"),("t","θ"),("k","x"),("kʷ","xʷ")]:
        shifts += [rule([a],b,left_edge=True),rule([a],b,left=[non_obstruents])]
    for a,b in [("b","p"),("d","t"),("g","k"),("gʷ","kʷ"),("bʰ","β"),("dʰ","ð"),("gʰ","ɣ"),("gʷʰ","ɣʷ")]:shifts.append(rule([a],b))
    # Only V_C_V windows: the immediately preceding unaccented vowel is the
    # last preceding nucleus, and both neighbours are necessarily voiced.
    verner=[rule([a],b,left=[["a","e","i","o","u"]],right=[["a","á","e","é","i","í","o","ó","u","ú"]])
            for a,b in [("f","β"),("θ","ð"),("s","z"),("x","ɣ"),("xʷ","ɣʷ")]]
    stress=[]
    for a,b in [("a","á"),("e","é"),("i","í"),("o","ó"),("u","ú")]:
        stress.append(rule([a],b,left_edge=True))
        stress.append(rule([b],a,left=["*","*"]))
    correct=package("ringe-2022-vcv",shifts+verner+stress,inv,
                    "Ringe 2022 pp.55-56: changes a-d then stress f, restricted to explicitly accent-marked VCV/VCVCV controls; excludes clusters, later changes e/g and full PIE-to-Germanic derivations.",initial="accented-pre-germanic-window")
    reversed_=package("stress-before-verner-control",shifts+stress+verner,inv,
                      "Deliberately reversed chronology control, not an attributed historical theory.",initial="accented-pre-germanic-window")
    lar_inv=["h1","h2","h3","h","a","e","o","n","r","l","m","t","R"]
    conditioned=[rule(["h2","h3"],None,right=[["o"]],left_edge=True),
                 rule(["h3"],None,right=[["n","r","l","m","R"]],left_edge=True),
                 rule(["h1"],None,left_edge=True),rule(["h2","h3"],"h",left_edge=True),
                 rule(["e"],"a",left=[["h"]],left_edge=True),rule(["o"],"a")]
    retained=[rule(["h1"],None,left_edge=True),rule(["h2","h3"],"h",left_edge=True),
              rule(["e"],"a",left=[["h"]],left_edge=True),rule(["o"],"a")]
    pk=package("kloekhorst-2006-written-onset",conditioned,lar_inv,
               "Kloekhorst 2006 pp.82-91,105: restricted Hittite written-onset projection, with h2/h3 loss before o and h3 loss before resonants. Unwritten glottal stop is not a claim of phonetic absence.",initial="pie-onset-projection")
    pm=package("melchert-retention-as-reported-2006",retained,lar_inv,
               "Retention comparison attributed to Melchert 1987 as reported by Kloekhorst 2006 pp.85-86. Primary Melchert PDF unavailable; attribution and scope require specialist review.",initial="pie-onset-projection")
    cases=[]
    def add(cid,kind,source,locator,raw_input,raw_output,w,out,scope,uncertainty,models):
        cases.append(dict(id=cid,kind=kind,source=source,locator=locator,raw_input=raw_input,raw_output=raw_output,
                          input=w,expected=out,scope=scope,uncertainty=uncertainty,package_ids=models))
    for cid,w,out in [
        ("vcv-unaccented",["a","t","é"],["á","ð","e"]),
        ("vcv-accented",["á","t","e"],["á","θ","e"]),
        ("vcv-p",["a","p","é"],["á","β","e"]),
        ("vcv-k",["a","k","é"],["á","ɣ","e"]),
        ("vcv-kw",["a","kʷ","é"],["á","ɣʷ","e"]),
        ("vcv-s",["a","s","é"],["á","z","e"]),
        ("blocked-cluster",["s","t","e"],["s","t","e"]),
        ("voiced-stop-counterfeeding",["a","d","é"],["á","t","e"]),
        ("breathy-stop",["a","dʰ","é"],["á","ð","e"]),
        ("initial-stop",["p","é"],["f","é"])]:
        add(cid,"synthetic-source-rule-control","ringe2022","printed pp.55-56; PDF pp.73-74",None,None,w,out,
            "Control strings illustrating a restricted source condition, not attested etymologies or full Proto-Germanic outputs.",
            "The full seven-change sequence is not implemented; these controls cover only the declared fragment.",[correct["id"],reversed_["id"]])
    # These tests compare the specified features of cited forms.
    # Whole words and disputed etymologies remain visible beside the projection.
    lar_cases=[
        ("forehead","84","*h₂ent-","ḫant-",["h2","e"],["h","a"],"Shared h2e retention."),
        ("join","84","*h₂ep-","ḫapp-",["h2","e"],["h","a"],"Only the initial sequence; gemination is outside scope."),
        ("grandmother","84","*h₂eno-","ḫanna-",["h2","e"],["h","a"],"Only the initial sequence."),
        ("right-proper","83","*h₂ór-o-","āra-",["h2","o"],["a"],"Etymology and o-grade explicitly tentative in source; vowel quantity projected away."),
        ("obeisance","83-84","*h₂oru̯o-i̯e/o-","aruuae-",["h2","o"],["a"],"Source analysis disputes an alternative derivation; consonant development omitted."),
        ("carry-out","88","*h₃n-i̯e/o-","anii̯a-",["h3","R"],["R"],"Only initial laryngeal presence: R abstracts the first resonant, ignoring vowels and resonant identity. No full-word epenthesis/gemination derivation."),
        ("stand","88","*h₃r-tó","arta",["h3","R"],["R"],"R abstracts the first resonant; the preceding a is outside the retention projection."),
        ("name","90","*h₃neh₃-men-","lāman",["h3","R"],["R"],"R abstracts source n and observed l, so this tests only initial laryngeal presence. The n-to-l history is not derived; h1/h3 reconstruction is disputed.")]
    for cid,page,rawi,rawo,w,out,note in lar_cases:
        add(cid,"source-backed-projection","kloekhorst2006-laryngeals","printed p."+page,rawi,rawo,w,out,
            "Two-token initial-context diagnostic, not a full-word derivation. h is conventional written laryngeal retention; no phonetic value selected.",note,[pk["id"],pm["id"]])
    jobs=[dict(id=c["id"]+"--"+pid,package_id=pid,input=c["input"],expected=c["expected"]) for c in cases for pid in c["package_ids"]]
    request=dict(schema_version="1.0.0",id="pie-source-diagnostics-v1",packages=[correct,reversed_,pk,pm],forward=jobs,inverse=[])
    sources=[
        dict(id="ringe2022",title="Don Ringe, What We Can (and Can't) Learn from Computational Cladistics, in Olander (ed.) 2022",url="https://www.cambridge.org/core/product/4B44B5ACF0D3BBA89B9408050F112A52",local_pdf="library/downloads/olandervol2022.pdf",sha256="6a361b313a4050163cfbd8994cfb54ac1e9bab8f8834a37911f46ddbf5dd2de8",locators=["pp.55-56; PDF pp.73-74"],reading="Text extraction inspected; rule conditions checked directly."),
        dict(id="kloekhorst2006-laryngeals",title="Alwin Kloekhorst (2006), Initial laryngeals in Anatolian",url="https://www.kloekhorst.nl/KloekhorstInitLar.pdf",local_pdf="library/downloads/kloekhorst2006-laryngeals.pdf",sha256="d89bf1e0803450eea187c96bb2bbdeb99c488f198f3e701df4925f1708dbb15e",locators=["pp.82-91,104-105"],reading="Scanned PDF page images inspected; disputed reconstructions retained."),
        dict(id="kloekhorst2013-ablaut",title="Alwin Kloekhorst (2013), Indo-European nominal ablaut patterns: The Anatolian evidence",url="https://www.kloekhorst.nl/KloekhorstIENominalAblautPatterns.pdf",local_pdf="library/downloads/kloekhorst2013-ablaut.pdf",sha256="bf5b6930cbde59c33608cf4e01d5891656a633c1e7372132c3f9f82304a03810",locators=["author PDF pp.1-2, especially footnote 6"],reading="Author PDF text inspected; traditional accounts are attributed through this source."),
        dict(id="kloekhorst2018-hi",title="Alwin Kloekhorst (2018), The origin of the Hittite hi-conjugation",url="https://www.kloekhorst.nl/KloekhorstOriginOfHiConjugation.pdf",local_pdf="library/downloads/kloekhorst2018-hi.pdf",sha256="ab76bb6a56ea7da62b55aae42989e2e92e676b8ec447ea3a14898a0c9b8225e5",locators=["pp.89-92; PDF pp.5-8"],reading="Source discussion inspected; Jasanoff/Eichner are reported positions, not independently read full monographs.")]
    return request,dict(schema_version="1.0.0",sources=sources,cases=cases,
        chronology=dict(source="ringe2022",edges=[["a","d"],["d","f"],["f","g"],["a","b"],["b","e"],["c","e"],["d","e"]],
                        encoded=["a: stop frication with obstruent blocking", "b/c: stop-series changes", "d: Verner only in explicit VCV windows", "f: accent shift only in the declared control shapes"],
                        excluded=["General last-nucleus lookup across arbitrary clusters", "postnasal/initial hardening e", "unstressed e raising g", "laryngeal history and full lexical morphology"],
                        caution="The source permits a/b simultaneity; this package chooses one licensed ordering. The reverse stress/Verner package is a falsification control, not a second scholarly theory."))


def morphology():
    return dict(schema_version="1.0.0",status="source-comparison-awaiting-specialist-review",dossiers=[
        dict(id="nominal-water",source="kloekhorst2013-ablaut",locator="author PDF pp.1-2, section 2 and note 6",core_set_ids=["335"],
             observed=dict(strong="u̯ātar",weak="u̯iten-"),analyses=[
                 dict(id="schindler-as-reported",strong="*u̯ód-r",weak="*u̯éd-n-",root_grade=["o","e"],accent=["root","root"],attribution="Schindler 1975 as discussed by Kloekhorst 2013"),
                 dict(id="kloekhorst-proterodynamic",strong="*u̯ód-r",weak="*ud-én-",root_grade=["o","zero"],accent=["root","suffix"],attribution="Kloekhorst 2013, including stated phonological interpretation of the weak stem")],
             discriminants=["The vowel and accent analysis of the weak stem", "Whether the strong/weak root alternation is inherited or remodeled"],
             conclusion="Unresolved: a spelling alone does not decide the accent/phonological analysis.",certificate_scope="No claim that a string rule proves the ablaut reconstruction."),
        dict(id="analogical-water",source="kloekhorst2013-ablaut",locator="author PDF p.2 note 6",core_set_ids=["335"],
             before="*udén-",after="*u̯dén-",model_form="*u̯ódr",operation="Introduce consonantal u̯ from the strong stem into the weak stem",
             operation_type="source-attributed-paradigm-analogy",regular_sound_law=False,
             conclusion="An explicit analysis-layer operation; it is not implemented as an unconditional sound law.",
             uncertainty="The source's reconstruction and interpretation require independent assessment."),
        dict(id="hi-conjugation",source="kloekhorst2018-hi",locator="pp.89-92; especially the ablaut and reduplication comparisons",core_set_ids=[],
             observations=[dict(strong="šākk-i",weak="šekk-",gloss="know"),dict(strong="kānk-i",weak="kank-",gloss="hang"),dict(strong="arai-i",weak="ari-",gloss="rise")],
             analyses=[
                 dict(id="jasanoff-h2e-as-reported",inherited_root_grades=["o","e"],zero_grade="later replacement in relevant formations",reduplication="not obligatory in the ancestral h2e category",attribution="Jasanoff 2003 as reported and criticized by Kloekhorst 2018; original monograph not independently checked"),
                 dict(id="kloekhorst-adapted-perfect",inherited_root_grades=["o","zero"],surface_e="analogy or epenthesis in the relevant weak stems",reduplication="not obligatory in the earliest perfect under an Indo-Hittite analysis",attribution="Kloekhorst 2018's adaptation of the perfect theory")],
             discriminants=["Whether apparent e-grade is inherited", "Independent support for each analogy/epenthesis", "Chronology and distribution of reduplication"],
             conclusion="Unresolved competing predictions; no automatic winner and no full morphological certificate.")])


def alignments(corpus):
    result={}
    for s in corpus["sets"]:
        if not s["core"]: continue
        available=[r for r in s["records"] if observed_tokens(r) and "+" not in observed_tokens(r)]
        left=available[0]; right=next(r for r in available[1:] if r["branch"]!=left["branch"])
        pairs=align(observed_tokens(left),observed_tokens(right))
        cell=lambda x:dict(kind="gap",value=None) if x is None else dict(kind="segment",value=x)
        aid="pie-"+s["id"]
        rows=[dict(doculect_id=r["id"],source_ref=r["source_locator"]+":Phonemic_Segments",original=[cell(x) for x in observed_tokens(r)],aligned=[cell(p[i]) for p in pairs]) for i,r in enumerate([left,right])]
        sites=[dict(id=aid+"-c"+str(i),alignment_id=aid,column_index=i) for i in range(len(pairs))]
        result["alignments/"+s["id"]+".json"] = dict(alignment_data=dict(schema_version="1.0.0",id=aid,description="Source-backed unit-edit baseline alignment; phonological homology and cognacy are not certified.",source_kind="sourced",doculects=[r["id"] for r in [left,right]],alignments=[dict(id=aid,evidence_unit=s["family_id"],width=len(pairs),rows=rows)]),
            sites=sites,groups=[dict(id="column-"+str(i),members=[x["id"]],claimed_support=1) for i,x in enumerate(sites)],support_policy="distinct-evidence-units-v1",claim="feasibility-only")
    return result


def generate():
    corpus=json.loads((DEST/"corpus.json").read_text())
    lexical,design=lexical_experiment(corpus); diagnostic,sources=source_diagnostics()
    return {"lexical-input.json":lexical,"experiment.json":design,"diagnostic-input.json":diagnostic,
            "source-analyses.json":sources,"morphology.json":morphology(),**alignments(corpus)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--check",action="store_true");args=p.parse_args()
    files=generate()
    for name,value in files.items():
        path=DEST/name;data=encoded(value)
        if args.check: assert path.read_bytes()==data,"Stale PIE experiment: "+name
        else: path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    r=files["lexical-input.json"]
    print(f"PIE: {len(r['forward'])} forward jobs, {len(r['inverse'])} finite-pool queries, 20 core alignments and 3 morphology dossiers")


if __name__=="__main__":main()
