import Historical.Protolexicon

/-! Reflex-only requests and untrusted inverse-graph certificates. Parsing,
binding, topology and semantic checking all run in the native Lean process. -/
namespace Historical.LexiconInput
open Lean Rules Certificates RuleInput Reconstruction SearchGraph

deriving instance FromJson, ToJson for Inverse.State
deriving instance FromJson, ToJson for PrefixSearch.State
deriving instance FromJson, ToJson for Node

structure Language where
  id : String
  label : String
  deriving FromJson, ToJson
structure Reflex where
  language_id : String
  form : Option (List (Option String))
  source_ref : String
  deriving FromJson, ToJson
structure Entry where
  id : String
  meaning : String
  reflexes : List Reflex
  deriving FromJson, ToJson
structure Branch where
  language_id : String
  package : Package
  deriving FromJson, ToJson
structure Analysis where
  id : String
  description : String
  source_ref : String
  branches : List Branch
  deriving FromJson, ToJson
structure Request where
  schema_version : String
  id : String
  description : String
  languages : List Language
  proto_inventory : List String
  min_length : Nat
  max_length : Nat
  phonotactics : Option (List (List (List String)))
  analyses : List Analysis
  entries : List Entry
  deriving FromJson, ToJson

def alphabet (r : Request) : List Atom := r.proto_inventory.map Atom.segment
def shapes (r : Request) : Inverse.Shapes :=
  r.phonotactics.map (List.map (List.map (List.map Atom.segment)))
def mask (r : Reflex) : Inverse.Mask := r.form.map (List.map fun s => match s with
  | none => Cell.unknown "m7-unknown"
  | some "+" => Cell.boundary "+"
  | some a => Cell.segment a)
def masks (e : Entry) : List Inverse.Mask := e.reflexes.map mask
def root (r : Request) (e : Entry) : Inverse.State :=
  ⟨r.max_length, r.min_length, masks e, shapes r⟩
def tables (r : Request) (a : Analysis) : List Compile.Table :=
  a.branches.map fun b => Compile.compile b.package.laws (alphabet r)
def supported (a : Analysis) : Bool := a.branches.all fun b => Compile.supportedLaws b.package.laws

def validate (r : Request) : Except String Unit := do
  if r.schema_version != "1.0.0" || !goodId r.id || r.description.isEmpty then
    throw "REQUEST_METADATA: expected schema 1.0.0, stable ID and description"
  if r.proto_inventory.isEmpty || r.proto_inventory.length > 64 ||
      !unique r.proto_inventory || !(r.proto_inventory.all goodSymbol) then
    throw "PROTO_INVENTORY: supply 1–64 distinct atomic segments"
  if r.min_length > r.max_length || r.max_length > 64 then
    throw "WORD_BOUND: require 0 ≤ minimum ≤ maximum ≤ 64"
  let ids := r.languages.map (·.id)
  if ids.isEmpty || ids.length > 32 || !unique ids || !(ids.all goodId) ||
      !(r.languages.all fun l => !l.label.isEmpty) then
    throw "LANGUAGES: supply 1–32 distinct named daughter languages"
  if let some ps := r.phonotactics then
    if ps.length > 256 || !(ps.all fun p => p.length ≤ 64 &&
        p.all (validClass r.proto_inventory)) then throw "PHONOTACTICS: invalid slot templates"
  if r.analyses.isEmpty || r.analyses.length > 32 || !unique (r.analyses.map (·.id)) then
    throw "ANALYSES: supply 1–32 distinct global sound-law models"
  for a in r.analyses do
    if !goodId a.id || a.description.isEmpty || a.source_ref.isEmpty ||
        a.branches.map (·.language_id) != ids then
      throw "ANALYSIS_BINDING: every model must cover the ordered language columns"
    for b in a.branches do
      if b.package.inventory.length > 256 || b.package.laws.length > 128 ||
          !(validatePackage b.package).isEmpty ||
          !(r.proto_inventory.all b.package.inventory.contains) then
        throw s!"SOUND_LAWS: invalid or underspecified package {b.package.id}"
  if r.entries.isEmpty || r.entries.length > 10000 || !unique (r.entries.map (·.id)) then
    throw "ENTRIES: supply 1–10000 distinct cognate rows"
  for e in r.entries do
    if !goodId e.id || e.meaning.isEmpty || e.reflexes.map (·.language_id) != ids then
      throw "REFLEX_BINDING: every row must cover the ordered language columns; use null for missing"
    for f in e.reflexes do
      if f.source_ref.isEmpty then throw "PROVENANCE: every reflex needs a source reference"
      if let some cells := f.form then
        if cells.length > 64 || !(cells.all fun c => match c with
          | none => true
          | some s => s == "+" || goodSymbol s) then throw "REFLEX: invalid atomic segments"

