"""Build the M6 transcription baselines and source-defined rule fragments."""
import argparse
from collections import Counter, defaultdict
import json
import re
import unicodedata

from build_pie_corpus import ROOT, encoded, digest
from build_pie_experiment import align, package, compile_map
from build_m2_fixtures import rule
from build_kuki_corpus import DEST, LANGUAGES

FREEZE_COMMIT="2ed6130"
TONES=set("\u0300\u0301\u0302\u0304\u030c")


def parse_form(raw,doculect="proto"):
    """Return complete labelled cells, or a reason for withholding analysis.

    The tokens are transcription graphemes, not a new phonemic analysis.
    Tone is a separate observation; every removed mark remains in this record.
    """
    original=raw
    s=unicodedata.normalize("NFD",raw).replace("ı","i")
    s=re.sub(r"\s+(?=[\u0300\u0301\u0302\u0304\u030c])","",s)
    s=re.sub(r"-\s*(III|II|I|INV)\b",r"-\1",s)
    s=s.strip().rstrip(";")
    trace=dict(original=original,display_normalized=unicodedata.normalize("NFC",s),tone_marks=[],cells=None,reason=None)
    if any(c in s for c in "⪤↭↮()/<>"):
        trace["reason"]="allofamy-optional-material-or-opaque-expression";return trace
    cells={}
    for chunk in s.split(","):
        chunk=chunk.strip()
        if doculect=="proto":chunk=re.sub(r"^\*\s*","",chunk)
        m=re.fullmatch(r"(.+?)-(III|II|I|INV)",chunk)
        label=m[2] if m else "unmarked";body=m[1] if m else chunk
        # Tedim's question mark denotes the glottal stop in this source (p.9 n.6).
        if doculect=="vb-tedim":body=body.replace("?","ʔ")
        tones=[dict(index=i,mark=c,kind="diacritic") for i,c in enumerate(body) if c in TONES]
        if doculect=="vb-tedim":
            tones += [dict(index=i,mark=c,kind="Tedim-numeral") for i,c in enumerate(body) if c in "1234"]
        trace["tone_marks"].append(dict(cell=label,marks=tones,
            status="marked" if tones else "not-marked-in-this-form; not necessarily toneless"))
        body="".join(c for c in body if c not in TONES and not (doculect=="vb-tedim" and c in "1234"))
        if not body or any(c.isspace() for c in body) or any(c in body for c in "-*?;0123456789'’ʻ"):
            trace["reason"]="compound-or-unsupported-transcription";return trace
        if any(not (c.isalpha() or unicodedata.combining(c) or c==":") for c in body):
            trace["reason"]="unsupported-transcription-character";return trace
        tokens=[]
        for c in body:
            if unicodedata.combining(c) and tokens:tokens[-1]+=c
            elif unicodedata.combining(c):
                trace["reason"]="unattached-combining-mark";return trace
            else:tokens.append(c)
        tokens=[unicodedata.normalize("NFC",t) for t in tokens]
        if label in cells:
            trace["reason"]="multiple-readings-for-one-stem-cell";return trace
        cells[label]=tokens
    if len(cells)>1 and "unmarked" in cells:
        trace["reason"]="unlabelled-alternatives";return trace
    trace["cells"]=cells
    return trace


def match_cells(root,reflex):
    if root["cells"] is None:return [],"unsupported-proto-expression"
    if reflex["cells"] is None:return [],reflex["reason"]
    a,b=root["cells"],reflex["cells"]
    # INV explicitly says that the source reflex is invariant. An unlabelled
    # reflex does not say which of two distinct reconstructed stems it reflects.
    if set(b)=={"INV"}:return [(k,w,b["INV"]) for k,w in a.items()],None
    if set(a)!=set(b):return [],"unmatched-stem-cell-labels"
    return [(k,a[k],b[k]) for k in a],None


def node(source,id):return dict(source_id=source,node_id=id)


