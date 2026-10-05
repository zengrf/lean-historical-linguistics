import Historical.JsonInput

open Lean Historical System

private def readDossier (path : FilePath) : IO (Except String Dossier) := do
  let bytes ← IO.FS.readBinFile path
  match String.fromUTF8? bytes with
  | none => return .error "UTF8: input must be valid UTF-8"
  | some text => return decodeDossier text

private def inputFiles (path : FilePath) : IO (Array FilePath) := do
  if ← path.isDir then
    let entries ← path.readDir
    return (entries.filterMap fun e => if e.path.extension == some "json" then some e.path else none)
      |>.qsort (fun a b => a.toString < b.toString)
  else return #[path]

def main (args : List String) : IO UInt32 := do
  let out ← IO.getStdout
  let err ← IO.getStderr
  let mut positional : List String := []
  let mut report : Option String := none
  let mut roundtrip : Option String := none
  let mut strict := false
  let mut rest := args
  while !rest.isEmpty do
    match rest with
    | "--strict" :: xs => strict := true; rest := xs
    | "--report" :: x :: xs => report := some x; rest := xs
    | "--roundtrip" :: x :: xs => roundtrip := some x; rest := xs
    | x :: xs => positional := positional ++ [x]; rest := xs
    | [] => pure ()
  if positional.length != 1 || !strict || positional.any (·.startsWith "--") then
    err.putStrLn "Usage: lake exe dossier_check PATH --strict [--report FILE] [--roundtrip FILE]"
    return (2 : UInt32)
  let mut path : FilePath := positional.head!
  -- Permit the acceptance command's root-relative data/pilots from lean/.
  if !(← path.pathExists) && (← (FilePath.mk ".." / path).pathExists) then
    path := FilePath.mk ".." / path
  try
    let files ← inputFiles path
    let mut items : Array Json := #[]
    let mut accepted := 0
    let mut records := 0
    let mut primaryIds : List String := []
    let mut dossierIds : List String := []
    let mut successful : Array Dossier := #[]
    if files.isEmpty then
      err.putStrLn "NO_INPUT: no JSON dossier files found"
      return (2 : UInt32)
    for f in files do
      let mut issues : List Issue := []
      match ← readDossier f with
      | .error e =>
          let code := (e.splitOn ":").head!
          issues := [⟨code, f.toString, e⟩]
      | .ok d =>
          issues := validate d
          if dossierIds.contains d.id then
            issues := issues ++ [⟨"DUPLICATE_DOSSIER", d.id, "Dossier IDs must be unique across the input directory"⟩]
          dossierIds := d.id :: dossierIds
          for r in d.records do
            if primaryIds.contains r.id then
              issues := issues ++ [⟨"DUPLICATE_GLOBAL_RECORD", r.id, "Record IDs must be unique across dossiers"⟩]
            primaryIds := r.id :: primaryIds
          records := records + d.records.length
          if issues.isEmpty then successful := successful.push d
      if issues.isEmpty then accepted := accepted + 1
      items := items.push (Json.mkObj [("file", toJson f.toString),
        ("accepted", toJson issues.isEmpty), ("issues", toJson issues)])
    let result := Json.mkObj [("schema_version", toJson "1.0.0"),
      ("files", toJson files.size), ("accepted", toJson accepted),
      ("rejected", toJson (files.size - accepted)), ("records", toJson records),
      ("results", Json.arr items)]
    if let some p := report then IO.FS.writeFile p (result.pretty ++ "\n")
    if let some p := roundtrip then
      if successful.size != 1 || files.size != 1 then
        err.putStrLn "ROUNDTRIP: requires exactly one accepted dossier"
        return (2 : UInt32)
      if let some d := successful[0]? then
        IO.FS.writeFile p ((toJson d).pretty ++ "\n")
    out.putStrLn result.compress
    return if accepted == files.size then (0 : UInt32) else (1 : UInt32)
  catch e =>
    err.putStrLn s!"IO_ERROR: {e}"
    return (2 : UInt32)
