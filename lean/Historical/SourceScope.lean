import Historical.Batch

namespace Historical.SourceScope
open Lean Rules Certificates RuleInput

/-- A source's reconstruction level or recorded variety. Names alone do not
identify levels across authors. -/
structure Node where
  source_id : String
  node_id : String
  deriving DecidableEq, BEq, FromJson, ToJson, Repr

/-- Endpoints are part of the type of a sequence of changes. -/
structure Path (ancestor descendant : Node) where
  laws : List Law

def Path.then {a b c : Node} (p : Path a b) (q : Path b c) : Path a c :=
  ⟨p.laws ++ q.laws⟩

def Path.predict {a b : Node} (p : Path a b) (w : Word) : Word := run p.laws w

theorem run_append (xs ys : List Law) (w : Word) :
    run (xs ++ ys) w = run ys (run xs w) := by
  induction xs generalizing w with
  | nil => rfl
  | cons x xs ih => simpa [run] using ih (applyRule x.rule w)

/-- Inserting a named intermediate node does not change a composed derivation. -/
theorem path_composition {a b c : Node} (p : Path a b) (q : Path b c) (w : Word) :
    (p.then q).predict w = q.predict (p.predict w) := run_append _ _ _

theorem path_associativity {a b c d : Node}
    (p : Path a b) (q : Path b c) (r : Path c d) :
    (p.then q).then r = p.then (q.then r) := by
  cases p; cases q; cases r
  simp [Path.then, List.append_assoc]

/-- An observation distinguishes two paths only through their predictions. -/
theorem indistinguishable_paths {a b : Node} (p q : Path a b)
    (h : ∀ w, p.predict w = q.predict w) (pool : List Word) (out : Word) :
    pool.filter (fun w => p.predict w == out) =
      pool.filter (fun w => q.predict w == out) := by
  have hf : (fun w => p.predict w == out) = (fun w => q.predict w == out) := by
    funext w; rw [h w]
  rw [hf]

structure PackageScope where
  package_id : String
  ancestor : Node
  descendant : Node
  deriving FromJson, ToJson

structure QueryScope where
  query_id : String
  ancestor : Node
  deriving FromJson, ToJson

structure Request where
  schema_version : String
  nodes : List Node
  package_scopes : List PackageScope
  query_scopes : List QueryScope
  batch : Batch.Request
  deriving FromJson, ToJson

/-- These checks prevent accidental reuse at a different source level. They do
not establish a historical relationship or the authenticity of a source label. -/
def validate (r : Request) : Except String Unit := do
  if r.schema_version != "1.0.0" || r.nodes.isEmpty || r.nodes.eraseDups != r.nodes ||
      !(r.nodes.all (fun n => goodId n.source_id && goodId n.node_id)) then
    throw "Invalid or repeated source-qualified node"
  Batch.validate r.batch
  if !unique (r.package_scopes.map (·.package_id)) ||
      r.package_scopes.length != r.batch.packages.length then throw "Incomplete package scopes"
  for p in r.batch.packages do
    let some s := r.package_scopes.find? (fun s => s.package_id == p.id)
      | throw "Missing package scope"
    if !r.nodes.contains s.ancestor || !r.nodes.contains s.descendant then throw "Unknown scope endpoint"
  if !unique (r.query_scopes.map (·.query_id)) ||
      r.query_scopes.length != r.batch.inverse.length then throw "Incomplete query scopes"
  for j in r.batch.inverse do
    let some q := r.query_scopes.find? (fun q => q.query_id == j.id)
      | throw "Missing query scope"
    if !r.nodes.contains q.ancestor then throw "Unknown query ancestor"
    for b in j.branches do
      let some p := r.package_scopes.find? (fun p => p.package_id == b.package_id)
        | throw "Missing inverse package scope"
      if p.ancestor != q.ancestor then throw "Inverse branches have different source ancestors"
      if p.descendant.node_id != b.doculect_id then throw "Observation is for another source variety"

def execute (r : Request) : Json :=
  Json.mkObj [("scope_valid", toJson true), ("result", Batch.execute r.batch)]

end Historical.SourceScope
