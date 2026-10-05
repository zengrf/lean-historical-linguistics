import Historical.JsonInput
import Historical.Certificates

/-! Strict interchange for M2's restricted synthetic rule packages. -/
namespace Historical.RuleInput
open Lean Rules Certificates

instance : FromJson Atom where
  fromJson? j := do
    let s ← j.getStr?
    return if s == "+" then .morpheme else .segment s

instance : ToJson Atom where
  toJson
    | .morpheme => toJson ("+" : String)
    | .segment s => toJson s

instance : FromJson Test where
  fromJson? j :=
    match j with
    | .str "+" => return .morpheme
    | .str "*" => return .anySegment
    | .arr _ => return .segments (← fromJson? j)
    | _ => throw "Context test must be a segment array, *, or +"

instance : ToJson Test where
  toJson
    | .morpheme => toJson ("+" : String)
    | .anySegment => toJson ("*" : String)
    | .segments ss => toJson ss

instance : FromJson Direction where
  fromJson? j := do
    match ← j.getStr? with
    | "left-to-right" => return .leftToRight
    | "right-to-left" => return .rightToLeft
    | _ => throw "Unsupported application direction"

instance : ToJson Direction where
  toJson d := toJson (match d with
    | .leftToRight => "left-to-right"
    | .rightToLeft => "right-to-left")

instance : FromJson Mode where
  fromJson? j := do
    match ← j.getStr? with
    | "simultaneous" => return .simultaneous
    | "feeding" => return .feeding
    | _ => throw "Unsupported pass convention"

instance : ToJson Mode where
  toJson m := toJson (match m with
    | .simultaneous => "simultaneous"
    | .feeding => "feeding")

deriving instance FromJson, ToJson for Rule
deriving instance FromJson, ToJson for Law
deriving instance FromJson, ToJson for Certificates.Step

structure Package where
  id : String
  version : String
  description : String
  inventory : List String
  initial_stage : String
  final_stage : String
  laws : List Law
  deriving FromJson, ToJson, Repr

structure Certificate where
  package_id : String
  package_version : String
  input : Word
  steps : List Certificates.Step
  output : Word
  deriving FromJson, ToJson, Repr

structure RuleDossier where
  schema_version : String
  id : String
  model : Package
  certificate : Certificate
  deriving FromJson, ToJson, Repr

def decodeRuleDossier (text : String) : Except String RuleDossier := decodeExact text

/-- Unicode 17.0 White_Space, pinned independently of Lean's ASCII predicate.
Source: https://www.unicode.org/Public/17.0.0/ucd/PropList.txt -/
def ruleWhitespace (c : Char) : Bool :=
  let n := c.toNat
  (n ≥ 0x0009 && n ≤ 0x000D) || (n ≥ 0x2000 && n ≤ 0x200A) ||
    ([0x0020, 0x0085, 0x00A0, 0x1680, 0x2028, 0x2029, 0x202F, 0x205F, 0x3000] : List Nat).contains n

def goodSymbol (s : String) : Bool :=
  !s.isEmpty && !(["+", "#", "*"].contains s) &&
    s.toList.all (fun c => !ruleWhitespace c && c.toNat ≥ 32 &&
      !(c.toNat ≥ 127 && c.toNat ≤ 159))

def validClass (inventory symbols : List String) : Bool :=
  !symbols.isEmpty && unique symbols && symbols.all inventory.contains

def validTest (inventory : List String) : Test → Bool
  | .segments ss => validClass inventory ss
  | _ => true

def validWord (inventory : List String) (w : Word) : Bool :=
  w.all fun a => match a with
    | .segment s => inventory.contains s
    | .morpheme => true

