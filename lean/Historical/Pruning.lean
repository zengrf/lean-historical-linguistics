import Historical.Protolexicon

/-! A sound over-approximation for contextual sound laws. Each input segment
may be copied, replaced or deleted only as permitted by its rule sequence.
Contexts are forgotten for pruning, then checked by the original interpreter
at every accepting word. Thus pruning cannot remove a genuine reconstruction. -/
namespace Historical.Pruning
open Rules Certificates Reconstruction Inverse

abbrev Choices := Atom → List Word

def distinct [DecidableEq α] : List α → List α
  | [] => []
  | a :: xs => if a ∈ xs then distinct xs else a :: distinct xs

theorem mem_distinct [DecidableEq α] (a : α) (xs : List α) :
    a ∈ distinct xs ↔ a ∈ xs := by
  induction xs with
  | nil => simp [distinct]
  | cons b xs ih =>
    by_cases hb : b ∈ xs
    · simp only [distinct, if_pos hb, ih, List.mem_cons]
      constructor
      · exact Or.inr
      · intro h; rcases h with rfl | h
        · exact hb
        · exact h
    · simp [distinct, hb, ih]

inductive Expands (f : Choices) : Word → Word → Prop where
  | nil : Expands f [] []
  | cons {a w chunk tail} : chunk ∈ f a → Expands f w tail →
      Expands f (a :: w) (chunk ++ tail)

def language (f : Choices) : Word → List Word
  | [] => [[]]
  | a :: w => (f a).flatMap fun chunk => (language f w).map (chunk ++ ·)

theorem language_correct (f : Choices) (w out : Word) :
    out ∈ language f w ↔ Expands f w out := by
  induction w generalizing out with
  | nil => simp only [language, List.mem_singleton]; constructor
           · intro h; subst out; exact .nil
           · intro h; cases h; rfl
  | cons a w ih =>
    simp only [language, List.mem_flatMap, List.mem_map]
    constructor
    · rintro ⟨chunk, hc, tail, ht, rfl⟩
      exact .cons hc ((ih tail).mp ht)
    · intro h; cases h with
      | cons hc ht => exact ⟨_, hc, _, (ih _).mpr ht, rfl⟩

theorem expands_append (f : Choices) {u v x y : Word}
    (hu : Expands f u x) (hv : Expands f v y) : Expands f (u ++ v) (x ++ y) := by
  induction hu with
  | nil => simpa using hv
  | cons hc ht ih => simpa [List.append_assoc] using Expands.cons hc ih

theorem expands_split (f : Choices) {u v out : Word}
    (h : Expands f (u ++ v) out) :
    ∃ x y, Expands f u x ∧ Expands f v y ∧ out = x ++ y := by
  induction u generalizing out with
  | nil => exact ⟨[], out, .nil, h, rfl⟩
  | cons a u ih =>
    cases h with
    | cons hc ht =>
      obtain ⟨x, y, hx, hy, rfl⟩ := ih ht
      exact ⟨_ ++ x, y, .cons hc hx, hy, (List.append_assoc _ _ _).symm⟩

theorem expands_reverse (f : Choices)
    (hf : ∀ a chunk, chunk ∈ f a → chunk.reverse ∈ f a)
    {w out : Word} (h : Expands f w out) : Expands f w.reverse out.reverse := by
  induction h with
  | nil => exact .nil
  | @cons a w chunk tail hc ht ih =>
    have one : Expands f [a] chunk.reverse := by
      simpa using Expands.cons (hf a chunk hc) (Expands.nil (f := f))
    simpa using expands_append f ih one

def replacement (r : Rule) : Word := r.replacement.toList.map Atom.segment

def choices (r : Rule) (a : Atom) : List Word :=
  if Compile.supported r then [outputAt r [] a []]
  else match a with
    | .morpheme => [[a]]
    | .segment s => if s ∈ r.target then [[a], replacement r] else [[a]]

