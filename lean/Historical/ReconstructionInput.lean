import Historical.Identifiability
import Historical.CorrespondenceInput

namespace Historical.ReconstructionInput
open Lean Rules Certificates Reconstruction

structure BranchInput where
  doculect_id : String
  package : RuleInput.Package
  deriving FromJson, ToJson, Repr

def BranchInput.core (b : BranchInput) : Reconstruction.Branch := ⟨b.doculect_id, b.package.laws⟩

structure ObservationInput where
  doculect_id : String
  source_ref : String
  form : Option (List Cell)
  deriving FromJson, ToJson, Repr, DecidableEq

def ObservationInput.core (o : ObservationInput) : Reconstruction.Observation := ⟨o.doculect_id, o.form⟩

def observationFromRow (r : CorrespondenceInput.RowEntry) : ObservationInput :=
  ⟨r.doculect_id, r.source_ref, r.original⟩

theorem m3_projection_recovers (d : CorrespondenceInput.AlignmentData)
    (h : CorrespondenceInput.dataAccepted d = true) (a : CorrespondenceInput.AlignmentEntry)
    (ha : a ∈ d.alignments) (r : CorrespondenceInput.RowEntry) (hr : r ∈ a.rows) :
    (observationFromRow r).form = Alignment.recover r.aligned :=
  (CorrespondenceInput.accepted_data_recovers_row d h a ha r hr).symm

structure AlignmentEvidence where
  dossier : CorrespondenceInput.CorrespondenceDossier
  alignment_id : String
  deriving FromJson, ToJson, Repr

structure AnalysisInput where
  id : String
  description : String
  proto_node_id : String
  choice_bindings : List Binding
  branches : List BranchInput
  observations : List ObservationInput
  alignment_evidence : Option AlignmentEvidence
  deriving FromJson, ToJson, Repr

def AnalysisInput.core (a : AnalysisInput) : Scenario :=
  ⟨a.id, a.branches.map BranchInput.core, a.observations.map ObservationInput.core⟩

structure Spec where
  schema_version : String
  id : String
  description : String
  source_kind : String
  claim : String
  proto_inventory : List String
  allow_morphemes : Bool
  max_length : Nat
  analysis_bound : Nat
  max_rules_per_branch : Nat
  doculects : List String
  choice_groups : List ChoiceGroup
  analyses : List AnalysisInput
  candidate_budget : Nat
  time_limit_ms : Option Nat
  deriving FromJson, ToJson, Repr

def Spec.alphabet (d : Spec) : List Atom :=
  d.proto_inventory.map Atom.segment ++ if d.allow_morphemes then [.morpheme] else []

def Spec.scenarios (d : Spec) : List Scenario := d.analyses.map AnalysisInput.core

def rawUpperBound (d : Spec) : Nat := d.analyses.length * wordCount d.alphabet.length d.max_length

def maxRawHypotheses : Nat := 20000

