"""The DSL's signature, in one table, used twice.

The grounder decides what a name means while it unrolls quantifiers, which is the
right place for it but the wrong place to learn you made a mistake: by then the
message is about an argument count, not about what you meant. This file writes the
signature down once and gets two things out of it.

    gbnf(mode)      a grammar llama.cpp can generate under, so a proposal that does
                    not parse is structurally impossible rather than merely unlikely
    check(tree)     a sort checker, so `unanimous(p, i, b)` with a voter where a
                    candidate goes is caught here and explained in English

Neither talks to Z3 and neither imports a model.
"""

from __future__ import annotations

from core import dsl

# head -> (argument sorts, result sort). A result of None is a formula, not a term.
TERMS = {
    "sub": (("profile", "voter", "ballot"), "profile"),
    "lift": (("profile", "voter", "cand"), "profile"),
    "permc": (("profile", "cperm"), "profile"),
    "permv": (("profile", "vperm"), "profile"),
    "top": (("profile", "voter"), "cand"),
    "rev": (("profile",), "profile"),
}

FACTS = {
    "pref": ("profile", "voter", "cand", "cand"),
    "unanimous": ("profile", "cand", "cand"),
    "condorcet": ("profile", "cand"),
    "condorcetloser": ("profile", "cand"),
    "majoritytop": ("profile", "cand"),
    "samepair": ("profile", "profile", "cand", "cand"),
    "sametops": ("profile", "profile"),
    "improves": ("profile", "profile", "cand"),
    "neq": ("*", "*"),  # any two values of the same sort
}

ATOMS = {
    "wins": ("scf", ("profile", "cand")),
    "prefers": ("swf", ("profile", "cand", "cand")),
    "ranks": ("swf", ("profile", "ballot")),
}

# what a bound permutation maps when you apply it, as in s(a)
APPLIES = {"cperm": ("cand", "cand"), "vperm": ("voter", "voter")}

ENGLISH_SORT = {
    "profile": "a profile (everyone's ballots)",
    "voter": "a voter",
    "cand": "a candidate",
    "ballot": "a ballot (one ranking)",
    "cperm": "a relabelling of the candidates",
    "vperm": "a reshuffle of the voters",
}

ORDINAL = ("first", "second", "third", "fourth", "fifth")


class SortError(Exception):
    """A formula that parses but does not typecheck."""


# -- the sort checker -------------------------------------------------------


def check(tree, mode: str) -> None:
    """Raise SortError unless every application is applied to the right sorts."""
    if mode not in dsl.MODES:
        raise SortError(f"unknown rule kind {mode!r}")
    _formula(tree, mode, {})


def _formula(node, mode: str, env: dict) -> None:
    if isinstance(node, dsl.Quant):
        seen = set()
        for name, _ in node.binds:
            if name in seen:
                raise SortError(f"{name!r} is introduced twice in the same quantifier")
            seen.add(name)
        for name, sort in node.binds:
            if name in env:
                raise SortError(
                    f"{name!r} is already in use as {ENGLISH_SORT[env[name]]}; "
                    f"the language does not let an inner quantifier reuse a name"
                )
        inner = dict(env)
        inner.update(dict(node.binds))
        _formula(node.body, mode, inner)
        return
    if isinstance(node, dsl.Not):
        return _formula(node.arg, mode, env)
    if isinstance(node, (dsl.And, dsl.Or)):
        for a in node.args:
            _formula(a, mode, env)
        return
    if isinstance(node, (dsl.Imp, dsl.Iff)):
        _formula(node.left, mode, env)
        _formula(node.right, mode, env)
        return
    if isinstance(node, dsl.Var):
        raise SortError(
            f"{node.name!r} on its own is a value, not a statement; a statement has to "
            f"say something about it, like wins(p, {node.name})"
        )
    if not isinstance(node, dsl.App):
        raise SortError(f"cannot make sense of {node!r}")

    head, args = node.head, node.args
    if head in ATOMS:
        wants_mode, sorts = ATOMS[head]
        if wants_mode != mode:
            other = "a rule that elects one winner" if wants_mode == "scf" else "a rule that produces a ranking"
            raise SortError(f"{head}() only exists for {other}; this axiom is for the other kind")
        _apply(head, args, sorts, mode, env)
        return
    if head in FACTS:
        _apply(head, args, FACTS[head], mode, env)
        return
    if head in TERMS:
        raise SortError(
            f"{head}() builds {ENGLISH_SORT[TERMS[head][1]]}, it does not state anything; "
            f"it belongs inside a statement, not as one"
        )
    raise SortError(f"there is no property called {head!r} in this language")


