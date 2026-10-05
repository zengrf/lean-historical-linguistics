"""Check the declared proof audit against the current Lean source files.

Run after `lake build` and `lake env lean Audit.lean`. This does not replace Lean:
it checks for disallowed escape hatches and unexpected reported dependencies.
"""
import argparse
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def strip_comments(text):
    # Lean block comments nest. Retain newlines for useful error reporting.
    out=[]; i=0; depth=0
    while i<len(text):
        if text.startswith('/-',i): depth+=1;i+=2;continue
        if depth and text.startswith('-/',i):depth-=1;i+=2;continue
        if depth:
            if text[i]=='\n':out.append('\n')
            i+=1;continue
        if text.startswith('--',i):
            end=text.find('\n',i);i=len(text) if end<0 else end;continue
        out.append(text[i]);i+=1
    if depth:raise ValueError('unterminated block comment')
    return ''.join(out)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('audit',type=Path);a=p.parse_args()
    files=[ROOT/'lean/Comparative.lean',*(ROOT/'lean/Comparative').glob('*.lean')]
    banned=r'\b(sorry|admit|axiom|native_decide|unsafe|implemented_by)\b'
    count=0
    for path in files:
        code=strip_comments(path.read_text())
        if re.search(banned,code):raise SystemExit(f'Forbidden proof escape hatch in {path.name}')
        count+=len(re.findall(r'^\s*(?:theorem|lemma)\s+',code,re.M))
    declarations=re.findall(r'^#print axioms\s+(\S+)',(ROOT/'lean/Audit.lean').read_text(),re.M)
    if len(declarations)!=count or len(set(declarations))!=count:
        raise SystemExit('Every theorem must appear once in Audit.lean')
    output=a.audit.read_text()
    found=re.findall(r"^'([^']+)' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])",output,re.M)
    if set(found)!=set(declarations) or len(found)!=len(declarations):
        raise SystemExit('Audit output does not cover the declared theorem list exactly')
    allowed={'propext','Quot.sound','Classical.choice'}
    dependencies=set()
    for group in re.findall(r'depends on axioms: \[([^\]]*)\]',output):
        dependencies.update(x.strip() for x in group.split(',') if x.strip())
    if dependencies-allowed:
        raise SystemExit('Unexpected logical dependency: '+str(dependencies-allowed))
    print(f'{count} theorem declarations audited; dependencies: {sorted(dependencies)}; no project axioms or proof placeholders')


if __name__=='__main__': main()