def fitsReflexes : List Branch → List Reflex → Word → Bool
  | [], [], _ => true
  | b :: bs, f :: fs, w => formMatches (mask f) (run b.package.laws w) && fitsReflexes bs fs w
  | _, _, _ => false
def predicate (r : Request) (a : Analysis) (e : Entry) (w : Word) : Bool :=
  decide (r.min_length ≤ w.length) && Inverse.shapeFits (shapes r) w && fitsReflexes a.branches e.reflexes w
def wordFits (r : Request) (a : Analysis) (e : Entry) (w : Word) : Bool :=
  w.all (fun x => (alphabet r).contains x) && decide (w.length ≤ r.max_length) && predicate r a e w

theorem compiled_reflexes_correct (alphabet : List Atom) (bs : List Branch)
    (fs : List Reflex) (w : Word)
    (hs : bs.all (fun b => Compile.supportedLaws b.package.laws) = true)
    (hw : ∀ x ∈ w, x ∈ alphabet) :
    Inverse.fits (bs.map (fun b => Compile.compile b.package.laws alphabet)) (fs.map mask) w =
      fitsReflexes bs fs w := by
  induction bs generalizing fs with
  | nil => cases fs <;> rfl
  | cons b bs ih =>
    have hh : Compile.supportedLaws b.package.laws = true ∧
        bs.all (fun b => Compile.supportedLaws b.package.laws) = true := by simpa using hs
    cases fs with
    | nil => rfl
    | cons f fs =>
      simp only [List.map_cons, Inverse.fits, fitsReflexes]
      rw [Compile.compile_correct b.package.laws alphabet hh.1 w hw, ih fs hh.2]

/-- End-to-end language equivalence for a correctly bound compiled graph:
acceptance is exactly the original sound-law interpreter fitting the reflexes
and the selected protoform constraints. -/
theorem compiled_request_complete (r : Request) (a : Analysis) (e : Entry)
    (g : Graph Inverse.State) (i : Nat) (n : Node Inverse.State)
    (hs : supported a = true)
    (hg : faithful (alphabet r) (Inverse.step (tables r a)) (Inverse.finish (tables r a)) g = true)
    (hi : g[i]? = some n) (hr : n.state = root r e) (w : Word) :
    graphAccept (alphabet r) g i w = true ↔ wordFits r a e w = true := by
  rw [graph_correct _ _ _ _ hg i n hi, inverse_machine_correct, hr]
  by_cases hw : ∀ x ∈ w, x ∈ alphabet r
  · have hf := compiled_reflexes_correct (alphabet r) a.branches e.reflexes w hs hw
    change Inverse.fits (tables r a) (masks e) w = fitsReflexes a.branches e.reflexes w at hf
    have ha : w.all (fun x => (alphabet r).contains x) = true := by
      simpa only [List.all_eq_true, List.contains_iff] using hw
    constructor
    · intro h
      have hp := Bool.and_eq_true_iff.mp h.2
      have hb := Bool.and_eq_true_iff.mp hp.1
      have bounds : r.min_length ≤ w.length ∧ w.length ≤ r.max_length :=
        @of_decide_eq_true _ _ hb.1
      simp only [wordFits, predicate, Bool.and_eq_true]
      exact ⟨⟨ha, @decide_eq_true _ _ bounds.2⟩,
        ⟨⟨@decide_eq_true _ _ bounds.1, hp.2⟩, hf ▸ hb.2⟩⟩
    · intro h
      have hp := Bool.and_eq_true_iff.mp h
      have ht := Bool.and_eq_true_iff.mp hp.2
      have hm := Bool.and_eq_true_iff.mp ht.1
      have hmax := (Bool.and_eq_true_iff.mp hp.1).2
      have bounds : r.min_length ≤ w.length ∧ w.length ≤ r.max_length :=
        ⟨@of_decide_eq_true _ _ hm.1, @of_decide_eq_true _ _ hmax⟩
      exact ⟨hw, Bool.and_eq_true_iff.mpr
        ⟨Bool.and_eq_true_iff.mpr ⟨@decide_eq_true _ _ bounds, hf.symm ▸ ht.2⟩, hm.2⟩⟩
  · simp [wordFits, List.all_eq_true, hw]

