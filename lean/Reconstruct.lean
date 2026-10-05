import Historical.ReconstructionInput

open Lean System Historical Historical.ReconstructionInput

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
  status : String
  reason : String
  issues : List Issue
  report : Json
  code : UInt32
  keys : List (String × List String)

private def invalid (issues : List Issue) : Checked :=
  ⟨"invalid", "input", issues,
    Json.mkObj [("input_valid", toJson false), ("status", toJson "invalid"),
      ("complete", toJson false), ("reason", toJson "input"),
      ("no_candidate_in_scope", toJson false), ("issues", toJson issues)], 1, []⟩

private def checkSpec (d : Spec) : IO Checked := do
  let issues := validateSpec d
  if !issues.isEmpty then return invalid issues
  let outcome ← search d
  let keys := outcome.candidates.map fun c => (c.scenario.id, c.protoform.map fun a => match a with
    | .segment s => s
    | .morpheme => "+")
  return ⟨if outcome.complete then "complete" else "incomplete", outcome.reason, [],
    reportSearch d outcome, if outcome.complete then 0 else 3, keys⟩

private def checkFile (path : FilePath) : IO Checked := do
  let text ← readText path
  match text.bind (decodeExact (α := Spec)) with
  | .error e => return invalid [⟨(e.splitOn ":").head!, path.toString, e⟩]
  | .ok d => checkSpec d

private structure ExpectedCandidate where
  analysis_id : String
  protoform : List String
  deriving FromJson, ToJson

private structure Fixture where
  path : String
  status : String
  code : Option String
  reason : String
  candidates : List ExpectedCandidate
  category : String
  rationale : String
  deriving FromJson, ToJson

private structure Suite where
  schema_version : String
  suite : String
  fixtures : List Fixture
  deriving FromJson, ToJson

private def runSuite : IO (Json × UInt32) := do
  let path ← resolve (FilePath.mk "data/reconstruction/manifest.json")
  let text ← readText path
  let s : Suite ← match text.bind (decodeExact (α := Suite)) with
    | .error e => throw (IO.userError e)
    | .ok s => pure s
  if s.schema_version != "1.0.0" || s.suite != "bounded-reconstruction" || s.fixtures.isEmpty ||
      !unique (s.fixtures.map (·.path)) then
    throw (IO.userError "SUITE: invalid version, name, empty manifest or repeated fixture path")
  let mut results : Array Json := #[]
  let mut passed := 0
  let mut complete := 0
  let mut incomplete := 0
  let mut rejected := 0
  for f in s.fixtures do
    if (f.path.splitOn "/").any (fun p => p == ".." || p.isEmpty) ||
        f.category.isEmpty || f.rationale.isEmpty || !(["complete", "incomplete", "invalid"].contains f.status) ||
        ((f.status == "invalid") != f.code.isSome) then
      throw (IO.userError "SUITE: invalid fixture metadata or expected error")
    let actual ← checkFile (path.parent.getD (FilePath.mk ".") / f.path)
    let expected := f.candidates.map (fun c => (c.analysis_id, c.protoform))
    let matched := actual.status == f.status && actual.reason == f.reason && actual.keys == expected &&
      (match f.code with | none => true | some code => actual.issues.any (·.code == code))
    if matched then passed := passed + 1
    if actual.status == "complete" then complete := complete + 1
    else if actual.status == "incomplete" then incomplete := incomplete + 1
    else rejected := rejected + 1
    results := results.push (Json.mkObj [("fixture", toJson f.path), ("category", toJson f.category),
      ("expected_status", toJson f.status), ("expected_error", toJson f.code),
      ("expected_reason", toJson f.reason), ("passed", toJson matched), ("result", actual.report)])
  let ok := passed == s.fixtures.length && complete ≥ 15 && rejected ≥ 25 && incomplete ≥ 3
  return (Json.mkObj [("suite", toJson s.suite), ("passed", toJson ok),
    ("complete_fixtures", toJson complete), ("incomplete_fixtures", toJson incomplete),
    ("invalid_fixtures", toJson rejected), ("matched_expectations", toJson passed),
    ("results", Json.arr results)], if ok then 0 else 1)

private structure Batch where
  queries : List Spec
  deriving FromJson, ToJson

private def batch (path : FilePath) : IO (Json × UInt32) := do
  let text ← readText path
  let req : Batch ← match text.bind (decodeExact (α := Batch)) with
    | .error e => throw (IO.userError e)
    | .ok r => pure r
  let mut results : List Json := []
  let mut code : UInt32 := 0
  for query in req.queries do
    let result ← checkSpec query
    results := results ++ [result.report]
    if result.code != 0 then code := if result.code == 1 || code == 1 then 1 else 3
  return (Json.mkObj [("results", toJson results)], code)

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
      | ["--suite", "bounded-reconstruction"] => runSuite
      | ["--file", p] => do
          let checked ← checkFile (← resolve (FilePath.mk p))
          pure (checked.report, checked.code)
      | ["--batch", p] => batch (← resolve (FilePath.mk p))
      | _ => throw (IO.userError "Usage: reconstruct (--suite bounded-reconstruction | --file PATH | --batch PATH) [--report FILE]")
    if let some file := report then IO.FS.writeFile file (result.1.pretty ++ "\n")
    out.putStrLn result.1.compress
    return result.2
  catch e =>
    err.putStrLn s!"IO_OR_INPUT_ERROR: {e}"
    return 2
