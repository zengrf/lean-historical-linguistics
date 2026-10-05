"""Validate the milestone dependency graph and delivered-artifact references."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
items=json.loads((ROOT/'data/milestones.json').read_text())
by={m['id']:m for m in items}
assert len(by)==len(items), 'duplicate milestone ID'
visiting=set();done=set()


def visit(k):
    assert k in by, f'unknown dependency {k}'
    assert k not in visiting, f'dependency cycle at {k}'
    if k in done:return
    visiting.add(k)
    for dep in by[k]['depends_on']:visit(dep)
    visiting.remove(k);done.add(k)


criteria=set()
for m in items:
    visit(m['id'])
    assert m['status'] in {'delivered','in_review','planned'}, 'unrecognized status'
    assert m['owner_role'] and m['artifacts'] and m['acceptance'], 'incomplete milestone'
    for c in m['acceptance']:
        assert c['id'] not in criteria, 'duplicate acceptance ID'
        criteria.add(c['id'])
        assert c['test'] and c['pass_condition'], 'unverifiable criterion'
    if m['status'] in {'delivered','in_review'}:
        for path in m['artifacts']:assert (ROOT/path).exists(), f'missing delivered artifact {path}'
print(f'{len(items)} milestones, {len(criteria)} acceptance criteria; acyclic dependencies and delivered paths verified')
