"""Encode thirty cross-branch comparisons with author-specific assumptions.

These are research dossiers, including rejected and unresolved comparisons.
They do not constitute thirty established Proto-Sino-Tibetan etymologies.
The forms below are manually transcribed lexical facts from the cited pages.
"""
import argparse
import hashlib
import json

from build_pie_corpus import ROOT, encoded

DEST=ROOT/"data/cross-branch"
SR="jacques-halshs-01287468"
WA="jacques-halshs-00408281"
TI="jacques2012-internal"
SB="sagart-hal-00781153"
SU="jacques-halshs-01566036"


def witness(doculect,branch,form,meaning,kind="source-transcription",node=None):
    return dict(doculect=doculect,branch=branch,form=form,meaning=meaning,
                representation=kind,reconstruction_node=node,chinese=None)


def chinese(graph,mc,oc,meaning,system):
    w=witness("Chinese as analysed in the cited paper","Sinitic",graph,meaning,"written-character")
    w["chinese"]=dict(written_character=graph,middle_chinese=mc,
        middle_chinese_status="source transcription, not a recording of historical speech",
        old_chinese=oc,old_chinese_status="source reconstruction" if oc else "not specified in this dossier",
        reconstruction_system=system,rhyme_and_phonetic_series=None,
        philological_scope="No independent collation of rhyme texts, phonetic series or manuscript witnesses. Those arguments must be checked in the cited paper and its references.")
    return w


def analysis(id,claim,assumptions,attribution="primary-paper",forms=None):
    return dict(id=id,claim=claim,assumptions=assumptions,attribution=attribution,linked_forms=forms or {})


def dossier(id,title,theme,source,pages,evidence,analyses,morphology,discriminate,limits,
            outcome="unresolved",kind="lexical-comparison",fragments=()):
    return dict(id=id,title=title,theme=theme,comparison_kind=kind,
        citations=[dict(source_id=source,pdf_pages=pages)],evidence=evidence,analyses=analyses,
        topology_assumptions=["unresolved-ST-polytomy","ST-with-TB-node"],
        topology_scope="The grouping of the cited branches is an assumption. A node named PTB in a source is not silently identified with PST or a subgroup ancestor.",
        morphology=morphology,discriminating_evidence=discriminate,non_discriminating_evidence=limits,
        outcome=outcome,formal_fragments=list(fragments),specialist_review="pending")


