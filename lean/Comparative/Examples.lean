import Comparative.Core

/-! Synthetic examples: these are not reconstructions of real languages. -/
namespace Comparative.Examples

inductive Seg where
  | p | b | f | v | a
  deriving DecidableEq, Repr

open Seg

def replace (source target : Seg) : Rule Seg :=
  List.map fun s => if s = source then target else s

def pToF : Rule Seg := replace p f
def fToV : Rule Seg := replace f v

theorem rule_order_matters :
    run [pToF, fToV] [p, a] ≠ run [fToV, pToF] [p, a] := by decide

theorem valid_certificate :
    checkTrace [pToF, fToV] [p, a] [[f, a], [v, a]] [v, a] = true := by decide

theorem corrupted_certificate_rejected :
    checkTrace [pToF, fToV] [p, a] [[b, a], [v, a]] [v, a] = false := by decide

theorem missing_step_rejected :
    checkTrace [pToF, fToV] [p, a] [[v, a]] [v, a] = false := by decide

theorem extra_step_rejected :
    checkTrace [pToF] [p, a] [[f, a], [v, a]] [v, a] = false := by decide

def merger : Model Unit Seg := fun _ => replace b p

theorem distinct_protoforms : ([p, a] : Word Seg) ≠ [b, a] := by decide

theorem merger_ambiguity : ObsEquivalent merger [p, a] [b, a] := by
  intro l
  rfl

def acceptsMerged (w : Word Seg) : Bool := decide (merger () w = [p, a])
def pool : List (Word Seg) := [[p, a], [b, a], [f, a]]

theorem finite_reconstruction_keeps_ambiguity :
    reconstruct pool acceptsMerged = [[p, a], [b, a]] := by decide

theorem fits_checker_reflects (w : Word Seg) :
    acceptsMerged w = true ↔ Fits merger [⟨(), [p, a]⟩] w := by
  simp [acceptsMerged, Fits]

end Comparative.Examples
