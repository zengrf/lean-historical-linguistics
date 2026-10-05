import Historical.CorrespondenceInput

open Lean System Historical Historical.Alignment Historical.Correspondence
open Historical.CorrespondenceInput Historical.RuleInput

private def readText (path : FilePath) : IO (Except String String) := do
  let bytes ← IO.FS.readBinFile path
  return match String.fromUTF8? bytes with
    | some text => .ok text
    | none => .error "UTF8: input must be valid UTF-8"

private def resolve (path : FilePath) : IO FilePath := do
  if !(← path.pathExists) && (← (FilePath.mk ".." / path).pathExists) then
    return FilePath.mk ".." / path
  return path

private structure Checked where
  accepted : Bool
  issues : List Issue
  report : Json
  baselineEligible : Bool := false
  sites : Nat := 0
  incomplete : Nat := 0
  conflicting : Nat := 0

private def invalid (path : FilePath) (error : String) : Checked :=
  let issues : List Issue := [⟨(error.splitOn ":").head!, path.toString, error⟩]
  ⟨false, issues, Json.mkObj [("accepted", toJson false), ("issues", toJson issues)], false, 0, 0, 0⟩

private def checkFile (path : FilePath) (kind : String) : IO Checked := do
  let text ← readText path
  if kind == "alignment" then
    match text.bind (decodeExact (α := AlignmentData)) with
    | .error e => return invalid path e
    | .ok d => return ⟨dataAccepted d, validateData d ++ d.alignments.flatMap alignmentIssues, reportData d, false, 0, 0, 0⟩
  else if kind == "dossier" then
    match text.bind (decodeExact (α := CorrespondenceDossier)) with
    | .error e => return invalid path e
    | .ok d =>
        let sites := derivedSites d
        let incomplete := sites.filter fun s => s.cells.any fun c => match c with
          | .missing | .unknown _ => true
          | _ => false
        let conflicting := sites.filter fun s => d.groups.any fun g =>
          g.members.contains s.id && (select sites g.members).any fun t =>
            s.id != t.id && !noConflict s.cells t.cells
        return ⟨dossierAccepted d, diagnose d, reportDossier d,
          dataAccepted d.alignment_data && (validateRegistry d).isEmpty,
          sites.length, incomplete.length, conflicting.length⟩
  else throw (IO.userError "SUITE: unknown fixture kind")

private structure Fixture where
  path : String
  kind : String
  accept : Bool
  code : Option String
  category : String
  rationale : String
  counts_toward_site_suite : Bool
  deriving FromJson, ToJson

private structure Suite where
  schema_version : String
  suite : String
  fixtures : List Fixture
  deriving FromJson, ToJson

private def runSuite : IO (Json × Bool) := do
  let path ← resolve (FilePath.mk "data/correspondence/manifest.json")
  let text ← readText path
  let s : Suite ← match text.bind (decodeExact (α := Suite)) with
    | .error e => throw (IO.userError e)
    | .ok s => pure s
  if s.schema_version != "1.0.0" || s.suite != "correspondence-sites" || s.fixtures.isEmpty ||
      !unique (s.fixtures.map (·.path)) then
    throw (IO.userError "SUITE: invalid version, name, empty manifest or repeated fixture path")
  let mut results : Array Json := #[]
  let mut matched := 0
  let mut valid := 0
  let mut rejected := 0
  let mut sites := 0
  let mut incomplete := 0
  let mut conflicting := 0
  for f in s.fixtures do
    if (f.path.splitOn "/").any (fun p => p == ".." || p.isEmpty) ||
        f.category.isEmpty || f.rationale.isEmpty || (f.accept == f.code.isSome) then
      throw (IO.userError "SUITE: invalid fixture path, rationale or expected error")
    let checked ← checkFile (path.parent.getD (FilePath.mk ".") / f.path) f.kind
    let ok := checked.accepted == f.accept &&
      (match f.code with | none => true | some code => checked.issues.any (·.code == code))
    if ok then matched := matched + 1
    if f.accept then valid := valid + 1 else rejected := rejected + 1
    if f.counts_toward_site_suite then
      if !checked.baselineEligible then
        throw (IO.userError "SUITE: counted sites must have valid alignments and a complete unique registry")
      sites := sites + checked.sites
      incomplete := incomplete + checked.incomplete
      conflicting := conflicting + checked.conflicting
    results := results.push (Json.mkObj [("fixture", toJson f.path), ("kind", toJson f.kind),
      ("category", toJson f.category), ("expected_accept", toJson f.accept),
      ("expected_error", toJson f.code), ("passed", toJson ok),
      ("counts_toward_site_suite", toJson f.counts_toward_site_suite), ("result", checked.report)])
  let success := matched == s.fixtures.length && sites ≥ 100 && incomplete ≥ 20 && conflicting ≥ 10
  return (Json.mkObj [("suite", toJson s.suite), ("passed", toJson success),
    ("valid_fixtures", toJson valid), ("rejected_fixtures", toJson rejected),
    ("matched_expectations", toJson matched), ("site_count", toJson sites),
    ("incomplete_site_count", toJson incomplete), ("conflicting_site_count", toJson conflicting),
    ("results", Json.arr results)], success)

