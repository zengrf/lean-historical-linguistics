import Historical.RuleInput

/-! A finite paradigm shares one input stem and tonal category across its cells.
Affixation and declared allomorphy are morphological operations, distinct from
the contextual sound changes. Tone labels are source-specific categories. -/
namespace Historical.Paradigm
open Lean Rules Certificates RuleInput

structure Form where
  segments : Word
  tone : Option String
  deriving DecidableEq, FromJson, ToJson

structure Allomorph where
  input : Word
  output : Word
  deriving DecidableEq, FromJson, ToJson

structure ToneRule where
  id : String
  from_tone : String
  to_tone : String
  initial_class : List String
  final_class : List String
  conditioning : String
  deriving DecidableEq, FromJson, ToJson

structure Cell where
  id : String
  source_ref : String
  «prefix» : Word
  suffix : Word
  allomorphs : List Allomorph
  stem : Package
  sound : Package
  tone_rules : List ToneRule
  expected : Option Form
  deriving FromJson, ToJson

def stemInput (c : Cell) (w : Word) : Word :=
  ((c.allomorphs.find? (fun a => a.input == w)).map (·.output)).getD w

def segments (w : Word) : List String := w.filterMap fun a =>
  match a with | .segment s => some s | .morpheme => none

def toneApplies (r : ToneRule) (stem surface : Word) (tone : Option String) : Bool :=
  let word := segments (if r.conditioning == "stem" then stem else surface)
  tone == some r.from_tone &&
  (r.initial_class.isEmpty || (word.head?.any r.initial_class.contains)) &&
  (r.final_class.isEmpty || (word.getLast?.any r.final_class.contains))

def toneStep (r : ToneRule) (stem surface : Word) (tone : Option String) : Option String :=
  if toneApplies r stem surface tone then some r.to_tone else tone

def toneRun : List ToneRule → Word → Word → Option String → Option String
  | [], _, _, tone => tone
  | r :: rs, stem, surface, tone => toneRun rs stem surface (toneStep r stem surface tone)

inductive ToneDerives (stem surface : Word) : List ToneRule → Option String → Option String → Prop where
  | nil (tone) : ToneDerives stem surface [] tone tone
  | cons {r rs tone middle out} : toneStep r stem surface tone = middle →
      ToneDerives stem surface rs middle out → ToneDerives stem surface (r :: rs) tone out

theorem tone_derivation_iff (rules : List ToneRule) (stem surface : Word) (tone out : Option String) :
    ToneDerives stem surface rules tone out ↔ toneRun rules stem surface tone = out := by
  constructor
  · intro h
    induction h with
    | nil => rfl
    | cons hs _ ih => simp only [toneRun]; rw [hs]; exact ih
  · intro h
    subst out
    induction rules generalizing tone with
    | nil => exact ToneDerives.nil _
    | cons r rs ih => exact ToneDerives.cons rfl (ih _)

def realize (c : Cell) (input : Form) : Form :=
  let stem := run c.stem.laws (stemInput c input.segments)
  let surface := run c.sound.laws (c.prefix ++ stem ++ c.suffix)
  ⟨surface, toneRun c.tone_rules stem surface input.tone⟩

def Realizes (c : Cell) (input out : Form) : Prop :=
  ∃ stem surface,
    Derives c.stem.laws (stemInput c input.segments) stem ∧
    Derives c.sound.laws (c.prefix ++ stem ++ c.suffix) surface ∧
    ToneDerives stem surface c.tone_rules input.tone out.tone ∧ out.segments = surface

theorem realization_correct (c : Cell) (input out : Form) :
    Realizes c input out ↔ realize c input = out := by
  simp only [Realizes, derives_iff_run, tone_derivation_iff]
  constructor
  · rintro ⟨stem, surface, hs, ho, ht, hw⟩
    cases out with
    | mk word tone =>
      simp only at hw ht
      simp only [realize]
      rw [hs, ho, ht, hw]
  · intro h
    subst out
    exact ⟨_, _, rfl, rfl, rfl, rfl⟩

theorem realization_deterministic (c : Cell) (input a b : Form)
    (ha : Realizes c input a) (hb : Realizes c input b) : a = b :=
  ((realization_correct _ _ _).mp ha).symm.trans ((realization_correct _ _ _).mp hb)

def agrees (out expected : Form) : Bool :=
  out.segments == expected.segments && expected.tone.all (fun t => out.tone == some t)

def Agrees (out expected : Form) : Prop :=
  out.segments = expected.segments ∧ ∀ t ∈ expected.tone, out.tone = some t

theorem agrees_iff (out expected : Form) : agrees out expected = true ↔ Agrees out expected := by
  cases h : expected.tone <;> simp [agrees, Agrees, h, Option.all]

def fits (cells : List Cell) (input : Form) : Bool :=
  cells.all fun c => c.expected.all (fun expected => agrees (realize c input) expected)

def reconstruct (pool : List Form) (cells : List Cell) : List Form := pool.filter (fits cells)

