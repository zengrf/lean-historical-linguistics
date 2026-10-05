import Std

/-!
Small, independent feasibility experiment. Everything is conditional on the
supplied rules and observations. No linguistic reconstruction is asserted here.
The generic functions below do not yet implement contextual phonological rules.
-/

namespace Comparative

abbrev Word (α : Type) := List α
abbrev Rule (α : Type) := Word α → Word α

/-- Rules are applied once each, in chronological list order. -/
def run {α : Type} : List (Rule α) → Word α → Word α
  | [], w => w
  | r :: rs, w => run rs (r w)

/-- An inductive derivation specification for a supplied rule sequence. -/
inductive Derives {α : Type} : List (Rule α) → Word α → Word α → Prop where
  | nil (w) : Derives [] w w
  | cons {r rs w v} : Derives rs (r w) v → Derives (r :: rs) w v

theorem run_append {α : Type} (rs ss : List (Rule α)) (w : Word α) :
    run (rs ++ ss) w = run ss (run rs w) := by
  induction rs generalizing w with
  | nil => rfl
  | cons r rs ih => exact ih (r w)

theorem derives_iff_run {α : Type} (rs : List (Rule α)) (w v : Word α) :
    Derives rs w v ↔ run rs w = v := by
  constructor
  · intro h
    induction h with
    | nil => rfl
    | cons h ih => exact ih
  · intro h
    subst v
    induction rs generalizing w with
    | nil => exact Derives.nil w
    | cons r rs ih => exact Derives.cons (ih (r w))

/-- A certificate supplies every post-rule word, including the final word.
    Extra or missing steps are rejected. -/
def checkTrace {α : Type} [DecidableEq α] :
    List (Rule α) → Word α → List (Word α) → Word α → Bool
  | [], w, [], v => decide (w = v)
  | r :: rs, w, x :: xs, v => decide (r w = x) && checkTrace rs x xs v
  | _, _, _, _ => false

theorem checkTrace_sound {α : Type} [DecidableEq α]
    (rs : List (Rule α)) (w : Word α) (xs : List (Word α)) (v : Word α)
    (h : checkTrace rs w xs v = true) : Derives rs w v := by
  induction rs generalizing w xs with
  | nil =>
      cases xs with
      | nil =>
          have hw : w = v := by simpa [checkTrace] using h
          subst v
          exact Derives.nil w
      | cons x xs => simp [checkTrace] at h
  | cons r rs ih =>
      cases xs with
      | nil => simp [checkTrace] at h
      | cons x xs =>
          have hh : r w = x ∧ checkTrace rs x xs v = true := by
            simpa [checkTrace] using h
          have hd := ih x xs hh.2
          rw [← hh.1] at hd
          exact Derives.cons hd

def trace {α : Type} : List (Rule α) → Word α → List (Word α)
  | [], _ => []
  | r :: rs, w => r w :: trace rs (r w)

theorem checkTrace_complete {α : Type} [DecidableEq α]
    (rs : List (Rule α)) (w : Word α) :
    checkTrace rs w (trace rs w) (run rs w) = true := by
  induction rs generalizing w with
  | nil => simp [checkTrace, trace, run]
  | cons r rs ih => simp [checkTrace, trace, run, ih]

structure Observation (L α : Type) where
  language : L
  form : Word α

abbrev Model (L α : Type) := L → Word α → Word α

def Fits {L α : Type} (m : Model L α) (obs : List (Observation L α)) (w : Word α) :
    Prop := ∀ o ∈ obs, m o.language w = o.form

/-- More observations can only eliminate compatible candidates in a fixed model. -/
theorem fits_mono {L α : Type} (m : Model L α)
    (small large : List (Observation L α)) (w : Word α)
    (hsub : ∀ o ∈ small, o ∈ large) (h : Fits m large w) : Fits m small w := by
  intro o ho
  exact h o (hsub o ho)

def ObsEquivalent {L α : Type} (m : Model L α) (x y : Word α) : Prop :=
  ∀ l, m l x = m l y

/-- Observationally indistinguishable protoforms fit exactly the same evidence. -/
theorem fits_of_equivalent {L α : Type} (m : Model L α)
    (obs : List (Observation L α)) (x y : Word α)
    (heq : ObsEquivalent m x y) : Fits m obs x ↔ Fits m obs y := by
  constructor
  · intro h o ho
    rw [← heq o.language]
    exact h o ho
  · intro h o ho
    rw [heq o.language]
    exact h o ho

/-- Finite search, not a claim that every possible protoform is in the pool. -/
def reconstruct {H : Type} (pool : List H) (accept : H → Bool) : List H :=
  pool.filter accept

theorem mem_reconstruct_iff {H : Type} (pool : List H) (accept : H → Bool) (h : H) :
    h ∈ reconstruct pool accept ↔ h ∈ pool ∧ accept h = true := by
  simp [reconstruct]

/-- Reflection contract needed to connect any executable checker to its specification. -/
theorem reconstruction_correct {H : Type} (pool : List H) (accept : H → Bool)
    (compatible : H → Prop) (reflect : ∀ h, accept h = true ↔ compatible h) (h : H) :
    h ∈ reconstruct pool accept ↔ h ∈ pool ∧ compatible h := by
  rw [mem_reconstruct_iff, reflect]

/-- Fixed-model compatibility shrinks when a stronger checker is used. -/
theorem reconstruct_mono {H : Type} (pool : List H) (weak strong : H → Bool)
    (hrefine : ∀ h, strong h = true → weak h = true) :
    ∀ h ∈ reconstruct pool strong, h ∈ reconstruct pool weak := by
  intro h hh
  obtain ⟨hp, ha⟩ := (mem_reconstruct_iff pool strong h).mp hh
  exact (mem_reconstruct_iff pool weak h).mpr ⟨hp, hrefine h ha⟩

end Comparative
