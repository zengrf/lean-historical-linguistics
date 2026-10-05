import Historical.Certificates
import Historical.Alignment

namespace Historical.Reconstruction
open Rules Certificates

/-- Enumerate every sequence of exactly the declared length, in alphabet order. -/
def wordsExact (alphabet : List Atom) : Nat → List Word
  | 0 => [[]]
  | n + 1 => alphabet.flatMap fun a => (wordsExact alphabet n).map (a :: ·)

theorem mem_wordsExact (alphabet : List Atom) (n : Nat) (w : Word) :
    w ∈ wordsExact alphabet n ↔ w.length = n ∧ ∀ a ∈ w, a ∈ alphabet := by
  induction n generalizing w with
  | zero => cases w <;> simp [wordsExact]
  | succ n ih =>
      cases w with
      | nil => simp [wordsExact]
      | cons a w => simp [wordsExact, ih, and_assoc, and_left_comm, and_comm]

def wordsUpTo (alphabet : List Atom) : Nat → List Word
  | 0 => [[]]
  | n + 1 => wordsUpTo alphabet n ++ wordsExact alphabet (n + 1)

def wordCount (alphabetSize : Nat) : Nat → Nat
  | 0 => 1
  | n + 1 => wordCount alphabetSize n + alphabetSize ^ (n + 1)

theorem length_prefixed (alphabet : List Atom) (ws : List Word) :
    (alphabet.flatMap fun a => ws.map (a :: ·)).length = alphabet.length * ws.length := by
  induction alphabet with
  | nil => simp
  | cons a rest ih => simp [List.flatMap_cons, ih, Nat.succ_mul, Nat.add_comm]

theorem length_wordsExact (alphabet : List Atom) (n : Nat) :
    (wordsExact alphabet n).length = alphabet.length ^ n := by
  induction n with
  | zero => simp [wordsExact]
  | succ n ih =>
      rw [wordsExact, length_prefixed, ih, Nat.pow_succ]
      exact Nat.mul_comm _ _

theorem length_wordsUpTo (alphabet : List Atom) (n : Nat) :
    (wordsUpTo alphabet n).length = wordCount alphabet.length n := by
  induction n with
  | zero => simp [wordsUpTo, wordCount]
  | succ n ih => simp [wordsUpTo, wordCount, ih, length_wordsExact]

theorem mem_wordsUpTo (alphabet : List Atom) (n : Nat) (w : Word) :
    w ∈ wordsUpTo alphabet n ↔ w.length ≤ n ∧ ∀ a ∈ w, a ∈ alphabet := by
  induction n with
  | zero => cases w <;> simp [wordsUpTo]
  | succ n ih =>
      simp only [wordsUpTo, List.mem_append, ih, mem_wordsExact]
      constructor
      · intro h
        rcases h with h | h
        · exact ⟨Nat.le_trans h.1 (Nat.le_succ n), h.2⟩
        · exact ⟨Nat.le_of_eq h.1, h.2⟩
      · intro ⟨hl, ha⟩
        by_cases h : w.length ≤ n
        · exact Or.inl ⟨h, ha⟩
        · exact Or.inr ⟨by omega, ha⟩

def atomCell : Atom → Cell
  | .segment s => .segment s
  | .morpheme => .boundary "+"

def wordShape (w : Word) : Bool := Alignment.boundaryLayout (w.map atomCell)

def protoWords (alphabet : List Atom) (bound : Nat) : List Word :=
  (wordsUpTo alphabet bound).filter wordShape

def InWordSpace (alphabet : List Atom) (bound : Nat) (w : Word) : Prop :=
  w.length ≤ bound ∧ (∀ a ∈ w, a ∈ alphabet) ∧ wordShape w = true

theorem mem_protoWords (alphabet : List Atom) (bound : Nat) (w : Word) :
    w ∈ protoWords alphabet bound ↔ InWordSpace alphabet bound w := by
  simp [protoWords, mem_wordsUpTo, InWordSpace, and_assoc]

inductive CellMatches : Cell → Atom → Prop where
  | segment (s : String) : CellMatches (.segment s) (.segment s)
  | boundary : CellMatches (.boundary "+") .morpheme
  | unknown (reading s : String) : CellMatches (.unknown reading) (.segment s)

def cellMatches : Cell → Atom → Bool
  | .segment s, .segment t => decide (s = t)
  | .boundary s, .morpheme => decide (s = "+")
  | .unknown _, .segment _ => true
  | _, _ => false

theorem cellMatches_iff (c : Cell) (a : Atom) : cellMatches c a = true ↔ CellMatches c a := by
  constructor
  · intro h
    cases c <;> cases a <;> simp [cellMatches] at h
    · subst h; exact CellMatches.segment _
    · subst h; exact CellMatches.boundary
    · exact CellMatches.unknown _ _
  · intro h; cases h <;> simp [cellMatches]

