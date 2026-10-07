import Historical.RuleInput
import Historical.Reconstruction

/-! Finite evidence analysis. Predictions are supplied with separately checked
derivations; this layer reasons about their declared observation matrix. -/
namespace Historical.Research
open Lean Rules Reconstruction

structure History where
  id : String
  agreements : List Bool
  predictions : List String
  deriving FromJson, ToJson

def fits (h : History) (indices : List Nat) : Bool :=
  indices.all fun i => h.agreements[i]?.getD false

def Fits (h : History) (indices : List Nat) : Prop :=
  ∀ i ∈ indices, h.agreements[i]?.getD false = true

theorem fits_iff (h : History) (indices : List Nat) : fits h indices = true ↔ Fits h indices := by
  simp [fits, Fits, List.all_eq_true]

theorem fits_mono (h : History) (small large : List Nat)
    (sub : ∀ i ∈ small, i ∈ large) (hf : Fits h large) : Fits h small := by
  intro i hi
  exact hf i (sub i hi)

def anyFits (histories : List History) (indices : List Nat) : Bool :=
  histories.any fun h => fits h indices

theorem anyFits_iff (histories : List History) (indices : List Nat) :
    anyFits histories indices = true ↔ ∃ h ∈ histories, Fits h indices := by
  simp [anyFits, List.any_eq_true, fits_iff]

def minimalConflict (histories : List History) (indices : List Nat) : Bool :=
  !anyFits histories indices && indices.all (fun i => anyFits histories (indices.erase i))

/-- For distinct observation indices, every single deletion being satisfiable
implies inclusion minimality, by monotonicity. -/
def MinimalConflict (histories : List History) (indices : List Nat) : Prop :=
  (¬ ∃ h ∈ histories, Fits h indices) ∧
  ∀ i ∈ indices, ∃ h ∈ histories, Fits h (indices.erase i)

theorem minimalConflict_iff (histories : List History) (indices : List Nat) :
    minimalConflict histories indices = true ↔ MinimalConflict histories indices := by
  simp [minimalConflict, MinimalConflict, List.all_eq_true, Bool.not_eq_true,
    ← Bool.not_eq_true, anyFits_iff]

theorem minimal_conflict_proper_subset (histories : List History) (core small : List Nat)
    (hc : MinimalConflict histories core) (sub : ∀ j ∈ small, j ∈ core)
    (proper : ∃ i ∈ core, i ∉ small) : ∃ h ∈ histories, Fits h small := by
  obtain ⟨i, hi, missing⟩ := proper
  obtain ⟨h, hh, hf⟩ := hc.2 i hi
  refine ⟨h, hh, fits_mono h small (core.erase i) ?_ hf⟩
  intro j hj
  have ne : j ≠ i := by
    intro eq
    exact missing (eq ▸ hj)
  exact (List.mem_erase_of_ne ne).mpr (sub j hj)

def subsets : List Nat → List (List Nat)
  | [] => [[]]
  | i :: rest => let ss := subsets rest; ss ++ ss.map (i :: ·)

theorem mem_subsets (core indices : List Nat) :
    core ∈ subsets indices ↔ core.Sublist indices := by
  induction indices generalizing core with
  | nil => simp [subsets]
  | cons i rest ih =>
    simp only [subsets, List.mem_append, List.mem_map, List.sublist_cons_iff]
    constructor
    · intro h
      rcases h with h | ⟨r, hr, he⟩
      · exact Or.inl ((ih core).mp h)
      · exact Or.inr ⟨r, he.symm, (ih r).mp hr⟩
    · intro h
      rcases h with h | ⟨r, he, hr⟩
      · exact Or.inl ((ih core).mpr h)
      · exact Or.inr ⟨r, (ih r).mpr hr, he.symm⟩

def conflicts (histories : List History) (indices : List Nat) (budget : Nat) : List (List Nat) :=
  ((subsets indices).take budget).filter (minimalConflict histories)

theorem reported_conflict_sound (histories : List History) (indices core : List Nat) (budget : Nat)
    (h : core ∈ conflicts histories indices budget) : MinimalConflict histories core := by
  exact (minimalConflict_iff _ _).mp (List.mem_filter.mp h).2

theorem conflicts_complete_in_enumeration (histories : List History) (indices core : List Nat)
    (h : core ∈ subsets indices) :
    core ∈ conflicts histories indices (subsets indices).length ↔ MinimalConflict histories core := by
  simp [conflicts, List.take_length, h, minimalConflict_iff]

theorem full_conflict_enumeration_correct (histories : List History) (indices core : List Nat) :
    core ∈ conflicts histories indices (subsets indices).length ↔
      core.Sublist indices ∧ MinimalConflict histories core := by
  simp [conflicts, List.take_length, mem_subsets, minimalConflict_iff]

def signature (h : History) (axis : List Nat) : List String :=
  axis.map fun i => h.predictions[i]?.getD ""

def Equivalent (axis : List Nat) (left right : History) : Prop :=
  signature left axis = signature right axis

theorem equivalent_refl (axis : List Nat) (h : History) : Equivalent axis h h := rfl
theorem equivalent_symm (axis : List Nat) (a b : History) (h : Equivalent axis a b) :
    Equivalent axis b a := h.symm