private structure MatrixRequest where
  columns : List (List Cell)
  deriving FromJson, ToJson

private structure PartitionRequest where
  sites : List Correspondence.Site
  proposals : List (List Correspondence.Group)
  deriving FromJson, ToJson

private def matrix (path : FilePath) : IO Json := do
  let text ← readText path
  let req : MatrixRequest ← match text.bind (decodeExact (α := MatrixRequest)) with
    | .error e => throw (IO.userError e)
    | .ok r => pure r
  let rows := req.columns.map fun x => req.columns.map fun y => Json.mkObj [
    ("no_conflict", toJson (noConflict x y)), ("shared_positions", toJson (sharedPositions x y)),
    ("compatible", toJson (compatible x y))]
  return Json.mkObj [("scope", toJson "typed-core-evaluation"), ("rows", toJson rows)]

private def partitions (path : FilePath) : IO Json := do
  let text ← readText path
  let req : PartitionRequest ← match text.bind (decodeExact (α := PartitionRequest)) with
    | .error e => throw (IO.userError e)
    | .ok r => pure r
  return Json.mkObj [("scope", toJson "typed-core-evaluation"),
    ("results", toJson (req.proposals.map (checkPartition req.sites)))]

def main (args : List String) : IO UInt32 := do
  let out ← IO.getStdout
  let err ← IO.getStderr
  let mut positional : List String := []
  let mut report : Option String := none
  let mut rest := args
  while !rest.isEmpty do
    match rest with
    | "--report" :: file :: xs => report := some file; rest := xs
    | x :: xs => positional := positional ++ [x]; rest := xs
    | [] => pure ()
  try
    let result ← match positional with
      | ["--suite", "correspondence-sites"] => runSuite
      | ["--file", p] => do
          let c ← checkFile (← resolve (FilePath.mk p)) "dossier"
          pure (c.report, c.accepted)
      | ["--alignment", p] => do
          let c ← checkFile (← resolve (FilePath.mk p)) "alignment"
          pure (c.report, c.accepted)
      | ["--matrix", p] => do pure (← matrix (← resolve (FilePath.mk p)), true)
      | ["--partitions", p] => do pure (← partitions (← resolve (FilePath.mk p)), true)
      | _ => throw (IO.userError "Usage: correspondence_check (--suite correspondence-sites | --file PATH | --alignment PATH | --matrix PATH | --partitions PATH) [--report FILE]")
    if let some file := report then IO.FS.writeFile file (result.1.pretty ++ "\n")
    out.putStrLn result.1.compress
    return if result.2 then (0 : UInt32) else (1 : UInt32)
  catch e =>
    err.putStrLn s!"IO_OR_INPUT_ERROR: {e}"
    return (2 : UInt32)
