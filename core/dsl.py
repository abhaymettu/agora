"""The axiom language: tokeniser, syntax tree, parser.

An axiom file is a sequence of blocks. Each block names an axiom, says which
rule kinds it is defined for, gives one sentence of English for the renderer,
and gives one formula per kind:

    axiom pareto
      modes swf scf
      english if every voter ranks a above b, society ranks a above b
      swf forall p:profile, a:cand, b:cand. unanimous(p,a,b) -> prefers(p,a,b)
      scf forall p:profile, a:cand, b:cand. unanimous(p,a,b) -> not wins(p,b)

Formulas are first-order over a finite, fixed signature. Quantifiers range over
sorts (profile, voter, cand, ballot, cperm, vperm); connectives are not, and,
or, ->, <->. Everything else is an application, and whether an application is a
solver variable, a ground fact, or a term is settled by the grounder, not here.

Nothing in this file evaluates anything. It parses text into a tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SORTS = ("profile", "voter", "cand", "ballot", "cperm", "vperm")
MODES = ("scf", "swf")
KEYWORDS = ("forall", "exists", "not", "and", "or")


class ParseError(Exception):
    pass


# -- syntax tree -----------------------------------------------------------


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class App:
    head: str
    args: tuple


@dataclass(frozen=True)
class Not:
    arg: object


@dataclass(frozen=True)
class And:
    args: tuple


@dataclass(frozen=True)
class Or:
    args: tuple


@dataclass(frozen=True)
class Imp:
    left: object
    right: object


@dataclass(frozen=True)
class Iff:
    left: object
    right: object


@dataclass(frozen=True)
class Quant:
    kind: str  # "forall" or "exists"
    binds: tuple  # ((var, sort), ...)
    body: object


@dataclass
class Axiom:
    name: str
    modes: tuple
    english: str
    bodies: dict = field(default_factory=dict)  # mode -> formula tree

    def supports(self, mode: str) -> bool:
        return mode in self.bodies


# -- tokeniser -------------------------------------------------------------

_PUNCT = {"(", ")", ",", ":", "."}


def tokenise(text: str, line: int) -> list:
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
        elif text.startswith("<->", i):
            out.append("<->")
            i += 3
        elif text.startswith("->", i):
            out.append("->")
            i += 2
        elif ch in _PUNCT:
            out.append(ch)
            i += 1
        elif ch.isalpha() or ch == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] in "_"):
                j += 1
            out.append(text[i:j])
            i = j
        else:
            raise ParseError(f"line {line}: unexpected character {ch!r}")
    return out


# -- parser ----------------------------------------------------------------


class _Parser:
    def __init__(self, tokens: list, line: int) -> None:
        self.t = tokens
        self.i = 0
        self.line = line

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, expected=None):
        tok = self.peek()
        if tok is None:
            raise ParseError(f"line {self.line}: formula ends early")
        if expected is not None and tok != expected:
            raise ParseError(f"line {self.line}: expected {expected!r}, got {tok!r}")
        self.i += 1
        return tok

    def parse(self):
        f = self.formula()
        if self.peek() is not None:
            raise ParseError(f"line {self.line}: trailing {self.peek()!r}")
        return f

    def formula(self):
        left = self.implication()
        while self.peek() == "<->":
            self.take()
            left = Iff(left, self.implication())
        return left

    def implication(self):
        left = self.disjunction()
        if self.peek() == "->":
            self.take()
            return Imp(left, self.implication())
        return left

    def disjunction(self):
        parts = [self.conjunction()]
        while self.peek() == "or":
            self.take()
            parts.append(self.conjunction())
        return parts[0] if len(parts) == 1 else Or(tuple(parts))

    def conjunction(self):
        parts = [self.unary()]
        while self.peek() == "and":
            self.take()
            parts.append(self.unary())
        return parts[0] if len(parts) == 1 else And(tuple(parts))

    def unary(self):
        tok = self.peek()
        if tok == "not":
            self.take()
            return Not(self.unary())
        if tok in ("forall", "exists"):
            return self.quantifier()
        if tok == "(":
            self.take()
            f = self.formula()
            self.take(")")
            return f
        return self.application()

    def quantifier(self):
        kind = self.take()
        binds = [self.binding()]
        while self.peek() == ",":
            self.take()
            binds.append(self.binding())
        self.take(".")
        return Quant(kind, tuple(binds), self.formula())

    def binding(self):
        name = self.name()
        self.take(":")
        sort = self.name()
        if sort not in SORTS:
            raise ParseError(f"line {self.line}: unknown sort {sort!r}")
        return (name, sort)

    def application(self):
        head = self.name()
        if self.peek() != "(":
            return Var(head)
        self.take("(")
        args = [self.application()]
        while self.peek() == ",":
            self.take()
            args.append(self.application())
        self.take(")")
        return App(head, tuple(args))

    def name(self):
        tok = self.take()
        if tok in KEYWORDS or tok in _PUNCT or tok in ("->", "<->"):
            raise ParseError(f"line {self.line}: expected a name, got {tok!r}")
        return tok


def parse_formula(text: str, line: int = 0):
    return _Parser(tokenise(text, line), line).parse()


# -- file parser -----------------------------------------------------------


def parse_axioms(text: str) -> dict:
    """Parse an axiom file into {name: Axiom}, preserving file order."""
    axioms, current = {}, None
    for line, raw in _logical_lines(text):
        head, _, rest = raw.partition(" ")
        rest = rest.strip()
        if head == "axiom":
            if not rest:
                raise ParseError(f"line {line}: axiom needs a name")
            if rest in axioms:
                raise ParseError(f"line {line}: axiom {rest!r} defined twice")
            current = Axiom(name=rest, modes=(), english="")
            axioms[rest] = current
        elif current is None:
            raise ParseError(f"line {line}: {head!r} before any axiom block")
        elif head == "modes":
            modes = tuple(m for m in rest.replace(",", " ").split() if m)
            bad = [m for m in modes if m not in MODES]
            if bad:
                raise ParseError(f"line {line}: unknown mode {bad[0]!r}")
            current.modes = modes
        elif head == "english":
            current.english = rest
        elif head in MODES:
            if head not in current.modes:
                raise ParseError(
                    f"line {line}: {current.name} gives a {head} formula "
                    f"but does not list {head} in its modes"
                )
            current.bodies[head] = parse_formula(rest, line)
        else:
            raise ParseError(f"line {line}: unknown directive {head!r}")

    for ax in axioms.values():
        missing = [m for m in ax.modes if m not in ax.bodies]
        if missing:
            raise ParseError(f"axiom {ax.name!r} declares {missing[0]} but gives no formula")
        if not ax.english:
            raise ParseError(f"axiom {ax.name!r} has no english line")
    return axioms


def _logical_lines(text: str):
    """Yield (line number, joined line), dropping comments and blanks.

    A line ending in a backslash continues onto the next.
    """
    buf, start = "", 0
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line and not buf:
            continue
        if not buf:
            start = n
        if line.endswith("\\"):
            buf += line[:-1].strip() + " "
            continue
        buf += line
        if buf:
            yield start, buf
        buf = ""
    if buf:
        yield start, buf