def cellsMatch : List Cell → Word → Bool
  | [], [] => true
  | c :: cs, a :: w => cellMatches c a && cellsMatch cs w
  | _, _ => false

inductive CellsMatch : List Cell → Word → Prop where
  | nil : CellsMatch [] []
  | cons {c cs a w} : CellMatches c a → CellsMatch cs w → CellsMatch (c :: cs) (a :: w)

theorem cellsMatch_iff (cs : List Cell) (w : Word) : cellsMatch cs w = true ↔ CellsMatch cs w := by
  induction cs generalizing w with
  | nil =>
      cases w with
      | nil => exact ⟨fun _ => CellsMatch.nil, fun _ => rfl⟩
      | cons a w => constructor <;> intro h; cases h; cases h
  | cons c cs ih =>
      cases w with
      | nil => constructor <;> intro h; cases h; cases h
      | cons a w =>
          constructor
          · intro h
            have hh : cellMatches c a = true ∧ cellsMatch cs w = true := by simpa [cellsMatch] using h
            exact CellsMatch.cons ((cellMatches_iff _ _).mp hh.1) ((ih _).mp hh.2)
          · intro h
            cases h with
            | cons hc ht => simp [cellsMatch, (cellMatches_iff _ _).mpr hc, (ih _).mpr ht]

def formMatches (form : Option (List Cell)) (w : Word) : Bool :=
  match form with
  | none => true
  | some cs => cellsMatch cs w

def FormMatches (form : Option (List Cell)) (w : Word) : Prop :=
  match form with
  | none => True
  | some cs => CellsMatch cs w

theorem formMatches_iff (form : Option (List Cell)) (w : Word) :
    formMatches form w = true ↔ FormMatches form w := by
  cases form <;> simp [formMatches, FormMatches, cellsMatch_iff]

structure Branch where
  doculect_id : String
  laws : List Law
  deriving DecidableEq, Repr

abbrev Model := List Branch

structure Observation where
  doculect_id : String
  form : Option (List Cell)
  deriving DecidableEq, Repr

def lookup (model : Model) (doculect : String) : Option Branch :=
  model.find? (fun b => b.doculect_id == doculect)

def predict (model : Model) (w : Word) (doculect : String) : Option Word :=
  (lookup model doculect).map (fun b => run b.laws w)

def checkObservation (model : Model) (w : Word) (o : Observation) : Bool :=
  match lookup model o.doculect_id with
  | none => false
  | some b => formMatches o.form (run b.laws w)

/-- Licensed forward derivation, with a mask only at explicitly unknown cells. -/
def Observes (model : Model) (w : Word) (o : Observation) : Prop :=
  ∃ b, lookup model o.doculect_id = some b ∧
    ∃ out, Derives b.laws w out ∧ FormMatches o.form out

theorem checkObservation_iff (model : Model) (w : Word) (o : Observation) :
    checkObservation model w o = true ↔ Observes model w o := by
  unfold Observes
  cases h : lookup model o.doculect_id with
  | none => simp [checkObservation, h]
  | some b => simp [checkObservation, h, formMatches_iff, derives_iff_run]

def fits (model : Model) (observations : List Observation) (w : Word) : Bool :=
  observations.all (checkObservation model w)

def Fits (model : Model) (observations : List Observation) (w : Word) : Prop :=
  ∀ o ∈ observations, Observes model w o

theorem fits_iff (model : Model) (observations : List Observation) (w : Word) :
    fits model observations w = true ↔ Fits model observations w := by
  simp [fits, Fits, List.all_eq_true, checkObservation_iff]

/-- A scenario is a whole joint model and observation tuple, never a product of readings. -/
structure Scenario where
  id : String
  model : Model
  observations : List Observation
  deriving DecidableEq, Repr

structure Candidate where
  scenario : Scenario
  protoform : Word
  deriving DecidableEq, Repr

def space (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario) : List Candidate :=
  scenarios.flatMap fun s => (protoWords alphabet bound).map (Candidate.mk s)

def InSpace (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario) (c : Candidate) : Prop :=
  c.scenario ∈ scenarios ∧ InWordSpace alphabet bound c.protoform

theorem mem_space (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario) (c : Candidate) :
    c ∈ space alphabet bound scenarios ↔ InSpace alphabet bound scenarios c := by
  rcases c with ⟨s, w⟩
  simp [space, InSpace, mem_protoWords]

def accepts (c : Candidate) : Bool := fits c.scenario.model c.scenario.observations c.protoform

def CandidateFits (c : Candidate) : Prop := Fits c.scenario.model c.scenario.observations c.protoform