def scoped(batch,bindings,query_roots):
    ns=[]
    for b in bindings:
        for n in [b["ancestor"],b["descendant"]]:
            if n not in ns:ns.append(n)
    return dict(schema_version="1.0.0",nodes=ns,package_scopes=bindings,
        query_scopes=[dict(query_id=j["id"],ancestor=query_roots[j["id"]]) for j in batch["inverse"]],batch=batch)


def lexical(corpus):
    roots={s["id"]:parse_form(s["source_reconstruction"]) for s in corpus["sets"]}
    refs={r["id"]:parse_form(r["source_form"],r["doculect_id"]) for s in corpus["sets"] for r in s["records"]}
    pools=defaultdict(list)
    for p in roots.values():
        for cell,w in (p["cells"] or {}).items():
            if w not in pools[cell]:pools[cell].append(w)
    inventory=sorted({a for p in list(roots.values())+list(refs.values()) for w in (p["cells"] or {}).values() for a in w})
    counts=defaultdict(lambda:defaultdict(Counter));training=[];ignored=0
    for s in corpus["sets"]:
        if s["split"]!="train" or s["extraction"]["loan_mentioned"]:continue
        seen=set()
        for r in s["records"]:
            pairs,_=match_cells(roots[s["id"]],refs[r["id"]])
            for cell,w,obs in pairs:
                key=(r["doculect_id"],cell,tuple(w),tuple(obs))
                if key in seen:continue
                seen.add(key)
                training.append(dict(set_id=s["id"],family_id=s["family_id"],record_id=r["id"],doculect_id=r["doculect_id"],cell=cell,input=w,output=obs))
                for a,b in align(w,obs):
                    if a is None:ignored+=1
                    else:counts[r["doculect_id"]][a][b]+=1
    maps={d:{a:sorted(c,key=lambda b:(-c[b],b!=a,"" if b is None else b))[0] for a,c in cs.items()} for d,cs in counts.items()}
    docs=sorted({r["doculect_id"] for s in corpus["sets"] for r in s["records"]})
    packages=[];bindings=[];ancestor=node("vanbik2009","vanbik-2009-PKC")
    for d in docs:
        for model in ["identity","correspondence"]:
            pid=model+"-"+d
            p=package(pid,[],inventory,"Identity of transcription graphemes; no historical change asserted") if model=="identity" else compile_map(pid,maps.get(d,{}),inventory)
            packages.append(p);bindings.append(dict(package_id=pid,ancestor=ancestor,descendant=node("vanbik2009",d)))
    jobs=[];inverse=[];outcomes=[];query_roots={};withheld=[];topology_queries=[]
    for s in corpus["sets"]:
        available=defaultdict(lambda:defaultdict(list))
        for r in s["records"]:
            pairs,why=match_cells(roots[s["id"]],refs[r["id"]]);ids=[]
            for cell,w,obs in pairs:
                available[cell][r["doculect_id"]].append((r,obs))
                for model in ["identity","correspondence"]:
                    jid=f"{r['id']}-{cell}-{model}";ids.append(jid)
                    jobs.append(dict(id=jid,package_id=model+"-"+r["doculect_id"],input=w,expected=obs))
            outcomes.append(dict(set_id=s["id"],record_id=r["id"],split=s["split"],core=s["core"],source_locator=r["source_locator"],
                doculect_id=r["doculect_id"],source_loan_mentioned=s["extraction"]["loan_mentioned"],root_normalization=roots[s["id"]],
                reflex_normalization=refs[r["id"]],failure_category=why,forward_job_ids=ids))
        for cell,by_doc in available.items():
            obs=[]
            for d,rs in by_doc.items():
                words={tuple(w) for _,w in rs}
                if len(words)!=1:
                    withheld.append(dict(set_id=s["id"],cell=cell,doculect=d,reason="multiple-source-readings-not-collapsed"));continue
                obs.append((rs[0][0],rs[0][1]))
            if len(obs)<2 or len({r["branch"] for r,_ in obs})<2:
                withheld.append(dict(set_id=s["id"],cell=cell,reason="fewer-than-two-principal-groups"));continue
            for model in ["identity","correspondence"]:
                # Restricted scope is an observation-removal experiment, not
                # a conversion of VanBik's ancestor into Button's ancestor.
                for scope in ["all-groups","northern-only"]:
                    kept=obs if scope=="all-groups" else [(r,w) for r,w in obs if r["subgroup"]=="Northern"]
                    if len(kept)<2:continue
                    jid=f"vb-{s['id']}-{cell}-{model}-{scope}"
                    inverse.append(dict(id=jid,pool=pools[cell],reference=[roots[s["id"]]["cells"][cell]],
                        branches=[dict(doculect_id=r["doculect_id"],package_id=model+"-"+r["doculect_id"],expected=w) for r,w in kept]))
                    query_roots[jid]=ancestor
                    topology_queries.append(dict(id=jid,set_id=s["id"],cell=cell,model=model,scope=scope,
                        observed_doculects=[r["doculect_id"] for r,_ in kept],ancestor_unchanged="vanbik-2009-PKC"))
    batch=dict(schema_version="1.0.0",id="m6-kuki-transcription-baselines",packages=packages,forward=jobs,inverse=inverse)
    design=dict(schema_version="1.0.0",freeze_commit=FREEZE_COMMIT,corpus_sha256=digest(corpus),
        normalization="NFD, typographic dotless i to i, remove whitespace immediately before tone combining marks and within stem labels, then NFC grapheme tokens. Five declared tone diacritics and Tedim 1–4 numeral marks are retained separately and excluded from the segmental baseline. Tedim ? is ʔ (source p.9 n.6). Length notation and other diacritics remain; no cross-variety phonetic recoding.",
        morphology="Named stem cells must agree. INV is an explicit invariant reflex of each specified source stem; an unlabelled reflex is not assigned freely to I/II. Allofams, optional material and compounds stay unsupported. The whole record is exact only if every required cell matches.",
        tone_limit="No tonal predictions are made by the learned baseline. Unmarked tone does not mean zero, and chapter-4 roots do not acquire invented chapter-6 tones.",
        models=maps,training_examples=training,training_sha256=digest(training),ignored_training_insertions=ignored,
        reference_pools=dict(pools),inventory=inventory,reference_labels_include_test=True,
        split_limit="All source labels and the fixed inventory are known. Only training reflex pairs fit mappings. This is retrospective closed-set retrieval, not a blind discovery experiment.",
        inverse_withheld=withheld,topology_queries=topology_queries,outcomes=outcomes)
    return scoped(batch,bindings,query_roots),design