def validatePackage (p : Package) : List Issue := Id.run do
  let mut issues : List Issue := []
  let add := fun code path message => Issue.mk code path message
  if !goodId p.id || p.version.isEmpty || p.description.isEmpty then
    issues := issues ++ [add "PACKAGE_METADATA" "model" "Stable ID, version and description required"]
  if p.inventory.isEmpty || !unique p.inventory || !(p.inventory.all goodSymbol) then
    issues := issues ++ [add "INVENTORY" "model.inventory" "Inventory must contain distinct nonempty atomic segment symbols"]
  if !goodId p.initial_stage || !goodId p.final_stage then
    issues := issues ++ [add "STAGE_ID" "model" "Valid initial and final stage IDs required"]
  if !unique (p.laws.map (·.id)) then
    issues := issues ++ [add "RULE_IDS" "model.laws" "Law IDs must be unique"]
  if !unique (p.initial_stage :: p.laws.map (·.output_stage)) then
    issues := issues ++ [add "STAGE_ORDER" "model.laws" "Chronological stage names must be distinct"]
  let mut previous := p.initial_stage
  for law in p.laws do
    if !goodId law.id then
      issues := issues ++ [add "RULE_IDS" law.id "Valid law ID required"]
    if !goodId law.input_stage || !goodId law.output_stage then
      issues := issues ++ [add "STAGE_ID" law.id "Valid law stage IDs required"]
    if law.input_stage != previous then
      issues := issues ++ [add "STAGE_CHAIN" law.id "Input stage must equal the preceding output stage"]
    previous := law.output_stage
    let r := law.rule
    if !validClass p.inventory r.target then
      issues := issues ++ [add "TARGET_CLASS" law.id "Target must be a nonempty distinct subset of the segment inventory"]
    if let some s := r.replacement then
      if !p.inventory.contains s then
        issues := issues ++ [add "REPLACEMENT" law.id "Replacement must be a declared segment, or null for deletion"]
    if r.left.length > 2 || r.right.length > 2 then
      issues := issues ++ [add "CONTEXT_BOUND" law.id "At most two context tokens are permitted on each side"]
    if !((r.left ++ r.right).all (validTest p.inventory)) then
      issues := issues ++ [add "CONTEXT_CLASS" law.id "Context classes must be nonempty distinct subsets of the inventory"]
  if previous != p.final_stage then
    issues := issues ++ [add "STAGE_CHAIN" "model.final_stage" "Final stage must close the ordered law chain"]
  return issues

def validateDossier (d : RuleDossier) : List Issue := Id.run do
  let mut issues := validatePackage d.model
  let add := fun code path message => Issue.mk code path message
  if d.schema_version != "1.0.0" then
    issues := issues ++ [add "SCHEMA_VERSION" "schema_version" "Expected contextual-rules schema 1.0.0"]
  if !goodId d.id then
    issues := issues ++ [add "DOSSIER_ID" "id" "Valid dossier ID required"]
  let c := d.certificate
  if c.package_id != d.model.id || c.package_version != d.model.version then
    issues := issues ++ [add "PACKAGE_IDENTITY" "certificate" "Certificate must identify this exact named package/version"]
  if !validWord d.model.inventory c.input || !validWord d.model.inventory c.output ||
      !(c.steps.all (fun s => validWord d.model.inventory s.output)) then
    issues := issues ++ [add "WORD_INVENTORY" "certificate" "All input, intermediate and final segments must be declared"]
  return issues

def checkDossier (d : RuleDossier) : Bool :=
  (validateDossier d).isEmpty &&
    checkTrace d.model.laws d.certificate.input d.certificate.steps d.certificate.output

theorem checkDossier_iff (d : RuleDossier) : checkDossier d = true ↔
    validateDossier d = [] ∧ LicensedTrace d.model.laws d.certificate.input
      d.certificate.steps d.certificate.output := by
  simp [checkDossier, checkTrace_iff]

/-- Diagnostics explain rejection; acceptance uses the proved checker above. -/
def traceIssues (laws : List Law) (input : Word) (steps : List Certificates.Step)
    (out : Word) : List Issue := Id.run do
  let mut issues : List Issue := []
  let add := fun code path message => Issue.mk code path message
  if laws.length != steps.length then
    issues := issues ++ [add "TRACE_LENGTH" "certificate.steps" "Exactly one step per law, including unchanged passes, is required"]
  let mut previous := input
  for (law, step) in laws.zip steps do
    if law.id != step.rule_id then
      issues := issues ++ [add "RULE_ID" law.id "Certificate law IDs must follow package order"]
    if law.input_stage != step.input_stage || law.output_stage != step.output_stage then
      issues := issues ++ [add "TRACE_STAGE" law.id "Certificate stages must equal the named law's stages"]
    if applyRule law.rule previous != step.output then
      issues := issues ++ [add "STEP_OUTPUT" law.id "Post-rule word is not licensed by this pass"]
    previous := step.output
  if previous != out then
    issues := issues ++ [add "FINAL_OUTPUT" "certificate.output" "Final word must equal the last complete stage"]
  return issues

def diagnose (d : RuleDossier) : List Issue :=
  let issues := validateDossier d ++ traceIssues d.model.laws d.certificate.input
    d.certificate.steps d.certificate.output
  if !checkDossier d && issues.isEmpty then
    [⟨"CHECKER_REJECT", d.id, "Certificate checker rejected the supplied trace"⟩]
  else issues

end Historical.RuleInput