theorem paradigm_reconstruction_correct (pool : List Form) (cells : List Cell) (input : Form) :
    input ∈ reconstruct pool cells ↔ input ∈ pool ∧
      ∀ c ∈ cells, ∀ expected ∈ c.expected, ∃ out, Realizes c input out ∧ Agrees out expected := by
  have point (c : Cell) : c.expected.all (fun expected => agrees (realize c input) expected) = true ↔
      ∀ expected ∈ c.expected, ∃ out, Realizes c input out ∧ Agrees out expected := by
    cases h : c.expected <;> simp [Option.all, h, realization_correct, agrees_iff]
  simp [reconstruct, fits, List.all_eq_true, point]

def certificate (c : Cell) (input : Form) : Json := Id.run do
  let base := stemInput c input.segments
  let stem := run c.stem.laws base
  let affixed := c.prefix ++ stem ++ c.suffix
  let surface := run c.sound.laws affixed
  let mut tone := input.tone
  let mut tones : List Json := []
  for r in c.tone_rules do
    let next := toneStep r stem surface tone
    tones := tones ++ [Json.mkObj [("rule_id", toJson r.id), ("input", toJson tone),
      ("output", toJson next), ("applied", toJson (toneApplies r stem surface tone)),
      ("conditioning", toJson r.conditioning)]]
    tone := next
  return Json.mkObj [("cell_id", toJson c.id), ("source_ref", toJson c.source_ref),
    ("input", toJson input), ("allomorph_input", toJson base),
    ("stem_steps", toJson (trace c.stem.laws base)), ("stem_output", toJson stem),
    ("prefix", toJson c.prefix), ("suffix", toJson c.suffix), ("affixed", toJson affixed),
    ("sound_steps", toJson (trace c.sound.laws affixed)), ("tone_steps", toJson tones),
    ("output", toJson (realize c input)),
    ("certificate_accepted", toJson (checkTrace c.stem.laws base (trace c.stem.laws base) stem &&
      checkTrace c.sound.laws affixed (trace c.sound.laws affixed) surface &&
      tone == (realize c input).tone))]

structure Analysis where
  id : String
  description : String
  source_ref : String
  cells : List Cell
  deriving FromJson, ToJson

structure Request where
  schema_version : String
  id : String
  source_kind : String
  source_scope : String
  inventory : List String
  tone_inventory : List String
  pool : List Form
  analyses : List Analysis
  deriving FromJson, ToJson

def validForm (r : Request) (f : Form) : Bool :=
  f.segments.length ≤ 100 && validWord r.inventory f.segments && f.tone.all r.tone_inventory.contains

def validate (r : Request) : Except String Unit := do
  if r.schema_version != "1.0.0" || !goodId r.id || r.source_scope.isEmpty ||
      !(["synthetic", "source-worked"].contains r.source_kind) ||
      r.inventory.isEmpty || !unique r.inventory || !(r.inventory.all goodSymbol) ||
      !unique r.tone_inventory || !(r.tone_inventory.all goodSymbol) ||
      r.pool.isEmpty || r.pool.length > 256 || r.pool.eraseDups != r.pool || !(r.pool.all (validForm r)) ||
      r.analyses.isEmpty || r.analyses.length > 16 || !unique (r.analyses.map (·.id)) then
    throw "Invalid paradigm scope or finite pool"
  for a in r.analyses do
    if !goodId a.id || a.description.isEmpty || a.source_ref.isEmpty || a.cells.isEmpty ||
        a.cells.length > 16 || !unique (a.cells.map (·.id)) then throw "Invalid joint paradigm analysis"
    for c in a.cells do
      if !goodId c.id || c.source_ref.isEmpty || c.tone_rules.length > 32 ||
          c.allomorphs.length > 256 || (c.allomorphs.map (·.input)).eraseDups != c.allomorphs.map (·.input) ||
          c.prefix.length + c.suffix.length > 100 ||
          !validWord r.inventory (c.prefix ++ c.suffix) || !(c.expected.all (validForm r)) ||
          !(validatePackage c.stem).isEmpty || !(validatePackage c.sound).isEmpty ||
          c.stem.inventory != r.inventory || c.sound.inventory != r.inventory ||
          !(c.allomorphs.all (fun x => validWord r.inventory x.input && validWord r.inventory x.output &&
            x.input.length ≤ 100 && x.output.length ≤ 100)) || !unique (c.tone_rules.map (·.id)) then
        throw "Invalid morphology, expected form or sound package"
      for t in c.tone_rules do
        if !goodId t.id || !r.tone_inventory.contains t.from_tone || !r.tone_inventory.contains t.to_tone ||
            !(t.initial_class.all r.inventory.contains) || !(t.final_class.all r.inventory.contains) ||
            !(["stem", "surface"].contains t.conditioning) then throw "Invalid tonal category or conditioning stage"

def execute (r : Request) : Json := Id.run do
  let mut histories : List Json := []
  for a in r.analyses do
    for input in r.pool do
      histories := histories ++ [Json.mkObj [("analysis_id", toJson a.id), ("input", toJson input),
        ("accepted", toJson (fits a.cells input)),
        ("cells", toJson (a.cells.map (fun c => certificate c input)))]]
  return Json.mkObj [("input_valid", toJson true), ("complete", toJson true),
    ("id", toJson r.id), ("scope", toJson "declared-joint-paradigm-pool"),
    ("examined", toJson (r.pool.length * r.analyses.length)), ("histories", toJson histories)]

end Historical.Paradigm