def diagnostics():
    packages=[];bindings=[];jobs=[];cases=[];queries=[];qroots={}
    inv=["a","e","i","o","u","ə","ɤ","ɯ","s","r","w","b","p","t","k","g","n","m","d","z","ɕ","ʔ","ŋ","l","ɓ","ɗ","v","f","θ","h","ʰ","N","dz","ndz","nd","n̥","G","D","B","V","T1","T2","T3","TC-I","TC-IIA","TC-IIB","TC-III"]
    def add_package(pid,rs,source,ancestor,descendant,description):
        packages.append(package(pid,rs,inv,description));bindings.append(dict(package_id=pid,ancestor=node(source,ancestor),descendant=node(source,descendant)))
        return pid
    def case(cid,w,out,pids,source,pages,scope,kind="source-backed-projection",dossiers=()):
        ids=[]
        for pid in pids:
            jid=cid+"--"+pid;ids.append(jid);jobs.append(dict(id=jid,package_id=pid,input=w,expected=out))
        cases.append(dict(id=cid,source_id=source,pdf_pages=pages,input=w,expected=out,package_ids=pids,job_ids=ids,
                          kind=kind,projection=scope,dossier_ids=list(dossiers)))
    # VanBik's initial correspondences are explicitly projections. Word-final
    # losses, vowels, tone and compound morphology do not enter these cases.
    for doc,mapping in [("central",{"ɓ":"b","ɗ":"d","r":"r","w":"v","y":"z","θ":"f"}),
                        ("northern",{"ɓ":"b","ɗ":"d","r":"g","w":"v","y":"z"}),
                        ("mindat",{"ɓ":"ɓ","ɗ":"ɗ","r":"g","w":"v"})]:
        for symbol in mapping:
            if symbol not in inv:inv.append(symbol)
        rs=[rule([a],b,left_edge=True) for a,b in mapping.items() if a!=b]
        add_package("vanbik-"+doc,rs,"vanbik2009","vanbik-2009-PKC",doc,"VanBik's cited initial correspondence only; no full-word derivation")
    # Keep every package's shared inventory stable after adding y above.
    for p in packages:p["inventory"]=sorted(inv)
    add_package("plain-stop-retention-control",[],"vanbik2009","vanbik-2009-PKC","mindat","Alternative plain-stop input with retention; a diagnostic control, not a complete attribution to Khoi")
    for cid,inp,doc,out,pg in [("implosive-central","ɓ","central","b",93),("implosive-mindat","ɓ","mindat","ɓ",93),
        ("dental-central","ɗ","central","d",102),("dental-mindat","ɗ","mindat","ɗ",102),
        ("r-central","r","central","r",51),("r-peripheral","r","northern","g",51),
        ("w-central","w","central","v",90),("w-northern","w","northern","v",90),
        ("y-central","y","central","z",71),("dental-fricative","θ","central","f",202)]:
        case(cid,[inp],[out],["vanbik-"+doc],"vanbik2009",[pg],"Initial only; source table phonetic value used for Mindat, not inferred from orthographic b/d")
    case("plain-stop-mindat",["b"],["ɓ"],["plain-stop-retention-control"],"vanbik2009",[92,93],"Plain b plus retention fails to recover the recorded implosive; an extra historical change could make this alternative fit",kind="counteranalysis-control")
    # Initial sr fragment. The broad rule is Handel's condition as reported by
    # Jacques; the restricted rule is one of Jacques's unresolved alternatives.
    sr="jacques-halshs-01287468"
    add_package("sr-broad",[rule(["r"],None,left=[["s"]],right=[["a","o","ə"]],left_edge=True)],sr,"PST-sr-hypothesis","non-Sinitic-projection","Handel's non-front condition as reported by Jacques; includes ə")
    add_package("sr-restricted",[rule(["r"],None,left=[["s"]],right=[["a","o"]],left_edge=True)],sr,"PST-sr-hypothesis","non-Sinitic-projection","Jacques's possible narrower condition; this alone is not a complete daughter-language history")
    for cid,v,expected in [("sr-kill","a",["s","a"]),("sr-suck","o",["s","o"]),("sr-shame","ə",["s","r","ə"]),("sr-root","ə",["s","r","ə"])]:
        case(cid,["s","r",v],expected,["sr-broad","sr-restricted"],sr,[4,5],"Projected retention or loss of r at the hypothesized non-Sinitic intermediate stage; subsequent reflex changes and word endings omitted",dossiers=[cid])
    add_package("Tibetan-sr-cluster",[rule(["r"],None,left=[["s"]],left_edge=True),rule(["s"],"ɕ",left_edge=True)],sr,"pre-Tibetan-sr","Tibetan-onset","Cluster sr > ɕ, expressed by two atomic edits")
    add_package("Tibetan-syllabic-prefix",[rule(["ə"],None,left=[["s"]],right=[["r"]],left_edge=True)],sr,"pre-Tibetan-sr","Tibetan-onset","sə-r loses the vowel and preserves sr")
    case("sr-louse",["s","r"],["ɕ"],["Tibetan-sr-cluster"],sr,[2],"Initial only",dossiers=["sr-louse"])
    case("sr-presyllable",["s","ə","r"],["s","r"],["Tibetan-syllabic-prefix"],sr,[2],"Initial only; lost vowel is a hypothesis",dossiers=["sr-nephew"])
    wa="jacques-halshs-00408281"
    laufer=[rule(["a"],"o",left=[["w"]]),rule(["w"],None,right=[["o"]])]
    fusion=[rule(["b"],None,left=[["u"]],right=[["a"]]),rule(["u"],"w",right=[["a"]])]
    add_package("early-wa-late-fusion",laufer+fusion,wa,"pre-Tibetan-wa","Tibetan-projection","Jacques's relative chronology, restricted to the nominal u-ba fragment")
    add_package("fusion-before-wa-control",fusion+laufer,wa,"pre-Tibetan-wa","Tibetan-projection","Wrong-order diagnostic control")
    for cid,w,out in [("wa-tooth",["s","w","a"],["s","o"]),("wa-handspan",["t","w","a"],["t","o"]),
                     ("wa-horn",["r","u","b","a"],["r","w","a"]),("wa-angle",["g","r","u","b","a"],["g","r","w","a"])]:
        case(cid,w,out,["early-wa-late-fusion","fusion-before-wa-control"],wa,[2,3,4],"Rhyme/fusion projection: supplied nominal concatenation, no '+' boundary is deleted. Handspan m- and aspiration are outside scope.",dossiers=[cid] if cid in {"wa-tooth","wa-handspan"} else ["wa-tooth"])
    ti="jacques2012-internal"
    add_package("nasal-attrition",[rule(["ndz"],"dz",left_edge=True),rule(["nd"],"d",left_edge=True),rule(["dz"],"z",left_edge=True)],ti,"pre-Tibetan","Tibetan-onset","Two ordered onset changes from Jacques's nasal attrition account")
    for cid,w,out in [("tib-bridge",["ndz"],["z"]),("tib-poison",["nd"],["d"]),("tib-eat",["dz"],["z"])]:
        case(cid,w,out,["nasal-attrition"],ti,[2,3,4,5],"Initial only; morphology, rhyme and the age of prenasalization remain separate claims",dossiers=[cid])
    add_package("prefix-merger",[rule(["G","D"],"g",left_edge=True),rule(["V"],None,left=[["g"]],left_edge=True)],ti,"pre-Tibetan","Tibetan-onset","Abstract G/D and unspecified non-o vowel V; merger diagnostic, not a choice of their phonetic values")
    for x in ["G","D"]:case("tib-eagle-"+x,[x,"V","l"],["g","l"],["prefix-merger"],ti,[2,3],"Merged presyllable projection",dossiers=["tib-eagle"])
    # Whole-paradigm alternatives: choices below select complete lists of stem
    # inputs. They are not Cartesian products over segment alternatives.
    add_package("TAM-rounding",[rule(["a"],"o",left=[["s"],["o"]]),rule(["o"],None,left=[["G","D"]],left_edge=True),rule(["G","D"],"g",left_edge=True),rule(["t"],"d",right_edge=True)],ti,"pre-Tibetan","Tibetan-present-projection","Present Go/Do-sat > gsod fragment. Does not implement the whole verbal paradigm.")
    for x in ["G","D"]:case("tib-kill-"+x,[x,"o","s","a","t"],["g","s","o","d"],["TAM-rounding"],ti,[8,9,11],"Present cell only; past/future/imperative preserved jointly in morphology.json",dossiers=["tib-kill-paradigm"])
    sb="sagart-hal-00781153"
    add_package("early-tight-sn",[rule(["n"],"n̥",left=[["s"]],left_edge=True),rule(["s"],None,right=[["n̥"]],left_edge=True)],sb,"pre-OC","OC-onset","Hypothetical pre-OC sn > voiceless n; this is not an OC s-cluster claim")
    case("prefix-nose",["s","n"],["n̥"],["early-tight-sn"],sb,[19],"Initial only, and only at the hypothetical pre-OC date",dossiers=["prefix-nose"])
    add_package("N-voicing",[rule(["p"],"b",left=[["N"]],left_edge=True),rule(["N"],None,left_edge=True)],sb,"OC","MC-onset","Post-OC nasal-induced voicing, onset projection")
    add_package("s-devoicing-control",[rule(["b"],"p",left=[["s"]],left_edge=True),rule(["s"],None,left_edge=True)],sb,"Mei-OC-as-reported","MC-onset","Reported competing derivational direction, onset projection")
    for cid,w,out,pid in [("N-transitive",["p"],["p"],"N-voicing"),("N-intransitive",["N","p"],["b"],"N-voicing"),
        ("s-transitive",["s","b"],["p"],"s-devoicing-control"),("s-intransitive",["b"],["b"],"s-devoicing-control")]:
        case(cid,w,out,[pid],sb,[28,29],"The p/b contrast alone fits both whole derivational analyses; evidence for nasality and direction is external to this projection",dossiers=["prefix-separate"])
    su="jacques-halshs-01566036"
    add_package("grave-coda-t-to-s",[rule(["t"],"s",left=[["p","m","k","ŋ"]],right_edge=True)],su,"pre-OC-suffix","OC-coda","Jacques's proposed t > s after a subset of codas, instantiated here only for labial/velar codas")
    add_package("unconditioned-t-to-s-control",[rule(["t"],"s",right_edge=True)],su,"pre-OC-suffix","OC-coda","Overgeneralized control; wrongly changes t after l")
    for cid,w,out in [("suffix-coda",["k","t"],["k","s"]),("suffix-l-control",["l","t"],["l","t"])]:
        case(cid,w,out,["grave-coda-t-to-s","unconditioned-t-to-s-control"],su,[5,7],"Coda window only. Analogy and the later creation of departing tone are not computed.",kind="synthetic-source-rule-control",dossiers=["suffix-weave","suffix-bring","suffix-lie","suffix-hoe"])
    add_package("middle-i-loss",[rule(["i"],None,left=[["s"]],right_edge=True)],su,"pre-OC-suffix","OC-coda","Hypothesized loss of the vowel in a middle si suffix, without deriving an entire lexical form")
    case("suffix-middle",["s","i"],["s"],["middle-i-loss"],su,[9],"Suffix only; does not assert cognacy of the different Chinese and Khaling roots",dossiers=["suffix-remember"])
    # Two observations with the same function expose merger ambiguity exactly.
    for pid,src,anc,dst in [("merger-daughter-a",ti,"pre-Tibetan","onset-a"),("merger-daughter-b",ti,"pre-Tibetan","onset-b")]:
        add_package(pid,[rule(["ndz"],"dz",left_edge=True),rule(["dz"],"z",left_edge=True)],src,anc,dst,"Replicated merger functions as a synthetic identifiability control")
    queries.append(dict(id="merged-affricate-pool",pool=[["ndz"],["dz"],["p"]],reference=[["ndz"]],branches=[dict(doculect_id="onset-"+d,package_id="merger-daughter-"+d,expected=["z"]) for d in ["a","b"]]))
    qroots["merged-affricate-pool"]=node(ti,"pre-Tibetan")
    batch=dict(schema_version="1.0.0",id="m6-source-fragments",packages=packages,forward=jobs,inverse=queries)
    return scoped(batch,bindings,qroots),dict(schema_version="1.0.0",cases=cases,
        scope="Source-defined projections and labelled controls; certificate acceptance proves execution only. Full derivations and wider empirical validity remain under review.")


