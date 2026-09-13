"""Expand an axiom tree over a finite electorate into a Z3 formula.

This is the only place quantifiers are unrolled. Ground facts (who prefers what,
who beats whom) are decided in Python during the unroll, so a guard that is false
takes its whole clause out of the formula before Z3 ever sees it. That is what
keeps these encodings small enough to solve.

Two families of decision variable, one per rule kind:

    scf   wins(p, c)        candidate c wins at profile p
    swf   prefers(p, a, b)  society ranks a above b at profile p
"""

from __future__ import annotations

import math
import time
from itertools import product

import z3

from . import dsl
from .domain import Electorate


class GroundError(Exception):
    pass


class EncodingBudget(Exception):
    """The formula ran out of time or out of room before the solver saw it.

    Grounding is Python, not Z3, so a solver timeout cannot interrupt it: a
    quantifier over pairs of profiles is quadratic, and at four candidates and
    three voters that is billions of iterations. Assembling the result costs
    again, about seven seconds per million clauses. Both are budgeted here, so
    that a run which cannot finish says so instead of disappearing.
    """


# Assembling a conjunction costs roughly seven seconds per million clauses, and
# anything this large has no chance in the solver anyway.
MAX_CLAUSES = 2_000_000


# -- boolean constructors that fold Python bools ---------------------------


def mk_not(f):
    if f is True:
        return False
    if f is False:
        return True
    return z3.Not(f)


def mk_and(parts):
    out = []
    for f in parts:
        if f is False:
            return False
        if f is not True:
            out.append(f)
    if not out:
        return True
    return out[0] if len(out) == 1 else z3.And(out)


def mk_or(parts):
    out = []
    for f in parts:
        if f is True:
            return True
        if f is not False:
            out.append(f)
    if not out:
        return False
    return out[0] if len(out) == 1 else z3.Or(out)


def mk_imp(a, b):
    return mk_or([mk_not(a), b])


def mk_iff(a, b):
    if a is True:
        return b
    if a is False:
        return mk_not(b)
    if b is True:
        return a
    if b is False:
        return mk_not(a)
    return a == b


# -- variables --------------------------------------------------------------


class Context:
    """The decision variables for one electorate and one rule kind.

    Each context owns a private Z3 context. Z3's default context is global, so
    two identical calls in one process can be handed different AST ids by
    whatever ran between them, and come back with different (equally valid)
    models. Isolating it is what makes a question have one answer.
    """

    def __init__(self, elec: Electorate, mode: str, deadline: float | None = None) -> None:
        if mode not in dsl.MODES:
            raise GroundError(f"unknown mode {mode!r}")
        self.elec = elec
        self.mode = mode
        self.deadline = deadline
        self.z3ctx = z3.Context()
        self.pid = {p: n for n, p in enumerate(elec.profiles)}
        self.vars: dict[tuple, z3.BoolRef] = {}
        if mode == "scf":
            for p in elec.profiles:
                for c in elec.cands:
                    self.vars[(p, c)] = z3.Bool(f"w{self.pid[p]}_{c}", self.z3ctx)
        else:
            for p in elec.profiles:
                for a in elec.cands:
                    for b in elec.cands:
                        if a != b:
                            self.vars[(p, a, b)] = z3.Bool(f"r{self.pid[p]}_{a}_{b}", self.z3ctx)

    @property
    def var_count(self) -> int:
        return len(self.vars)

    def wins(self, p, c):
        return self.vars[(p, c)]

    def prefers(self, p, a, b):
        return False if a == b else self.vars[(p, a, b)]

    def ranks(self, p, r):
        """The social ranking at p is exactly the ballot r."""
        return mk_and(
            [self.prefers(p, r[i], r[j]) for i in range(len(r)) for j in range(i + 1, len(r))]
        )


def estimate_vars(voters: int, candidates: int, mode: str) -> int:
    """Variable count without building anything. Used to refuse hopeless sizes."""
    profiles = math.factorial(candidates) ** voters
    per = candidates if mode == "scf" else candidates * (candidates - 1)
    return profiles * per


# -- grounding --------------------------------------------------------------

_FACTS = {"pref": 4, "unanimous": 3, "condorcet": 2, "samepair": 4, "neq": 2}
_TERMS = {"sub": 3, "lift": 3, "permc": 2, "permv": 2, "top": 2}
_ATOMS = {"wins": ("scf", 2), "prefers": ("swf", 3), "ranks": ("swf", 2)}


def _domain(ctx: Context, sort: str):
    e = ctx.elec
    return {
        "profile": e.profiles,
        "voter": e.vs,
        "cand": e.cands,
        "ballot": e.ballots,
        "cperm": e.cperms,
        "vperm": e.vperms,
    }[sort]


def _term(node, ctx: Context, env: dict):
    """Evaluate a term to a Python value: a profile, a voter, a candidate, a ballot."""
    if isinstance(node, dsl.Var):
        if node.name not in env:
            raise GroundError(f"unbound name {node.name!r}")
        return env[node.name]

    head, args = node.head, node.args
    if head in _TERMS:
        if len(args) != _TERMS[head]:
            raise GroundError(f"{head} takes {_TERMS[head]} arguments, got {len(args)}")
        vals = [_term(a, ctx, env) for a in args]
        return getattr(ctx.elec, head)(*vals)
    if head in env and len(args) == 1:
        # applying a bound permutation, as in s(a)
        return env[head][_term(args[0], ctx, env)]
    raise GroundError(f"unknown term {head!r}")