theorem reference_request_complete (r : Request) (a : Analysis) (e : Entry)
    (g : Graph PrefixSearch.State) (i : Nat) (n : Node PrefixSearch.State)
    (hg : faithful (alphabet r) PrefixSearch.step (PrefixSearch.finish (predicate r a e)) g = true)
    (hi : g[i]? = some n) (hr : n.state = ⟨r.max_length, []⟩) (w : Word) :
    graphAccept (alphabet r) g i w = true ↔ wordFits r a e w = true := by
  rw [PrefixSearch.reference_graph_correct _ _ _ hg i n hi, hr]
  simp [wordFits, List.all_eq_true, and_assoc]

structure GraphData where
  nodes : Array Json
  deriving FromJson, ToJson, Inhabited
structure Binding where
  entry_id : String
  graph : Nat
  root : Nat
  deriving FromJson, ToJson
structure ModelGraph where
  analysis_id : String
  mode : String
  graphs : Array GraphData
  bindings : List Binding
  deriving FromJson, ToJson
structure Forest where
  request : Request
  models : List ModelGraph
  deriving FromJson, ToJson

def decodeGraph (σ : Type) [FromJson σ] [ToJson σ] (data : GraphData) : Except String (Graph σ) := do
  data.nodes.mapM fun j => do
    let n ← fromJson? (α := Node σ) j
    if j != toJson n then throw "GRAPH_SCHEMA: unknown or omitted fields"
    return n

/-- Counts are recomputed from the checked, deterministic acyclic graph; they
are not supplied by the proposer. The language-equivalence theorem is
SearchGraph.graph_correct. Cardinality arithmetic is separately regression tested. -/
def checkGraph [DecidableEq σ] (alphabet : List Atom) (transition : σ → Atom → Option σ)
    (terminal : σ → Bool) (g : Graph σ) : Except String (Array Nat) := do
  if !faithful alphabet transition terminal g then throw "GRAPH_SEMANTICS: transition or accepting state differs"
  let mut counts : Array Nat := #[]
  for i in [:g.size] do
    let some n := g[i]? | throw "GRAPH_INDEX: missing node"
    if !unique (n.edges.map (fun e => toJson e.1 |>.compress)) ||
        !(n.edges.all fun e => alphabet.contains e.1 && e.2 < i) then
      throw "GRAPH_TOPOLOGY: edges must be distinct alphabet labels pointing to earlier nodes"
    let count := n.edges.foldl (fun acc e => acc + counts[e.2]!) (if n.accepting then 1 else 0)
    counts := counts.push count
  return counts

