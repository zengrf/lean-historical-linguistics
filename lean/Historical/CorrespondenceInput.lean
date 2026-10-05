import Historical.Correspondence
import Historical.RuleInput

namespace Historical.CorrespondenceInput
open Lean Alignment Correspondence

deriving instance FromJson, ToJson for Correspondence.Group
deriving instance FromJson, ToJson for Correspondence.Site

structure RowEntry where
  doculect_id : String
  source_ref : String
  original : Option (List Cell)
  aligned : Option (List Cell)
  deriving FromJson, ToJson, Repr

def RowEntry.core (r : RowEntry) : Alignment.Row := ⟨r.original, r.aligned⟩

structure AlignmentEntry where
  id : String
  evidence_unit : String
  width : Nat
  rows : List RowEntry
  deriving FromJson, ToJson, Repr

def AlignmentEntry.core (a : AlignmentEntry) : List Alignment.Row := a.rows.map RowEntry.core

structure AlignmentData where
  schema_version : String
  id : String
  description : String
  source_kind : String
  doculects : List String
  alignments : List AlignmentEntry
  deriving FromJson, ToJson, Repr

structure SiteRef where
  id : String
  alignment_id : String
  column_index : Nat
  deriving FromJson, ToJson, Repr

structure CorrespondenceDossier where
  alignment_data : AlignmentData
  sites : List SiteRef
  groups : List Correspondence.Group
  support_policy : String
  claim : String
  deriving FromJson, ToJson, Repr

def goodCell : Cell → Bool
  | .segment s => RuleInput.goodSymbol s
  | .boundary s => s == "+"
  | .unknown s => !s.isEmpty
  | .missing | .gap => true

def validateData (d : AlignmentData) : List Issue := Id.run do
  let mut issues : List Issue := []
  let add := fun code path message => Issue.mk code path message
  if d.schema_version != "1.0.0" then
    issues := issues ++ [add "SCHEMA_VERSION" "alignment_data.schema_version" "Expected M3 schema 1.0.0"]
  if !goodId d.id || d.description.isEmpty || !(["synthetic", "sourced"].contains d.source_kind) then
    issues := issues ++ [add "DATA_METADATA" "alignment_data" "Valid ID, description and explicit source kind required"]
  if d.doculects.length < 2 || !unique d.doculects || !(d.doculects.all goodId) then
    issues := issues ++ [add "DOCULECT_AXIS" "doculects" "At least two distinct named doculects are required"]
  if d.alignments.isEmpty then
    issues := issues ++ [add "EMPTY_ALIGNMENTS" "alignments" "At least one alignment is required"]
  if !unique (d.alignments.map (·.id)) then
    issues := issues ++ [add "ALIGNMENT_IDS" "alignments" "Alignment IDs must be unique"]
  for a in d.alignments do
    if !goodId a.id || !goodId a.evidence_unit then
      issues := issues ++ [add "ALIGNMENT_METADATA" a.id "Valid alignment and evidence-unit IDs required"]
    if a.rows.map (·.doculect_id) != d.doculects then
      issues := issues ++ [add "DOCULECT_AXIS" a.id "Every row must follow the same complete declared doculect axis"]
    for r in a.rows do
      if r.source_ref.isEmpty then
        issues := issues ++ [add "SOURCE_REF" a.id "Every present or absent row needs a source reference"]
      if !((r.original.getD [] ++ r.aligned.getD []).all goodCell) then
        issues := issues ++ [add "CELL_VALUE" a.id "Invalid atomic segment, unknown reading or boundary marker"]
  return issues

def dataAccepted (d : AlignmentData) : Bool :=
  (validateData d).isEmpty && d.alignments.all (fun a => checkAlignment a.width a.core)

theorem dataAccepted_iff (d : AlignmentData) : dataAccepted d = true ↔
    validateData d = [] ∧ ∀ a ∈ d.alignments, ValidAlignment a.width a.core := by
  simp [dataAccepted, List.all_eq_true, checkAlignment_iff]

theorem accepted_data_recovers_row (d : AlignmentData) (h : dataAccepted d = true)
    (a : AlignmentEntry) (ha : a ∈ d.alignments) (r : RowEntry) (hr : r ∈ a.rows) :
    recover r.aligned = r.original := by
  have hac := (checkAlignment_iff _ _).mpr (((dataAccepted_iff d).mp h).2 a ha)
  exact accepted_alignment_preserves_rows a.width a.core hac r.core (List.mem_map.mpr ⟨r, hr, rfl⟩)

def requiredPositions (d : AlignmentData) : List (String × Nat) :=
  d.alignments.flatMap fun a =>
    ((List.range a.width).filter fun i => (column a.core i).any isSegment).map (a.id, ·)

def deriveSite (d : AlignmentData) (s : SiteRef) : Option Correspondence.Site := do
  let a ← d.alignments.find? (fun a => a.id == s.alignment_id)
  if s.column_index < a.width then
    some ⟨s.id, a.evidence_unit, column a.core s.column_index⟩
  else none

def derivedSites (d : CorrespondenceDossier) : List Correspondence.Site :=
  d.sites.filterMap (deriveSite d.alignment_data)

