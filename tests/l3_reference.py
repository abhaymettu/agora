"""L3's independent re-derivation of the axiom library.

Nothing here imports from `core`. This is a second implementation, written from
the axiom library (`core/axioms.agora`, which is data) and the classical
statements of the theorems, so that the core can be checked against something
that does not share its bugs. If the two agree, agreement means something.

Three deliberate differences from the core, so the check is not a mirror:

1. Social rankings use one boolean per *unordered* pair, with `above(p, b, a)`
   being the syntactic negation of `above(p, a, b)`. Antisymmetry is therefore
   a property of the representation, not an asserted constraint. The core
   asserts Xor over two variables per pair instead.
2. Exactly-one-winner is at-least-one plus pairwise at-most-one, not a
   pseudo-boolean count.
3. Axioms are Python generators of (label, constraint) pairs over a swappable
   logic backend. The same generator runs twice: against z3 expressions to
   search for a rule, and against Python booleans to check a decided rule.
   One definition, two uses, so the symbolic and concrete readings of an axiom
   cannot drift apart.

The labels exist so a violation says which profile broke which axiom.
"""

from itertools import combinations, permutations, product

import z3

NAMES = "ABCDEFGH"


# --------------------------------------------------------------------------
# domain
# --------------------------------------------------------------------------


class Elec:
    """A finite electorate: n voters, m candidates, resolute outcomes.

    Candidates are 0..m-1. A ballot is a tuple of candidates, best first.
    A profile is a tuple of ballots, one per voter.
    """

    def __init__(self, voters, candidates):
        self.n = voters
        self.m = candidates
        self.cands = tuple(range(candidates))
        self.vs = tuple(range(voters))
        self.ballots = tuple(permutations(self.cands))
        self.profiles = tuple(product(self.ballots, repeat=voters))
        self.cperms = tuple(permutations(self.cands))
        self.vperms = tuple(permutations(self.vs))
        # ordered pairs of distinct candidates, and unordered ones
        self.opairs = tuple((a, b) for a in self.cands for b in self.cands if a != b)
        self.upairs = tuple(combinations(self.cands, 2))
        self._rank = {
            b: {c: i for i, c in enumerate(b)} for b in self.ballots
        }

    # ground facts -------------------------------------------------------

    def pref(self, p, i, a, b):
        """Voter i ranks a strictly above b in p."""
        r = self._rank[p[i]]
        return r[a] < r[b]

    def unanimous(self, p, a, b):
        return a != b and all(self.pref(p, i, a, b) for i in self.vs)

    def beats(self, p, a, b):
        """a beats b head to head: strictly more voters put a first."""
        for_a = sum(1 for i in self.vs if self.pref(p, i, a, b))
        return for_a * 2 > self.n

    def condorcet(self, p, c):
        return all(self.beats(p, c, d) for d in self.cands if d != c)

    def samepair(self, p, q, a, b):
        return all(self.pref(p, i, a, b) == self.pref(q, i, a, b) for i in self.vs)

    # terms --------------------------------------------------------------

    def sub(self, p, i, r):
        """p with voter i's ballot replaced by r."""
        return p[:i] + (r,) + p[i + 1 :]

    def lift(self, p, i, c):
        """p with c raised one place on voter i's ballot; unchanged at the top."""
        k = self._rank[p[i]][c]
        if k == 0:
            return p
        b = list(p[i])
        b[k - 1], b[k] = b[k], b[k - 1]
        return self.sub(p, i, tuple(b))

    def permc(self, p, s):
        """p with every candidate relabelled: a becomes s[a]."""
        return tuple(tuple(s[a] for a in b) for b in p)

    def permv(self, p, t):
        """p with ballots reassigned between voters: voter i gets t[i]'s ballot."""
        return tuple(p[t[i]] for i in self.vs)

    def top(self, p, i):
        return p[i][0]

    # display ------------------------------------------------------------

    def show_ballot(self, b):
        return " > ".join(NAMES[c] for c in b)

    def show_profile(self, p):
        return " | ".join(self.show_ballot(b) for b in p)


# --------------------------------------------------------------------------
# logic backends
# --------------------------------------------------------------------------


class PyLogic:
    """Constraints evaluated as Python booleans, for checking a decided rule."""

    def and_(self, xs):
        return all(xs)

    def or_(self, xs):
        return any(xs)

    def not_(self, x):
        return not x

    def implies(self, a, b):
        return (not a) or b

    def iff(self, a, b):
        return bool(a) == bool(b)