def validateSpec (d : Spec) : List Issue := Id.run do
  let mut issues : List Issue := []
  let add := fun code path message => Issue.mk code path message
  if d.schema_version != "1.0.0" then
    issues := issues ++ [add "SCHEMA_VERSION" "schema_version" "Expected bounded-reconstruction schema 1.0.0"]
  if !goodId d.id || d.description.isEmpty || !(["synthetic", "sourced"].contains d.source_kind) then
    issues := issues ++ [add "QUERY_METADATA" "query" "Valid ID, description and explicit source kind required"]
  if d.claim != "bounded-relative-completeness" then
    issues := issues ++ [add "UNSUPPORTED_CLAIM" "claim" "Only bounded-relative-completeness is supported"]
  if !unique d.proto_inventory || !(d.proto_inventory.all RuleInput.goodSymbol) then
    issues := issues ++ [add "PROTO_INVENTORY" "proto_inventory" "Proto segments must be distinct atomic symbols"]
  if d.proto_inventory.length > 15 || d.max_length > 16 || d.analysis_bound > 16 ||
      d.max_rules_per_branch > 16 || d.doculects.length > 8 || d.candidate_budget > maxRawHypotheses ||
      (d.time_limit_ms.any (fun n => n > 60000)) then
    issues := issues ++ [add "PROFILE_LIMIT" "query" "Executable profile limits: 15 segments, length 16, 16 analyses, 16 rules/branch, 8 doculects, 20000 evaluations, 60000 ms"]
  if d.doculects.length < 2 || !unique d.doculects || !(d.doculects.all goodId) then
    issues := issues ++ [add "DOCULECT_AXIS" "doculects" "At least two distinct valid doculect IDs are required"]
  if d.analyses.isEmpty || d.analyses.length > d.analysis_bound ||
      !unique (d.analyses.map (·.id)) then
    issues := issues ++ [add "ANALYSIS_SPACE" "analyses" "Nonempty finite list of distinct analyses must fit the declared bound"]
  if !unique (d.choice_groups.map (·.id)) then
    issues := issues ++ [add "CHOICE_GROUP" "choice_groups" "Choice group IDs must be distinct"]
  for g in d.choice_groups do
    if !goodId g.id || g.description.isEmpty || g.options.isEmpty || !unique g.options || !(g.options.all goodId) then
      issues := issues ++ [add "CHOICE_GROUP" g.id "Every choice group requires valid distinct options and a description"]
  let packages := d.analyses.flatMap (fun a => a.branches.map (·.package))
  for p in packages do
    if packages.any (fun q => p.id == q.id && p.version == q.version && toJson p != toJson q) then
      issues := issues ++ [add "PACKAGE_COLLISION" p.id "A package ID/version cannot denote different definitions"]
  for a in d.analyses do
    if !goodId a.id || a.description.isEmpty || !goodId a.proto_node_id then
      issues := issues ++ [add "ANALYSIS_METADATA" a.id "Every analysis needs a valid ID, proto node and description"]
    if a.branches.map (·.doculect_id) != d.doculects || a.observations.map (·.doculect_id) != d.doculects then
      issues := issues ++ [add "DOCULECT_AXIS" a.id "Each joint analysis must contain the complete ordered branch and observation axes"]
    if a.choice_bindings.map (·.group_id) != d.choice_groups.map (·.id) then
      issues := issues ++ [add "JOINT_BINDINGS" a.id "Each analysis explicitly binds every declared choice group exactly once in declaration order"]
    for binding in a.choice_bindings do
      if !(d.choice_groups.any fun g => g.id == binding.group_id && g.options.contains binding.option_id) then
        issues := issues ++ [add "JOINT_BINDINGS" a.id "Unknown choice group or option"]
    for b in a.branches do
      issues := issues ++ (RuleInput.validatePackage b.package).map (fun i => {i with path := a.id ++ ":" ++ b.doculect_id ++ ":" ++ i.path})
      if b.package.initial_stage != a.proto_node_id then
        issues := issues ++ [add "PROTO_STAGE" a.id "Each branch starts at this analysis's declared proto node"]
      if b.package.laws.length > d.max_rules_per_branch then
        issues := issues ++ [add "RULE_BOUND" a.id "Branch exceeds the declared rule-count bound"]
      if !(d.proto_inventory.all b.package.inventory.contains) then
        issues := issues ++ [add "PROTO_PACKAGE_INVENTORY" a.id "Every branch package must include the proto inventory"]
    for o in a.observations do
      if o.source_ref.isEmpty then
        issues := issues ++ [add "SOURCE_REF" a.id "Every observation, including absence, needs a source reference"]
      if !Alignment.originalShape o.form || !((o.form.getD []).all CorrespondenceInput.goodCell) then
        issues := issues ++ [add "OBSERVATION_SHAPE" a.id "Original forms cannot contain gaps/missing cells, malformed boundaries or invalid symbols"]
      if let some b := a.branches.find? (fun b => b.doculect_id == o.doculect_id) then
        if !((o.form.getD []).all fun c => match c with
            | .segment s => b.package.inventory.contains s
            | _ => true) then
          issues := issues ++ [add "OBSERVATION_INVENTORY" a.id "Known observed segments must occur in the branch inventory"]
    if let some source := a.alignment_evidence then
      if !CorrespondenceInput.dossierAccepted source.dossier then
        issues := issues ++ [add "M3_CERTIFICATE" a.id "The attached correspondence dossier must pass M3"]
      match source.dossier.alignment_data.alignments.find? (fun x => x.id == source.alignment_id) with
      | none => issues := issues ++ [add "M3_ALIGNMENT" a.id "Unknown target alignment"]
      | some alignment =>
          if a.observations != alignment.rows.map observationFromRow then
            issues := issues ++ [add "M3_OBSERVATIONS" a.id "Observations must exactly match the selected M3 original rows and source references"]
  return issues

