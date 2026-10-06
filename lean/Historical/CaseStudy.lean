import Historical.ReconstructionInput

namespace Historical.CaseStudy
open Rules Certificates Reconstruction

/-- Retrieve compatible forms from a supplied finite pool of published reconstructions. -/
def retrieve (pool : List Word) (model : Model) (obs : List Observation) : List Word :=
  pool.filter (fits model obs)

theorem retrieval_correct (pool : List Word) (model : Model) (obs : List Observation) (w : Word) :
    w ∈ retrieve pool model obs ↔ w ∈ pool ∧ Fits model obs w := by
  simp [retrieve, fits_iff]

theorem retrieval_sound (pool : List Word) (model : Model) (obs : List Observation) (w : Word)
    (h : w ∈ retrieve pool model obs) : Fits model obs w :=
  ((retrieval_correct _ _ _ _).mp h).2

theorem retrieval_complete (pool : List Word) (model : Model) (obs : List Observation) (w : Word)
    (hp : w ∈ pool) (hf : Fits model obs w) : w ∈ retrieve pool model obs :=
  (retrieval_correct _ _ _ _).mpr ⟨hp, hf⟩

theorem retrieval_mono (pool : List Word) (model : Model) (weak strong : List Observation)
    (hsub : ∀ o ∈ weak, o ∈ strong) :
    ∀ w ∈ retrieve pool model strong, w ∈ retrieve pool model weak := by
  intro w hw
  obtain ⟨hp, hf⟩ := (retrieval_correct _ _ _ _).mp hw
  exact (retrieval_correct _ _ _ _).mpr ⟨hp, Identifiability.fits_mono model weak strong w hsub hf⟩

theorem retrieval_empty_iff (pool : List Word) (model : Model) (obs : List Observation) :
    retrieve pool model obs = [] ↔ ¬ ∃ w ∈ pool, Fits model obs w := by
  constructor
  · intro h ⟨w, hp, hf⟩
    have hw := retrieval_complete pool model obs w hp hf
    rw [h] at hw
    cases hw
  · intro h
    apply List.eq_nil_iff_forall_not_mem.mpr
    intro w hw
    exact h ⟨w, (retrieval_correct _ _ _ _).mp hw⟩

theorem forward_certificate_accepted (laws : List Law) (w : Word) :
    checkTrace laws w (trace laws w) (run laws w) = true := canonical_trace_accepted _ _

end Historical.CaseStudy