def alignments(corpus,design):
    result={};by=defaultdict(list)
    for o in design["outcomes"]:
        if o["core"] and o["failure_category"] is None:by[o["set_id"]].append(o)
    for s in corpus["sets"]:
        if not s["core"]:continue
        # Display-string alignments cover even unsupported compounds/alternatives.
        # This checks the M3 losslessness contract, not phonological homology.
        left=s["records"][0];right=next(r for r in s["records"][1:] if r["branch"]!=left["branch"])
        pair=align(list(left["source_form"]),list(right["source_form"]));aid="vb-core-"+s["id"]
        # M3 segments cannot be whitespace. Encode *all* display characters as
        # reversible scalar IDs, including spaces and combining tone marks.
        def cell(a):return dict(kind="gap",value=None) if a is None else dict(kind="segment",value=f"U{ord(a):06X}")
        rows=[dict(doculect_id=r["id"],source_ref=f"VanBik2009:[{s['id']}]:{r['source_alias']}",original=[cell(c) for c in r["source_form"]],aligned=[cell(p[i]) for p in pair]) for i,r in enumerate([left,right])]
        sites=[dict(id=aid+"-c"+str(i),alignment_id=aid,column_index=i) for i in range(len(pair))]
        result["alignments/"+s["id"]+".json"]=dict(alignment_data=dict(schema_version="1.0.0",id=aid,description="Display-character unit-edit alignment using reversible Uxxxxxx Unicode scalar IDs; preserves spaces and tone marks, without certifying phonological homology",source_kind="sourced",doculects=[r["id"] for r in [left,right]],alignments=[dict(id=aid,evidence_unit=s["family_id"],width=len(pair),rows=rows)]),sites=sites,
            groups=[dict(id="column-"+str(i),members=[site["id"]],claimed_support=1) for i,site in enumerate(sites)],support_policy="distinct-evidence-units-v1",claim="feasibility-only")
    return result