def checkedReconstruct (d : Spec) : Option (List Candidate) :=
  if (validateSpec d).isEmpty then some (reconstruct d.alphabet d.max_length d.scenarios) else none

theorem checked_reconstruction_iff (d : Spec) (result : List Candidate) :
    checkedReconstruct d = some result ↔
    validateSpec d = [] ∧ reconstruct d.alphabet d.max_length d.scenarios = result := by
  unfold checkedReconstruct
  split <;> simp_all

theorem checked_candidate_correct (d : Spec) (result : List Candidate)
    (h : checkedReconstruct d = some result) (c : Candidate) :
    c ∈ result ↔ InSpace d.alphabet d.max_length d.scenarios c ∧ CandidateFits c := by
  rw [← ((checked_reconstruction_iff d result).mp h).2]
  exact reconstruction_correct _ _ _ _

def candidateReport (d : Spec) (c : Candidate) : Json := Id.run do
  let input := d.analyses.find? (fun a => a.id == c.scenario.id)
  let mut branches : List Json := []
  if let some a := input then
    for b in a.branches do
      let steps := trace b.package.laws c.protoform
      let output := run b.package.laws c.protoform
      let observation := a.observations.find? (fun o => o.doculect_id == b.doculect_id)
      branches := branches ++ [Json.mkObj [
        ("doculect_id", toJson b.doculect_id), ("package_id", toJson b.package.id),
        ("package_version", toJson b.package.version), ("input", toJson c.protoform),
        ("steps", toJson steps), ("output", toJson output),
        ("certificate_accepted", toJson (checkTrace b.package.laws c.protoform steps output)),
        ("observation_satisfied", toJson (observation.any (fun o => formMatches o.form output)))]]
  return Json.mkObj [("analysis_id", toJson c.scenario.id),
    ("proto_node_id", toJson (input.map (·.proto_node_id))),
    ("choice_bindings", toJson (input.map (·.choice_bindings))),
    ("protoform", toJson c.protoform), ("branches", toJson branches)]

structure SearchOutcome where
  complete : Bool
  reason : String
  examined : Nat
  scopeSize : Option Nat
  candidates : List Candidate

/-- A cooperative driver; the returned candidates are recomputed by the proved
prefix checker at the recorded examined count. It never labels a prefix empty
as an exhausted space. Time is checked between complete candidate evaluations. -/
def search (d : Spec) : IO SearchOutcome := do
  if rawUpperBound d > maxRawHypotheses then
    return ⟨false, "space-limit", 0, none, []⟩
  if d.time_limit_ms == some 0 then
    return ⟨false, "time-limit", 0, none, []⟩
  let started ← IO.monoMsNow
  let pool := space d.alphabet d.max_length d.scenarios
  let mut examined := 0
  let mut reason := "exhausted"
  let mut acceptedCount := 0
  for c in pool do
    if examined ≥ d.candidate_budget then
      reason := "candidate-budget"
      break
    let now ← IO.monoMsNow
    if d.time_limit_ms.any (fun limit => now - started ≥ limit) then
      reason := "time-limit"
      break
    if accepts c then acceptedCount := acceptedCount + 1
    examined := examined + 1
  let candidates := prefixResults pool examined
  if candidates.length != acceptedCount then
    throw (IO.userError "SEARCH_DRIVER: prefix decisions disagree with the formal checker")
  let complete := prefixComplete pool examined
  return ⟨complete, if complete then "exhausted" else reason, examined, some pool.length,
    candidates⟩

def reportSearch (d : Spec) (outcome : SearchOutcome) : Json :=
  Json.mkObj [("id", toJson d.id), ("input_valid", toJson true),
    ("status", toJson (if outcome.complete then "complete" else "incomplete")),
    ("complete", toJson outcome.complete), ("reason", toJson outcome.reason),
    ("claim", toJson d.claim), ("raw_hypothesis_upper_bound", toJson (rawUpperBound d)),
    ("scope_size", toJson outcome.scopeSize), ("examined", toJson outcome.examined),
    ("no_candidate_in_scope", toJson (outcome.complete && outcome.candidates.isEmpty)),
    ("history_count", toJson outcome.candidates.length),
    ("distinct_protoform_count", toJson ((outcome.candidates.map (·.protoform)).eraseDups.length)),
    ("issues", toJson ([] : List Issue)),
    ("candidates", toJson (outcome.candidates.map (candidateReport d)))]

end Historical.ReconstructionInput
