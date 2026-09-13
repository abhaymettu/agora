"""Timing sweep across electorate sizes.

    PYTHONPATH=. python notes/sweep.py > notes/timings.txt

Runs the two flagship axiom sets at every size in scope, with degradation off so
each row is that size and nothing else. Numbers are from one machine and will
move; the shape (three candidates is cheap, four is where it stops) will not.
"""

import time

from core import derive

SETS = {
    "scf": ["strategyproof", "surjective", "nondictatorial"],  # Gibbard-Satterthwaite
    "swf": ["pareto", "iia", "nondictatorial"],  # Arrow
}
TIMEOUT = 120


def label(note: str) -> str:
    if "not attempted" in note:
        return "refused up front"
    if "passed" in note and "clauses" in note:
        return "encoding budget, clauses"
    if "encoding did not fit" in note:
        return "encoding budget, time"
    return "solver budget" if note else ""


print(f"{'mode':5} {'size':6} {'profiles':>9} {'variables':>10} {'status':8} {'seconds':>9}  note")
for mode, axioms in SETS.items():
    for candidates in (3, 4):
        for voters in (2, 3, 4):
            start = time.perf_counter()
            r = derive(axioms, voters, candidates, mode=mode, timeout=TIMEOUT, degrade=False)
            elapsed = time.perf_counter() - start
            print(
                f"{mode:5} {voters}v{candidates}c  {r.profiles:>9,} {r.variables:>10,} "
                f"{r.status:8} {elapsed:>9.2f}  {label(r.note)}",
                flush=True,
            )