def generate():
    corpus=json.loads((DEST/"corpus.json").read_text());lex,design=lexical(corpus);diag,sources=diagnostics()
    ds=json.loads((ROOT/"data/cross-branch/dossiers.json").read_text())["dossiers"]
    morphology=dict(schema_version="1.0.0",choice_policy="An analysis selects all its listed cells jointly. No segment-wise Cartesian product is permitted.",
        dossiers=[dict(id=d["id"],source=d["citations"],morphology=d["morphology"],analyses=d["analyses"],evidence=d["evidence"]) for d in ds if any(a["linked_forms"] for a in d["analyses"])])
    return {"lexical-input.json":lex,"experiment.json":design,"diagnostic-input.json":diag,"source-fragments.json":sources,
            "cross-evidence.json":cross_evidence(),"joint-analysis-input.json":joint_analysis(),
            "morphology.json":morphology,**alignments(corpus,design)}


def cross_evidence():
    """Keep written graphs, scholarly transcriptions and reconstructions apart."""
    source=json.loads((ROOT/"data/cross-branch/dossiers.json").read_text())
    out=dict(schema_version="1.0.0",id="m6-cross-branch-evidence",description="Display-string evidence projection. Chinese characters, Middle Chinese analyses and Old Chinese reconstructions have distinct records; no character is inferred to be a phone.",
        sources=[dict(id=s["id"],title=s["title"],url=s["url"],version=s["catalogue_year"],license="Lexical facts and locators; see the bibliography for PDF rights",kind="publication",sha256=s["pdf_sha256"]) for s in source["sources"]],
        doculects=[],meanings=[],analyses=[],normalization_methods=[dict(id="display-identity",version="1",description="Keep manually transcribed display strings verbatim")],choice_groups=[],records=[])
    def record(id,form,doc,branch,meaning,cites,reconstructed=False,node_name=None,readings=None):
        proto="node-"+id if reconstructed else None;aid="analysis-"+id if reconstructed else None
        out["doculects"].append(dict(id="doc-"+id,name=doc,family=branch,stage=node_name or "As identified in the cited source; no independent date assigned",kind="proto" if reconstructed else "attested",date_range=None))
        out["meanings"].append(dict(id="meaning-"+id,label=meaning))
        if reconstructed:out["analyses"].append(dict(id=aid,description=node_name or doc,source_ids=[cites[0]["source_id"]],proto_node_id=proto))
        if readings is None:readings=[reading("display",form)]
        out["records"].append(dict(id=id,doculect_id="doc-"+id,meaning_ids=["meaning-"+id],representation="orthographic",attestation="reconstructed" if reconstructed else "attested",evidence_state="present",analysis_id=aid,proto_node_id=proto,
            citations=cites,readings=readings,uncertain=True,uncertainty_note="Source transcription, cognacy, morphology and reconstruction assumptions require independent review; this record certifies neither pronunciation nor inheritance.",imported_from=None))
    def reading(id,form,choice=None):
        return dict(id=id,original=form,normalized=form,cells=[dict(kind="segment",value=c) for c in form],
            normalization=[dict(method_id="display-identity",method_version="1",input=form,output=form,reason="Retain source display notation")],choices=[] if choice is None else [choice])
    for d in source["dossiers"]:
        cites=[dict(source_id=c["source_id"],locator="PDF pages "+",".join(map(str,c["pdf_pages"]))+"; dossier "+d["id"]) for c in d["citations"]]
        for i,w in enumerate(d["evidence"]):
            rid=d["id"]+"-e"+str(i+1)
            record(rid,w["form"],w["doculect"],w["branch"],w["meaning"],cites,w["representation"]=="source-reconstruction",w["reconstruction_node"])
            if w["chinese"]:
                c=w["chinese"]
                for label,key in [("MC","middle_chinese"),("OC","old_chinese")]:
                    if c[key]:record(rid+"-"+label,c[key],label+" scholarly analysis","Sinitic",w["meaning"],cites,True,c["reconstruction_system"]+"; "+label)
    # The two readings of each member bind the same global source-analysis
    # choice. This preserves a whole paradigm through M1 serialization.
    out["choice_groups"].append(dict(id="voice-analysis",options=["N-anticausative","s-devoicing"],description="Choose both members of the separate/be-separated paradigm together"))
    for cell,forms in [("transitive",["*pret","*s-brjat"]),("intransitive",["*N-pret","*brjat"])]:
        rs=[reading(a,f,dict(group_id="voice-analysis",option_id=a)) for a,f in zip(["N-anticausative","s-devoicing"],forms)]
        record("linked-voice-"+cell,forms[0],"Alternative OC analyses reported by Sagart–Baxter","Sinitic",cell,
            [dict(source_id="sagart-hal-00781153",locator="PDF pp.28–29, examples 52 and 55")],True,"OC paradigm comparison; alternatives remain explicitly bound",rs)
    return out


