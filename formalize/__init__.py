"""Plain English in, a checked axiom out, or a plain-English refusal.

The model drafts. It does not decide. Between the draft and the axiom sit gates,
and every one of them is code that does not involve the model:

    grammar       generation is constrained by a GBNF built from the DSL grammar,
                  so a formula that does not parse is structurally impossible
    parse         belt and braces: the core's own parser, on the string
    sorts         arity and argument sort per head, unbound names, reused names
    ground        the formula expands over a real electorate without complaint
    satisfiable   some rule satisfies it alone, so it is not self-contradictory
    non-vacuous   some rule breaks it, so it is a constraint rather than a tautology

Then one thing that is shown rather than gated: which textbook rules the axiom
accepts and which it rejects. The model's English is a claim; that table is a
fact, and it is what a reader should look at before accepting the axiom.

    from formalize import formalize
    p = formalize("a candidate ranked last by everyone should never win", "scf")
    p.accepted, p.axiom, p.why, p.behaviour
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields

from core import Axiom, Electorate, ParseError, derive, parse_formula, reference_rules
from core.dsl import Not
from core.ground import Context, GroundError, encode
from core.rules import Rule

from .grammar import SortError, check
from .model import ModelUnavailable, health, propose

# Every gate runs over this electorate. Two voters and three candidates is the
# smallest size where all six sorts are non-trivial and every classical theorem
# already bites, and it grounds in well under a second, so a stranger typing an
# axiom is not left watching a spinner.
GATE_VOTERS = 2
GATE_CANDIDATES = 3

@dataclass
class Proposal:
    """What came back from a formalisation attempt, gates and all."""

    text: str
    mode: str
    name: str = ""
    english: str = ""
    formula: str = ""
    backend: str = ""
    accepted: bool = False
    failed: str = ""  # the gate that stopped it, if any
    why: str = ""  # plain English, for a reader who is not a logician
    gates: list = field(default_factory=list)  # [{step, passed, note}]
    behaviour: list = field(default_factory=list)  # [{rule, holds}]
    attempts: list = field(default_factory=list)  # rejected drafts, in order
    axiom: Axiom | None = None

    def as_dict(self) -> dict:
        """JSON-safe: everything except the Axiom object itself."""
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != "axiom"}


# How many times the model gets to answer the checker before we give up. Two is
# enough in practice: the 8B's usual mistake is a name it forgot to bind, and being
# told exactly that fixes it. More rounds mostly buys longer waits.
REPAIRS = 2


def formalize(text: str, mode: str, timeout: float = 90.0, repairs: int = REPAIRS) -> Proposal:
    """Draft a formalisation of `text` and run it through every gate.

    A rejected draft is not thrown away: the gate's own complaint goes back to the
    model and it tries again. Every attempt is kept on the proposal, so the page can
    show that the checker, not the model, is what decided.
    """
    history, p = [], None
    for attempt in range(repairs + 1):
        draft = propose(text, mode, timeout=timeout, repair=history,
                        temperature=0.0 if not attempt else 0.2 + 0.3 * attempt)
        p = vet(draft["formula"], mode, text=text, name=draft["name"],
                english=draft["english"], backend=draft["backend"])
        p.attempts = [{"formula": f, "why": w} for f, w in history]
        if p.accepted:
            return p
        history.append((p.formula, p.why))
    p.attempts = [{"formula": f, "why": w} for f, w in history[:-1]]
    return p


def vet(formula: str, mode: str, text: str = "", name: str = "custom",
        english: str = "", backend: str = "") -> Proposal:
    """Run one formula through the gates. No model involved; testable on its own."""
    p = Proposal(text=text or english, mode=mode, name=_slug(name),
                 english=english, formula=formula.strip(), backend=backend)

    tree = _gate(p, "parse", lambda: parse_formula(p.formula), ParseError,
                 "that is not a well-formed statement")
    if tree is _FAILED:
        return p

    if _gate(p, "sorts", lambda: check(tree, mode), SortError, "") is _FAILED:
        return p

    p.axiom = Axiom(name=p.name, modes=(mode,), english=english or text or p.name,
                    bodies={mode: tree})
    elec = Electorate(GATE_VOTERS, GATE_CANDIDATES)

    if _gate(p, "ground", lambda: encode(p.axiom, Context(elec, mode)), GroundError,
             "it cannot be expanded over a real electorate") is _FAILED:
        p.axiom = None
        return p

    result = derive([p.axiom], GATE_VOTERS, GATE_CANDIDATES, mode=mode, timeout=20.0,
                    minimise=False, degrade=False)
    if result.status != "sat":
        p.axiom = None
        p.failed = "satisfiable"
        undecided = result.status == "unknown"
        p.why = (
            "no rule at all satisfies this, not even on its own, so it cannot be "
            "combined with anything: it asks for something self-contradictory"
            if not undecided
            else "this could not be settled inside the budget, so it is not accepted"
        )
        p.gates.append({"step": "satisfiable", "passed": False, "note": p.why})
        return p
    p.gates.append({"step": "satisfiable", "passed": True,
                    "note": f"a rule satisfying it alone exists: {result.rule.describe()}"})

    p.behaviour = _behaviour(p.axiom, elec, mode)

    # Vacuity is a question about every rule, not about the eight we can name:
    # `monotone` at two voters and three candidates is satisfied by all eight and
    # is still a real axiom. So ask the solver for a rule that breaks it. If the
    # negation is satisfiable the axiom rules something out; if it is not, the
    # axiom is true of every rule there is and constrains nothing.
    negation = Axiom(name=f"not_{p.name}", modes=(mode,), english="",
                     bodies={mode: Not(tree)})
    against = derive([negation], GATE_VOTERS, GATE_CANDIDATES, mode=mode, timeout=20.0,
                     minimise=False, degrade=False)
    if against.status != "sat":
        p.axiom = None
        p.failed = "non-vacuous"
        p.why = (
            "every rule there is already satisfies this, so as written it rules "
            "nothing out and adding it changes no answer"
            if against.status == "unsat"
            else "whether any rule breaks this could not be settled inside the budget, "
            "so it is not accepted"
        )
        p.gates.append({"step": "non-vacuous", "passed": False, "note": p.why})
        return p
    p.gates.append({"step": "non-vacuous", "passed": True,
                    "note": f"a rule that breaks it exists, so it is a real constraint: "
                            f"{against.rule.describe()}"})

    p.accepted = True
    return p


def _behaviour(axiom: Axiom, elec: Electorate, mode: str) -> list:
    """Which named rules satisfy the axiom. No solver: each is a decided table."""
    out = []
    for name, table in reference_rules(elec, mode):
        out.append({"rule": name, "holds": Rule(mode, elec, table).satisfies(axiom)})
    return out


_FAILED = object()


def _gate(p: Proposal, step: str, run, kind, headline: str):
    try:
        value = run()
    except kind as exc:
        p.failed = step
        p.why = f"{headline}: {exc}" if headline else str(exc)
        p.gates.append({"step": step, "passed": False, "note": str(exc)})
        return _FAILED
    p.gates.append({"step": step, "passed": True, "note": ""})
    return value


def _slug(name: str) -> str:
    keep = [c if c.isalnum() else "_" for c in (name or "custom").strip().lower()]
    out = "".join(keep).strip("_") or "custom"
    return out[:32]


__all__ = ["formalize", "vet", "Proposal", "health", "propose", "ModelUnavailable"]