theorem accepts_iff (c : Candidate) : accepts c = true ↔ CandidateFits c := fits_iff _ _ _

def reconstruct (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario) : List Candidate :=
  (space alphabet bound scenarios).filter accepts

theorem reconstruction_correct (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario)
    (c : Candidate) : c ∈ reconstruct alphabet bound scenarios ↔
    InSpace alphabet bound scenarios c ∧ CandidateFits c := by
  simp [reconstruct, mem_space, accepts_iff]

theorem candidate_sound (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario)
    (c : Candidate) (h : c ∈ reconstruct alphabet bound scenarios) : CandidateFits c :=
  ((reconstruction_correct _ _ _ _).mp h).2

theorem candidate_complete (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario)
    (c : Candidate) (hs : InSpace alphabet bound scenarios c) (hf : CandidateFits c) :
    c ∈ reconstruct alphabet bound scenarios := (reconstruction_correct _ _ _ _).mpr ⟨hs, hf⟩

theorem alternatives_remain_joint (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario)
    (c : Candidate) (h : c ∈ reconstruct alphabet bound scenarios) :
    c.scenario ∈ scenarios ∧ ∀ o ∈ c.scenario.observations, Observes c.scenario.model c.protoform o := by
  obtain ⟨hs, hf⟩ := (reconstruction_correct _ _ _ _).mp h
  exact ⟨hs.1, hf⟩

def prefixResults (pool : List Candidate) (examined : Nat) : List Candidate :=
  (pool.take examined).filter accepts

theorem mem_prefixResults (pool : List Candidate) (examined : Nat) (c : Candidate) :
    c ∈ prefixResults pool examined ↔ c ∈ pool.take examined ∧ CandidateFits c := by
  simp [prefixResults, accepts_iff]

theorem prefix_results_sound (pool : List Candidate) (examined : Nat) (c : Candidate)
    (h : c ∈ prefixResults pool examined) : CandidateFits c :=
  ((mem_prefixResults _ _ _).mp h).2

theorem prefix_results_in_space (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario)
    (examined : Nat) (c : Candidate) (h : c ∈ prefixResults (space alphabet bound scenarios) examined) :
    InSpace alphabet bound scenarios c :=
  (mem_space _ _ _ _).mp (List.mem_of_mem_take ((mem_prefixResults _ _ _).mp h).1)

def prefixComplete (pool : List Candidate) (examined : Nat) : Bool := decide (pool.length ≤ examined)

theorem prefixComplete_iff (pool : List Candidate) (examined : Nat) :
    prefixComplete pool examined = true ↔ pool.length ≤ examined := by
  simp only [prefixComplete, decide_eq_true_eq]

theorem completed_prefix_eq (pool : List Candidate) (examined : Nat) (h : pool.length ≤ examined) :
    prefixResults pool examined = pool.filter accepts := by
  simp [prefixResults, List.take_of_length_le h]

theorem completed_search_correct (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario)
    (examined : Nat) (h : prefixComplete (space alphabet bound scenarios) examined = true) (c : Candidate) :
    c ∈ prefixResults (space alphabet bound scenarios) examined ↔
    InSpace alphabet bound scenarios c ∧ CandidateFits c := by
  rw [completed_prefix_eq _ _ ((prefixComplete_iff _ _).mp h)]
  exact reconstruction_correct _ _ _ _

theorem completed_empty_iff (alphabet : List Atom) (bound : Nat) (scenarios : List Scenario) :
    reconstruct alphabet bound scenarios = [] ↔
      ¬ ∃ c, InSpace alphabet bound scenarios c ∧ CandidateFits c := by
  constructor
  · intro h ⟨c, hs, hf⟩
    have hc := candidate_complete alphabet bound scenarios c hs hf
    rw [h] at hc
    cases hc
  · intro h
    apply List.eq_nil_iff_forall_not_mem.mpr
    intro c hc
    exact h ⟨c, (reconstruction_correct _ _ _ _).mp hc⟩

theorem candidate_trace_accepted (c : Candidate) (b : Branch) :
    checkTrace b.laws c.protoform (trace b.laws c.protoform) (run b.laws c.protoform) = true :=
  canonical_trace_accepted _ _

theorem missing_form_unconstrained (w : Word) : formMatches none w = true := rfl

theorem present_empty_differs_from_missing :
    formMatches (some []) [.segment "p"] = false ∧ formMatches none [.segment "p"] = true := by decide

theorem unknown_is_one_segment :
    formMatches (some [.unknown "?"]) [.segment "p"] = true ∧
    formMatches (some [.unknown "?"]) [] = false ∧
    formMatches (some [.unknown "?"]) [.morpheme] = false := by decide

end Historical.Reconstruction
