"""Which minimal impossibilities are one theorem restated with a stronger hypothesis.

A raw list of minimal inconsistent subsets reads as more results than it is. If
one axiom implies another, every impossibility stated with the weaker one has a
twin stated with the stronger one, and the twin is a corollary. This reads the
implication matrix from `discover.py implies` and splits the list accordingly.

Axioms that imply each other both ways are folded together first, so a pair like
strategyproof and maskinmonotone does not make each other's impossibilities look
derived.

    PYTHONPATH=. python notes/reduce_map.py
"""
import json
from itertools import permutations

def load(mus_path, imp_path):
    rec = json.loads(open(imp_path).read().strip())
    imp = {(a, b) for a, b, *unresolved in rec["implications"] if not unresolved}
    ms = [frozenset(r["core"] or r["axioms"])
          for r in (json.loads(l) for l in open(mus_path))
          if r["status"] == "unsat"]
    return imp, ms

def classes(imp, names):
    rep = {}
    for n in sorted(names):
        for r in rep.values():
            if (n, r) in imp and (r, n) in imp:
                rep[n] = r
                break
        else:
            rep[n] = n
    return rep

def report(mus_path, imp_path, title):
    imp, ms = load(mus_path, imp_path)
    names = {n for m in ms for n in m} | {n for e in imp for n in e}
    rep = classes(imp, names)
    folded = {}
    for m in ms:
        folded.setdefault(frozenset(rep[n] for n in m), m)
    keys = list(folded)
    def stronger(a, b):
        return a == b or (a, b) in imp
    def derives(src, dst):
        return len(src) <= len(dst) and any(
            all(stronger(d, s) for s, d in zip(sorted(src), combo))
            for combo in permutations(sorted(dst), len(src)))
    root = [k for k in keys if not any(o != k and derives(o, k) for o in keys)]
    print(f"\n== {title}: {len(ms)} minimal impossibilities, "
          f"{len(keys)} after folding equivalent axioms, {len(root)} substantive")
    for k in sorted(root, key=lambda s: (len(s), sorted(s))):
        alt = "" if sorted(folded[k]) == sorted(k) else f"   (also as {' + '.join(sorted(folded[k]))})"
        print("  " + " + ".join(sorted(k)) + alt)
    print("  --- the rest, each a strengthening of one above ---")
    for k in sorted(set(keys) - set(root), key=lambda s: (len(s), sorted(s))):
        src = next(o for o in keys if o != k and derives(o, k))
        print("   " + " + ".join(sorted(k)) + "  <= " + " + ".join(sorted(src)))

report("notes/discovery/mus-scf-3v3c.jsonl", "notes/discovery/implies-scf-3v3c.jsonl", "scf 3v3c")
report("notes/discovery/mus-swf-3v3c.jsonl", "notes/discovery/implies-swf-3v3c.jsonl", "swf 3v3c")
report("notes/discovery/mus-scf-2v3c.jsonl", "notes/discovery/implies-scf-2v3c.jsonl", "scf 2v3c")