class Z3Logic:
    """Constraints built as z3 expressions, for searching for a rule."""

    def __init__(self, ctx):
        self.ctx = ctx

    def and_(self, xs):
        xs = list(xs)
        return z3.And(xs) if xs else z3.BoolVal(True, self.ctx)

    def or_(self, xs):
        xs = list(xs)
        return z3.Or(xs) if xs else z3.BoolVal(False, self.ctx)

    def not_(self, x):
        return z3.Not(x)

    def implies(self, a, b):
        return z3.Implies(a, b)

    def iff(self, a, b):
        return a == b


# --------------------------------------------------------------------------
# axioms, mode by mode
# --------------------------------------------------------------------------
#
# Each generator yields (label, constraint). `above(p, a, b)` is the literal
# for "society ranks a above b at p"; `wins(p, c)` for "c wins at p".


def swf_pareto(E, L, above):
    for p in E.profiles:
        for a, b in E.opairs:
            if E.unanimous(p, a, b):
                yield f"pareto: all of {E.show_profile(p)} put {NAMES[a]} over {NAMES[b]}", above(p, a, b)


def swf_nondictatorial(E, L, above):
    for i in E.vs:
        escapes = [
            L.not_(above(p, a, b))
            for p in E.profiles
            for a, b in E.opairs
            if E.pref(p, i, a, b)
        ]
        yield f"nondictatorial: voter {i + 1} is never overruled", L.or_(escapes)


def swf_surjective(E, L, above):
    for r in E.ballots:
        reachable = [
            L.and_([above(p, a, b) for a, b in combinations(r, 2)])
            for p in E.profiles
        ]
        yield f"surjective: {E.show_ballot(r)} is never the social ranking", L.or_(reachable)


def swf_monotone(E, L, above):
    for p in E.profiles:
        for i in E.vs:
            for a, b in E.opairs:
                q = E.lift(p, i, a)
                if q == p:
                    continue
                yield (
                    f"monotone: raising {NAMES[a]} on voter {i + 1}'s ballot at "
                    f"{E.show_profile(p)} loses it {NAMES[b]}",
                    L.implies(above(p, a, b), above(q, a, b)),
                )


def swf_condorcet(E, L, above):
    for p in E.profiles:
        for a, b in E.opairs:
            if E.condorcet(p, a):
                yield (
                    f"condorcet: {NAMES[a]} beats everyone at {E.show_profile(p)} "
                    f"but is not put over {NAMES[b]}",
                    above(p, a, b),
                )


def swf_iia(E, L, above):
    ps = E.profiles
    for j, q in enumerate(ps):
        for p in ps[:j]:
            for a, b in E.upairs:
                if E.samepair(p, q, a, b):
                    yield (
                        f"iia: {E.show_profile(p)} and {E.show_profile(q)} agree on "
                        f"{NAMES[a]} against {NAMES[b]} but society does not",
                        L.iff(above(p, a, b), above(q, a, b)),
                    )


def swf_anonymous(E, L, above):
    for p in E.profiles:
        for t in E.vperms:
            q = E.permv(p, t)
            if q == p:
                continue
            for a, b in E.upairs:
                yield (
                    f"anonymous: {E.show_profile(p)} and its reshuffle "
                    f"{E.show_profile(q)} differ on {NAMES[a]} against {NAMES[b]}",
                    L.iff(above(p, a, b), above(q, a, b)),
                )


def swf_neutral(E, L, above):
    for p in E.profiles:
        for s in E.cperms:
            q = E.permc(p, s)
            for a, b in E.upairs:
                yield (
                    f"neutral: relabelling {E.show_profile(p)} breaks "
                    f"{NAMES[a]} against {NAMES[b]}",
                    L.iff(above(p, a, b), above(q, s[a], s[b])),
                )


def scf_pareto(E, L, wins):
    for p in E.profiles:
        for a, b in E.opairs:
            if E.unanimous(p, a, b):
                yield (
                    f"pareto: {NAMES[b]} wins {E.show_profile(p)} though everyone "
                    f"prefers {NAMES[a]}",
                    L.not_(wins(p, b)),
                )


def scf_nondictatorial(E, L, wins):
    for i in E.vs:
        escapes = [L.not_(wins(p, E.top(p, i))) for p in E.profiles]
        yield f"nondictatorial: voter {i + 1}'s favourite always wins", L.or_(escapes)


def scf_surjective(E, L, wins):
    for c in E.cands:
        yield (
            f"surjective: {NAMES[c]} never wins",
            L.or_([wins(p, c) for p in E.profiles]),
        )


