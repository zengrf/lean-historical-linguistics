import Historical.RuleInput

/-! Compilation of unconditional left-to-right M2 passes to segment images.
Deletion is allowed. Contextual and right-to-left rules retain their reference
semantics and are not silently treated as unconditional rules. -/
namespace Historical.Compile
open Rules Certificates

def supported (r : Rule) : Bool := decide
  (r.left = [] ∧ r.right = [] ∧ r.left_edge = false ∧ r.right_edge = false ∧
   r.direction = .leftToRight)

def supportedLaws (laws : List Law) : Bool := laws.all (fun l => supported l.rule)

theorem output_independent (r : Rule) (h : supported r = true) (l t : Word) (a : Atom) :
    outputAt r l a t = outputAt r [] a [] := by
  have hh := of_decide_eq_true h
  rcases hh with ⟨hl, hr, hle, hre, _⟩
  cases a <;> simp [outputAt, eligible, hl, hr, hle, hre, sideMatches]

theorem scan_compiles (r : Rule) (h : supported r = true) (w l p : Word) :
    scan r l p w = w.flatMap (fun a => outputAt r [] a []) := by
  induction w generalizing l p with
  | nil => rfl
  | cons a w ih => simp only [scan, List.flatMap_cons, output_independent r h, ih]

theorem rule_compiles (r : Rule) (h : supported r = true) (w : Word) :
    applyRule r w = w.flatMap (fun a => outputAt r [] a []) := by
  have hd : r.direction = .leftToRight := (of_decide_eq_true h).2.2.2.2
  simpa [applyRule, hd] using scan_compiles r h w [] []

theorem run_nil (laws : List Law) : run laws [] = [] := by
  induction laws with
  | nil => rfl
  | cons law laws ih =>
    have h : applyRule law.rule [] = [] := by
      cases hd : law.rule.direction <;> simp [applyRule, hd, scan]
    simpa [run, h] using ih

theorem run_append (laws : List Law) (h : supportedLaws laws = true) (x y : Word) :
    run laws (x ++ y) = run laws x ++ run laws y := by
  induction laws generalizing x y with
  | nil => rfl
  | cons law laws ih =>
    have hh : supported law.rule = true ∧ supportedLaws laws = true := by
      simpa [supportedLaws] using h
    simp only [run, rule_compiles law.rule hh.1, List.flatMap_append]
    exact ih hh.2 _ _

theorem laws_compile (laws : List Law) (h : supportedLaws laws = true) (w : Word) :
    run laws w = w.flatMap (fun a => run laws [a]) := by
  induction w with
  | nil => simp [run_nil]
  | cons a w ih =>
    change run laws ([a] ++ w) = _
    rw [run_append laws h, ih]
    simp

abbrev Table := List (Atom × Word)

def image (table : Table) (a : Atom) : Word :=
  ((table.find? (fun p => p.1 == a)).map (·.2)).getD [a]

def compile (laws : List Law) (alphabet : List Atom) : Table :=
  alphabet.map fun a => (a, run laws [a])

theorem image_compile (laws : List Law) (alphabet : List Atom) (a : Atom)
    (h : a ∈ alphabet) : image (compile laws alphabet) a = run laws [a] := by
  induction alphabet with
  | nil => simp at h
  | cons b bs ih =>
    by_cases he : b = a
    · subst b; simp [image, compile]
    · have hab : a ∈ bs := by simpa [List.mem_cons, Ne.symm he] using h
      simpa [image, compile, he] using ih hab

def apply (table : Table) (w : Word) : Word := w.flatMap (image table)

theorem compile_correct (laws : List Law) (alphabet : List Atom)
    (h : supportedLaws laws = true) (w : Word) (hw : ∀ a ∈ w, a ∈ alphabet) :
    apply (compile laws alphabet) w = run laws w := by
  rw [laws_compile laws h]
  unfold apply
  induction w with
  | nil => rfl
  | cons a w ih =>
    simp only [List.flatMap_cons]
    rw [image_compile laws alphabet a (hw a (by simp))]
    rw [ih (fun b hb => hw b (by simp [hb]))]

end Historical.Compile