def validateRegistry (d : CorrespondenceDossier) : List Issue := Id.run do
  let mut issues : List Issue := []
  let add := fun code path message => Issue.mk code path message
  if d.claim != "feasibility-only" then
    issues := issues ++ [add "UNSUPPORTED_OPTIMALITY" "claim" "Only feasibility-only is accepted; no minimum, maximum or optimality claim is verified"]
  if d.support_policy != "distinct-evidence-units-v1" then
    issues := issues ++ [add "SUPPORT_POLICY" "support_policy" "Expected distinct-evidence-units-v1"]
  if !unique (d.sites.map (·.id)) || !(d.sites.all (fun s => goodId s.id)) then
    issues := issues ++ [add "SITE_IDS" "sites" "Site IDs must be distinct valid identifiers"]
  let required := requiredPositions d.alignment_data
  let actual := d.sites.map (fun s => (s.alignment_id, s.column_index))
  if required.isEmpty then
    issues := issues ++ [add "NO_SITES" "sites" "At least one segment-bearing alignment column is required"]
  if actual.eraseDups.length != actual.length then
    issues := issues ++ [add "DUPLICATE_SITE_POSITION" "sites" "Each alignment column can have only one site identity"]
  if !(required.all actual.contains) || !(actual.all required.contains) then
    issues := issues ++ [add "SITE_COVERAGE" "sites" "Registry must contain every segment-bearing column exactly once and no other column"]
  for s in d.sites do
    if (deriveSite d.alignment_data s).isNone then
      issues := issues ++ [add "SITE_REFERENCE" s.id "Unknown alignment or out-of-range column index"]
  if !unique (d.groups.map (·.id)) || !(d.groups.all (fun g => goodId g.id)) then
    issues := issues ++ [add "GROUP_IDS" "groups" "Group IDs must be distinct valid identifiers"]
  return issues

def dossierAccepted (d : CorrespondenceDossier) : Bool :=
  dataAccepted d.alignment_data && (validateRegistry d).isEmpty &&
    checkPartition (derivedSites d) d.groups

theorem dossierAccepted_iff (d : CorrespondenceDossier) : dossierAccepted d = true ↔
    (validateData d.alignment_data = [] ∧
      ∀ a ∈ d.alignment_data.alignments, ValidAlignment a.width a.core) ∧
    validateRegistry d = [] ∧ FeasiblePartition (derivedSites d) d.groups := by
  simp [dossierAccepted, dataAccepted_iff, checkPartition_iff, and_assoc]

def alignmentIssues (a : AlignmentEntry) : List Issue := Id.run do
  let mut issues : List Issue := []
  let add := fun code path message => Issue.mk code path message
  if a.width == 0 || a.rows.length < 2 then
    issues := issues ++ [add "ALIGNMENT_DIMENSIONS" a.id "Positive width and at least two rows required"]
  for r in a.rows do
    let p := a.id ++ ":" ++ r.doculect_id
    if !checkRow r.core then
      issues := issues ++ [add "ROW_RECOVERY" p "Removing only gaps must exactly recover the supplied original, including absence"]
    if !originalShape r.original then
      issues := issues ++ [add "ORIGINAL_SHAPE" p "Original rows cannot contain gaps/missing cells or malformed morpheme boundaries"]
    if !alignedShape a.width r.aligned then
      issues := issues ++ [add "ALIGNED_SHAPE" p "Present rows need the declared width and cannot contain missing-data cells"]
  for i in List.range a.width do
    let cs := column a.core i
    if !(cs.any isMaterial) then
      issues := issues ++ [add "VOID_COLUMN" (a.id ++ ":" ++ toString i) "A column cannot consist entirely of gaps/missing data"]
    if !boundaryColumn cs then
      issues := issues ++ [add "BOUNDARY_COLUMN" (a.id ++ ":" ++ toString i) "A boundary column cannot mix with segments or unknown readings"]
  return issues

def groupIssues (sites : List Correspondence.Site) (g : Correspondence.Group) : List Issue := Id.run do
  let mut issues : List Issue := []
  let add := fun code path message => Issue.mk code path message
  if g.members.isEmpty then issues := issues ++ [add "EMPTY_GROUP" g.id "Groups must contain at least one site"]
  if !unique g.members then issues := issues ++ [add "DUPLICATE_MEMBER" g.id "A group cannot repeat a site"]
  if !(g.members.all (fun id => (sites.map (·.id)).contains id)) then
    issues := issues ++ [add "UNKNOWN_SITE" g.id "Every member must reference a derived alignment site"]
  let members := select sites g.members
  if !(members.all hasObserved) then
    issues := issues ++ [add "NO_SEGMENT_SUPPORT" g.id "Every grouped site needs an observed segment"]
  for s in members do
    for t in members do
      if s.id != t.id then
        if !noConflict s.cells t.cells then
          issues := issues ++ [add "PAIR_CONFLICT" (g.id ++ ":" ++ s.id ++ ":" ++ t.id) "Observed cells conflict or axes differ"]
        if !hasShared s.cells t.cells then
          issues := issues ++ [add "NO_SHARED_SEGMENT" (g.id ++ ":" ++ s.id ++ ":" ++ t.id) "Missing, unknown and gap overlap cannot supply a shared observed segment"]
  if g.claimed_support != (supportUnits members).length then
    issues := issues ++ [add "SUPPORT_COUNT" g.id "Claimed support must equal the number of distinct declared evidence units"]
  if g.claimed_support == 0 then
    issues := issues ++ [add "NO_GROUP_SUPPORT" g.id "Group support must be positive"]
  return issues

