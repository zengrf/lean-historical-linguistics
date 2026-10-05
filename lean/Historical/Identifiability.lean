import Historical.Reconstruction

namespace Historical.Identifiability
open Rules Certificates Reconstruction

def ObsEquivalentOn (axis : List String) (left : Model) (x : Word) (right : Model) (y : Word) : Prop :=
  ∀ doc ∈ axis, predict left x doc = predict right y doc

theorem equivalent_refl (axis : List String) (model : Model) (w : Word) :
    ObsEquivalentOn axis model w model w := by intro _ _; rfl

theorem equivalent_symm (axis : List String) (left right : Model) (x y : Word)
    (h : ObsEquivalentOn axis left x right y) : ObsEquivalentOn axis right y left x := by
  intro doc hd; exact (h doc hd).symm

theorem equivalent_trans (axis : List String) (left middle right : Model) (x y z : Word)
    (hl : ObsEquivalentOn axis left x middle y) (hr : ObsEquivalentOn axis middle y right z) :
    ObsEquivalentOn axis left x right z := by
  intro doc hd; exact (hl doc hd).trans (hr doc hd)

def checkPrediction (prediction : Option Word) (form : Option (List Cell)) : Bool :=
  match prediction with
  | none => false
  | some w => formMatches form w

theorem observation_from_prediction (model : Model) (w : Word) (o : Observation) :
    checkObservation model w o = checkPrediction (predict model w o.doculect_id) o.form := by
  cases h : lookup model o.doculect_id <;> simp [checkObservation, predict, checkPrediction, h]

theorem equivalent_fits (axis : List String) (left right : Model) (x y : Word)
    (obs : List Observation) (covered : ∀ o ∈ obs, o.doculect_id ∈ axis)
    (h : ObsEquivalentOn axis left x right y) : Fits left obs x ↔ Fits right obs y := by
  have point : ∀ o ∈ obs, Observes left x o ↔ Observes right y o := by
    intro o ho
    rw [← checkObservation_iff, ← checkObservation_iff,
      observation_from_prediction, observation_from_prediction, h o.doculect_id (covered o ho)]
  constructor
  · intro hf o ho; exact (point o ho).mp (hf o ho)
  · intro hf o ho; exact (point o ho).mpr (hf o ho)

/-- The model, word, and interpretation of observations are held fixed. -/
theorem fits_mono (model : Model) (small large : List Observation) (w : Word)
    (hsub : ∀ o ∈ small, o ∈ large) (h : Fits model large w) : Fits model small w := by
  intro o ho; exact h o (hsub o ho)

def FormRefines (weak strong : Option (List Cell)) : Prop :=
  ∀ w, FormMatches strong w → FormMatches weak w

theorem missing_is_weaker (form : Option (List Cell)) : FormRefines none form := by
  intro _ _; trivial

def ObservationRefines (weak strong : Observation) : Prop :=
  weak.doculect_id = strong.doculect_id ∧ FormRefines weak.form strong.form

theorem observes_refinement (model : Model) (w : Word) (weak strong : Observation)
    (h : ObservationRefines weak strong) (hf : Observes model w strong) : Observes model w weak := by
  obtain ⟨b, hb, out, hd, hm⟩ := hf
  refine ⟨b, ?_, out, hd, h.2 out hm⟩
  rw [h.1]
  exact hb

def DataRefines (weak strong : List Observation) : Prop :=
  ∀ o ∈ weak, ∃ s ∈ strong, ObservationRefines o s

theorem fits_refinement (model : Model) (w : Word) (weak strong : List Observation)
    (h : DataRefines weak strong) (hf : Fits model strong w) : Fits model weak w := by
  intro o ho
  obtain ⟨s, hs, hr⟩ := h o ho
  exact observes_refinement model w o s hr (hf s hs)

def reconstructWords (alphabet : List Atom) (bound : Nat) (model : Model) (obs : List Observation) : List Word :=
  (protoWords alphabet bound).filter (fits model obs)

theorem mem_reconstructWords (alphabet : List Atom) (bound : Nat) (model : Model)
    (obs : List Observation) (w : Word) : w ∈ reconstructWords alphabet bound model obs ↔
    InWordSpace alphabet bound w ∧ Fits model obs w := by
  simp [reconstructWords, mem_protoWords, fits_iff]