def dossiers():
    out=[]
    alternatives=[
        analysis("restricted-r-loss","Loss of r outside Chinese before a (possibly o), but not ə.",
                 ["The compared words are inherited","The vowel contrast predates the change"],"Jacques's proposed revision of Handel (2002)"),
        analysis("Chinese-r-infix","Chinese r is secondary in the s : sr comparisons.",
                 ["The unattested uninfixed Chinese bases existed"],"Jacques, drawing on Sagart and Baxter–Sagart"),
        analysis("OC-r-overreconstruction","Some Chinese r-clusters are reconstruction artefacts.",
                 ["Middle Chinese second division or retroflexion need not always reflect r"],"Jacques's third possibility")]
    out.append(dossier("sr-louse","Louse: Chinese sr, Tibetan palatal fricative and Kiranti s","sr",SR,[1,2,3],
        [chinese("蝨","ṣit","*srik","louse","Baxter–Sagart 2014, as cited by Jacques"),
         witness("Tibetan in Jacques's IPA transcription","Tibetic","ɕig","louse"),
         witness("Limbu","Kiranti","siʔ","louse")],
        [analysis("inherited-sr","The three branches support an inherited sr-cluster.",["The louse comparison is cognate"]),
         analysis("separate-syllables","Tibetan sr in other words may continue sə-r rather than sr.",["Presyllable vowels distinguish the inputs"])],
        "No productive Tibetan causative is inferred from the initial s.",
        ["Additional independently established sr : ɕ : s correspondences"],
        ["An onset match alone cannot establish every vowel and coda correspondence"],fragments=["sr-louse"]))
    out.append(dossier("sr-shame","Shame and the disputed Tibetan comparison","sr",SR,[2,4,5],
        [chinese("色","ṣik","*srək","colour; shame","Baxter–Sagart 2014, as cited by Jacques"),
         witness("Written Burmese","Burmish","hrak","shame","written-transliteration")],
        alternatives+[analysis("Tibetan-semantic-objection","The Tibetan confess comparison is weakened by the older meaning declare.",["The treaty inscription is relevant to the semantic history"])],
        "The Tibetan verbal comparison is not treated as an attested instance of a productive shame derivation.",
        ["The treaty inscription's use of the Tibetan verb", "Independent examples with original ə"],
        ["Modern confess and shame glosses alone do not establish cognacy"],fragments=["sr-shame"]))
    out.append(dossier("sr-root","Plant root and Chinese 參","sr",SR,[3,4,5],
        [chinese("參","ṣim","*srum / *srəm","medicinal rhizome","Baxter–Sagart 2014 / Schuessler 2009, as cited by Jacques"),
         witness("Kulung","Kiranti","sam","root"),
         witness("Proto-Kiranti in Jacques","Kiranti","*sam","root","source-reconstruction","jacques-sr:PKiranti"),
         witness("Japhug","Gyalrongic","tɤ-zrɤm","plant root")],
        [analysis("OC-u","Chinese is reconstructed with u.",["Baxter–Sagart's reading-specific reconstruction"],"Baxter–Sagart as reported by Jacques"),
         analysis("OC-schwa","Chinese ə gives the proposed cross-branch vowel correspondence.",["The medicinal plant meaning continues the root noun"],"Jacques, following Schuessler")]+alternatives,
        "Japhug tɤ- is the indefinite possessor prefix. The abstract lineage variant is treated as a possible Situ loan, not merged with the inherited noun.",
        ["Chinese loans or phonetic-series evidence distinguishing u and ə", "Inherited versus borrowed Japhug variants"],
        ["The Chinese evidence cited here does not choose between u and ə"],fragments=["sr-root"]))
    for id,graph,mc,oc,tib,gloss in [
        ("sr-kill","殺","ṣɛt","*srat","gsod, bsad","kill"),
        ("sr-sand","沙","ṣæ","*srˤaj","sa","sand / place"),
        ("sr-suck","欶","ṣæwk","*srˤok","sok","suck / drink")]:
        other=witness("Written Burmese" if id=="sr-suck" else "Written Tibetan","Burmish" if id=="sr-suck" else "Tibetic",tib,gloss,"written-transliteration")
        ev=[chinese(graph,mc,oc,gloss,"Baxter–Sagart 2014, as cited by Jacques"),other]
        if id=="sr-kill":ev.append(witness("Japhug","Gyalrongic","sat","kill"))
        out.append(dossier(id,gloss.capitalize()+": alternative origins of Chinese r","sr",SR,[4,5],ev,alternatives,
            "Chinese infixation is a competing historical analysis; Tibetan present and past belong to one paradigm." if id=="sr-kill" else "The Chinese r-infix hypothesis requires a lost base; the relevant morphology is not directly observed.",
            ["Chinese word-family evidence for infixation", "More examples establishing the vowel condition"],
            ["The small comparison set fits more than one historical account"],fragments=[id]))
    out.append(dossier("sr-nephew","Nephew and sister: cluster versus presyllable","sr",SR,[2,5],
        [chinese("甥",None,None,"sister's son","Jacques's discussion of Baxter–Sagart; only the initial sr is encoded"),
         witness("Tibetan in Jacques's transcription","Tibetic","sriŋ.mo","sister")],
        [analysis("presyllable","Retained Tibetan sr may reflect sə-r rather than the cluster sr.",["The kinship comparison is valid"]),
         analysis("unresolved-cluster","The correspondence need not yet determine a unique ancestral onset.",["A larger correspondence set is needed"])],
        "Tibetan -mo is retained in the evidence; it is not projected as part of the compared root onset.",
        ["Presyllable evidence and the vowel correspondence discussed under Dempsey's law"],
        ["A matching pair of written initial letters does not settle the proto-cluster"],fragments=["sr-presyllable"]))
    out.append(dossier("sr-pair-rejected","The rejected Chinese–Tibetan pair comparison","sr",SR,[4],
        [chinese("雙",None,None,"pair","Chinese r-cluster analysis discussed by Jacques"),
         witness("Written Tibetan","Tibetic","zung","pair","written-transliteration")],
        [analysis("surface-comparison","Compare Chinese pair with Tibetan zung.",["Similar meanings and surface forms"],"Coblin as reported by Jacques"),
         analysis("affricate-origin-objection","Tibetan z continues dz and invalidates the proposed sr comparison.",["The pre-Tibetan affricate-to-fricative change"])],
        "No morphology is supplied that would repair the initial correspondence.",
        ["Regular pre-Tibetan dz > z and the actual Chinese initial history"],
        ["Identical glosses do not repair an irregular correspondence"],outcome="rejected-in-primary-source"))
    for id,tib,bur,ps,m,meaning in [
        ("wa-tooth","so","swa³","*Gʷa (s-)","*-wa","tooth"),
        ("wa-handspan","mtho","thwa³","*Tua","*-wa","handspan"),
        ("wa-fat","tsho","chu²","*chāw","*-ow","fat"),
        ("wa-corpse","ro","raw²","*rɨ̄w(H)","*-aw","corpse / withered"),
        ("wa-pleased","spro","pyau²","*phrɨw","*-o","be pleased")]:
        out.append(dossier(id,meaning.capitalize()+": more than one origin of Tibetan o","wa-fusion",WA,[2,3,4],
            [witness("Old Tibetan as cited","Tibetic",tib,meaning,"written-transliteration"),
             witness("Burmese as cited in Table 1","Burmish",bur,meaning,"written-transliteration")],
            [analysis("Peiros-Starostin","Source etymon: "+ps,["The source's rhyme and prefix analysis"],"Peiros–Starostin 1996 as reported by Jacques",{"etymon":ps}),
             analysis("Matisoff","Source rhyme: "+m,["The source's rhyme reconstruction"],"Matisoff 2003 as reported by Jacques",{"rhyme":m}),
             analysis("late-nominal-fusion","Some Tibetan wa is younger than wa > o, from u + ba.",["Nominal fusion occurred after Laufer's law"],"Jacques 2009",{"horn":["*ru-ba","*rua","rwa"],"angle":["*gru-ba","*grua","grwa"],"hat":["*zyu-ba","*zyua","zhwa"]})],
            "Prefixes and suffixes belong to the complete source analysis. The horn/angle/hat doublets are internal Tibetan controls, not extra cross-branch etyma.",
            ["Burmese rhymes distinguish several sources of Tibetan o", "Old Tibetan doublets and the restriction of fusion to early nominal formations"],
            ["Modern Tibetan o alone cannot select a unique proto-rhyme", "Later yu-ba and verbal zhu-ba do not license unrestricted fusion"],
            fragments=[id] if id in {"wa-tooth","wa-handspan"} else []))
    out.append(dossier("tib-bridge","Bridge and loss of prenasalization","tibetan-morphophonology",TI,[2,3,4,5],
        [witness("Written Tibetan","Tibetic","zam","bridge","written-transliteration"),witness("Japhug","Gyalrongic","ndzom","bridge")],
        [analysis("nasal-attrition","ndzam > dzam > zam in pre-Tibetan.",["Japhug prenasalization is conservative"],forms={"pre-Tibetan":["*ndzam","*dzam","zam"]}),
         analysis("plain-affricate","The last Tibetan change alone only establishes dzam > zam.",["The earlier nasal requires comparative evidence"],forms={"pre-Tibetan":["*dzam","zam"]})],
        "The initial nasal's lexical origin is not identified solely by the word for bridge.",
        ["The Japhug prenasalized cognate and the wider voiced/prenasalized correspondence"],
        ["Tibetan zam alone cannot distinguish dzam from earlier ndzam"],fragments=["tib-bridge"]))
    out.append(dossier("tib-poison","Poison and the proposed nasal attrition cycle","tibetan-morphophonology",TI,[4,5],
        [witness("Written Tibetan","Tibetic","dug","poison","written-transliteration"),witness("Japhug","Gyalrongic","tɤ-ndɤɣ","poison")],
        [analysis("nasal-loss","Pre-Tibetan ndug loses prenasalization.",["The prenasalized Japhug form preserves the older onset"]),
         analysis("unresolved-nasal-origin","The pair does not by itself establish the age or morphological function of every nasal.",["Lexical and grammatical nasals must be distinguished"])],
        "Japhug tɤ- is a nominal prefix; neither it nor the nasal is silently identified with the Tibetan present prefix.",
        ["Additional cognates and the phonology of the nasal attrition cycle"],
        ["Two similar nouns alone do not recover the whole prefix system"],fragments=["tib-poison"]))
    out.append(dossier("tib-eagle","Eagle and merged presyllable contrasts","tibetan-morphophonology",TI,[2,3],
        [witness("Written Tibetan","Tibetic","glag","eagle","written-transliteration"),witness("Japhug","Gyalrongic","qaliaʁ","eagle")],
        [analysis("velar-presyllable","Reconstruct a velar presyllable in pre-Tibetan.",["Its vowel is not recoverable from Tibetan alone"],forms={"pre-Tibetan":"*gV-lak"}),
         analysis("dental-presyllable","A dental presyllable has the same Tibetan outcome.",["Dental/velar preinitials merge conditionally"],forms={"pre-Tibetan":"*dV-lak"})],
        "A lost nominal presyllable is distinguished from a productive verbal TAM prefix.",
        ["Other branches preserving presyllable vowels and uvular/velar contrasts"],
        ["Tibetan g- alone cannot recover the lost dental/velar or vowel contrast"],fragments=["tib-eagle"]))
    out.append(dossier("tib-eat","Eat: lexical affricate history and an irregular paradigm","tibetan-morphophonology",TI,[1,2,3],
        [witness("Written Tibetan","Tibetic","za; zos","eat: present; past","written-transliteration"),witness("Japhug","Gyalrongic","ndza","eat"),
         witness("Proto-Lolo-Burmese as cited","Lolo-Burmese","*dza²","eat","source-reconstruction","bradley-1979:PLB")],
        [analysis("affricate-origin","Tibetan z reflects dz.",["The comparative affricate correspondence"]),
         analysis("old-agreement","The irregular a/o alternation may preserve agreement morphology.",["The analysis attributed to Jacques 2010 applies"],"Jacques 2010 as reported by Jacques 2012")],
        "Present za and past zos are linked cells. Recovering the onset does not explain the past stem or prove the agreement analysis.",
        ["Comparative paradigm morphology and historical uses of both stems"],
        ["The initial correspondence does not distinguish proposed sources of the irregular vowel alternation"],fragments=["tib-eat"]))
    out.append(dossier("tib-kill-paradigm","Kill: Tibetan TAM prefixes and Japhug directional prefixes","tibetan-morphophonology",TI,[7,8,9,10,11],
        [witness("Written Tibetan","Tibetic","gsod; bsad; gsad; sod","kill: present; past; future; imperative","written-transliteration"),
         witness("Japhug","Gyalrongic","ku-sat; pɯ-a-sat","kill: present; aorist")],
        [analysis("directional-origin","Tibetan alternations could derive from directional prefixes.",["Go/Do causes rounding; BV marks the past"],forms={"present":["*Go-sat","*Do-sat"],"past":["*BV-sat-s"]}),
         analysis("independent-innovation","The similar Tibetan and Japhug prefixes may have arisen independently.",["Directional TAM systems can develop through contact","Japhug down differs from other Gyalrongic languages"]),
         analysis("labiovelar-rounding","A labiovelar prefix rather than an o vowel could cause rounding.",["Coblin's alternative sound history"],"Coblin 1976 as reported by Jacques")],
        "The four Tibetan cells form one paradigm. Go/Do and BV alternatives must be chosen as whole analyses, not segment by segment. The Japhug aorist a is a transitive direct marker.",
        ["Other Gyalrongic directional forms", "Tibetan dialect and textual paradigms", "Independent evidence for the vowel of the lost prefix"],
        ["The two similar-looking prefix pairs do not establish inherited PST verbal morphology"],fragments=["tib-kill-paradigm"]))
    out.append(dossier("prefix-black","Black, ink and the function of a proposed s-prefix","oc-prefixes",SB,[6,7,8],
        [chinese("黑; 墨",None,"*m̥ˤək; *C.mˤək","black; ink","Sagart–Baxter 2012"),
         witness("Written Tibetan","Tibetic","smag","dark","written-transliteration")],
        [analysis("denominal-s","Black is derived from the nominal root ink with s-.",["Ink is the unaffixed noun"],"Mei 2010 as discussed by Sagart–Baxter"),
         analysis("voiceless-nasal","OC black has a voiceless nasal; the prefix/function remain uncertain.",["The early Tai loan points to an additional consonant in ink"],"Sagart–Baxter")],
        "The direction noun > adjective is disputed; a Tibetan s-cluster does not establish a Chinese denominal prefix.",
        ["Early loans and Chinese-internal evidence for the preinitial in ink"],
        ["The Tibetan cluster alone cannot date a Chinese s-prefix"] ))
    out.append(dossier("prefix-loose","Loose, escape and the Burmese causative","oc-prefixes",SB,[8],
        [chinese("脫; 悅","thwat; ywet","*l̥ˤot; *lot","escape; pleased","Sagart–Baxter 2012"),
         witness("Written Burmese","Burmish","lwat; hluat","be free; set free","written-transliteration")],
        [analysis("Chinese-causative","Treat the Chinese initial as a causative s-cluster.",["The semantics are causative"],"Mei as reported by Sagart–Baxter"),
         analysis("semantic-objection","Burmese has a clear causative; the Chinese meanings do not establish the same derivation.",["Escape is not automatically a causative of loose"],"Sagart–Baxter")],
        "The Burmese pair is one linked intransitive/causative paradigm; it is not copied into Chinese by assumption.",
        ["Actual argument structure in Chinese texts", "Chinese-internal evidence for the initial"],
        ["A Burmese s-causative does not prove an identical affix in the compared Chinese word"] ))
    out.append(dossier("prefix-nose","Nose, breathing and Chinese voiceless nasals","oc-prefixes",SB,[19],
        [chinese("嘆; 歎","than","*n̥ˤar","sigh","Sagart–Baxter 2012"),
         witness("Proto-Northern-Chin in Button as cited","Kuki-Chin","*ʰnarᴵ; *ʰnarᴵᴵᴵ","nose; breathe, snore","source-reconstruction","button-2009:PNC"),
         witness("Proto-Tibeto-Burman in Matisoff as cited","Tibeto-Burman-assumed","*s-naːr","nose","source-reconstruction","matisoff-2003:PTB")],
        [analysis("early-tight-cluster","A tight s-n cluster may underlie the voiceless nasal before OC.",["The hypothetical pre-OC scheme holds"],"Sagart–Baxter hypothetical scheme"),
         analysis("OC-voiceless-nasal","At the OC stage reconstruct the voiceless nasal without importing a TB prefix.",["No Chinese-internal s evidence for this word"],"Sagart–Baxter")],
        "Button's tone categories distinguish the noun and verb. They are not phonetic pitch values or VanBik's proto-tone labels.",
        ["Evidence dating the loss of s relative to the OC stage"],
        ["A possible pre-OC cluster and an OC voiceless nasal are compatible at different dates"],fragments=["prefix-nose"]))
    out.append(dossier("prefix-fly","Fly and the limits of projecting a nasal to PTB or PST","oc-prefixes",SB,[27,28],
        [chinese("飛","pj+j","*Cə.pər","fly","Sagart–Baxter 2012"),
         witness("Written Tibetan in the discussion","Tibetic","N-phur","fly","written-transliteration"),
         witness("Naxi as cited","Naic","mbi","fly")],
        [analysis("inherited-nasal","Project a nasal from Tibetan and Naxi to PTB and PST.",["The two verbs and their prefixes are cognate"],"Mei as reported by Sagart–Baxter"),
         analysis("scope-objection","Neither prefix identity nor obligatory attachment at the family ancestor follows.",["Tibetan inflection need not be the OC intransitive prefix","The Naxi root may be a different etymon"],"Sagart–Baxter")],
        "A present prefix, an intransitive prefix and a lexical prenasalized onset are distinct hypotheses.",
        ["Naxi etymology", "Min evidence for a minor syllable", "Distribution and function of nasal morphology"],
        ["A hypothetical binary tree alone cannot promote a prefix from two daughter forms to every ancestral cell"] ))
    out.append(dossier("prefix-nine","Nine: alternative preinitials and ancestral scope","oc-prefixes",SB,[28],
        [chinese("九","kjuwX","*kuʔ / *tə.kuʔ","nine","Sagart–Baxter 2012"),
         witness("Written Tibetan","Tibetic","dgu","nine","written-transliteration"),
         witness("PTB in Benedict as reported","Tibeto-Burman-assumed","*d-kuw","nine","source-reconstruction","benedict-1972:PTB")],
        [analysis("PTB-nasal-alternation","Project N-kuw beside d-kuw to PTB and PST.",["Eastern nasal forms are inherited at both nodes"],"Mei as reported by Sagart–Baxter"),
         analysis("local-nasal","Nasal preinitials may be an eastern innovation; OC may lack them.",["Distribution of the nasal is restricted"],"Sagart–Baxter",{"OC":["*kuʔ","*tə.kuʔ"]})],
        "The dental minor syllable and nasal preinitial are alternatives, not interchangeable phonetic spellings.",
        ["Distribution of nasal forms", "Oracle-bone use of the elbow graph for nine"],
        ["Tibetan dgu alone cannot establish a PST nasal"] ))
    out.append(dossier("prefix-separate","Separate: competing directions of voice derivation","oc-prefixes",SB,[28,29],
        [chinese("別","pjet; bjet","*pret; *N-pret","separate; be separated","Sagart–Baxter 2012"),
         witness("Written Burmese","Burmish","phrat; prat","cut; be cut","written-transliteration"),
         witness("Japhug","Gyalrongic","prɤt; mbrɤt","cut; be cut")],
        [analysis("s-devoicing","Derive the transitive from a voiced intransitive with s-.",["The voiced member is basic"],"Mei/Matisoff account as reported by Sagart–Baxter",{"Chinese":["*brjat","*s-brjat"]}),
         analysis("N-anticausative","Derive the intransitive from a voiceless transitive with N-.",["Japhug anticausative morphology informs the comparison"],"Sagart–Baxter",{"Chinese":["*pret","*N-pret"]})],
        "Transitive and intransitive members are linked. A mixed pair from the two analyses is not a third source analysis.",
        ["Japhug derivational productivity", "Early loans showing nasality on the intransitive member", "Chinese-internal voicing evidence"],
        ["A p/b alternation by itself does not establish derivational direction"],fragments=["prefix-separate"]))
    out.append(dossier("suffix-weave","Weave and textile: nominalization and departing tone","oc-suffixes",SU,[5,6],
        [chinese("織","tɕik; tɕiH",None,"weave; cloth","Jacques's IPA adaptation of Baxter MC; OC -s hypothesis"),
         witness("Tibetan in Jacques's transcription","Tibetic","ɴtʰag, btags; tʰags","weave: present, past; textile")],
        [analysis("s-nominalizer","Compare Chinese departing-tone nominalization and Tibetan nominal s.",["The lexical roots are cognate"]),
         analysis("multiple-sources","The ending of every Chinese departing-tone word need not be the same morpheme.",["Coda mergers and other suffixes must be considered"])],
        "The Tibetan past s and nominal s are recorded in separate cells; shared letters alone do not identify them.",
        ["Lexical correspondence plus matched derivational function", "Historical readings in Chinese"],
        ["Departing tone by itself does not identify a nominalizer rather than another suffix"],fragments=["suffix-coda"]))
    out.append(dossier("suffix-bring","Come and bring: the applicative t suffix","oc-suffixes",SU,[6,7],
        [witness("Japhug","Gyalrongic","ɣi; ɣɯt","come; bring"),witness("Khaling abstract verb roots","Kiranti","|pi|; |pit|","come; bring")],
        [analysis("inherited-t","The motion verb pair supports an old applicative t.",["Root and derivational function are cognate"],forms={"Japhug":["*wi","*wit"],"Khaling":["|pi|","|pit|"]}),
         analysis("Chinese-extension","Some Chinese s may reflect t after codas and subsequent analogical extension.",["The proposed t > s change and analogy apply"])],
        "Applicative and causative are kept distinct; Limbu has separate s-causative and t-applicative morphology.",
        ["Kiranti distinctions and matching Gyalrongic roots", "Chinese evidence for final clusters"],
        ["The come/bring pair alone does not prove the origin of all Chinese departing tones"],fragments=["suffix-coda"]))
    out.append(dossier("suffix-lie","Lie down, rest and the exceptional Chinese t reading","oc-suffixes",SU,[7],
        [chinese("尼","ɳij; ɳit","*n<r>ɨl; *n<r>əl-t","rest; stop someone","Jacques modifies Baxter–Sagart's final r to l"),
         witness("Tibetan in Jacques's transcription","Tibetic","ɲal","lie down; sleep"),witness("Japhug","Gyalrongic","nɯna","rest")],
        [analysis("applicative-t","The fanqie reading with final t is a direct applicative trace.",["The cited reading is correctly identified"]),
         analysis("coda-r-or-l","Final l is an explicit amendment to the Baxter–Sagart system.",["Tibetan l comparisons and cluster restrictions support it"],"Jacques's proposal versus Baxter–Sagart")],
        "The proposed t > s change does not apply after l. Analogy is a separate explanation where s nevertheless occurs.",
        ["The fanqie 女乙反 versus 女夷切", "The original textual context and its argument structure"],
        ["An undifferentiated departing-tone label would erase the relevant final-t evidence"],fragments=["suffix-l-control"]))
    out.append(dossier("suffix-remember","Remember and think: a comparison of middle derivation","oc-suffixes",SU,[8,9,10],
        [chinese("憶; 意","ʔik; ʔiH",None,"remember; think","Jacques's MC transcription; OC suffix hypothesis"),
         witness("Khaling abstract verb roots","Kiranti","|mimt|; |mimt-si|","remember; think that")],
        [analysis("middle-si","Chinese s may continue syllabic si with middle functions.",["The derivations, not the different lexical roots, are compared"]),
         analysis("functional-parallel","The shared function is compatible with inheritance but does not prove it.",["Independent grammatical developments remain possible"])],
        "The two lexical roots are explicitly different. The Tibetan kak-si > khegs proposal is another hypothesis, not an attested preform.",
        ["Distribution and syntax of the middle derivation", "Evidence for loss of suffix vowels"],
        ["Identical meanings of derivations do not establish lexical cognacy"],kind="morphological-comparison",fragments=["suffix-middle"]))
    out.append(dossier("suffix-hoe","Hoe: a noun and a denominal t verb","oc-suffixes",SU,[11],
        [witness("Khaling abstract verb root","Kiranti","|kakt|","hoe (verb)"),witness("Japhug","Gyalrongic","qaʁ","hoe (noun)")],
        [analysis("denominal-t","Khaling retains a denominal t added to the inherited noun root.",["The nominal and verbal roots are cognate"]),
         analysis("Chinese-t-to-s","This type of t derivation may be relevant to Chinese departing-tone denominals.",["A corresponding Chinese root and the proposed sound change would need evidence"])],
        "No Chinese lexical cognate is supplied here. The cited Limbu comparison has unexplained initial voicing and is not used as confirmation.",
        ["Nominal cognates and productive t morphology in Kiranti"],
        ["The pair does not establish a specific Chinese etymology"],fragments=["suffix-coda"]))
    out.append(dossier("suffix-adverb","Adverbialization and a possible locative s","oc-suffixes",SU,[3,11,12,13],
        [chinese("三","sam; samH",None,"three; thrice","Jacques's MC transcription; OC suffix hypothesis"),
         witness("Written Tibetan","Tibetic","yas; -las; -nas","from above; ablative; elative","written-transliteration"),
         witness("Japhug","Gyalrongic","zɯ","locative clitic")],
        [analysis("locative-origin","Some Chinese adverbial s may come from a locative used in subordination.",["The clausal-linker-to-adverbializer development occurred"]),
         analysis("distinct-suffixes","The adverbial, middle and nominal uses need not descend from one suffix.",["Formal mergers can conceal distinct morphological sources"])],
        "This dossier compares grammatical functions and morphemes, not the numeral three with the Tibetan words.",
        ["Early Chinese distribution and readings", "Gyalrongic and Tibetan locative constructions"],
        ["A final s or departing tone alone does not select the morphological source"],kind="morphological-comparison"))
    assert len(out)==30 and len({d["id"] for d in out})==30
    return out