def diagnose (d : CorrespondenceDossier) : List Issue := Id.run do
  let sites := derivedSites d
  let mut issues := validateData d.alignment_data ++
    d.alignment_data.alignments.flatMap alignmentIssues ++ validateRegistry d ++ d.groups.flatMap (groupIssues sites)
  for s in sites do
    if occurrences s.id d.groups != 1 then
      issues := issues ++ [⟨"PARTITION_COVERAGE", s.id, "Every required site must occur exactly once across the groups"⟩]
  if !dossierAccepted d && issues.isEmpty then
    issues := [⟨"CHECKER_REJECT", d.alignment_data.id, "The formal certificate checker rejected this proposal"⟩]
  return issues

def sharedPositions (x y : List Cell) : List Nat :=
  (List.range x.length).filter fun i => match x[i]?, y[i]? with
    | some a, some b => sharedSound a b
    | _, _ => false

def siteReports (d : CorrespondenceDossier) : List Json := Id.run do
  let sites := derivedSites d
  let inputOk := dataAccepted d.alignment_data && (validateRegistry d).isEmpty
  let mut result := []
  for s in sites do
    let groups := d.groups.filter (fun g => g.members.contains s.id)
    let mut pairChecks : List Json := []
    let mut support : List Json := []
    let mut conflicts : List String := []
    let mut pairwiseOk := !groups.isEmpty
    for g in groups do
      let members := select sites g.members
      let units := supportUnits members
      support := support ++ [Json.mkObj [("group_id", toJson g.id),
        ("claimed", toJson g.claimed_support), ("computed", toJson units.length),
        ("evidence_units", toJson units), ("group_accepted", toJson (checkGroup sites g))]]
      for t in members do
        if s.id != t.id then
          let ok := compatible s.cells t.cells
          pairwiseOk := pairwiseOk && ok
          if !noConflict s.cells t.cells then conflicts := conflicts ++ [t.id]
          let positions := sharedPositions s.cells t.cells
          pairChecks := pairChecks ++ [Json.mkObj [("group_id", toJson g.id), ("with_site", toJson t.id),
            ("no_conflict", toJson (noConflict s.cells t.cells)), ("compatible", toJson ok),
            ("shared_segment_count", toJson positions.length),
            ("shared_doculects", toJson (positions.filterMap (d.alignment_data.doculects[·]?)))]]
    let sr := d.sites.find? (fun r => r.id == s.id)
    result := result ++ [Json.mkObj [("site_id", toJson s.id),
      ("alignment_id", toJson (sr.map (·.alignment_id))), ("column_index", toJson (sr.map (·.column_index))),
      ("evidence_unit", toJson s.evidence_unit), ("cells", toJson s.cells),
      ("incomplete", toJson (s.cells.any (fun c => match c with | .missing | .unknown _ => true | _ => false))),
      ("assigned_groups", toJson (groups.map (·.id))), ("assignment_count", toJson (occurrences s.id d.groups)),
      ("support", toJson support), ("pairwise_compatible", toJson pairwiseOk),
      ("conflicting_with", toJson conflicts.eraseDups), ("pair_checks", toJson pairChecks),
      ("site_accepted", toJson (inputOk && decide (occurrences s.id d.groups = 1) && groups.all (checkGroup sites))),
      ("document_accepted", toJson (dossierAccepted d))]]
  return result

def reportAlignment (a : AlignmentEntry) : Json :=
  Json.mkObj [("alignment_id", toJson a.id), ("accepted", toJson (checkAlignment a.width a.core)),
    ("rows", toJson (a.rows.map fun r => Json.mkObj [("doculect_id", toJson r.doculect_id),
      ("recovered", toJson (recover r.aligned)), ("original", toJson r.original),
      ("preserved", toJson (checkRow r.core))]))]

def reportData (d : AlignmentData) : Json :=
  Json.mkObj [("id", toJson d.id), ("accepted", toJson (dataAccepted d)),
    ("issues", toJson (validateData d ++ d.alignments.flatMap alignmentIssues)),
    ("alignments", toJson (d.alignments.map reportAlignment))]

def reportDossier (d : CorrespondenceDossier) : Json :=
  Json.mkObj [("id", toJson d.alignment_data.id), ("accepted", toJson (dossierAccepted d)),
    ("alignment_accepted", toJson (dataAccepted d.alignment_data)),
    ("claim", toJson d.claim), ("minimum_cover_verified", toJson false),
    ("issues", toJson (diagnose d)), ("sites", toJson (siteReports d)),
    ("alignments", toJson (d.alignment_data.alignments.map reportAlignment))]

end Historical.CorrespondenceInput