def checkForest (f : Forest) : Except String Json := do
  let r := f.request
  validate r
  if f.models.map (·.analysis_id) != r.analyses.map (·.id) then
    throw "MODEL_COVERAGE: certificate must cover every selected model, in order"
  let nodes := f.models.foldl (fun n m => n + m.graphs.foldl (fun k g => k + g.nodes.size) 0) 0
  if nodes > 250000 then throw "GRAPH_BOUND: at most 250000 nodes"
  let mut results : List Json := []
  let mut total := 0
  for (a, m) in r.analyses.zip f.models do
    if m.bindings.map (·.entry_id) != r.entries.map (·.id) then
      throw "ENTRY_COVERAGE: certificate must cover every cognate row, in order"
    if m.graphs.isEmpty || m.graphs.size > r.entries.length ||
        !(m.bindings.all fun b => b.graph < m.graphs.size) then throw "GRAPH_BINDING: invalid graph index"
    let mut graphCounts : Array (Array Nat) := #[]
    if m.mode == "compiled" then
      if !supported a || m.graphs.size != 1 then throw "COMPILE_FRAGMENT: model is not supported by this compiler"
      let g ← decodeGraph Inverse.State m.graphs[0]!
      let ts := tables r a
      graphCounts := graphCounts.push (← checkGraph (alphabet r) (Inverse.step ts) (Inverse.finish ts) g)
      for (e, b) in r.entries.zip m.bindings do
        if (g[b.root]?.map (·.state)) != some (root r e) then throw "ROOT_BINDING: wrong residual state"
    else if m.mode == "reference" then
      for gi in [:m.graphs.size] do
        let rows := (r.entries.zip m.bindings).filter fun eb => eb.2.graph == gi
        let some first := rows.head? | throw "GRAPH_BINDING: unreferenced graph"
        if !(rows.all fun eb => masks eb.1 == masks first.1) then throw "GRAPH_BINDING: different observations share a reference trie"
        let g ← decodeGraph PrefixSearch.State m.graphs[gi]!
        graphCounts := graphCounts.push (← checkGraph (alphabet r) PrefixSearch.step
          (PrefixSearch.finish (predicate r a first.1)) g)
        for (_, b) in rows do
          if (g[b.root]?.map (·.state)) != some (PrefixSearch.State.mk r.max_length []) then
            throw "ROOT_BINDING: wrong reference state"
    else throw "GRAPH_MODE: expected compiled or reference"
    let mut count := 1
    let mut entries : List Json := []
    for b in m.bindings do
      let some cs := graphCounts[b.graph]? | throw "GRAPH_BINDING: missing graph"
      let some n := cs[b.root]? | throw "ROOT_BINDING: missing root"
      count := count * n
      entries := entries ++ [Json.mkObj [("entry_id", toJson b.entry_id), ("count", toJson (toString n))]]
    total := total + count
    results := results ++ [Json.mkObj [("analysis_id", toJson a.id), ("mode", toJson m.mode),
      ("lexicon_count", toJson (toString count)), ("entries", toJson entries)]]
  return Json.mkObj [("input_valid", toJson true), ("complete", toJson true),
    ("graph_checked", toJson true), ("nodes", toJson nodes),
    ("lexicon_count", toJson (toString total)), ("models", toJson results)]

structure Proposal where
  analysis_id : String
  entry_id : String
  word : Word
  deriving FromJson, ToJson
structure Proposals where
  request : Request
  proposals : List Proposal
  deriving FromJson, ToJson
structure Supplied where
  proposal : Proposal
  certificates : List Certificate
  deriving FromJson, ToJson
structure CertificatesInput where
  request : Request
  proposals : List Supplied
  deriving FromJson, ToJson

def context (r : Request) (p : Proposal) : Except String (Analysis × Entry) := do
  let some a := r.analyses.find? (fun a => a.id == p.analysis_id) | throw "PROPOSAL_MODEL: unknown model"
  let some e := r.entries.find? (fun e => e.id == p.entry_id) | throw "PROPOSAL_ENTRY: unknown row"
  return (a, e)
def certificate (b : Branch) (w : Word) : Certificate :=
  ⟨b.package.id, b.package.version, w, trace b.package.laws w, run b.package.laws w⟩
def checkSupplied (r : Request) (s : Supplied) : Except String Json := do
  let (a, e) ← context r s.proposal
  let accepted := wordFits r a e s.proposal.word && s.certificates.length == a.branches.length &&
    (a.branches.zip s.certificates).all fun bc =>
      bc.2.input == s.proposal.word && checkDossier ⟨"1.0.0", "m7-proposal", bc.1.package, bc.2⟩
  return Json.mkObj [("proposal", toJson s.proposal), ("accepted", toJson accepted),
    ("certificates", toJson s.certificates)]
def derive (p : Proposals) : Except String Json := do
  validate p.request
  if p.proposals.length > 10000 then throw "PROPOSAL_BOUND: at most 10000 words per batch"
  let results ← p.proposals.mapM fun x => do
    let (a, _) ← context p.request x
    checkSupplied p.request ⟨x, a.branches.map (fun b => certificate b x.word)⟩
  return Json.mkObj [("input_valid", toJson true), ("proposals", toJson results)]
def verifyProposals (p : CertificatesInput) : Except String Json := do
  validate p.request
  if p.proposals.length > 10000 then throw "PROPOSAL_BOUND: at most 10000 words per batch"
  return Json.mkObj [("input_valid", toJson true),
    ("proposals", toJson (← p.proposals.mapM (checkSupplied p.request)))]

end Historical.LexiconInput