theorem equivalent_trans (axis : List Nat) (a b c : History)
    (ab : Equivalent axis a b) (bc : Equivalent axis b c) : Equivalent axis a c := ab.trans bc

def classMembers (histories : List History) (axis : List Nat) (key : List String) : List History :=
  histories.filter fun h => signature h axis == key

theorem class_members_correct (histories : List History) (axis : List Nat)
    (key : List String) (h : History) :
    h ∈ classMembers histories axis key ↔ h ∈ histories ∧ signature h axis = key := by
  simp [classMembers]

def groups (histories : List History) (axis : List Nat) : Json :=
  toJson (((histories.map (fun h => signature h axis)).eraseDups).map fun key =>
    Json.mkObj [("prediction", toJson key),
      ("histories", toJson ((classMembers histories axis key).map (·.id)))])

structure Matrix where
  schema_version : String
  id : String
  axes : List String
  selected : List Nat
  histories : List History
  subset_budget : Nat
  deriving FromJson, ToJson

def validateMatrix (r : Matrix) : Except String Unit := do
  if r.schema_version != "1.0.0" || !goodId r.id || r.axes.isEmpty || r.axes.length > 16 ||
      !unique r.axes || !(r.axes.all goodId) || r.selected.length > 12 ||
      r.selected.eraseDups != r.selected || !(r.selected.all (· < r.axes.length)) ||
      r.histories.isEmpty || r.histories.length > 1024 || !unique (r.histories.map (·.id)) ||
      r.subset_budget > 4096 then throw "Invalid matrix metadata or finite profile"
  for h in r.histories do
    if !goodId h.id || h.agreements.length != r.axes.length || h.predictions.length != r.axes.length then
      throw "History does not cover the declared axes"

def analyze (r : Matrix) : Json := Id.run do
  let surviving := r.histories.filter (fun h => fits h r.selected)
  let ss := subsets r.selected
  let cores := if surviving.isEmpty then conflicts r.histories r.selected r.subset_budget else []
  let complete := !surviving.isEmpty || ss.length ≤ r.subset_budget
  let probes := (List.range r.axes.length).filter (fun i => !r.selected.contains i)
  let probeResults := probes.map fun i =>
    let distinguished := (surviving.flatMap fun a => surviving.filter fun b =>
      a.id < b.id && signature a [i] != signature b [i]).length
    Json.mkObj [("axis", toJson i), ("partitions", groups surviving [i]),
      ("distinguished_pairs", toJson distinguished), ("discriminating", toJson (decide (distinguished > 0)))]
  return Json.mkObj [("input_valid", toJson true), ("id", toJson r.id),
    ("complete", toJson complete), ("conflicts_complete", toJson complete),
    ("subsets_examined", toJson (if surviving.isEmpty then min r.subset_budget ss.length else 0)),
    ("subset_space", toJson ss.length), ("minimal_conflicts", toJson cores),
    ("survivors", toJson (surviving.map (·.id))), ("equivalence_classes", groups surviving r.selected),
    ("probes", toJson probeResults)]

structure Precedence where
  earlier : String
  later : String
  deriving FromJson, ToJson

def precedes (edge : Precedence) (order : Word) : Bool :=
  decide (order.idxOf (.segment edge.earlier) < order.idxOf (.segment edge.later))

def ordered (edges : List Precedence) (order : Word) : Bool := edges.all (fun e => precedes e order)

def orders (ids : List String) (edges : List Precedence) : List Word :=
  (wordsExact (ids.map Atom.segment) ids.length).filter fun w =>
    w.eraseDups == w && ordered edges w

theorem order_enumeration_correct (ids : List String) (edges : List Precedence) (w : Word) :
    w ∈ orders ids edges ↔ w.length = ids.length ∧
      (∀ a ∈ w, a ∈ ids.map Atom.segment) ∧ w.eraseDups = w ∧ ordered edges w = true := by
  simp [orders, mem_wordsExact, and_assoc]

theorem order_respects_constraints (ids : List String) (edges : List Precedence) (w : Word)
    (h : w ∈ orders ids edges) : ∀ e ∈ edges, precedes e w = true := by
  have ho := ((order_enumeration_correct _ _ _).mp h).2.2.2
  simpa [ordered, List.all_eq_true] using ho

structure Chronology where
  schema_version : String
  id : String
  rule_ids : List String
  constraints : List Precedence
  deriving FromJson, ToJson

def validateChronology (r : Chronology) : Except String Unit := do
  if r.schema_version != "1.0.0" || !goodId r.id || r.rule_ids.length > 6 ||
      !unique r.rule_ids || !(r.rule_ids.all goodId) || r.constraints.length > 36 then
    throw "Invalid chronology (at most six distinct rules)"
  for e in r.constraints do
    if !r.rule_ids.contains e.earlier || !r.rule_ids.contains e.later then throw "Unknown rule in precedence constraint"

def chronologyResult (r : Chronology) : Json :=
  let found := orders r.rule_ids r.constraints
  Json.mkObj [("input_valid", toJson true), ("complete", toJson true), ("id", toJson r.id),
    ("cyclic", toJson found.isEmpty), ("orders", toJson found)]

end Historical.Research
