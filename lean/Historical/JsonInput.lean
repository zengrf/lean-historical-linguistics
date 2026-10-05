import Historical.Validation

namespace Historical
open Lean

private inductive Token where
  | keyText (s : String)
  | openObj | closeObj | colon | other

private def charsToString (xs : List Char) : String :=
  xs.foldl (fun s c => s.push c) ""

/- The library JSON parser accepts duplicate keys. This lexical preflight runs
after JSON syntax validation and rejects them before decoding typed evidence.
Supplementary Unicode must be literal UTF-8 for compatibility with Lean 4.19's
parser, which does not combine UTF-16 surrogate escape pairs. -/
private def tokens : List Char → Bool → Bool → List Char → List Token →
    Except String (List Token)
  | [], false, _, _, acc => return acc.reverse
  | [], true, _, _, _ => throw "JSON_SYNTAX: unterminated string"
  | c :: cs, true, escaped, current, acc => do
      if escaped then
        if c == 'u' then
          let hex := charsToString (cs.take 4)
          if hex.length == 4 && (hex.startsWith "d" || hex.startsWith "D") &&
              ((cs.drop 1).head?.map (fun x => "89abcdefABCDEF".contains x)).getD false then
            throw "UNICODE_ESCAPE: encode supplementary characters as literal UTF-8, not surrogate escapes"
        tokens cs true false (c :: current) acc
      else if c == '\\' then tokens cs true true (c :: current) acc
      else if c == '"' then
        let j ← Json.parse (charsToString ((c :: current).reverse))
        let s ← j.getStr?
        tokens cs false false [] (.keyText s :: acc)
      else tokens cs true false (c :: current) acc
  | c :: cs, false, _, _, acc =>
      if c == '"' then tokens cs true false ['"'] acc
      else if c == '{' then tokens cs false false [] (.openObj :: acc)
      else if c == '}' then tokens cs false false [] (.closeObj :: acc)
      else if c == ':' then tokens cs false false [] (.colon :: acc)
      else if c.isWhitespace then tokens cs false false [] acc
      else tokens cs false false [] (.other :: acc)

private def checkKeys : List Token → List (List String) → Except String Unit
  | [], _ => return ()
  | .openObj :: rest, stack => checkKeys rest ([] :: stack)
  | .closeObj :: rest, stack => checkKeys rest stack.tail
  | .keyText s :: .colon :: rest, current :: stack =>
      if current.contains s then throw s!"DUPLICATE_JSON_KEY: {s}"
      else checkKeys rest ((s :: current) :: stack)
  | _ :: rest, stack => checkKeys rest stack

def decodeExact {α : Type} [FromJson α] [ToJson α] (text : String) : Except String α := do
  let j ← (Json.parse text).mapError ("JSON_SYNTAX: " ++ ·)
  checkKeys (← tokens text.toList false false [] []) []
  let d : α ← (fromJson? j).mapError ("JSON_SHAPE: " ++ ·)
  if j != toJson d then
    throw "JSON_SHAPE: unknown fields or omitted explicit fields; every optional field must be present as null or a value"
  return d

def decodeDossier (text : String) : Except String Dossier := decodeExact text

end Historical
