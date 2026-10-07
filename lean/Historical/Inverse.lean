import Historical.Compile
import Historical.Reconstruction

/-! Residual constraints and a finite inverse language. The candidate alphabet
is supplied as a constraint; no published protoform pool occurs in this model. -/
namespace Historical.Inverse
open Rules Reconstruction
abbrev Mask := Option (List Cell)
abbrev Shapes := Option (List (List (List Atom)))

/-- Consume a known emitted front. The outer none means incompatibility;
the inner none is an entirely unobserved daughter form. -/
def consumeCells : List Cell → Word → Option (List Cell)
  | cs, [] => some cs
  | c :: cs, a :: w => if cellMatches c a then consumeCells cs w else none
  | [], _ :: _ => none

def consume (mask : Mask) (out : Word) : Option Mask :=
  match mask with
  | none => some none
  | some cs => (consumeCells cs out).map some

theorem consumeCells_correct (cs : List Cell) (front suffix : Word) :
    cellsMatch cs (front ++ suffix) = true ↔
      ∃ rest, consumeCells cs front = some rest ∧ cellsMatch rest suffix = true := by
  induction front generalizing cs with
  | nil => simp [consumeCells]
  | cons a front ih =>
    cases cs with
    | nil => simp [cellsMatch, consumeCells]
    | cons c cs =>
      cases h : cellMatches c a <;> simp [cellsMatch, consumeCells, h, ih]

theorem consume_correct (mask : Mask) (front suffix : Word) :
    formMatches mask (front ++ suffix) = true ↔
      ∃ rest, consume mask front = some rest ∧ formMatches rest suffix = true := by
  cases mask with
  | none => simp [consume, formMatches]
  | some cs =>
    simp only [formMatches, consume]
    rw [consumeCells_correct]
    cases h : consumeCells cs front <;> simp [formMatches]

def residual : List Compile.Table → List Mask → Atom → Option (List Mask)
  | [], [], _ => some []
  | t :: ts, m :: ms, a => do
      let rest ← consume m (Compile.image t a)
      let rests ← residual ts ms a
      pure (rest :: rests)
  | _, _, _ => none

def fits : List Compile.Table → List Mask → Word → Bool
  | [], [], _ => true
  | t :: ts, m :: ms, w => formMatches m (Compile.apply t w) && fits ts ms w
  | _, _, _ => false

theorem residual_correct (ts : List Compile.Table) (ms : List Mask) (a : Atom) (w : Word) :
    fits ts ms (a :: w) = true ↔
      ∃ rests, residual ts ms a = some rests ∧ fits ts rests w = true := by
  induction ts generalizing ms with
  | nil => cases ms <;> simp [fits, residual]
  | cons t ts ih =>
    cases ms with
    | nil => simp [fits, residual]
    | cons m ms =>
      simp only [fits, Compile.apply, List.flatMap_cons, Bool.and_eq_true]
      rw [consume_correct, ih]
      cases hc : consume m (Compile.image t a) <;>
        cases hr : residual ts ms a <;> simp [residual, hc, hr, fits, Compile.apply]

def shapeStep (shapes : Shapes) (a : Atom) : Shapes :=
  shapes.map fun ps => ps.filterMap fun p =>
    match p with
    | [] => none
    | slot :: rest => if a ∈ slot then some rest else none

def shapeAccept : Shapes → Bool
  | none => true
  | some ps => ps.any List.isEmpty

def shapeFits : Shapes → Word → Bool
  | s, [] => shapeAccept s
  | s, a :: w => shapeFits (shapeStep s a) w

structure State where
  remaining : Nat
  minimum : Nat
  masks : List Mask
  shapes : Shapes
  deriving DecidableEq, Repr

def finish (ts : List Compile.Table) (s : State) : Bool :=
  (s.minimum == 0) && fits ts s.masks [] && shapeAccept s.shapes

def step (ts : List Compile.Table) (s : State) (a : Atom) : Option State :=
  match s.remaining with
  | 0 => none
  | n + 1 => (residual ts s.masks a).map fun ms =>
      ⟨n, s.minimum - 1, ms, shapeStep s.shapes a⟩

def allows (ts : List Compile.Table) (s : State) (w : Word) : Bool :=
  decide (s.minimum ≤ w.length ∧ w.length ≤ s.remaining) &&
    fits ts s.masks w && shapeFits s.shapes w

theorem allows_nil (ts : List Compile.Table) (s : State) :
    allows ts s [] = finish ts s := by
  apply Bool.eq_iff_iff.mpr
  simp [allows, finish, shapeFits]

theorem allows_cons (ts : List Compile.Table) (s : State) (a : Atom) (w : Word) :
    allows ts s (a :: w) = true ↔
      ∃ next, step ts s a = some next ∧ allows ts next w = true := by
  rcases s with ⟨n, m, ms, ps⟩
  cases n with
  | zero => simp [allows, step]
  | succ n =>
    simp only [allows, List.length_cons, Bool.and_eq_true, decide_eq_true_eq, shapeFits]
    rw [residual_correct]
    cases hr : residual ts ms a with
    | none => simp [step, hr]
    | some rest =>
      have hb : (m ≤ w.length + 1 ∧ w.length + 1 ≤ n + 1) ↔
          (m - 1 ≤ w.length ∧ w.length ≤ n) := by omega
      simp [step, hr, allows, hb, shapeFits] <;> omega

/-- Mathematical enumeration. Runtime uses checked DAG certificates instead of
materializing this list when mergers or deletion create enormous inverse sets. -/
def enumerate (alphabet : List Atom) (ts : List Compile.Table) (s : State) : List Word :=
  (wordsUpTo alphabet s.remaining).filter (allows ts s)

theorem inverse_correct (alphabet : List Atom) (ts : List Compile.Table) (s : State) (w : Word) :
    w ∈ enumerate alphabet ts s ↔ (∀ a ∈ w, a ∈ alphabet) ∧ allows ts s w = true := by
  simp only [enumerate, List.mem_filter, mem_wordsUpTo]
  constructor
  · intro h; exact ⟨h.1.2, h.2⟩
  · intro h
    have hl : w.length ≤ s.remaining := by
      have hh := h.2
      simp only [allows, Bool.and_eq_true, decide_eq_true_eq] at hh
      exact hh.1.1.2
    exact ⟨⟨hl, h.1⟩, h.2⟩

end Historical.Inverse