def generate():
    ds=dossiers();ids=[SR,WA,TI,SB,SU,"vanbik2009","button2011"]
    bibliography={s["id"]:s for s in json.loads((ROOT/"bibliography/sources.json").read_text())}
    downloads={s["id"]:s for s in json.loads((ROOT/"bibliography/downloads.json").read_text())}
    sources=[]
    for id in ids:
        b=bibliography[id];d=downloads[id]
        local=ROOT/d["path"]
        if local.exists():assert hashlib.sha256(local.read_bytes()).hexdigest()==d["sha256"]
        pages=sorted({n for item in ds for c in item["citations"] if c["source_id"]==id for n in c["pdf_pages"]})
        if id=="vanbik2009":pages=[25,26,29,30,37,38,46,51,67,68,69,70,71,79,80,81,85,86,90,91,92,93]
        if id=="button2011":pages=[11,15,16,17,19,31,35,37,39]
        sources.append(dict(id=id,title=b["title"],catalogue_year=b["year"],url=b["pdf_url"],pdf_sha256=d["sha256"],
            pdf_pages=d["pages"],pages_examined=pages,
            reading_scope="Selected arguments, tables and examples listed here; no claim of reading every cited secondary work.",
            transcription_method="Manual lexical transcription checked against PDF text and, for broken font encodings, rendered pages; independent specialist review pending."))
    nodes=[
        dict(id="vanbik-2009-PKC",source="vanbik2009",label="Proto-Kuki-Chin",scope=["Peripheral","Central","Maraic"],locator="printed pp. 18, 23, 58"),
        dict(id="vanbik-2009-PCC",source="vanbik2009",label="Proto-Central-Chin",scope=["Laamtuk Thet","Lai","Mizo"],locator="printed pp. 39–50"),
        dict(id="vanbik-2009-PNC",source="vanbik2009",label="Proto-Northern-Chin",scope=["Northern Zo group"],locator="printed pp. 25–31"),
        dict(id="vanbik-2009-PM",source="vanbik2009",label="Proto-Maraic",scope=["Mara","Zotung","Senthang"],locator="printed pp. 51–54"),
        dict(id="button-2011-PNC",source="button2011",label="Proto Northern Chin",scope=["Mizo","Zahau","Thado","Zo","Tedim","Sizang"],locator="printed pp. 11–14, 27"),
        dict(id="PST-unspecified",source=None,label="Proto-Sino-Tibetan",scope=["family ancestor under the chosen topology"],locator=None),
        dict(id="PTB-assumed",source=None,label="Proto-Tibeto-Burman",scope=["non-Sinitic branches only if their common exclusive node is assumed"],locator=None)]
    topo=[dict(id="unresolved-ST-polytomy",kind="sensitivity-assumption",edges=[["PST-unspecified",b] for b in ["Sinitic","Tibetic","Gyalrongic","Kiranti","Burmish","Naic","Kuki-Chin"]],
               interpretation="Withhold a non-Sinitic clade; equal branch predictions alone cannot resolve topology."),
          dict(id="ST-with-TB-node",kind="sensitivity-assumption",edges=[["PST-unspecified","Sinitic"],["PST-unspecified","PTB-assumed"]]+[["PTB-assumed",b] for b in ["Tibetic","Gyalrongic","Kiranti","Burmish","Naic","Kuki-Chin"]],
               interpretation="A shared non-Sinitic change can be assigned to one edge only conditionally on this topology and on its inheritance." )]
    result=dict(schema_version="1.0.0",id="m6-cross-branch-v1",sources=sources,dossiers=ds,
                scope="30 source-backed comparisons, including morphological comparisons and rejected etymologies; no family-wide wordlist or settled PST reconstruction.")
    scoping=dict(schema_version="1.0.0",nodes=nodes,topologies=topo,
        identity_policy="Source-qualified nodes are distinct. Similar names and overlapping language coverage do not authorize a cast between reconstructions.",
        doculect_identity="VanBik's Falam Lai is also called Zahao in his abbreviation list. Button's Zahau remains a separate source dataset; no row-level identity is assumed.",
        tone_conventions=[dict(source="vanbik2009",locator="printed p. 9 n. 6 and chapter 6",description="Pitch diacritics in reflexes; numeral markers for Tedim. H. Lai checked-syllable tones are predictable and unmarked. No chapter-6 proto-tone is inferred from an untoned chapter-4 entry."),
            dict(source="button2011",locator="printed p. 27 and n. 33",description="Tone categories I, II, III; II splits into IIA/IIB in Mizo and Zahau. These are correspondence categories, not universal pitches. Button inverts Luce's II/III labels.")])
    return {"dossiers.json":result,"source-scopes.json":scoping}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--check",action="store_true");a=p.parse_args()
    DEST.mkdir(parents=True,exist_ok=True)
    for name,obj in generate().items():
        path=DEST/name;data=encoded(obj)
        if a.check:assert path.read_bytes()==data,"Source dossier changed: "+name
        else:
            if path.exists() and path.read_bytes()!=data:raise ValueError("Version the frozen source dossiers before changing them: "+name)
            path.write_bytes(data)
    print("30 cross-branch source dossiers; reconstruction levels and unresolved analyses retained")


if __name__=="__main__":main()