def _apply(head: str, args, sorts, mode: str, env: dict) -> None:
    if len(args) != len(sorts):
        raise SortError(
            f"{head} takes {len(sorts)} argument{'s' if len(sorts) != 1 else ''}, "
            f"this one was given {len(args)}"
        )
    got = [_term(a, mode, env) for a in args]
    if sorts == ("*", "*"):
        if got[0] != got[1]:
            raise SortError(
                f"neq compares two things of the same kind, but this one compares "
                f"{ENGLISH_SORT[got[0]]} with {ENGLISH_SORT[got[1]]}"
            )
        return
    for n, (want, have) in enumerate(zip(sorts, got)):
        if want != have:
            raise SortError(
                f"the {ORDINAL[n]} argument of {head} should be {ENGLISH_SORT[want]}, "
                f"but it was given {ENGLISH_SORT[have]}"
            )


def _term(node, mode: str, env: dict) -> str:
    """Return the sort of a term, or raise."""
    if isinstance(node, dsl.Var):
        if node.name not in env:
            have = ", ".join(f"{n}:{s}" for n, s in env.items()) or "nothing"
            raise SortError(
                f"{node.name!r} was never introduced. In scope here: {have}. Every name "
                f"has to be introduced by a forall or an exists before it is used, so "
                f"either add {node.name} to the quantifier with a sort, or use one of "
                f"the names that is already there"
            )
        return env[node.name]
    if not isinstance(node, dsl.App):
        raise SortError(f"cannot make sense of {node!r}")

    head, args = node.head, node.args
    if head in TERMS:
        sorts, result = TERMS[head]
        _apply(head, args, sorts, mode, env)
        return result
    if head in env:
        sort = env[head]
        if sort not in APPLIES:
            raise SortError(
                f"{head} is {ENGLISH_SORT[sort]}; only a relabelling of the candidates "
                f"or a reshuffle of the voters can be applied to something"
            )
        takes, gives = APPLIES[sort]
        _apply(head, args, (takes,), mode, env)
        return gives
    if head in FACTS or head in ATOMS:
        raise SortError(
            f"{head}() is a statement, not a value; it cannot be used as an argument"
        )
    raise SortError(f"there is no operation called {head!r} in this language")


# -- the grammar ------------------------------------------------------------

_HEAD = """root ::= "{" ws "\\"name\\":" ws "\\"" name "\\"," ws "\\"english\\":" ws "\\"" english "\\"," ws "\\"formula\\":" ws "\\"" formula "\\"" ws "}"
ws ::= " "?
name ::= [a-z] [a-z0-9_]{2,30}
english ::= [a-zA-Z0-9 ,.'()>-]{8,180}
"""

# Bounded on purpose. An 8B under a grammar with unbounded repetition will happily
# emit forty bindings and never come back, so the binding list, the connective
# chains and the nesting depth all have ceilings. Every axiom in the library fits
# inside them: at most one quantifier prefix inside another, and parentheses one
# level deep.
_BODY = """
formula ::= quant | body
quant ::= ("forall " | "exists ") bind ("," ws bind){0,4} ". " nested
nested ::= inner-quant | body
inner-quant ::= ("forall " | "exists ") bind ("," ws bind){0,4} ". " body
bind ::= var ":" sort
sort ::= "profile" | "voter" | "cand" | "ballot" | "cperm" | "vperm"
var ::= [a-z]

body ::= imp (" <-> " imp)?
imp ::= disj (" -> " disj)?
disj ::= conj (" or " conj){0,2}
conj ::= unary (" and " unary){0,3}
unary ::= "not " simple | simple
simple ::= "(" flat ")" | atom

flat ::= fimp (" <-> " fimp)?
fimp ::= fdisj (" -> " fdisj)?
fdisj ::= fconj (" or " fconj){0,2}
fconj ::= lit (" and " lit){0,3}
lit ::= "not " atom | atom

term ::= var | app
app ::= APPS
atom ::= ATOMS
"""


def _call(head: str, arity: int, arg: str = "term") -> str:
    return '"%s(" %s ")"' % (head, ' "," ws '.join([arg] * arity))


def gbnf(mode: str) -> str:
    """A GBNF grammar whose every string is a well-formed DSL proposal for this mode."""
    if mode not in dsl.MODES:
        raise ValueError(f"unknown rule kind {mode!r}")
    apps = [_call(h, len(s), "var") for h, (s, _) in TERMS.items()]
    apps.append('var "(" var ")"')  # applying a bound permutation, as in s(a)
    atoms = [_call(h, len(s)) for h, s in FACTS.items()]
    atoms += [_call(h, len(s)) for h, (m, s) in ATOMS.items() if m == mode]
    body = _BODY.replace("APPS", " | ".join(apps)).replace("ATOMS", " | ".join(atoms))
    return _HEAD + body