theorem output_allowed (r : Rule) (left right : Word) (a : Atom) :
    outputAt r left a right ∈ choices r a := by
  by_cases hs : Compile.supported r = true
  · rw [Compile.output_independent r hs]
    simp [choices, hs]
  · have hs' : Compile.supported r = false := by cases h : Compile.supported r <;> simp_all
    cases a with
    | morpheme => simp [choices, hs', outputAt, eligible]
    | segment s =>
      by_cases ht : s ∈ r.target
      · simp only [choices, hs', Bool.false_eq_true, ↓reduceIte, ht]
        unfold outputAt
        split
        · cases h : r.replacement <;> simp [replacement, h]
        · simp
      · simp [choices, hs', ht, outputAt, eligible]

theorem choices_reverse (r : Rule) (a : Atom) (chunk : Word)
    (h : chunk ∈ choices r a) : chunk.reverse ∈ choices r a := by
  have short : ∀ x ∈ choices r a, x.length ≤ 1 := by
    intro x hx
    by_cases hs : Compile.supported r = true
    · have he : x = outputAt r [] a [] := by simpa [choices, hs] using hx
      rw [he]
      exact outputAt_length_le _ _ _ _
    · have hs' : Compile.supported r = false := by cases h : Compile.supported r <;> simp_all
      cases a with
      | morpheme =>
        have he : x = [.morpheme] := by simpa [choices, hs'] using hx
        simp [he]
      | segment s =>
        by_cases ht : s ∈ r.target
        · have he : x = [.segment s] ∨ x = replacement r := by simpa [choices, hs', ht] using hx
          rcases he with rfl | rfl
          · simp
          · cases hr : r.replacement <;> simp [replacement, hr]
        · have he : x = [.segment s] := by simpa [choices, hs', ht] using hx
          simp [he]
  have hn := short chunk h
  cases chunk with
  | nil => exact h
  | cons a tail => cases tail <;> simp_all

theorem scan_allowed (r : Rule) (w left produced : Word) :
    Expands (choices r) w (scan r left produced w) := by
  induction w generalizing left produced with
  | nil => exact .nil
  | cons a w ih => exact .cons (output_allowed _ _ _ _) (ih _ _)

theorem mirror_choices (r : Rule) : choices (mirror r) = choices r := by
  funext a
  by_cases hs : Compile.supported r = true
  · have hh := of_decide_eq_true hs
    rcases hh with ⟨hl, hr, hle, hre, hd⟩
    have hm : mirror r = r := by cases r; simp_all [mirror]
    rw [hm]
  · have hm : Compile.supported (mirror r) = Compile.supported r := by
      apply Bool.eq_iff_iff.mpr
      simp [Compile.supported, mirror, and_comm, and_left_comm, and_assoc]
    simp only [choices, hm, hs, ↓reduceIte]
    cases a <;> rfl

theorem rule_allowed (r : Rule) (w : Word) :
    Expands (choices r) w (applyRule r w) := by
  cases hd : r.direction with
  | leftToRight => simpa [applyRule, hd] using scan_allowed r w [] []
  | rightToLeft =>
    have h := scan_allowed (mirror r) w.reverse [] []
    rw [mirror_choices] at h
    simpa [applyRule, hd] using expands_reverse (choices r) (choices_reverse r) h

def compile : List Law → Choices
  | [], a => [[a]]
  | l :: ls, a => distinct ((choices l.rule a).flatMap (language (compile ls)))

theorem expands_identity (w : Word) : Expands (compile []) w w := by
  induction w with
  | nil => exact .nil
  | cons a w ih => exact .cons (chunk := [a]) (by simp [compile]) ih

theorem expands_compose (l : Law) (ls : List Law) {w mid out : Word}
    (h : Expands (choices l.rule) w mid) (ht : Expands (compile ls) mid out) :
    Expands (compile (l :: ls)) w out := by
  induction h generalizing out with
  | nil => cases ht; exact .nil
  | @cons a w chunk tail hc hh ih =>
    obtain ⟨x, y, hx, hy, rfl⟩ := expands_split _ ht
    apply Expands.cons (tail := y)
    · simp only [compile, mem_distinct, List.mem_flatMap, language_correct]
      exact ⟨chunk, hc, hx⟩
    · exact ih hy

theorem run_allowed (laws : List Law) (w : Word) :
    Expands (compile laws) w (run laws w) := by
  induction laws generalizing w with
  | nil => exact expands_identity w
  | cons l ls ih => exact expands_compose l ls (rule_allowed l.rule w) (ih _)

def advance (f : Choices) (masks : List Mask) (a : Atom) : List Mask :=
  distinct (masks.flatMap fun m => (f a).filterMap (consume m))

def residuals (f : Choices) (masks : List Mask) : Word → List Mask
  | [] => masks
  | a :: w => residuals f (advance f masks a) w

theorem residuals_allowed (f : Choices) {front output : Word}
    (h : Expands f front output) (m : Mask) (ms : List Mask) (hm : m ∈ ms)
    (suffix : Word) (hf : formMatches m (output ++ suffix) = true) :
    ∃ rest ∈ residuals f ms front, formMatches rest suffix = true := by
  induction h generalizing m ms with
  | nil => exact ⟨m, hm, hf⟩
  | @cons a w chunk tail hc ht ih =>
    have hfc : formMatches m (chunk ++ (tail ++ suffix)) = true := by
      simpa [List.append_assoc] using hf
    obtain ⟨rest, hr, hfit⟩ := (consume_correct m chunk (tail ++ suffix)).mp hfc
    apply ih rest (advance f ms a) _ hfit
    simp only [advance, mem_distinct, List.mem_flatMap, List.mem_filterMap]
    exact ⟨m, hm, chunk, hc, hr⟩

/-- Every actual fitting word has a nonempty abstract residual set at each
prefix. The over-approximation is used only to exclude impossible prefixes. -/
theorem fitting_prefix (laws : List Law) (mask : Mask) (front suffix : Word)
    (h : formMatches mask (run laws (front ++ suffix)) = true) :
    (residuals (compile laws) [mask] front).isEmpty = false := by
  obtain ⟨x, y, hx, hy, he⟩ := expands_split _ (run_allowed laws (front ++ suffix))
  rw [he] at h
  obtain ⟨rest, hr, _⟩ := residuals_allowed _ hx mask [mask] (by simp) y h
  cases hs : residuals (compile laws) [mask] front with
  | nil => simp [hs] at hr
  | cons => rfl

end Historical.Pruning

namespace Historical.PrefixSearch
open Rules SearchGraph

def prunedStep (guard : Word → Bool) (s : State) (a : Atom) : Option State :=
  match s.remaining with
  | 0 => none
  | n + 1 => if guard (s.front ++ [a]) then some ⟨n, s.front ++ [a]⟩ else none

theorem pruned_machine_correct (alphabet : List Atom) (predicate guard : Word → Bool)
    (safe : ∀ front suffix, predicate (front ++ suffix) = true → guard front = true)
    (s : State) (w : Word) :
    machineAccept alphabet (prunedStep guard) (finish predicate) s w = true ↔
      (∀ a ∈ w, a ∈ alphabet) ∧ w.length ≤ s.remaining ∧ predicate (s.front ++ w) = true := by
  induction w generalizing s with
  | nil => simp [machineAccept, finish]
  | cons a w ih =>
    rcases s with ⟨n, front⟩
    cases n with
    | zero => simp [machineAccept, prunedStep]
    | succ n =>
      by_cases hg : guard (front ++ [a]) = true
      · simp [machineAccept, prunedStep, hg, ih, List.append_assoc, and_assoc]
      · have hp : predicate (front ++ (a :: w)) ≠ true := by
          intro h
          apply hg
          apply safe (front ++ [a]) w
          simpa [List.append_assoc] using h
        simp [machineAccept, prunedStep, hg, hp]

end Historical.PrefixSearch