def scf_strategyproof(E, L, wins):
    for p in E.profiles:
        for i in E.vs:
            for a, b in E.opairs:
                if not E.pref(p, i, a, b):
                    continue
                for r in E.ballots:
                    q = E.sub(p, i, r)
                    if q == p:
                        continue
                    yield (
                        f"strategyproof: at {E.show_profile(p)} voter {i + 1} gets "
                        f"{NAMES[b]}, and {E.show_ballot(r)} would get {NAMES[a]}",
                        L.not_(L.and_([wins(p, b), wins(q, a)])),
                    )


def scf_monotone(E, L, wins):
    for p in E.profiles:
        for i in E.vs:
            for c in E.cands:
                q = E.lift(p, i, c)
                if q == p:
                    continue
                yield (
                    f"monotone: {NAMES[c]} wins {E.show_profile(p)} but loses once "
                    f"voter {i + 1} raises it",
                    L.implies(wins(p, c), wins(q, c)),
                )


def scf_condorcet(E, L, wins):
    for p in E.profiles:
        for c in E.cands:
            if E.condorcet(p, c):
                yield (
                    f"condorcet: {NAMES[c]} beats everyone at {E.show_profile(p)} "
                    f"but does not win",
                    wins(p, c),
                )


def scf_anonymous(E, L, wins):
    for p in E.profiles:
        for t in E.vperms:
            q = E.permv(p, t)
            if q == p:
                continue
            for c in E.cands:
                yield (
                    f"anonymous: {E.show_profile(p)} and its reshuffle "
                    f"{E.show_profile(q)} disagree about {NAMES[c]}",
                    L.iff(wins(p, c), wins(q, c)),
                )


def scf_neutral(E, L, wins):
    for p in E.profiles:
        for s in E.cperms:
            q = E.permc(p, s)
            for c in E.cands:
                yield (
                    f"neutral: relabelling {E.show_profile(p)} does not carry "
                    f"{NAMES[c]} with it",
                    L.iff(wins(p, c), wins(q, s[c])),
                )


AXIOMS = {
    "swf": {
        "pareto": swf_pareto,
        "nondictatorial": swf_nondictatorial,
        "surjective": swf_surjective,
        "monotone": swf_monotone,
        "condorcet": swf_condorcet,
        "iia": swf_iia,
        "anonymous": swf_anonymous,
        "neutral": swf_neutral,
    },
    "scf": {
        "pareto": scf_pareto,
        "nondictatorial": scf_nondictatorial,
        "surjective": scf_surjective,
        "strategyproof": scf_strategyproof,
        "monotone": scf_monotone,
        "condorcet": scf_condorcet,
        "anonymous": scf_anonymous,
        "neutral": scf_neutral,
    },
}


# --------------------------------------------------------------------------
# checking a decided rule, with no solver in sight
# --------------------------------------------------------------------------


def concrete_reader(E, mode, table):
    """Turn an outcome table into the literal reader the axioms consume.

    `table` maps profile -> winning candidate (scf) or social ranking (swf).
    """
    L = PyLogic()
    if mode == "scf":
        return L, (lambda p, c: table[p] == c)
    rank = {p: {c: i for i, c in enumerate(r)} for p, r in table.items()}
    return L, (lambda p, a, b: rank[p][a] < rank[p][b])


def frame_violations(E, mode, table):
    """The rule itself must be well formed before any axiom is asked about."""
    bad = []
    if set(table) != set(E.profiles):
        bad.append(
            f"frame: table covers {len(table)} profiles, electorate has {len(E.profiles)}"
        )
        return bad
    for p, out in table.items():
        if mode == "scf":
            if out not in E.cands:
                bad.append(f"frame: {E.show_profile(p)} elects {out!r}")
        else:
            if tuple(sorted(out)) != E.cands:
                bad.append(f"frame: {E.show_profile(p)} ranks {out!r}")
    return bad


def violations(E, mode, table, names):
    """Every axiom in `names`, checked against `table` on every profile."""
    bad = frame_violations(E, mode, table)
    if bad:
        return bad, 0
    L, lit = concrete_reader(E, mode, table)
    checked = 0
    for name in names:
        for label, ok in AXIOMS[mode][name](E, L, lit):
            checked += 1
            if not ok:
                bad.append(label)
    return bad, checked


# --------------------------------------------------------------------------
# searching for a rule, with my own encoding
# --------------------------------------------------------------------------