def joint_analysis():
    """A bounded onset test: two whole paradigms fit the same MC p/b pair.

    Affix presence is a model assumption, not an insertion by M2. The axes here
    are paradigm cells used as formal observation names, not separate languages.
    """
    axis=["MC-transitive","MC-intransitive"];analyses=[]
    for aid,rules in [("N-anticausative",[[],[rule(["p"],"b")]]),("s-devoicing",[[rule(["b"],"p")],[]])]:
        analyses.append(dict(id=aid,description="Onset projection of the complete "+aid+" analysis of 別; affix-conditioned change is supplied by the selected paradigm cell",proto_node_id="basic-onset-projection",
            choice_bindings=[dict(group_id="voice-analysis",option_id=aid)],alignment_evidence=None,
            branches=[dict(doculect_id=d,package=package(aid+"-"+d,rs,["p","b"],"Paradigm-cell onset projection, not a full lexical history",initial="basic-onset-projection")) for d,rs in zip(axis,rules)],
            observations=[dict(doculect_id=d,source_ref="Sagart–Baxter2012:PDF28–29:MC-onset",form=[dict(kind="segment",value=w)]) for d,w in zip(axis,["p","b"])]))
    return dict(schema_version="1.0.0",id="m6-voice-paradigm-projection",description="Source-inspired bounded onset control. Observation axes are two paradigm cells; this does not claim two daughter languages.",source_kind="synthetic",claim="bounded-relative-completeness",proto_inventory=["p","b"],allow_morphemes=False,max_length=1,
        analysis_bound=2,max_rules_per_branch=1,doculects=axis,choice_groups=[dict(id="voice-analysis",options=["N-anticausative","s-devoicing"],description="Whole derivational analyses, not independent choices for the two cells")],analyses=analyses,candidate_budget=100,time_limit_ms=None)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--check",action="store_true");a=p.parse_args()
    for name,obj in generate().items():
        path=DEST/name;data=encoded(obj)
        if a.check:assert path.read_bytes()==data,"Stale M6 experiment: "+name
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print("M6 transcription baselines, source fragments, joint morphology and 50 display alignments generated")


if __name__=="__main__":main()
