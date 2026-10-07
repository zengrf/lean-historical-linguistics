import Historical.Research
import Historical.Paradigm

open Lean Historical Historical.RuleInput

def main (args : List String) : IO UInt32 := do
  let out ← IO.getStdout
  let err ← IO.getStderr
  try
    let (mode, file) ← match args with
      | [m, f] => pure (m, f)
      | _ => throw (IO.userError "Usage: research_check (--matrix|--chronology|--paradigm) FILE")
    let bytes ← IO.FS.readBinFile file
    let parsed : Except String Json := do
      let text ← match String.fromUTF8? bytes with
        | some text => .ok text
        | none => .error "UTF8: invalid input"
      match mode with
      | "--matrix" =>
        let r ← decodeExact (α := Research.Matrix) text
        Research.validateMatrix r
        pure (Research.analyze r)
      | "--chronology" =>
        let r ← decodeExact (α := Research.Chronology) text
        Research.validateChronology r
        pure (Research.chronologyResult r)
      | "--paradigm" =>
        let r ← decodeExact (α := Paradigm.Request) text
        Paradigm.validate r
        pure (Paradigm.execute r)
      | _ => throw "Unknown research operation"
    match parsed with
    | .error e =>
      out.putStrLn ((Json.mkObj [("input_valid", toJson false), ("complete", toJson false),
        ("error", toJson e)]).compress)
      return (1 : UInt32)
    | .ok result => out.putStrLn result.compress; return (0 : UInt32)
  catch e =>
    err.putStrLn s!"IO_OR_INPUT_ERROR: {e}"
    return (2 : UInt32)