theorem reconstruction_mono (alphabet : List Atom) (bound : Nat) (model : Model)
    (small large : List Observation) (hsub : ∀ o ∈ small, o ∈ large) :
    ∀ w ∈ reconstructWords alphabet bound model large, w ∈ reconstructWords alphabet bound model small := by
  intro w hw
  obtain ⟨hs, hf⟩ := (mem_reconstructWords _ _ _ _ _).mp hw
  exact (mem_reconstructWords _ _ _ _ _).mpr ⟨hs, fits_mono model small large w hsub hf⟩

theorem reconstruction_refinement (alphabet : List Atom) (bound : Nat) (model : Model)
    (weak strong : List Observation) (h : DataRefines weak strong) :
    ∀ w ∈ reconstructWords alphabet bound model strong, w ∈ reconstructWords alphabet bound model weak := by
  intro w hw
  obtain ⟨hs, hf⟩ := (mem_reconstructWords _ _ _ _ _).mp hw
  exact (mem_reconstructWords _ _ _ _ _).mpr ⟨hs, fits_refinement model w weak strong h hf⟩

theorem equivalent_membership (alphabet : List Atom) (bound : Nat) (axis : List String)
    (left right : Model) (x y : Word) (obs : List Observation)
    (hx : InWordSpace alphabet bound x) (hy : InWordSpace alphabet bound y)
    (covered : ∀ o ∈ obs, o.doculect_id ∈ axis) (h : ObsEquivalentOn axis left x right y) :
    x ∈ reconstructWords alphabet bound left obs ↔ y ∈ reconstructWords alphabet bound right obs := by
  simp only [mem_reconstructWords, hx, hy, true_and]
  exact equivalent_fits axis left right x y obs covered h

def mergerLaw : Law := ⟨"merge", "proto", "daughter",
  ⟨["b"], some "p", [], [], false, false, .leftToRight, .simultaneous⟩⟩

def merger : Model := [⟨"A", [mergerLaw]⟩, ⟨"B", [mergerLaw]⟩]
def mergedObservations : List Observation :=
  [⟨"A", some [.segment "p"]⟩, ⟨"B", some [.segment "p"]⟩]

theorem merger_is_indistinguishable :
    ObsEquivalentOn ["A", "B"] merger [.segment "p"] merger [.segment "b"] := by
  intro doc hd
  simp only [List.mem_cons, List.not_mem_nil, or_false] at hd
  rcases hd with h | h <;> subst doc <;> decide

theorem merger_retains_both_ancestors :
    [.segment "p"] ∈ reconstructWords [.segment "p", .segment "b"] 1 merger mergedObservations ∧
    [.segment "b"] ∈ reconstructWords [.segment "p", .segment "b"] 1 merger mergedObservations ∧
    ([.segment "p"] : Word) ≠ [.segment "b"] := by decide

def identityModel : Model := [⟨"A", []⟩, ⟨"B", []⟩]
def linkedAB : Scenario := ⟨"ab", identityModel,
  [⟨"A", some [.segment "a"]⟩, ⟨"B", some [.segment "b"]⟩]⟩
def linkedBA : Scenario := ⟨"ba", identityModel,
  [⟨"A", some [.segment "b"]⟩, ⟨"B", some [.segment "a"]⟩]⟩
def inventedAA : Scenario := ⟨"hybrid", identityModel,
  [⟨"A", some [.segment "a"]⟩, ⟨"B", some [.segment "a"]⟩]⟩

theorem linked_alternatives_do_not_license_hybrids :
    reconstruct [.segment "a", .segment "b"] 1 [linkedAB, linkedBA] = [] ∧
    accepts ⟨inventedAA, [.segment "a"]⟩ = true := by decide

theorem unexamined_empty_is_not_exhaustion :
    prefixResults [⟨inventedAA, [.segment "a"]⟩] 0 = [] ∧
    reconstruct [.segment "a"] 1 [inventedAA] ≠ [] := by decide

end Historical.Identifiability
