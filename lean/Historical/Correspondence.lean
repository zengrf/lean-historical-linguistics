import Historical.Alignment

namespace Historical.Correspondence

def Unavailable : Cell → Prop
  | .missing | .unknown _ => True
  | _ => False

def Agrees (x y : Cell) : Prop := Unavailable x ∨ Unavailable y ∨ x = y

def SharedSound (x y : Cell) : Prop := ∃ s, x = .segment s ∧ y = .segment s

def cellAgrees (x y : Cell) : Bool :=
  match x, y with
  | .missing, _ | _, .missing | .unknown _, _ | _, .unknown _ => true
  | _, _ => decide (x = y)

def sharedSound : Cell → Cell → Bool
  | .segment a, .segment b => decide (a = b)
  | _, _ => false

theorem cellAgrees_iff (x y : Cell) : cellAgrees x y = true ↔ Agrees x y := by
  cases x <;> cases y <;> simp [cellAgrees, Agrees, Unavailable]

theorem sharedSound_iff (x y : Cell) : sharedSound x y = true ↔ SharedSound x y := by
  cases x <;> cases y <;> simp [sharedSound, SharedSound, eq_comm]

/-- Failure on unequal lengths prevents silent truncation of the doculect axis. -/
def noConflict : List Cell → List Cell → Bool
  | [], [] => true
  | x :: xs, y :: ys => cellAgrees x y && noConflict xs ys
  | _, _ => false

def hasShared : List Cell → List Cell → Bool
  | x :: xs, y :: ys => sharedSound x y || hasShared xs ys
  | _, _ => false

def AgreeRows (xs ys : List Cell) : Prop :=
  xs.length = ys.length ∧ ∀ p ∈ xs.zip ys, Agrees p.1 p.2

def ShareRows (xs ys : List Cell) : Prop := ∃ p ∈ xs.zip ys, SharedSound p.1 p.2

theorem noConflict_iff (xs ys : List Cell) : noConflict xs ys = true ↔ AgreeRows xs ys := by
  induction xs generalizing ys with
  | nil => cases ys <;> simp [noConflict, AgreeRows]
  | cons x xs ih =>
      cases ys with
      | nil => simp [noConflict, AgreeRows]
      | cons y ys =>
          simp [noConflict, AgreeRows, cellAgrees_iff, ih, and_assoc, and_left_comm, and_comm]

theorem hasShared_iff (xs ys : List Cell) : hasShared xs ys = true ↔ ShareRows xs ys := by
  induction xs generalizing ys with
  | nil => cases ys <;> simp [hasShared, ShareRows]
  | cons x xs ih =>
      cases ys with
      | nil => simp [hasShared, ShareRows]
      | cons y ys => simp [hasShared, ShareRows, sharedSound_iff, ih]

def compatible (xs ys : List Cell) : Bool := noConflict xs ys && hasShared xs ys

def Compatible (xs ys : List Cell) : Prop := AgreeRows xs ys ∧ ShareRows xs ys

theorem compatible_iff (xs ys : List Cell) : compatible xs ys = true ↔ Compatible xs ys := by
  simp [compatible, Compatible, noConflict_iff, hasShared_iff]

theorem missing_only_no_support (n : Nat) (ys : List Cell) :
    hasShared (List.replicate n .missing) ys = false := by
  induction n generalizing ys with
  | zero => simp [hasShared]
  | succ n ih => cases ys <;> simp [List.replicate_succ, hasShared, sharedSound, ih]

theorem unknown_only_no_support (n : Nat) (s : String) (ys : List Cell) :
    hasShared (List.replicate n (.unknown s)) ys = false := by
  induction n generalizing ys with
  | zero => simp [hasShared]
  | succ n ih => cases ys <;> simp [List.replicate_succ, hasShared, sharedSound, ih]

theorem gap_only_no_support (n : Nat) (ys : List Cell) :
    hasShared (List.replicate n .gap) ys = false := by
  induction n generalizing ys with
  | zero => simp [hasShared]
  | succ n ih => cases ys <;> simp [List.replicate_succ, hasShared, sharedSound, ih]

structure Site where
  id : String
  evidence_unit : String
  cells : List Cell
  deriving Repr, DecidableEq

structure Group where
  id : String
  members : List String
  claimed_support : Nat
  deriving Repr, DecidableEq

def select (sites : List Site) (members : List String) : List Site :=
  sites.filter fun s => decide (s.id ∈ members)

def hasObserved (s : Site) : Bool := s.cells.any Alignment.isSegment

/-- Keep each label once. The proof below fixes the meaning of deduplication. -/
def distinctUnits : List String → List String
  | [] => []
  | u :: us =>
      let tail := distinctUnits us
      if u ∈ tail then tail else u :: tail

theorem mem_distinctUnits (unit : String) (units : List String) :
    unit ∈ distinctUnits units ↔ unit ∈ units := by
  induction units with
  | nil => simp [distinctUnits]
  | cons u us ih =>
      by_cases h : u ∈ distinctUnits us
      · simp only [distinctUnits, if_pos h, List.mem_cons]
        constructor
        · intro hu; exact Or.inr (ih.mp hu)
        · intro hu
          rcases hu with he | ht
          · subst unit; exact h
          · exact ih.mpr ht
      · simp [distinctUnits, h, ih]

theorem distinctUnits_nodup (units : List String) : (distinctUnits units).Nodup := by
  induction units with
  | nil => simp [distinctUnits]
  | cons u us ih =>
      simp only [distinctUnits]
      split
      · exact ih
      · exact List.nodup_cons.mpr ⟨by assumption, ih⟩

