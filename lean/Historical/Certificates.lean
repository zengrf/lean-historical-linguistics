import Historical.Rules

namespace Historical.Certificates
open Rules

structure Law where
  id : String
  input_stage : String
  output_stage : String
  rule : Rule
  deriving DecidableEq, Repr

structure Step where
  rule_id : String
  input_stage : String
  output_stage : String
  output : Word
  deriving DecidableEq, Repr

def Identifies (law : Law) (step : Step) : Prop :=
  step.rule_id = law.id ∧ step.input_stage = law.input_stage ∧
    step.output_stage = law.output_stage

instance (law : Law) (step : Step) : Decidable (Identifies law step) := by
  unfold Identifies
  infer_instance

/-- Every stage, including no-change passes, must occur exactly once. -/
def checkTrace : List Law → Word → List Step → Word → Bool
  | [], w, [], out => decide (w = out)
  | law :: laws, w, step :: steps, out =>
      decide (Identifies law step ∧ applyRule law.rule w = step.output) &&
        checkTrace laws step.output steps out
  | _, _, _, _ => false

inductive LicensedTrace : List Law → Word → List Step → Word → Prop where
  | nil (w) : LicensedTrace [] w [] w
  | cons {law laws w step steps out} : Identifies law step →
      Pass law.rule w step.output → LicensedTrace laws step.output steps out →
      LicensedTrace (law :: laws) w (step :: steps) out

theorem checkTrace_iff (laws : List Law) (w : Word) (steps : List Step) (out : Word) :
    checkTrace laws w steps out = true ↔ LicensedTrace laws w steps out := by
  induction laws generalizing w steps with
  | nil =>
      cases steps with
      | nil =>
          constructor
          · intro h
            have hw : w = out := by simpa [checkTrace] using h
            subst out
            exact LicensedTrace.nil w
          · intro h; cases h; simp [checkTrace]
      | cons step steps =>
          constructor
          · intro h; simp [checkTrace] at h
          · intro h; cases h
  | cons law laws ih =>
      cases steps with
      | nil =>
          constructor
          · intro h; simp [checkTrace] at h
          · intro h; cases h
      | cons step steps =>
          constructor
          · intro h
            have hh : (Identifies law step ∧ applyRule law.rule w = step.output) ∧
                checkTrace laws step.output steps out = true := by
              simpa [checkTrace] using h
            exact LicensedTrace.cons hh.1.1 ((pass_iff_apply _ _ _).mpr hh.1.2)
              ((ih _ _).mp hh.2)
          · intro h
            cases h with
            | cons labels hp ht =>
                have hh : (Identifies law step ∧ applyRule law.rule w = step.output) ∧
                    checkTrace laws step.output steps out = true :=
                  ⟨⟨labels, (pass_iff_apply _ _ _).mp hp⟩, (ih _ _).mpr ht⟩
                simpa [checkTrace] using hh

theorem checkTrace_sound (laws : List Law) (w : Word) (steps : List Step) (out : Word)
    (h : checkTrace laws w steps out = true) : LicensedTrace laws w steps out :=
  (checkTrace_iff _ _ _ _).mp h

theorem checkTrace_complete (laws : List Law) (w : Word) (steps : List Step) (out : Word)
    (h : LicensedTrace laws w steps out) : checkTrace laws w steps out = true :=
  (checkTrace_iff _ _ _ _).mpr h

def run : List Law → Word → Word
  | [], w => w
  | law :: laws, w => run laws (applyRule law.rule w)

inductive Derives : List Law → Word → Word → Prop where
  | nil (w) : Derives [] w w
  | cons {law laws w middle out} : Pass law.rule w middle → Derives laws middle out →
      Derives (law :: laws) w out

theorem derives_iff_run (laws : List Law) (w out : Word) :
    Derives laws w out ↔ run laws w = out := by
  constructor
  · intro h
    induction h with
    | nil => rfl
    | cons hp _ ih =>
        simp only [run]
        rw [(pass_iff_apply _ _ _).mp hp]
        exact ih
  · intro h
    subst out
    induction laws generalizing w with
    | nil => exact Derives.nil w
    | cons law laws ih =>
        exact Derives.cons ((pass_iff_apply _ _ _).mpr rfl) (ih _)

theorem trace_implies_derives (laws : List Law) (w : Word) (steps : List Step) (out : Word)
    (h : LicensedTrace laws w steps out) : Derives laws w out := by
  induction h with
  | nil => exact Derives.nil _
  | cons _ hp _ ih => exact Derives.cons hp ih

theorem run_append (laws more : List Law) (w : Word) :
    run (laws ++ more) w = run more (run laws w) := by
  induction laws generalizing w with
  | nil => rfl
  | cons law laws ih => exact ih _

def trace : List Law → Word → List Step
  | [], _ => []
  | law :: laws, w =>
      let next := applyRule law.rule w
      ⟨law.id, law.input_stage, law.output_stage, next⟩ :: trace laws next

theorem canonical_trace_accepted (laws : List Law) (w : Word) :
    checkTrace laws w (trace laws w) (run laws w) = true := by
  induction laws generalizing w with
  | nil => simp [checkTrace, trace, run]
  | cons law laws ih => simp [checkTrace, trace, run, Identifies, ih]

theorem derivation_iff_certificate (laws : List Law) (w out : Word) :
    Derives laws w out ↔ ∃ steps, checkTrace laws w steps out = true := by
  constructor
  · intro h
    rw [← (derives_iff_run _ _ _).mp h]
    exact ⟨trace laws w, canonical_trace_accepted laws w⟩
  · intro ⟨steps, h⟩
    exact trace_implies_derives _ _ _ _ (checkTrace_sound _ _ _ _ h)

end Historical.Certificates
