import Historical.Batch

open Lean System Historical Historical.RuleInput Historical.Batch

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
