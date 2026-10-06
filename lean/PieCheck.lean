import Historical.CaseStudy

open Lean System Historical Historical.Rules Historical.Certificates
open Historical.RuleInput Historical.Reconstruction Historical.CaseStudy

private structure ForwardJob where
  id : String
  package_id : String
  input : Word
  expected : Option Word
  deriving FromJson, ToJson

private structure ObservedBranch where
  doculect_id : String
  package_id : String
  expected : Word
  deriving FromJson, ToJson

private structure InverseJob where
  id : String
  pool : List Word
  branches : List ObservedBranch
  reference : List Word
  deriving FromJson, ToJson

private structure Request where
  schema_version : String
  id : String
  packages : List Package
  forward : List ForwardJob
  inverse : List InverseJob
  deriving FromJson, ToJson

private def findPackage (r : Request) (id : String) : Except String Package :=
  match r.packages.find? (fun p => p.id == id) with
  | some p => .ok p
  | none => .error ("Unknown package: " ++ id)

private def validate (r : Request) : Except String Unit := do
  if r.schema_version != "1.0.0" || !goodId r.id then throw "Invalid study metadata"
  if !unique (r.packages.map (·.id)) || !unique (r.forward.map (·.id)) || !unique (r.inverse.map (·.id)) then
    throw "Repeated package or job ID"
  if r.packages.isEmpty || r.forward.length > 10000 || r.inverse.length > 1000 then
    throw "Study exceeds executable profile (10000 forward, 1000 inverse jobs)"
  for p in r.packages do
    if !(validatePackage p).isEmpty then throw ("Invalid package: " ++ p.id)
  for j in r.forward do
    let p ← findPackage r j.package_id
    if !goodId j.id || j.input.length > 100 || !validWord p.inventory j.input ||
        !(j.expected.all (validWord p.inventory)) then throw ("Invalid forward job: " ++ j.id)
  for j in r.inverse do
    if !goodId j.id || j.pool.isEmpty || j.pool.length > 1000 || j.branches.length < 2 ||
        j.branches.length > 32 || !(j.pool.all (fun w => w.length ≤ 100)) ||
        !unique (j.branches.map (·.doculect_id)) || !((j.branches.map (·.doculect_id)).all goodId) ||
        j.pool.eraseDups != j.pool || j.reference.isEmpty || !(j.reference.all j.pool.contains) then
      throw ("Invalid inverse pool/observations: " ++ j.id)
    for b in j.branches do
      let p ← findPackage r b.package_id
      if !(j.pool.all (validWord p.inventory)) || !validWord p.inventory b.expected then
        throw ("Word outside inverse package inventory: " ++ j.id)
      if p.initial_stage != "published-root" then throw "Inverse branch must start at published-root"

private def execute (r : Request) : Json := Id.run do
  let mut forwards : List Json := []
  for j in r.forward do
    if let .ok p := findPackage r j.package_id then
      let steps := trace p.laws j.input
      let out := run p.laws j.input
      forwards := forwards ++ [Json.mkObj [("id", toJson j.id), ("package_id", toJson p.id),
        ("input", toJson j.input), ("steps", toJson steps), ("output", toJson out),
        ("expected", toJson j.expected), ("exact", toJson (j.expected.map (fun w => w == out))),
        ("certificate_accepted", toJson (checkTrace p.laws j.input steps out))]]
  let mut inverses : List Json := []
  for j in r.inverse do
    let model : Model := j.branches.filterMap fun b =>
      match findPackage r b.package_id with
      | .ok p => some ⟨b.doculect_id, p.laws⟩
      | .error _ => none
    let obs : List Observation := j.branches.map fun b =>
      ⟨b.doculect_id, some (b.expected.map Reconstruction.atomCell)⟩
    let found := retrieve j.pool model obs
    inverses := inverses ++ [Json.mkObj [("id", toJson j.id), ("complete", toJson true),
      ("scope", toJson "declared-published-reference-pool"), ("examined", toJson j.pool.length),
      ("candidates", toJson found), ("reference", toJson j.reference),
      ("reference_recalled", toJson (found.any j.reference.contains)),
      ("ambiguous", toJson (decide (found.length > 1))), ("empty_in_scope", toJson found.isEmpty)]]
  return Json.mkObj [("id", toJson r.id), ("input_valid", toJson true),
    ("forward", toJson forwards), ("inverse", toJson inverses)]

def main (args : List String) : IO UInt32 := do
  let out ← IO.getStdout
  let err ← IO.getStderr
  try
    let (file, report) ← match args with
      | ["--batch", f] => pure (f, none)
      | ["--batch", f, "--report", p] => pure (f, some p)
      | _ => throw (IO.userError "Usage: pie_check --batch FILE [--report FILE]")
    let bytes ← IO.FS.readBinFile file
    let parsed : Except String Request := do
      let text ← match String.fromUTF8? bytes with
        | some text => .ok text
        | none => .error "UTF8: invalid input"
      let req ← decodeExact (α := Request) text
      validate req
      pure req
    match parsed with
    | .error e =>
      out.putStrLn ((Json.mkObj [("input_valid", toJson false), ("error", toJson e)]).compress)
      return (1 : UInt32)
    | .ok req =>
      let result := execute req
      if let some p := report then IO.FS.writeFile p (result.pretty ++ "\n")
      out.putStrLn result.compress
      return (0 : UInt32)
  catch e =>
    err.putStrLn s!"IO_OR_INPUT_ERROR: {e}"
    return (2 : UInt32)
