import Lean

/-! M1 evidence interchange types. These represent sourced claims, not a proof
that an attestation or reconstruction is historically correct. -/
namespace Historical
open Lean

structure Source where
  id : String
  title : String
  url : String
  version : String
  license : String
  kind : String
  sha256 : Option String
  deriving FromJson, ToJson, Repr

structure Citation where
  source_id : String
  locator : String
  deriving FromJson, ToJson, Repr

structure DateRange where
  earliest : Int
  latest : Int
  convention : String
  deriving FromJson, ToJson, Repr

structure Doculect where
  id : String
  name : String
  family : String
  stage : String
  kind : String
  date_range : Option DateRange
  deriving FromJson, ToJson, Repr

structure Meaning where
  id : String
  label : String
  deriving FromJson, ToJson, Repr

structure Analysis where
  id : String
  description : String
  source_ids : List String
  proto_node_id : String
  deriving FromJson, ToJson, Repr

structure Method where
  id : String
  version : String
  description : String
  deriving FromJson, ToJson, Repr

structure Step where
  method_id : String
  method_version : String
  input : String
  output : String
  reason : String
  deriving FromJson, ToJson, Repr

/-- Missing observations, alignment gaps and unresolved readings are distinct. -/
inductive Cell where
  | segment (value : String)
  | boundary (value : String)
  | missing
  | gap
  | unknown (reading : String)
  deriving Repr, DecidableEq

instance : FromJson Cell where
  fromJson? j := do
    let kind : String ← j.getObjValAs? String "kind"
    let value : Option String ← j.getObjValAs? (Option String) "value"
    match kind, value with
    | "segment", some s => return .segment s
    | "boundary", some s => return .boundary s
    | "unknown", some s => return .unknown s
    | "missing", none => return .missing
    | "gap", none => return .gap
    | _, _ => throw "CELL_SHAPE: cell kind and value disagree"

instance : ToJson Cell where
  toJson c :=
    let (kind, value) : String × Option String := match c with
      | .segment s => ("segment", some s)
      | .boundary s => ("boundary", some s)
      | .unknown s => ("unknown", some s)
      | .missing => ("missing", none)
      | .gap => ("gap", none)
    Json.mkObj [("kind", toJson kind), ("value", toJson value)]

structure ChoiceGroup where
  id : String
  options : List String
  description : String
  deriving FromJson, ToJson, Repr

structure Binding where
  group_id : String
  option_id : String
  deriving FromJson, ToJson, Repr

/-- Each reading is a complete joint alternative, not a product of choices at
individual positions. Bindings can link the same choice across several records. -/
structure Reading where
  id : String
  original : String
  normalized : String
  cells : List Cell
  normalization : List Step
  choices : List Binding
  deriving FromJson, ToJson, Repr

structure RawColumn where
  name : String
  value : String
  deriving FromJson, ToJson, Repr

structure ImportOrigin where
  dataset_id : String
  table : String
  row_id : String
  id_column : String
  original_column : String
  raw_columns : List RawColumn
  deriving FromJson, ToJson, Repr

structure Record where
  id : String
  doculect_id : String
  meaning_ids : List String
  representation : String
  attestation : String
  evidence_state : String
  analysis_id : Option String
  proto_node_id : Option String
  citations : List Citation
  readings : List Reading
  uncertain : Bool
  uncertainty_note : Option String
  imported_from : Option ImportOrigin
  deriving FromJson, ToJson, Repr

structure Dossier where
  schema_version : String
  id : String
  description : String
  sources : List Source
  doculects : List Doculect
  meanings : List Meaning
  analyses : List Analysis
  normalization_methods : List Method
  choice_groups : List ChoiceGroup
  records : List Record
  deriving FromJson, ToJson, Repr

/-- Replay the recorded input/output chain; this checks continuity, not the
linguistic or Unicode correctness of an externally described transformation. -/
def replay : String → List Step → Option String
  | s, [] => some s
  | s, step :: rest => if s = step.input then replay step.output rest else none

inductive Chain : String → List Step → String → Prop where
  | nil (s) : Chain s [] s
  | cons {s t steps result} : s = t.input → Chain t.output steps result →
      Chain s (t :: steps) result

theorem replay_iff_chain (s : String) (steps : List Step) (result : String) :
    replay s steps = some result ↔ Chain s steps result := by
  induction steps generalizing s with
  | nil => simp only [replay, Option.some.injEq]; constructor
           · intro h; subst result; exact Chain.nil s
           · intro h; cases h; rfl
  | cons t ts ih =>
    simp only [replay]
    split <;> rename_i h
    · rw [ih]; constructor
      · exact Chain.cons h
      · intro hc; cases hc with | cons _ hr => exact hr
    · constructor
      · intro hn; cases hn
      · intro hc; cases hc with | cons he _ => exact False.elim (h he)

def renderCells (cells : List Cell) : String :=
  String.join (cells.map fun c => match c with
    | .segment s | .boundary s | .unknown s => s
    | .missing | .gap => "")

/-- Update the display and its tokens together, retaining the source and choices.
The result still requires dossier validation (e.g. for method/version references). -/
def renormalize (r : Reading) (m : Method) (cells : List Cell) (reason : String) : Reading :=
  let output := renderCells cells
  { r with
    normalized := output
    cells := cells
    normalization := r.normalization ++ [⟨m.id, m.version, r.normalized, output, reason⟩] }

theorem renormalize_preserves_original (r : Reading) (m : Method) (cells : List Cell) (why : String) :
    (renormalize r m cells why).original = r.original := rfl

theorem renormalize_preserves_choices (r : Reading) (m : Method) (cells : List Cell) (why : String) :
    (renormalize r m cells why).choices = r.choices := rfl

theorem missing_ne_gap : Cell.missing ≠ Cell.gap := by decide

theorem cell_json_roundtrip (c : Cell) : fromJson? (toJson c) = Except.ok c := by
  cases c <;> rfl

end Historical
