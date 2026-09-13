"""Ask the question and answer it.

One boolean selector per axiom, asserted as `selector -> axiom`. Checking under
those selectors as assumptions gives an unsat core in terms of axiom names, and
dropping an axiom is dropping an assumption, so the core can be minimised
without re-encoding anything.

Three answers, and only three:

    sat      a rule exists; here it is, and you can run it
    unsat    no rule exists; here is a minimal set of axioms to blame, and a
             witness rule for each proper subset of it
    unknown  the budget ran out; here is what was and was not established
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path

import z3

from . import rules
from .domain import Electorate
from .dsl import Axiom, parse_axioms
from .ground import Context, GroundTimeout, encode, estimate_vars, frame

AXIOM_FILE = Path(__file__).with_name("axioms.agora")

# Above this the encoding is too large to build, let alone solve. Refusing up
# front beats swapping for ten minutes and then reporting a timeout.
MAX_VARS = 1_500_000

_library: dict[str, Axiom] | None = None


def library() -> dict[str, Axiom]:
    """The axiom library, parsed once."""
    global _library
    if _library is None:
        _library = parse_axioms(AXIOM_FILE.read_text())
    return _library


def axiom_names(mode: str | None = None) -> list[str]:
    return [n for n, a in library().items() if mode is None or a.supports(mode)]


@dataclass
class Result:
    status: str  # "sat", "unsat" or "unknown"
    mode: str
    voters: int
    candidates: int
    axioms: tuple
    profiles: int
    variables: int
    timeout_s: float
    elapsed: float = 0.0
    rule: rules.Rule | None = None
    core: tuple | None = None
    core_minimal: bool = False
    witnesses: dict = field(default_factory=dict)
    verified: bool = False
    note: str = ""
    partial: "Result | None" = None

    def __str__(self) -> str:
        from .render import render

        return render(self)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "mode": self.mode,
            "voters": self.voters,
            "candidates": self.candidates,
            "axioms": list(self.axioms),
            "profiles": self.profiles,
            "variables": self.variables,
            "elapsed": round(self.elapsed, 3),
            "timeout_s": self.timeout_s,
            "rule": self.rule.as_dict() if self.rule else None,
            "core": list(self.core) if self.core else None,
            "core_minimal": self.core_minimal,
            "witnesses": {k: v.describe() for k, v in self.witnesses.items()},
            "verified": self.verified,
            "note": self.note,
            "partial": self.partial.as_dict() if self.partial else None,
        }


def derive(
    axioms,
    voters: int,
    candidates: int,
    mode: str = "scf",
    timeout: float = 60.0,
    minimise: bool = True,
    verify: bool = True,
    degrade: bool = True,
) -> Result:
    """Is there a rule over this electorate satisfying all these axioms?

    axioms      names from the library, or Axiom objects
    voters      number of voters
    candidates  number of candidates
    mode        "scf" (elect one winner) or "swf" (produce a social ranking)
    timeout     seconds for this electorate, minimisation included; if the run
                degrades to a smaller electorate, that attempt gets its own budget
    minimise    shrink an unsat core to a minimal one
    verify      re-check every rule handed back against its axioms, without the solver
    degrade     on timeout, report the largest smaller electorate that resolved
    """
    picked = _resolve(axioms, mode)
    names = tuple(a.name for a in picked)
    profiles = math.factorial(candidates) ** voters
    nvars = estimate_vars(voters, candidates, mode)

    base = Result(
        status="unknown",
        mode=mode,
        voters=voters,
        candidates=candidates,
        axioms=names,
        profiles=profiles,
        variables=nvars,
        timeout_s=timeout,
    )

    if nvars > MAX_VARS:
        base.note = (
            f"not attempted: the encoding needs {nvars:,} variables over {profiles:,} "
            f"profiles, past the {MAX_VARS:,} ceiling this core will build"
        )
        return _degraded(base, axioms, mode, timeout, minimise, verify) if degrade else base

    started = time.perf_counter()
    elec = Electorate(voters, candidates)
    ctx = Context(elec, mode, deadline=started + timeout)
    solver = z3.Solver(ctx=ctx.z3ctx)
    solver.set("random_seed", 0)
    solver.add(frame(ctx))
    sel = {}
    try:
        for ax in picked:
            s = z3.Bool(f"sel!{ax.name}", ctx.z3ctx)
            sel[ax.name] = s
            solver.add(z3.Implies(s, encode(ax, ctx)))
    except GroundTimeout as exc:
        base.elapsed = time.perf_counter() - started
        base.note = (
            f"the encoding itself did not finish inside {timeout:g}s over {profiles:,} "
            f"profiles ({exc}); the solver was never reached, so nothing is claimed "
            f"either way at this size"
        )
        return _degraded(base, axioms, mode, timeout, minimise, verify) if degrade else base

    def check(active):
        left = timeout - (time.perf_counter() - started)
        if left <= 0:
            return z3.unknown
        solver.set("timeout", max(1, int(left * 1000)))
        return solver.check([sel[n] for n in active])

    verdict = check(names)
    base.elapsed = time.perf_counter() - started

    if verdict == z3.sat:
        base.status = "sat"
        base.rule = rules.from_model(solver.model(), ctx, elec)
        if verify:
            bad = [a.name for a in picked if not base.rule.satisfies(a)]
            if bad:
                raise RuntimeError(f"solver returned a rule violating {bad}; encoding is wrong")
            base.verified = True
        base.elapsed = time.perf_counter() - started
        return base

    if verdict == z3.unsat:
        base.status = "unsat"
        core = tuple(n for n in names if sel[n] in solver.unsat_core())
        base.core_minimal = False
        if minimise:
            core, base.core_minimal = _minimise(core, check)
        base.core = core
        if base.core_minimal:
            lib = {a.name: a for a in picked}
            ok = True
            for dropped in core:
                rest = [n for n in core if n != dropped]
                if check(rest) != z3.sat:
                    ok = False
                    continue
                w = rules.from_model(solver.model(), ctx, elec)
                base.witnesses[dropped] = w
                if verify and not all(w.satisfies(lib[n]) for n in rest):
                    raise RuntimeError(f"witness for dropping {dropped} fails an axiom it should hold")
            base.verified = verify and ok and len(base.witnesses) == len(core)
        base.elapsed = time.perf_counter() - started
        return base

    base.note = (
        f"the solver did not settle this within {timeout:g}s over {profiles:,} profiles "
        f"and {nvars:,} variables; nothing is claimed either way at this size"
    )
    return _degraded(base, axioms, mode, timeout, minimise, verify) if degrade else base


def _resolve(axioms, mode: str) -> list[Axiom]:
    lib = library()
    out = []
    for a in axioms:
        if isinstance(a, str):
            if a not in lib:
                raise ValueError(f"no axiom named {a!r}; have {', '.join(lib)}")
            a = lib[a]
        if not a.supports(mode):
            raise ValueError(
                f"axiom {a.name!r} is not defined for {mode}; it covers {', '.join(a.modes)}"
            )
        out.append(a)
    if not out:
        raise ValueError("give at least one axiom")
    return out


def _minimise(core: tuple, check) -> tuple[tuple, bool]:
    """Deletion-based minimal unsatisfiable subset: one pass, each drop tested."""
    cur = list(core)
    for name in list(cur):
        trial = [n for n in cur if n != name]
        if not trial:
            continue
        verdict = check(trial)
        if verdict == z3.unsat:
            cur = trial
        elif verdict == z3.unknown:
            return tuple(cur), False
    return tuple(cur), True


def _degraded(base: Result, axioms, mode, timeout, minimise, verify) -> Result:
    """Walk the electorate down a voter at a time and report the first size that resolves."""
    for n in range(base.voters - 1, 1, -1):
        smaller = derive(
            axioms,
            n,
            base.candidates,
            mode=mode,
            timeout=timeout,
            minimise=minimise,
            verify=verify,
            degrade=False,
        )
        if smaller.status != "unknown":
            base.partial = smaller
            base.note += (
                f". The same axioms over {n} voters and {base.candidates} candidates came "
                f"out {smaller.status}; that is a statement about {n} voters, and nothing "
                f"here shows it carries up to {base.voters}"
            )
            return base
    return base
