import Historical.Evidence

namespace Historical
open Lean

structure Issue where
  code : String
  path : String
  message : String
  deriving ToJson, FromJson, Repr

def goodId (s : String) : Bool :=
  !s.isEmpty && s.toList.all (fun c => c.isAlphanum && c.toNat < 128 ||
    c == '-' || c == '_' || c == '.' || c == ':')

def unique (xs : List String) : Bool := xs.eraseDups.length == xs.length

def identifierIssues (path : String) (ids : List String) : List Issue :=
  (if unique ids then [] else [⟨"DUPLICATE_ID", path, "Primary IDs must be unique in their table"⟩]) ++
  ids.filterMap (fun id => if goodId id then none else
    some ⟨"INVALID_ID", path, s!"Invalid stable identifier: {id}"⟩)

def validate (d : Dossier) : List Issue := Id.run do
  let mut errors : List Issue := []
  let add := fun code path message => Issue.mk code path message
  if d.schema_version != "1.0.0" then
    errors := errors ++ [add "SCHEMA_VERSION" "schema_version" "Expected 1.0.0; use an explicit migration"]
  if !goodId d.id then errors := errors ++ [add "INVALID_ID" "id" "Invalid dossier ID"]
  if d.description.isEmpty || d.records.isEmpty then
    errors := errors ++ [add "EMPTY_DOSSIER" "records" "Description and records are required"]
  let sources := d.sources.map (·.id)
  let doculects := d.doculects.map (·.id)
  let meanings := d.meanings.map (·.id)
  for (p, ids) in [("sources", sources), ("doculects", doculects), ("meanings", meanings),
      ("analyses", d.analyses.map (·.id)), ("normalization_methods", d.normalization_methods.map (·.id)),
      ("choice_groups", d.choice_groups.map (·.id)), ("records", d.records.map (·.id))] do
    errors := errors ++ identifierIssues p ids
  for s in d.sources do
    if s.title.isEmpty || s.url.isEmpty || s.version.isEmpty || s.license.isEmpty ||
        !(["publication", "dataset", "synthetic"].contains s.kind) then
      errors := errors ++ [add "SOURCE_METADATA" s.id "Title, URL, version, license and recognized source kind are required"]
    if let some hash := s.sha256 then
      if hash.length != 64 || !(hash.toList.all (fun c => c.isDigit || "abcdef".contains c)) then
        errors := errors ++ [add "SOURCE_HASH" s.id "Expected a lowercase SHA-256 digest"]
  for l in d.doculects do
    if l.name.isEmpty || l.family.isEmpty || l.stage.isEmpty || !(["attested", "proto"].contains l.kind) then
      errors := errors ++ [add "DOCULECT_METADATA" l.id "Name, family, stage and recognized node kind required"]
    if let some dates := l.date_range then
      if dates.earliest > dates.latest || dates.convention != "astronomical-year" then
        errors := errors ++ [add "DATE_RANGE" l.id "Dates must be ordered astronomical years"]
  for m in d.meanings do
    if m.label.isEmpty then errors := errors ++ [add "MEANING_LABEL" m.id "A meaning needs a label"]
  for a in d.analyses do
    if a.description.isEmpty || !goodId a.proto_node_id || a.source_ids.isEmpty then
      errors := errors ++ [add "ANALYSIS_METADATA" a.id "Analysis needs description, proto-node and sources"]
    if !(a.source_ids.all sources.contains) then
      errors := errors ++ [add "BROKEN_SOURCE" a.id "Analysis cites an unknown source"]
  for m in d.normalization_methods do
    if m.version.isEmpty || m.description.isEmpty then
      errors := errors ++ [add "METHOD_METADATA" m.id "Normalization method needs version and description"]
  for g in d.choice_groups do
    if g.options.length < 2 || !unique g.options || !(g.options.all goodId) || g.description.isEmpty then
      errors := errors ++ [add "CHOICE_GROUP" g.id "A choice group needs at least two distinct named options and a description"]
  for r in d.records do
    let p := r.id
    if !doculects.contains r.doculect_id then
      errors := errors ++ [add "BROKEN_DOCULECT" p "Unknown doculect/stage"]
    if r.meaning_ids.isEmpty || !unique r.meaning_ids || !(r.meaning_ids.all meanings.contains) then
      errors := errors ++ [add "BROKEN_MEANING" p "Meanings must be nonempty, distinct and declared"]
    if !(["orthographic", "phonetic", "phonemic", "mixed"].contains r.representation) then
      errors := errors ++ [add "REPRESENTATION" p "Unrecognized representation"]
    if !(["attested", "reconstructed"].contains r.attestation) then
      errors := errors ++ [add "ATTESTATION" p "Explicit attestation status required"]
    if !(["present", "missing", "unknown"].contains r.evidence_state) then
      errors := errors ++ [add "EVIDENCE_STATE" p "Unrecognized evidence state"]
    if r.citations.isEmpty then errors := errors ++ [add "MISSING_SOURCE" p "At least one citation is required"]
    for c in r.citations do
      if !sources.contains c.source_id then errors := errors ++ [add "BROKEN_SOURCE" p c.source_id]
      if c.locator.isEmpty then errors := errors ++ [add "SOURCE_LOCATOR" p "Exact source locator required"]
    if r.attestation == "reconstructed" then
      let a := d.analyses.find? (fun a => some a.id == r.analysis_id)
      match a with
      | none => errors := errors ++ [add "RECONSTRUCTION_ANALYSIS" p "A reconstructed form needs a declared analysis"]
      | some a => if r.proto_node_id != some a.proto_node_id then
          errors := errors ++ [add "PROTO_NODE" p "Proto-node disagrees with the named analysis"]
      if !(d.doculects.any (fun l => l.id == r.doculect_id && l.kind == "proto")) then
        errors := errors ++ [add "ATTESTATION_NODE" p "Reconstruction must refer to a proto doculect"]
    else
      if r.analysis_id.isSome || r.proto_node_id.isSome then
        errors := errors ++ [add "ATTESTED_ANALYSIS" p "An attested record must not silently carry reconstructed identity"]
      if d.doculects.any (fun l => l.id == r.doculect_id && l.kind == "proto") then
        errors := errors ++ [add "ATTESTATION_NODE" p "A proto doculect cannot supply attested records"]
    if r.uncertain != r.uncertainty_note.isSome || r.uncertainty_note == some "" then
      errors := errors ++ [add "UNCERTAINTY_NOTE" p "Uncertainty flag and nonempty note must agree"]
    if r.evidence_state == "unknown" && !r.uncertain then
      errors := errors ++ [add "UNKNOWN_UNFLAGGED" p "Unresolved source readings must be flagged"]
    if r.readings.isEmpty then errors := errors ++ [add "NO_READINGS" p "At least one explicit reading is required"]
    errors := errors ++ identifierIssues (p ++ ".readings") (r.readings.map (·.id))
    for rd in r.readings do
      let q := p ++ "." ++ rd.id
      if rd.normalization.isEmpty then
        errors := errors ++ [add "NORMALIZATION_MISSING" q "Even identity normalization must be recorded"]
      if replay rd.original rd.normalization != some rd.normalized then
        errors := errors ++ [add "NORMALIZATION_CHAIN" q "Normalization history does not connect original and normalized values"]
      for step in rd.normalization do
        if !(d.normalization_methods.any (fun m => m.id == step.method_id && m.version == step.method_version)) then
          errors := errors ++ [add "NORMALIZATION_METHOD" q "Normalization method/version not declared"]
        if step.reason.isEmpty then errors := errors ++ [add "NORMALIZATION_REASON" q "Normalization needs an explicit reason"]
        if step.method_id == "identity" && step.input != step.output then
          errors := errors ++ [add "IDENTITY_CHANGED" q "Identity normalization cannot change source text"]
      if rd.cells.isEmpty then errors := errors ++ [add "EMPTY_CELLS" q "Use explicit missing/unknown cells"]
      if renderCells rd.cells != rd.normalized then
        errors := errors ++ [add "CELL_RENDER" q "Cells must reproduce the declared normalized view"]
      if !r.uncertain && rd.cells.any (fun c => match c with | .unknown _ => true | _ => false) then
        errors := errors ++ [add "UNKNOWN_UNFLAGGED" q "Any unresolved cell requires an uncertainty flag"]
      for cell in rd.cells do
        match cell with
        | .segment s | .boundary s | .unknown s =>
          if s.isEmpty then errors := errors ++ [add "EMPTY_CELL" q "A segment, boundary or unresolved reading cannot be empty"]
        | _ => pure ()
      if r.evidence_state == "missing" then
        if rd.original != "" || rd.normalized != "" || rd.cells != [.missing] then
          errors := errors ++ [add "MISSING_CONTENT" q "Missing evidence must have empty source/view and one missing cell"]
      else
        if rd.original.isEmpty || rd.normalized.isEmpty || rd.cells.contains .missing then
          errors := errors ++ [add "PRESENT_CONTENT" q "Present/unknown evidence needs text; missing cells cannot substitute for gaps"]
      if r.evidence_state == "unknown" && !(rd.cells.any (fun c => match c with | .unknown _ => true | _ => false)) then
        errors := errors ++ [add "UNKNOWN_CELL" q "Unknown evidence needs an explicit unresolved cell"]
      if !unique (rd.choices.map (·.group_id)) then
        errors := errors ++ [add "CHOICE_CONFLICT" q "One reading cannot bind the same choice twice"]
      for b in rd.choices do
        if !(d.choice_groups.any (fun g => g.id == b.group_id && g.options.contains b.option_id)) then
          errors := errors ++ [add "BROKEN_CHOICE" q "Choice group/option not declared"]
    if let some o := r.imported_from then
      if !(d.sources.any (fun s => s.id == o.dataset_id && s.kind == "dataset")) ||
          !(r.citations.any (fun c => c.source_id == o.dataset_id)) then
        errors := errors ++ [add "IMPORT_SOURCE" p "Import must cite its declared dataset"]
      if o.table.isEmpty || o.row_id.isEmpty || o.raw_columns.isEmpty ||
          !unique (o.raw_columns.map (·.name)) then
        errors := errors ++ [add "IMPORT_ORIGIN" p "Import requires table, row ID and distinct retained raw columns"]
      if !(o.raw_columns.any (fun c => c.name == o.id_column && c.value == o.row_id)) then
        errors := errors ++ [add "IMPORT_ROW_ID" p "Declared upstream row ID differs from retained source columns"]
      match o.raw_columns.find? (fun c => c.name == o.original_column) with
      | none => errors := errors ++ [add "IMPORT_ORIGINAL" p "Original source column is absent"]
      | some c =>
        if !(r.readings.all (fun rd => rd.original == c.value)) then
          errors := errors ++ [add "IMPORT_ORIGINAL" p "Original string differs from the retained source value"]
  return errors

end Historical
