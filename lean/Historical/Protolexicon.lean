import Historical.SearchGraph

namespace Historical.PrefixSearch
open Rules SearchGraph

structure State where
  remaining : Nat
  front : Word
  deriving DecidableEq, Repr

def step (s : State) (a : Atom) : Option State :=
  match s.remaining with
  | 0 => none
  | n + 1 => some ⟨n, s.front ++ [a]⟩

def finish (predicate : Word → Bool) (s : State) : Bool := predicate s.front

theorem reference_machine_correct (alphabet : List Atom) (predicate : Word → Bool)
    (s : State) (w : Word) :
    machineAccept alphabet step (finish predicate) s w = true ↔
      (∀ a ∈ w, a ∈ alphabet) ∧ w.length ≤ s.remaining ∧ predicate (s.front ++ w) = true := by
  induction w generalizing s with
  | nil => simp [machineAccept, finish]
  | cons a w ih =>
    rcases s with ⟨n, front⟩
    cases n <;> simp [machineAccept, step, ih, List.append_assoc, and_assoc]

theorem reference_graph_correct (alphabet : List Atom) (predicate : Word → Bool)
    (g : Graph State) (h : faithful alphabet step (finish predicate) g = true)
    (i : Nat) (n : Node State) (hi : g[i]? = some n) (w : Word) :
    graphAccept alphabet g i w = true ↔
      (∀ a ∈ w, a ∈ alphabet) ∧ w.length ≤ n.state.remaining ∧
        predicate (n.state.front ++ w) = true := by
  rw [graph_correct _ _ _ _ h i n hi, reference_machine_correct]

end Historical.PrefixSearch

namespace Historical.Protolexicon
open Rules Inverse
abbrev Lexicon := List Word

/-- Conditional factorization: every word belongs to the same global model.
This does not take independent unions over competing models at each word. -/
def product : List (List Word) → List Lexicon
  | [] => [[]]
  | pool :: pools => pool.flatMap fun w => (product pools).map (w :: ·)

def Assigned : List (List Word) → Lexicon → Prop
  | [], [] => True
  | pool :: pools, w :: ws => w ∈ pool ∧ Assigned pools ws
  | _, _ => False

theorem product_correct (pools : List (List Word)) (ws : Lexicon) :
    ws ∈ product pools ↔ Assigned pools ws := by
  induction pools generalizing ws with
  | nil => cases ws <;> simp [product, Assigned]
  | cons pool pools ih => cases ws <;> simp [product, Assigned, ih]

def FitsRows (alphabet : List Atom) (tables : List Compile.Table) : List State → Lexicon → Prop
  | [], [] => True
  | s :: states, w :: ws =>
      ((∀ a ∈ w, a ∈ alphabet) ∧ allows tables s w = true) ∧ FitsRows alphabet tables states ws
  | _, _ => False

theorem protolexicon_correct (alphabet : List Atom) (tables : List Compile.Table)
    (states : List State) (ws : Lexicon) :
    ws ∈ product (states.map (enumerate alphabet tables)) ↔ FitsRows alphabet tables states ws := by
  rw [product_correct]
  induction states generalizing ws with
  | nil => cases ws <;> simp [Assigned, FitsRows]
  | cons s states ih => cases ws <;> simp [Assigned, FitsRows, inverse_correct, ih]

structure Family where
  analysis_id : String
  choices : List (List Word)

structure Solution where
  analysis_id : String
  forms : Lexicon
  deriving DecidableEq

def solutions (families : List Family) : List Solution :=
  families.flatMap fun f => (product f.choices).map fun ws => ⟨f.analysis_id, ws⟩

theorem solutions_correct (families : List Family) (s : Solution) :
    s ∈ solutions families ↔
      ∃ f ∈ families, s.analysis_id = f.analysis_id ∧ Assigned f.choices s.forms := by
  rcases s with ⟨id, ws⟩
  simp [solutions, product_correct, eq_comm, and_comm, and_left_comm, and_assoc]

theorem one_model_for_all_words (families : List Family) (s : Solution)
    (h : s ∈ solutions families) :
    ∃ f ∈ families, s.analysis_id = f.analysis_id ∧ Assigned f.choices s.forms :=
  (solutions_correct families s).mp h

theorem empty_entry_excludes_model (before after : List (List Word)) (ws : Lexicon) :
    ws ∉ product (before ++ [] :: after) := by
  induction before generalizing ws with
  | nil => simp [product]
  | cons pool before ih =>
    cases ws <;> simp [product, ih]

end Historical.Protolexicon
