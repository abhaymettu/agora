"""The discovery sweep: what the core says about axiom sets nobody aimed it at.

Three questions, three subcommands, one JSON line per question asked.

    PYTHONPATH=. python notes/discover.py mus      --mode scf --voters 3 --candidates 3 --max-size 3
    PYTHONPATH=. python notes/discover.py frontier --mode scf pareto strategyproof
    PYTHONPATH=. python notes/discover.py count    --mode scf --voters 3 --candidates 3 anonymous neutral

mus         every minimal inconsistent subset of the library, by level, pruning
            supersets of impossibilities already found
frontier    one axiom set, walked up through electorate sizes until it stops
            resolving
count       how many distinct rules satisfy one axiom set, enumerated by
            blocking each model found

Records go to notes/discovery/<tag>.jsonl and are appended, never rewritten, so
a run that dies part way leaves what it got. Every record carries the size, the
elapsed seconds, and either a core or a rule; an unresolved question is written
down as unresolved rather than dropped.
"""

from __future__ import annotations

import argparse
import json
import time
from itertools import combinations
from pathlib import Path

import z3

from core import Electorate, axiom_names, derive, library
from core import ground as _ground
from core.ground import Context, encode, estimate_vars, frame
from core.rules import from_model

OUT = Path(__file__).parent / "discovery"


def emit(tag: str, record: dict) -> dict:
    OUT.mkdir(exist_ok=True)
    with (OUT / f"{tag}.jsonl").open("a") as fh:
        fh.write(json.dumps(record) + "\n")
    return record


def row(result, extra: dict | None = None) -> dict:
    r = {
        "mode": result.mode,
        "voters": result.voters,
        "candidates": result.candidates,
        "axioms": list(result.axioms),
        "status": result.status,
        "seconds": round(result.elapsed, 3),
        "profiles": result.profiles,
        "variables": result.variables,
        "timeout_s": result.timeout_s,
        "verified": result.verified,
        "core": list(result.core) if result.core else None,
        "core_minimal": result.core_minimal,
        "witnesses": {k: v.describe() for k, v in result.witnesses.items()},
        "rule": result.rule.describe() if result.rule else None,
        "note": result.note,
    }
    if extra:
        r.update(extra)
    return r


# -- minimal inconsistent subsets ------------------------------------------


def mus(mode, voters, candidates, max_size, timeout, tag, pool=None):
    pool = tuple(pool or axiom_names(mode))
    found: list[frozenset] = []   # impossibilities, minimal among what resolved
    unresolved: list[frozenset] = []
    for k in range(1, max_size + 1):
        for combo in combinations(pool, k):
            s = frozenset(combo)
            if any(u <= s for u in found):
                continue
            # minimality is only established if every proper subset resolved
            shaky = any(u < s for u in unresolved)
            r = derive(list(combo), voters, candidates, mode=mode, timeout=timeout, degrade=False)
            rec = emit(tag, row(r, {"level": k, "subsets_resolved": not shaky}))
            print(
                f"{mode} {voters}v{candidates}c {'+'.join(combo):60} "
                f"{r.status:8} {r.elapsed:7.2f}s  {rec['rule'] or ''}",
                flush=True,
            )
            if r.status == "unsat":
                found.append(s)
            elif r.status == "unknown":
                unresolved.append(s)
    return found, unresolved


# -- size frontier ----------------------------------------------------------


def frontier(axioms, mode, sizes, timeout, tag):
    for voters, candidates in sizes:
        r = derive(list(axioms), voters, candidates, mode=mode, timeout=timeout, degrade=False)
        emit(tag, row(r))
        print(
            f"{mode} {voters}v{candidates}c {r.profiles:>8,}p {r.variables:>9,}v "
            f"{r.status:8} {r.elapsed:7.2f}s  {r.rule.describe() if r.rule else (r.note[:70] if r.note else '')}",
            flush=True,
        )


# -- model counting ---------------------------------------------------------


def count(axioms, mode, voters, candidates, cap, timeout, tag):
    """Every rule satisfying the set, up to cap, by blocking each one found."""
    started = time.perf_counter()
    lib = library()
    elec = Electorate(voters, candidates)
    ctx = Context(elec, mode, deadline=started + timeout)
    solver = z3.Solver(ctx=ctx.z3ctx)
    solver.set("random_seed", 0)
    solver.add(frame(ctx))
    for name in axioms:
        solver.add(encode(lib[name], ctx))

    seen, exhausted = [], False
    while len(seen) < cap:
        left = timeout - (time.perf_counter() - started)
        if left <= 0:
            break
        solver.set("timeout", max(1, int(left * 1000)))
        verdict = solver.check()
        if verdict != z3.sat:
            exhausted = verdict == z3.unsat
            break
        model = solver.model()
        seen.append(from_model(model, ctx, elec))
        solver.add(z3.Not(z3.And([v == model.eval(v, model_completion=True) for v in ctx.vars.values()])))

    named = sorted({n for r in seen for n in r.matches()})
    rec = {
        "mode": mode,
        "voters": voters,
        "candidates": candidates,
        "axioms": list(axioms),
        "rules_found": len(seen),
        "exhaustive": exhausted,
        "cap": cap,
        "seconds": round(time.perf_counter() - started, 3),
        "variables": estimate_vars(voters, candidates, mode),
        "named_matches": named,
        "unnamed": sum(1 for r in seen if not r.matches()),
        "descriptions": sorted({r.describe() for r in seen})[:12],
    }
    emit(tag, rec)
    print(json.dumps(rec, indent=2), flush=True)
    return seen


