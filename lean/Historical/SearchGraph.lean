import Historical.Inverse

/-! An external search program supplies a graph. Every successful and failed
alphabet transition, and every accepting state, is checked in Lean. Thus the
certificate checks completeness as well as the soundness of sampled words. -/
namespace Historical.SearchGraph
open Rules Lean

structure Node (σ : Type) where
  state : σ
  accepting : Bool
  edges : List (Atom × Nat)
  deriving Repr

abbrev Graph (σ : Type) := Array (Node σ)

def edge (n : Node σ) (a : Atom) : Option Nat :=
  (n.edges.find? (fun e => e.1 == a)).map (·.2)

def childState (g : Graph σ) (n : Node σ) (a : Atom) : Option σ := do
  let i ← edge n a
  let child ← g[i]?
  pure child.state

def faithfulNode [DecidableEq σ] (alphabet : List Atom)
    (transition : σ → Atom → Option σ) (terminal : σ → Bool)
    (g : Graph σ) (n : Node σ) : Bool :=
  (n.accepting == terminal n.state) &&
    alphabet.all (fun a => decide (childState g n a = transition n.state a))

def faithful [DecidableEq σ] (alphabet : List Atom)
    (transition : σ → Atom → Option σ) (terminal : σ → Bool) (g : Graph σ) : Bool :=
  g.all (faithfulNode alphabet transition terminal g)

def machineAccept (alphabet : List Atom) (transition : σ → Atom → Option σ)
    (terminal : σ → Bool) : σ → Word → Bool
  | s, [] => terminal s
  | s, a :: w => if a ∈ alphabet then
      match transition s a with
      | none => false
      | some next => machineAccept alphabet transition terminal next w
    else false

def graphAccept (alphabet : List Atom) (g : Graph σ) : Nat → Word → Bool
  | i, w => match g[i]? with
    | none => false
    | some n => match w with
      | [] => n.accepting
      | a :: rest => if a ∈ alphabet then
          match edge n a with
          | none => false
          | some j => graphAccept alphabet g j rest
        else false
termination_by _ w => w.length

theorem faithful_at [DecidableEq σ] (alphabet : List Atom)
    (transition : σ → Atom → Option σ) (terminal : σ → Bool) (g : Graph σ)
    (h : faithful alphabet transition terminal g = true) (i : Nat) (n : Node σ)
    (hi : g[i]? = some n) :
    n.accepting = terminal n.state ∧
      ∀ a ∈ alphabet, childState g n a = transition n.state a := by
  have hm : n ∈ g := by
    exact Array.mem_of_getElem? hi
  have hh := (Array.all_eq_true_iff_forall_mem.mp h) n hm
  simpa [faithfulNode, List.all_eq_true] using hh

theorem graph_correct [DecidableEq σ] (alphabet : List Atom)
    (transition : σ → Atom → Option σ) (terminal : σ → Bool) (g : Graph σ)
    (h : faithful alphabet transition terminal g = true) (i : Nat) (n : Node σ)
    (hi : g[i]? = some n) (w : Word) :
    graphAccept alphabet g i w = machineAccept alphabet transition terminal n.state w := by
  induction w generalizing i n with
  | nil => simpa [graphAccept, machineAccept, hi] using (faithful_at _ _ _ _ h i n hi).1
  | cons a w ih =>
    by_cases ha : a ∈ alphabet
    · have hs := (faithful_at _ _ _ _ h i n hi).2 a ha
      cases he : edge n a with
      | none =>
        have ht : transition n.state a = none := by simpa [childState, he] using hs.symm
        simp [graphAccept, machineAccept, hi, ha, he, ht]
      | some j =>
        cases hj : g[j]? with
        | none =>
          have ht : transition n.state a = none := by simpa [childState, he, hj] using hs.symm
          simp [graphAccept, machineAccept, hi, ha, he, hj, ht]
        | some child =>
          have ht : transition n.state a = some child.state := by
            simpa [childState, he, hj] using hs.symm
          rw [graphAccept, hi]
          dsimp only
          rw [if_pos ha, he]
          dsimp only
          rw [machineAccept, if_pos ha, ht]
          dsimp only
          exact ih j child hj
    · simp [graphAccept, machineAccept, hi, ha]

theorem inverse_machine_correct (alphabet : List Atom) (tables : List Compile.Table)
    (s : Inverse.State) (w : Word) :
    machineAccept alphabet (Inverse.step tables) (Inverse.finish tables) s w = true ↔
      (∀ a ∈ w, a ∈ alphabet) ∧ Inverse.allows tables s w = true := by
  induction w generalizing s with
  | nil => simp [machineAccept, Inverse.allows_nil]
  | cons a w ih =>
    rw [Inverse.allows_cons]
    cases ht : Inverse.step tables s a <;>
      simp [machineAccept, ht, ih, and_assoc, and_left_comm, and_comm]

theorem checked_inverse_complete (alphabet : List Atom) (tables : List Compile.Table)
    (g : Graph Inverse.State) (h : faithful alphabet (Inverse.step tables) (Inverse.finish tables) g = true)
    (i : Nat) (n : Node Inverse.State) (hi : g[i]? = some n) (w : Word) :
    graphAccept alphabet g i w = true ↔ w ∈ Inverse.enumerate alphabet tables n.state := by
  rw [graph_correct _ _ _ _ h i n hi, inverse_machine_correct, Inverse.inverse_correct]

end Historical.SearchGraph