def _encode(E, mode, names, ctx):
    L = Z3Logic(ctx)
    frame = []
    if mode == "scf":
        var = {
            (p, c): z3.Bool(f"w[{pi}][{c}]", ctx)
            for pi, p in enumerate(E.profiles)
            for c in E.cands
        }
        lit = lambda p, c: var[(p, c)]  # noqa: E731
        for p in E.profiles:
            row = [var[(p, c)] for c in E.cands]
            frame.append(z3.Or(*row))
            for x, y in combinations(row, 2):
                frame.append(z3.Not(z3.And(x, y)))
    else:
        var = {
            (p, a, b): z3.Bool(f"a[{pi}][{a}{b}]", ctx)
            for pi, p in enumerate(E.profiles)
            for a, b in E.upairs
        }
        # antisymmetry is in the representation: one variable per unordered pair
        def lit(p, a, b):
            return var[(p, a, b)] if a < b else z3.Not(var[(p, b, a)])

        # completeness and antisymmetry are free; a complete antisymmetric
        # relation is a linear order exactly when no triple cycles
        for p in E.profiles:
            for x, y, z in combinations(E.cands, 3):
                frame.append(z3.Not(z3.And(lit(p, x, y), lit(p, y, z), lit(p, z, x))))
                frame.append(z3.Not(z3.And(lit(p, x, z), lit(p, z, y), lit(p, y, x))))

    body = [c for name in names for _, c in AXIOMS[mode][name](E, L, lit)]
    return var, frame, body


def _read_model(E, mode, model, var):
    table = {}
    if mode == "scf":
        for p in E.profiles:
            won = [c for c in E.cands if z3.is_true(model.eval(var[(p, c)], True))]
            if len(won) != 1:
                raise AssertionError(f"model elects {won} at {E.show_profile(p)}")
            table[p] = won[0]
        return table
    for p in E.profiles:
        def above(a, b):
            v = model.eval(var[(p, a, b)] if a < b else var[(p, b, a)], True)
            return z3.is_true(v) if a < b else not z3.is_true(v)

        # position = how many candidates you sit above
        wins_over = {a: sum(1 for b in E.cands if b != a and above(a, b)) for a in E.cands}
        order = tuple(sorted(E.cands, key=lambda a: -wins_over[a]))
        if sorted(wins_over.values()) != list(range(E.m)):
            raise AssertionError(f"model is not a linear order at {E.show_profile(p)}")
        table[p] = order
    return table


def solve(E, mode, names, timeout=120.0):
    """My own encoding, my own solve. Returns (status, table).

    status is "sat", "unsat" or "unknown"; table is None unless sat.
    """
    ctx = z3.Context()
    var, frame, body = _encode(E, mode, names, ctx)
    s = z3.Solver(ctx=ctx)
    s.set("random_seed", 0)
    s.set("timeout", int(timeout * 1000))
    for c in frame + body:
        s.add(c)
    r = s.check()
    if r == z3.sat:
        return "sat", _read_model(E, mode, s.model(), var)
    if r == z3.unsat:
        return "unsat", None
    return "unknown", None


def verify_minimal_unsat(E, mode, core, timeout=120.0):
    """Confirm `core` is unsatisfiable and that every member of it is needed.

    Returns a dict. "unsat" is my own verdict on the whole set. "witnesses"
    maps each dropped axiom to a rule satisfying the rest, and every such rule
    is re-checked against the rest exhaustively, with no solver involved.
    """
    out = {"core": tuple(core), "witnesses": {}, "problems": []}  # dropped -> checks run
    status, _ = solve(E, mode, core, timeout)
    out["status"] = status
    if status != "unsat":
        out["problems"].append(f"the core came back {status}, not unsat")
    for dropped in core:
        rest = [x for x in core if x != dropped]
        if not rest:
            out["witnesses"][dropped] = 0
            continue
        st, table = solve(E, mode, rest, timeout)
        if st != "sat":
            out["problems"].append(f"dropping {dropped} left {st}, so it is not needed")
            continue
        bad, checked = violations(E, mode, table, rest)
        if bad:
            out["problems"].append(
                f"my own witness for dropping {dropped} violates {bad[0]}"
            )
        out["witnesses"][dropped] = checked
    return out


# --------------------------------------------------------------------------
# recognising the shapes the theory predicts
# --------------------------------------------------------------------------


def dictators(E, mode, table):
    """Voters (one-based) whose ballot is always the outcome."""
    out = []
    for i in E.vs:
        if mode == "scf":
            if all(table[p] == E.top(p, i) for p in E.profiles):
                out.append(i + 1)
        else:
            if all(table[p] == p[i] for p in E.profiles):
                out.append(i + 1)
    return out


def inverse_dictators(E, mode, table):
    """Voters whose ballot, reversed, is always the outcome."""
    if mode == "scf":
        return [i + 1 for i in E.vs if all(table[p] == p[i][-1] for p in E.profiles)]
    return [
        i + 1 for i in E.vs if all(table[p] == tuple(reversed(p[i])) for p in E.profiles)
    ]
