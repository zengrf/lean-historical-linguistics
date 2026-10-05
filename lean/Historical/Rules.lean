import Std

/-! M2's total local-rule interpreter and inductive scan semantics.
Tokens are atomic; boundaries are not segments. No lexical lookup or callback
can be embedded in a Rule. Packaging checks impose finite inventories and the
two-token context bound; the theorems hold even for longer finite contexts. -/
namespace Historical.Rules

inductive Atom where
  | segment (symbol : String)
  | morpheme
  deriving DecidableEq, Repr

abbrev Word := List Atom

inductive Test where
  | segments (symbols : List String)
  | anySegment
  | morpheme
  deriving DecidableEq, Repr

inductive Direction where
  | leftToRight | rightToLeft
  deriving DecidableEq, Repr

inductive Mode where
  | simultaneous | feeding
  deriving DecidableEq, Repr

structure Rule where
  target : List String
  replacement : Option String
  left : List Test
  right : List Test
  left_edge : Bool
  right_edge : Bool
  direction : Direction
  mode : Mode
  deriving DecidableEq, Repr

def testMatches : Test → Atom → Bool
  | .segments ss, .segment s => decide (s ∈ ss)
  | .anySegment, .segment _ => true
  | .morpheme, .morpheme => true
  | _, _ => false

/-- Contexts on both sides are nearest-first. Anchors follow all tests. -/
def sideMatches : List Test → Bool → Word → Bool
  | [], edge, xs => !edge || xs.isEmpty
  | t :: ts, edge, a :: xs => testMatches t a && sideMatches ts edge xs
  | _ :: _, _, [] => false

def eligible (r : Rule) (left : Word) (a : Atom) (right : Word) : Bool :=
  match a with
  | .morpheme => false
  | .segment s => decide (s ∈ r.target) &&
      sideMatches r.left r.left_edge left && sideMatches r.right r.right_edge right

def outputAt (r : Rule) (left : Word) (a : Atom) (right : Word) : Word :=
  if eligible r left a right then
    match r.replacement with
    | none => []
    | some s => [.segment s]
  else [a]

/-- Local inference rules distinguish copying, replacement and deletion. -/
inductive Emits (r : Rule) (left : Word) (a : Atom) (right : Word) : Word → Prop where
  | keep : eligible r left a right = false → Emits r left a right [a]
  | replace {s} : eligible r left a right = true → r.replacement = some s →
      Emits r left a right [.segment s]
  | delete : eligible r left a right = true → r.replacement = none →
      Emits r left a right []

theorem emits_iff_outputAt (r : Rule) (left : Word) (a : Atom) (right out : Word) :
    Emits r left a right out ↔ outputAt r left a right = out := by
  constructor
  · intro h
    cases h with
    | keep h => simp [outputAt, h]
    | replace h hr => simp [outputAt, h, hr]
    | delete h hr => simp [outputAt, h, hr]
  · intro h
    cases he : eligible r left a right with
    | false =>
        simp [outputAt, he] at h
        subst out
        exact Emits.keep he
    | true =>
        cases hr : r.replacement with
        | none =>
            simp [outputAt, he, hr] at h
            subst out
            exact Emits.delete he hr
        | some s =>
            simp [outputAt, he, hr] at h
            subst out
            exact Emits.replace he hr

def visibleLeft (r : Rule) (original produced : Word) : Word :=
  match r.mode with
  | .simultaneous => original
  | .feeding => produced

/-- Both prefixes are nearest-first; recursion consumes only original input. -/
def scan (r : Rule) (original produced : Word) : Word → Word
  | [] => []
  | a :: rest =>
      let chunk := outputAt r (visibleLeft r original produced) a rest
      chunk ++ scan r (a :: original) (chunk.reverse ++ produced) rest

inductive Scan (r : Rule) : Word → Word → Word → Word → Prop where
  | nil (original produced) : Scan r original produced [] []
  | cons {original produced a rest chunk tail} :
      Emits r (visibleLeft r original produced) a rest chunk →
      Scan r (a :: original) (chunk.reverse ++ produced) rest tail →
      Scan r original produced (a :: rest) (chunk ++ tail)

theorem scan_eq_iff (r : Rule) (original produced input out : Word) :
    scan r original produced input = out ↔ Scan r original produced input out := by
  induction input generalizing original produced out with
  | nil =>
      constructor
      · intro h; simp [scan] at h; subst out; exact Scan.nil original produced
      · intro h; cases h; rfl
  | cons a rest ih =>
      constructor
      · intro h
        subst out
        exact Scan.cons ((emits_iff_outputAt _ _ _ _ _).mpr rfl)
          ((ih _ _ _).mp rfl)
      · intro h
        cases h with
        | cons hc ht =>
            have he := (emits_iff_outputAt _ _ _ _ _).mp hc
            have hs := (ih _ _ _).mpr ht
            simp only [scan]
            rw [he, hs]

def mirror (r : Rule) : Rule :=
  { r with left := r.right, right := r.left,
           left_edge := r.right_edge, right_edge := r.left_edge }

def applyRule (r : Rule) (w : Word) : Word :=
  match r.direction with
  | .leftToRight => scan r [] [] w
  | .rightToLeft => (scan (mirror r) [] [] w.reverse).reverse

def Pass (r : Rule) (input out : Word) : Prop :=
  match r.direction with
  | .leftToRight => Scan r [] [] input out
  | .rightToLeft => Scan (mirror r) [] [] input.reverse out.reverse

theorem pass_iff_apply (r : Rule) (input out : Word) :
    Pass r input out ↔ applyRule r input = out := by
  cases hd : r.direction with
  | leftToRight => simp [Pass, applyRule, hd, ← scan_eq_iff]
  | rightToLeft =>
      simp only [Pass, applyRule, hd]
      rw [← scan_eq_iff]
      constructor
      · intro h; rw [h]; simp
      · intro h
        have hr := congrArg List.reverse h
        simpa using hr

theorem pass_deterministic (r : Rule) (input x y : Word)
    (hx : Pass r input x) (hy : Pass r input y) : x = y := by
  exact ((pass_iff_apply _ _ _).mp hx).symm.trans ((pass_iff_apply _ _ _).mp hy)

theorem outputAt_length_le (r : Rule) (left : Word) (a : Atom) (right : Word) :
    (outputAt r left a right).length ≤ 1 := by
  unfold outputAt
  split
  · cases r.replacement <;> simp
  · simp

theorem scan_length_le (r : Rule) (original produced input : Word) :
    (scan r original produced input).length ≤ input.length := by
  induction input generalizing original produced with
  | nil => simp [scan]
  | cons a rest ih =>
      have hc := outputAt_length_le r (visibleLeft r original produced) a rest
      have ht := ih (a :: original)
        ((outputAt r (visibleLeft r original produced) a rest).reverse ++ produced)
      simp only [scan, List.length_append, List.length_cons]
      omega

theorem applyRule_length_le (r : Rule) (w : Word) :
    (applyRule r w).length ≤ w.length := by
  cases hd : r.direction with
  | leftToRight => simpa [applyRule, hd] using scan_length_le r [] [] w
  | rightToLeft =>
      simpa [applyRule, hd] using scan_length_le (mirror r) [] [] w.reverse

theorem morpheme_copied (r : Rule) (left right : Word) :
    outputAt r left .morpheme right = [.morpheme] := by
  simp [outputAt, eligible]

end Historical.Rules
