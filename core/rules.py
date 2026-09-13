"""A rule the solver found, as an object you can run and check.

The solver returns an assignment. This turns it into something with a public
face: give it a profile, it gives you a winner or a ranking; ask it what it is,
and it tells you if it recognises itself as one of the textbook rules.
"""

from __future__ import annotations

from dataclasses import dataclass

from .domain import CAND_NAMES, Ballot, Electorate, Profile
from .ground import ConcreteContext, ground


@dataclass
class Rule:
    """A complete voting rule over one electorate."""

    mode: str
    elec: Electorate
    table: dict  # profile -> winning candidate (scf) or social ranking (swf)

    # -- running it ---------------------------------------------------------

    def outcome(self, profile):
        """Winner for scf, social ranking for swf. Accepts 'A>B>C | B>C>A'."""
        if not isinstance(profile, tuple):
            profile = self.elec.parse_profile(profile)
        if profile not in self.table:
            raise KeyError(f"{self.elec.show_profile(profile)} is not a profile of this electorate")
        return self.table[profile]

    def winner(self, profile) -> int:
        if self.mode != "scf":
            raise TypeError("this is a social welfare function; ask for ranking()")
        return self.outcome(profile)

    def ranking(self, profile) -> Ballot:
        if self.mode != "swf":
            raise TypeError("this is a social choice function; ask for winner()")
        return self.outcome(profile)

    def show_outcome(self, profile) -> str:
        out = self.outcome(profile)
        return CAND_NAMES[out] if self.mode == "scf" else self.elec.show_ballot(out)

    def rows(self):
        """Every profile and what it elects, in a fixed order."""
        for p in self.elec.profiles:
            yield self.elec.show_profile(p), self.show_outcome(p)

    def as_dict(self) -> dict:
        """JSON-safe. Profiles become 'A>B>C | B>C>A', outcomes become names."""
        return {
            "mode": self.mode,
            "voters": self.elec.voters,
            "candidates": self.elec.candidates,
            "table": {self.elec.show_profile(p): self.show_outcome(p) for p in self.elec.profiles},
        }

    # -- checking it --------------------------------------------------------

    def satisfies(self, axiom) -> bool:
        """Re-check an axiom against this rule without the solver."""
        ctx = ConcreteContext(self.elec, self.mode, self.table)
        result = ground(axiom.bodies[self.mode], ctx, {})
        if not isinstance(result, bool):
            raise RuntimeError(f"{axiom.name} did not fully decide against a concrete rule")
        return result

    # -- naming it ----------------------------------------------------------

    def matches(self) -> list[str]:
        """Textbook rules this one is identical to. Usually zero or one."""
        return [name for name, table in reference_rules(self.elec, self.mode) if table == self.table]

    def describe(self) -> str:
        named = self.matches()
        if named:
            return named[0]
        outs = {self.show_outcome(p) for p in self.elec.profiles}
        if len(outs) == 1:
            return f"the constant rule that always returns {outs.pop()}"
        ignored = [
            i + 1
            for i in self.elec.vs
            if all(
                self.table[p] == self.table[self.elec.sub(p, i, r)]
                for p in self.elec.profiles
                for r in self.elec.ballots
            )
        ]
        note = f"; ignores voter {ignored[0]}" if len(ignored) == 1 else ""
        return f"no textbook match: {len(outs)} distinct outcomes over {len(self.table)} profiles{note}"


def reference_rules(elec: Electorate, mode: str):
    """The rules we can name, as (name, table) pairs."""
    out = []
    for i in elec.vs:
        out.append(
            (f"dictatorship of voter {i + 1}", {p: (p[i][0] if mode == "scf" else p[i]) for p in elec.profiles})
        )
    if mode == "swf":
        for i in elec.vs:
            out.append(
                (
                    f"inverse dictatorship of voter {i + 1}",
                    {p: tuple(reversed(p[i])) for p in elec.profiles},
                )
            )
    else:
        for c in elec.cands:
            out.append((f"the constant rule that always elects {CAND_NAMES[c]}", {p: c for p in elec.profiles}))
    for name, score in (("plurality", _plurality), ("borda", _borda), ("copeland", _copeland)):
        out.append((f"{name} with alphabetical tie-breaking", {p: _from_scores(elec, score(elec, p), mode) for p in elec.profiles}))
    return out


def _from_scores(elec: Electorate, scores: list[int], mode: str):
    order = sorted(elec.cands, key=lambda c: (-scores[c], c))
    return order[0] if mode == "scf" else tuple(order)


def _plurality(elec: Electorate, p: Profile) -> list[int]:
    s = [0] * elec.candidates
    for b in p:
        s[b[0]] += 1
    return s


def _borda(elec: Electorate, p: Profile) -> list[int]:
    s = [0] * elec.candidates
    for b in p:
        for k, c in enumerate(b):
            s[c] += elec.candidates - 1 - k
    return s


def _copeland(elec: Electorate, p: Profile) -> list[int]:
    return [sum(1 for d in elec.cands if d != c and elec.beats(p, c, d)) for c in elec.cands]


def from_model(model, ctx, elec: Electorate) -> Rule:
    """Read a rule out of a Z3 model."""
    table = {}
    for p in elec.profiles:
        if ctx.mode == "scf":
            won = [c for c in elec.cands if bool(model.eval(ctx.wins(p, c), model_completion=True))]
            if len(won) != 1:
                raise RuntimeError(f"model elects {len(won)} candidates at one profile")
            table[p] = won[0]
        else:
            beaten = {
                c: sum(
                    1
                    for d in elec.cands
                    if d != c and bool(model.eval(ctx.prefers(p, c, d), model_completion=True))
                )
                for c in elec.cands
            }
            table[p] = tuple(sorted(elec.cands, key=lambda c: -beaten[c]))
    return Rule(ctx.mode, elec, table)