def ground(node, ctx: Context, env: dict):
    """Expand a formula tree to a Z3 expression, or to a Python bool if it decides."""
    if isinstance(node, dsl.Quant):
        return _ground_quant(node, ctx, env)
    if isinstance(node, dsl.Not):
        return mk_not(ground(node.arg, ctx, env))
    if isinstance(node, dsl.And):
        return mk_and([ground(a, ctx, env) for a in node.args])
    if isinstance(node, dsl.Or):
        return mk_or([ground(a, ctx, env) for a in node.args])
    if isinstance(node, dsl.Imp):
        left = ground(node.left, ctx, env)
        if left is False:
            return True
        return mk_imp(left, ground(node.right, ctx, env))
    if isinstance(node, dsl.Iff):
        return mk_iff(ground(node.left, ctx, env), ground(node.right, ctx, env))
    if isinstance(node, dsl.App):
        return _ground_app(node, ctx, env)
    if isinstance(node, dsl.Var):
        raise GroundError(f"{node.name!r} is a term, not a formula")
    raise GroundError(f"cannot ground {node!r}")


def _ground_app(node: dsl.App, ctx: Context, env: dict):
    head, args = node.head, node.args
    if head in _FACTS:
        if len(args) != _FACTS[head]:
            raise GroundError(f"{head} takes {_FACTS[head]} arguments, got {len(args)}")
        vals = [_term(a, ctx, env) for a in args]
        if head == "neq":
            return vals[0] != vals[1]
        return getattr(ctx.elec, head)(*vals)
    if head in _ATOMS:
        mode, arity = _ATOMS[head]
        if mode != ctx.mode:
            raise GroundError(f"{head}() is only defined for {mode}, not {ctx.mode}")
        if len(args) != arity:
            raise GroundError(f"{head} takes {arity} arguments, got {len(args)}")
        return getattr(ctx, head)(*[_term(a, ctx, env) for a in args])
    raise GroundError(f"unknown predicate {head!r}")


def _ground_quant(node: dsl.Quant, ctx: Context, env: dict):
    names = [v for v, _ in node.binds]
    for n in names:
        if n in env:
            raise GroundError(f"{n!r} is already bound; the language does not shadow")
    domains = [_domain(ctx, s) for _, s in node.binds]
    forall = node.kind == "forall"
    parts = []
    ticks = 0
    try:
        for combo in product(*domains):
            ticks += 1
            if ctx.deadline is not None and not ticks % 65536 and time.perf_counter() > ctx.deadline:
                raise EncodingBudget(
                    f"still expanding {node.kind} over {len(domains)} sorts "
                    f"after the time budget ran out"
                )
            if len(parts) > MAX_CLAUSES:
                raise EncodingBudget(
                    f"one {node.kind} alone passed {MAX_CLAUSES:,} clauses"
                )
            for n, v in zip(names, combo):
                env[n] = v
            f = ground(node.body, ctx, env)
            if f is (not forall):  # False under forall, True under exists
                return not forall
            if f is forall:
                continue
            parts.append(f)
    finally:
        for n in names:
            env.pop(n, None)
    return mk_and(parts) if forall else mk_or(parts)


def encode(axiom: dsl.Axiom, ctx: Context):
    """Ground one axiom for the context's rule kind."""
    if ctx.mode not in axiom.bodies:
        raise GroundError(
            f"axiom {axiom.name!r} is not defined for {ctx.mode}; "
            f"it covers {', '.join(axiom.modes)}"
        )
    return ground(axiom.bodies[ctx.mode], ctx, {})


def frame(ctx: Context):
    """Constraints that make the variables denote a rule at all.

    Asserted unconditionally and never tracked, so they cannot turn up in an
    unsat core and be reported as though transitivity were one of your axioms.
    """
    e, out = ctx.elec, []
    if ctx.mode == "scf":
        for p in e.profiles:
            out.append(z3.PbEq([(ctx.wins(p, c), 1) for c in e.cands], 1))
    else:
        for p in e.profiles:
            for a in e.cands:
                for b in e.cands:
                    if a >= b:
                        continue
                    out.append(z3.Xor(ctx.prefers(p, a, b), ctx.prefers(p, b, a)))
            for a, b, c in product(e.cands, repeat=3):
                if a == b or b == c or a == c:
                    continue
                out.append(
                    z3.Implies(
                        z3.And(ctx.prefers(p, a, b), ctx.prefers(p, b, c)),
                        ctx.prefers(p, a, c),
                    )
                )
    return out


class ConcreteContext(Context):
    """A context whose variables are already decided.

    Grounding an axiom against one of these returns a Python bool rather than a
    formula, so a rule the solver handed back can be re-checked without the
    solver. That is what makes the constructive branch inspectable instead of
    merely reported.
    """

    def __init__(self, elec: Electorate, mode: str, table: dict) -> None:
        self.elec = elec
        self.mode = mode
        self.table = table
        self.vars = {}
        self.deadline = None
        self.z3ctx = None

    def wins(self, p, c):
        return self.table[p] == c

    def prefers(self, p, a, b):
        if a == b:
            return False
        r = self.table[p]
        return r.index(a) < r.index(b)
