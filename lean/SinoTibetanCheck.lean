import Historical.SourceScope

open Lean System Historical Historical.RuleInput Historical.SourceScope

def main (args : List String) : IO UInt32 := do
  let out ← IO.getStdout
  let err ← IO.getStderr
  try
    let file ← match args with
      | ["--batch", f] => pure f
      | _ => throw (IO.userError "Usage: sino_tibetan_check --batch FILE")
    let bytes ← IO.FS.readBinFile file
    let parsed : Except String Request := do
      let text ← match String.fromUTF8? bytes with
        | some text => .ok text
        | none => .error "UTF8: invalid input"
      let r ← decodeExact (α := Request) text
      validate r
      pure r
    match parsed with
    | .error e =>
      out.putStrLn ((Json.mkObj [("scope_valid", toJson false), ("error", toJson e)]).compress)
      return (1 : UInt32)
    | .ok r =>
      out.putStrLn (execute r).compress
      return (0 : UInt32)
  catch e =>
    err.putStrLn s!"IO_OR_INPUT_ERROR: {e}"
    return (2 : UInt32)