def supportUnits (sites : List Site) : List String :=
  distinctUnits ((sites.filter hasObserved).map (·.evidence_unit))

theorem mem_supportUnits (unit : String) (sites : List Site) :
    unit ∈ supportUnits sites ↔ ∃ s ∈ sites, hasObserved s = true ∧ s.evidence_unit = unit := by
  simp [supportUnits, mem_distinctUnits, and_assoc]

def checkClique (sites : List Site) : Bool :=
  sites.all fun s => sites.all fun t => decide (s.id = t.id) || compatible s.cells t.cells

def Clique (sites : List Site) : Prop :=
  ∀ s ∈ sites, ∀ t ∈ sites, s.id = t.id ∨ Compatible s.cells t.cells

theorem checkClique_iff (sites : List Site) : checkClique sites = true ↔ Clique sites := by
  simp [checkClique, Clique, List.all_eq_true, compatible_iff]

def checkGroup (sites : List Site) (g : Group) : Bool :=
  decide ((sites.map (·.id)).Nodup) && decide (g.members ≠ []) && decide g.members.Nodup &&
    g.members.all (fun id => decide (id ∈ sites.map (·.id))) &&
    (select sites g.members).all hasObserved && checkClique (select sites g.members) &&
    decide (g.claimed_support = (supportUnits (select sites g.members)).length) &&
    decide (0 < g.claimed_support)

def ValidGroup (sites : List Site) (g : Group) : Prop :=
  (sites.map (·.id)).Nodup ∧ g.members ≠ [] ∧ g.members.Nodup ∧
    (∀ id ∈ g.members, id ∈ sites.map (·.id)) ∧
    (∀ s ∈ select sites g.members, hasObserved s = true) ∧ Clique (select sites g.members) ∧
    g.claimed_support = (supportUnits (select sites g.members)).length ∧ 0 < g.claimed_support

theorem checkGroup_iff (sites : List Site) (g : Group) : checkGroup sites g = true ↔ ValidGroup sites g := by
  simp [checkGroup, ValidGroup, List.all_eq_true, checkClique_iff, and_assoc]

theorem accepted_group_pairwise (sites : List Site) (g : Group) (h : checkGroup sites g = true)
    (s t : Site) (hs : s ∈ select sites g.members) (ht : t ∈ select sites g.members)
    (hne : s.id ≠ t.id) : Compatible s.cells t.cells := by
  have hc := ((checkGroup_iff _ _).mp h).2.2.2.2.2.1 s hs t ht
  exact hc.resolve_left hne

theorem accepted_group_support (sites : List Site) (g : Group) (h : checkGroup sites g = true) :
    g.claimed_support = (supportUnits (select sites g.members)).length := by
  exact ((checkGroup_iff _ _).mp h).2.2.2.2.2.2.1

/-- Sum occurrences, so duplicate membership within or across groups is counted. -/
def occurrences (id : String) (groups : List Group) : Nat :=
  (groups.map fun g => g.members.count id).sum

def checkPartition (sites : List Site) (groups : List Group) : Bool :=
  decide (sites ≠ []) && decide ((sites.map (·.id)).Nodup) &&
    decide ((groups.map (·.id)).Nodup) && groups.all (checkGroup sites) &&
    sites.all (fun s => decide (occurrences s.id groups = 1))

def FeasiblePartition (sites : List Site) (groups : List Group) : Prop :=
  sites ≠ [] ∧ (sites.map (·.id)).Nodup ∧ (groups.map (·.id)).Nodup ∧
    (∀ g ∈ groups, ValidGroup sites g) ∧ (∀ s ∈ sites, occurrences s.id groups = 1)

theorem checkPartition_iff (sites : List Site) (groups : List Group) :
    checkPartition sites groups = true ↔ FeasiblePartition sites groups := by
  simp [checkPartition, FeasiblePartition, List.all_eq_true, checkGroup_iff, and_assoc]

theorem accepted_partition_exactly_once (sites : List Site) (groups : List Group)
    (h : checkPartition sites groups = true) (s : Site) (hs : s ∈ sites) :
    occurrences s.id groups = 1 := by
  exact ((checkPartition_iff _ _).mp h).2.2.2.2 s hs

theorem accepted_partition_groups_valid (sites : List Site) (groups : List Group)
    (h : checkPartition sites groups = true) (g : Group) (hg : g ∈ groups) : ValidGroup sites g := by
  exact ((checkPartition_iff _ _).mp h).2.2.2.1 g hg

def exampleA : Site := ⟨"a", "root-a", [.segment "p", .segment "t"]⟩
def exampleB : Site := ⟨"b", "root-b", [.segment "p", .missing]⟩
def exampleC : Site := ⟨"c", "root-c", [.segment "p", .segment "k"]⟩

theorem compatibility_not_transitive :
    compatible exampleA.cells exampleB.cells = true ∧
    compatible exampleB.cells exampleC.cells = true ∧
    compatible exampleA.cells exampleC.cells = false := by decide

theorem nontransitive_merge_rejected :
    checkGroup [exampleA, exampleB, exampleC] ⟨"bad", ["a", "b", "c"], 3⟩ = false := by decide

theorem missing_differs_from_gap :
    compatible [.segment "p", .missing] [.segment "p", .segment "t"] = true ∧
    compatible [.segment "p", .gap] [.segment "p", .segment "t"] = false := by decide

theorem disjoint_observations_not_support :
    compatible [.segment "p", .missing] [.missing, .segment "t"] = false := by decide

theorem repeated_unit_not_extra_support :
    (supportUnits [exampleA, { exampleA with id := "another-position" }]).length = 1 := by decide

end Historical.Correspondence