# -- implication order ------------------------------------------------------


def implies(mode, voters, candidates, timeout, tag, pool=None):
    """Which axioms are strictly stronger than which, at this size.

    A implies B exactly when no rule satisfies A and fails B, so the question is
    one more satisfiability check: frame, A, and the negation of B. Without this
    the minimal-impossibility list reads as more results than it is. Half of it
    is one theorem restated with a stronger hypothesis.
    """
    started = time.perf_counter()
    pool = tuple(pool or axiom_names(mode))
    lib, elec = library(), Electorate(voters, candidates)
    ctx = Context(elec, mode, deadline=started + timeout * len(pool))
    formulas = {n: encode(lib[n], ctx) for n in pool}
    solver = z3.Solver(ctx=ctx.z3ctx)
    solver.set("random_seed", 0)
    solver.add(frame(ctx))
    edges = []
    for a in pool:
        solver.push()
        solver.add(formulas[a])
        for b in pool:
            if a == b:
                continue
            solver.push()
            solver.add(z3.Not(formulas[b]))
            solver.set("timeout", max(1, int(timeout * 1000)))
            verdict = solver.check()
            solver.pop()
            if verdict == z3.unsat:
                edges.append([a, b])
            elif verdict == z3.unknown:
                edges.append([a, b, "unknown"])
        solver.pop()
    rec = {
        "mode": mode,
        "voters": voters,
        "candidates": candidates,
        "pool": list(pool),
        "implications": edges,
        "seconds": round(time.perf_counter() - started, 3),
    }
    emit(tag, rec)
    for e in edges:
        print(" ".join(e[:2]) + (" [unknown]" if len(e) > 2 else ""), flush=True)
    print(f"\n{len(edges)} implications in {rec['seconds']}s", flush=True)
    return edges


# -- front end --------------------------------------------------------------


def main(argv=None):
    ap = argparse.ArgumentParser(prog="discover")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("mus")
    m.add_argument("--mode", default="scf")
    m.add_argument("--voters", type=int, default=3)
    m.add_argument("--candidates", type=int, default=3)
    m.add_argument("--max-size", type=int, default=3)
    m.add_argument("--timeout", type=float, default=60.0)
    m.add_argument("--tag", default=None)
    m.add_argument("--pool", nargs="*", default=None)

    f = sub.add_parser("frontier")
    f.add_argument("axioms", nargs="+")
    f.add_argument("--mode", default="scf")
    f.add_argument("--timeout", type=float, default=120.0)
    f.add_argument("--tag", default="frontier")
    f.add_argument("--sizes", default="2x3,3x3,4x3,5x3,6x3,2x4,3x4,2x5")

    i = sub.add_parser("implies")
    i.add_argument("--mode", default="scf")
    i.add_argument("--voters", type=int, default=3)
    i.add_argument("--candidates", type=int, default=3)
    i.add_argument("--timeout", type=float, default=60.0)
    i.add_argument("--tag", default=None)
    i.add_argument("--pool", nargs="*", default=None)

    c = sub.add_parser("count")
    c.add_argument("axioms", nargs="+")
    c.add_argument("--mode", default="scf")
    c.add_argument("--voters", type=int, default=3)
    c.add_argument("--candidates", type=int, default=3)
    c.add_argument("--cap", type=int, default=200)
    c.add_argument("--timeout", type=float, default=120.0)
    c.add_argument("--tag", default="count")

    ap.add_argument(
        "--max-clauses",
        type=int,
        default=None,
        help="raise the grounder's clause ceiling for a deliberate push past it",
    )
    a = ap.parse_args(argv)
    if a.max_clauses:
        _ground.MAX_CLAUSES = a.max_clauses
    if a.cmd == "mus":
        tag = a.tag or f"mus-{a.mode}-{a.voters}v{a.candidates}c"
        found, unresolved = mus(a.mode, a.voters, a.candidates, a.max_size, a.timeout, tag, a.pool)
        print(f"\n{len(found)} minimal impossibilities, {len(unresolved)} unresolved")
        for s in found:
            print("  " + " + ".join(sorted(s)))
    elif a.cmd == "implies":
        implies(a.mode, a.voters, a.candidates, a.timeout,
                a.tag or f"implies-{a.mode}-{a.voters}v{a.candidates}c", a.pool)
    elif a.cmd == "frontier":
        sizes = [tuple(int(x) for x in s.split("x")) for s in a.sizes.split(",")]
        frontier(a.axioms, a.mode, sizes, a.timeout, a.tag)
    else:
        count(a.axioms, a.mode, a.voters, a.candidates, a.cap, a.timeout, a.tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
