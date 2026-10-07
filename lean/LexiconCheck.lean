import Historical.LexiconInput
open Lean Historical Historical.LexiconInput

def main (args : List String) : IO UInt32 := do
  let out ← IO.getStdout
  let err ← IO.getStderr
  try
    let (mode, file) ← match args with
      | [m, f] => pure (m, f)
      | _ => throw (IO.userError "Usage: lexicon_check (--validate|--check|--derive|--check-proposals) FILE")
    let bytes ← IO.FS.readBinFile file
    let parsed : Except String Json := do
      if bytes.size > 134217728 then throw "INPUT_BOUND: certificate exceeds 128 MiB"
      let some text := String.fromUTF8? bytes | throw "UTF8: invalid input"
      match mode with
      | "--validate" =>
        let r ← decodeExact (α := Request) text
        validate r
        pure (Json.mkObj [("input_valid", toJson true)])
      | "--check" => checkForest (← decodeExact text)
      | "--derive" => derive (← decodeExact text)
      | "--check-proposals" => verifyProposals (← decodeExact text)
      | _ => throw "Unknown lexicon operation"
    match parsed with
    | .error e =>
      out.putStrLn ((Json.mkObj [("input_valid", toJson false), ("complete", toJson false),
        ("error", toJson e)]).compress)
      return (1 : UInt32)
    | .ok result => out.putStrLn result.compress; return (0 : UInt32)
  catch e =>
    err.putStrLn s!"IO_OR_INPUT_ERROR: {e}"
    return (2 : UInt32)
