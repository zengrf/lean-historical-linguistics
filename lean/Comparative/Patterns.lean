import Comparative.Core

/-! Missing data are not alignment gaps. Compatibility follows List (2019)'s
    two conditions: no conflicting observed cells, and a shared non-gap cell.
    The finite examples deliberately use a separate gap constructor. -/
namespace Comparative.Patterns

inductive Cell (α : Type) where
  | missing | gap | sound (value : α)
  deriving DecidableEq, Repr

def Agrees [DecidableEq α] (x y : Cell α) : Bool :=
  match x, y with
  | .missing, _ | _, .missing => true
  | _, _ => decide (x = y)

def SharedSound [DecidableEq α] (x y : Cell α) : Bool :=
  match x, y with
  | .sound a, .sound b => decide (a = b)
  | _, _ => false

abbrev Column (α : Type) := Cell α × Cell α

def compatible [DecidableEq α] (x y : Column α) : Bool :=
  Agrees x.1 y.1 && Agrees x.2 y.2 &&
    (SharedSound x.1 y.1 || SharedSound x.2 y.2)

def a : Column Nat := (.sound 0, .sound 1)
def b : Column Nat := (.sound 0, .missing)
def c : Column Nat := (.sound 0, .sound 2)

theorem compatible_is_not_transitive :
    compatible a b = true ∧ compatible b c = true ∧ compatible a c = false := by
  decide

theorem missing_is_not_gap :
    Agrees (Cell.missing : Cell Nat) (.sound 1) = true ∧
    Agrees (Cell.gap : Cell Nat) (.sound 1) = false := by decide

theorem missing_alone_is_not_support :
    compatible ((.missing, .missing) : Column Nat) (.missing, .missing) = false := by
  decide

/- Independent position-wise uncertainty can introduce an unattested combination.
   Two joint hypotheses [0,1] and [2,3] do not license the hybrid [0,3]. -/
def joint : List (List Nat) := [[0, 1], [2, 3]]
def independent : List (List Nat) := [[0, 1], [0, 3], [2, 1], [2, 3]]

theorem independent_choices_overgenerate :
    [0, 3] ∈ independent ∧ [0, 3] ∉ joint := by decide

end Comparative.Patterns
