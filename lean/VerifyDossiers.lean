import Historical.RuleInput

open Lean System Historical Historical.Rules Historical.Certificates Historical.RuleInput

private def readText (path : FilePath) : IO (Except String String) := do
  let bytes ← IO.FS.readBinFile path
  return match String.fromUTF8? bytes with
    | some text => .ok text
    | none => .error "UTF8: input must be valid UTF-8"

private def resolve (path : FilePath) : IO FilePath := do
  if !(← path.pathExists) && (← (FilePath.mk ".." / path).pathExists) then
    return FilePath.mk ".." / path
  return path

private def checkFile (path : FilePath) : IO (Bool × List Issue) := do
  let decoded := (← readText path).bind decodeRuleDossier
  match decoded with
  | .error e => return (false, [⟨(e.splitOn ":").head!, path.toString, e⟩])
  | .ok d => return (checkDossier d, if checkDossier d then [] else diagnose d)

private structure Fixture where
  path : String
  accept : Bool
  code : Option String
  category : String
  rationale : String
  deriving FromJson, ToJson

private structure Suite where
  schema_version : String
  suite : String
  fixtures : List Fixture
  deriving FromJson, ToJson

private def runSuite : IO (Json × Bool) := do
  let path ← resolve (FilePath.mk "data/contextual-rules/manifest.json")
  let text ← readText path
  let s : Suite ← match text.bind (decodeExact (α := Suite)) with
    | .error e => throw (IO.userError e)
    | .ok s => pure s
  if s.schema_version != "1.0.0" || s.suite != "contextual-rules" || s.fixtures.isEmpty then
    throw (IO.userError "SUITE: invalid version, name or empty fixture manifest")
  if !unique (s.fixtures.map (·.path)) then
    throw (IO.userError "SUITE: repeated fixture path")
  let mut results : Array Json := #[]
  let mut passed := 0
  let mut valid := 0
  let mut adversarial := 0
  for f in s.fixtures do
    if (f.path.splitOn "/").any (fun p => p == ".." || p.isEmpty) ||
        f.category.isEmpty || f.rationale.isEmpty || (f.accept == f.code.isSome) then
      throw (IO.userError "SUITE: invalid fixture path, rationale or expected error")
    let (accepted, issues) ← checkFile (path.parent.getD (FilePath.mk ".") / f.path)
    let matched := accepted == f.accept &&
      (match f.code with | none => true | some code => issues.any (·.code == code))
    if matched then passed := passed + 1
    if f.accept then valid := valid + 1 else adversarial := adversarial + 1
    results := results.push (Json.mkObj [("fixture", toJson f.path),
      ("category", toJson f.category), ("expected_accept", toJson f.accept),
      ("expected_error", toJson f.code), ("accepted", toJson accepted),
      ("issues", toJson issues), ("passed", toJson matched)])
  let success := passed == s.fixtures.length && valid ≥ 10 && adversarial ≥ 40
  return (Json.mkObj [("suite", toJson s.suite), ("passed", toJson success),
    ("valid_fixtures", toJson valid), ("adversarial_fixtures", toJson adversarial),
    ("matched_expectations", toJson passed), ("results", Json.arr results)], success)

private structure Evaluation where
  model : Package
  inputs : List Word
  deriving FromJson, ToJson

private def evaluate (path : FilePath) : IO (Json × Bool) := do
  let text ← readText path
  let req : Evaluation ← match text.bind (decodeExact (α := Evaluation)) with
    | .error e => throw (IO.userError e)
    | .ok req => pure req
  let issues := validatePackage req.model
  if !issues.isEmpty || req.inputs.isEmpty ||
      !(req.inputs.all (validWord req.model.inventory)) then
    return (Json.mkObj [("accepted", toJson false), ("issues", toJson issues),
      ("error", toJson "EVALUATION_INPUT: valid package and nonempty list of in-inventory words required")], false)
  let results := req.inputs.map fun w => Json.mkObj [("input", toJson w),
    ("steps", toJson (trace req.model.laws w)), ("output", toJson (run req.model.laws w))]
  return (Json.mkObj [("accepted", toJson true), ("package_id", toJson req.model.id),
    ("package_version", toJson req.model.version), ("results", toJson results)], true)

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
      | ["--suite", "contextual-rules"] => runSuite
      | ["--file", p] => do
          let (accepted, issues) ← checkFile (← resolve (FilePath.mk p))
          pure (Json.mkObj [("accepted", toJson accepted), ("issues", toJson issues)], accepted)
      | ["--evaluate", p] => evaluate (← resolve (FilePath.mk p))
      | _ => do
          throw (IO.userError "Usage: verify_dossiers (--suite contextual-rules | --file PATH | --evaluate PATH) [--report FILE]")
    if let some file := report then IO.FS.writeFile file (result.1.pretty ++ "\n")
    out.putStrLn result.1.compress
    return if result.2 then (0 : UInt32) else (1 : UInt32)
  catch e =>
    err.putStrLn s!"IO_OR_INPUT_ERROR: {e}"
    return (2 : UInt32)
