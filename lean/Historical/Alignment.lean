import Historical.Evidence

namespace Historical.Alignment

def removeGaps : List Cell → List Cell
  | [] => []
  | c :: cs => if c = .gap then removeGaps cs else c :: removeGaps cs

/-- Only gaps may be inserted; all original cells retain their order and value. -/
inductive GapInsertion : List Cell → List Cell → Prop where
  | nil : GapInsertion [] []
  | gap {original aligned} : GapInsertion original aligned →
      GapInsertion original (.gap :: aligned)
  | keep {c original aligned} : c ≠ .gap → GapInsertion original aligned →
      GapInsertion (c :: original) (c :: aligned)

theorem removeGaps_iff (aligned original : List Cell) :
    removeGaps aligned = original ↔ GapInsertion original aligned := by
  induction aligned generalizing original with
  | nil =>
      constructor
      · intro h; simp [removeGaps] at h; subst original; exact GapInsertion.nil
      · intro h; cases h; rfl
  | cons c cs ih =>
      constructor
      · intro h
        subst original
        by_cases hg : c = .gap
        · subst c
          simp only [removeGaps, if_pos rfl]
          exact GapInsertion.gap ((ih _).mp rfl)
        · simp only [removeGaps, if_neg hg]
          exact GapInsertion.keep hg ((ih _).mp rfl)
      · intro h
        cases h with
        | gap ht => simpa [removeGaps] using (ih _).mpr ht
        | keep hg ht => simp [removeGaps, hg, (ih _).mpr ht]

structure Row where
  original : Option (List Cell)
  aligned : Option (List Cell)
  deriving Repr, DecidableEq

def recover (aligned : Option (List Cell)) : Option (List Cell) := aligned.map removeGaps

def RowRelated (r : Row) : Prop :=
  match r.original, r.aligned with
  | none, none => True
  | some original, some aligned => GapInsertion original aligned
  | _, _ => False

def checkRow (r : Row) : Bool := decide (recover r.aligned = r.original)

theorem checkRow_iff (r : Row) : checkRow r = true ↔ RowRelated r := by
  rcases r with ⟨original, aligned⟩
  cases original <;> cases aligned <;> simp [checkRow, recover, RowRelated, removeGaps_iff]

theorem accepted_row_recovers (r : Row) (h : checkRow r = true) :
    recover r.aligned = r.original := by simpa [checkRow] using h

theorem missing_is_not_erased : removeGaps [.missing, .gap] = [.missing] := by decide

theorem missing_row_ne_empty : (none : Option (List Cell)) ≠ some [] := by decide

def isSegment : Cell → Bool
  | .segment _ => true
  | _ => false

def isBoundary : Cell → Bool
  | .boundary _ => true
  | _ => false

def isMaterial : Cell → Bool
  | .gap | .missing => false
  | _ => true

/-- Explicit boundaries separate nonempty spans; they cannot lead or trail. -/
def boundaryLayout : List Cell → Bool
  | [] => true
  | c :: cs =>
      !isBoundary c && go c cs
where
  go (previous : Cell) : List Cell → Bool
    | [] => !isBoundary previous
    | c :: cs => !(isBoundary previous && isBoundary c) && go c cs

def originalShape : Option (List Cell) → Bool
  | none => true
  | some cs => cs.all isMaterial && boundaryLayout cs

def alignedShape (width : Nat) : Option (List Cell) → Bool
  | none => true
  | some cs => decide (cs.length = width) && cs.all (fun c => decide (c ≠ .missing))

def column (rows : List Row) (index : Nat) : List Cell :=
  rows.map fun r => match r.aligned with
    | none => .missing
    | some cs => cs[index]?.getD .missing

def boundaryColumn (cs : List Cell) : Bool :=
  if cs.any isBoundary then
    cs.all fun c => match c with
      | .boundary "+" | .gap | .missing => true
      | _ => false
  else true

def checkAlignment (width : Nat) (rows : List Row) : Bool :=
  decide (0 < width) && decide (2 ≤ rows.length) &&
    rows.all (fun r => checkRow r && originalShape r.original && alignedShape width r.aligned) &&
    (List.range width).all (fun i => (column rows i).any isMaterial && boundaryColumn (column rows i))

def ValidAlignment (width : Nat) (rows : List Row) : Prop :=
  0 < width ∧ 2 ≤ rows.length ∧
    (∀ r ∈ rows, RowRelated r ∧ originalShape r.original = true ∧ alignedShape width r.aligned = true) ∧
    (∀ i ∈ List.range width, (column rows i).any isMaterial = true ∧ boundaryColumn (column rows i) = true)

theorem checkAlignment_iff (width : Nat) (rows : List Row) :
    checkAlignment width rows = true ↔ ValidAlignment width rows := by
  simp [checkAlignment, ValidAlignment, List.all_eq_true, checkRow_iff, and_assoc]

theorem accepted_alignment_preserves_rows (width : Nat) (rows : List Row)
    (h : checkAlignment width rows = true) (r : Row) (hr : r ∈ rows) :
    recover r.aligned = r.original := by
  have hh := ((checkAlignment_iff _ _).mp h).2.2.1 r hr
  exact accepted_row_recovers r ((checkRow_iff r).mpr hh.1)

theorem accepted_alignment_preserves_absence (width : Nat) (rows : List Row)
    (h : checkAlignment width rows = true) (r : Row) (hr : r ∈ rows) :
    r.original = none ↔ r.aligned = none := by
  have he := accepted_alignment_preserves_rows width rows h r hr
  rw [← he]
  cases r.aligned <;> simp [recover]

theorem accepted_alignment_has_material (width : Nat) (rows : List Row)
    (h : checkAlignment width rows = true) (i : Nat) (hi : i < width) :
    (column rows i).any isMaterial = true := by
  exact (((checkAlignment_iff _ _).mp h).2.2.2 i (List.mem_range.mpr hi)).1

end Historical.Alignment
