"""Turn a result into English.

The unsat branch is the one that has to earn its keep. It is not enough to name
the axioms that clash: the output says which ones are load-bearing and shows the
rule that appears the moment you give up each one. That is the part a reader can
check.
"""

from __future__ import annotations

import textwrap

from .solve import library

KIND = {
    "scf": ("social choice function", "a rule that elects one winner"),
    "swf": ("social welfare function", "a rule that produces a ranking"),
}
COUNT = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
PREVIEW = 8


def render(result) -> str:
    return {"sat": _sat, "unsat": _unsat, "unknown": _unknown}[result.status](result)


def _sat(r) -> str:
    kind, gloss = KIND[r.mode]
    out = [
        _wrap(
            f"A {kind} over {r.voters} voters and {r.candidates} candidates satisfying "
            f"all of these exists ({gloss}):"
        ),
        "",
        _axiom_list(r.axioms),
        "",
        _wrap(f"One such rule: {r.rule.describe()}."),
        "",
    ]
    rows = list(r.rule.rows())
    width = max(len(p) for p, _ in rows[:PREVIEW])
    for profile, outcome in rows[:PREVIEW]:
        out.append(f"  {profile.ljust(width)}  ->  {outcome}")
    if len(rows) > PREVIEW:
        out.append(f"  ... {len(rows) - PREVIEW} more profiles, all of them decided")
    out += ["", _wrap(_footer(r, found=True))]
    return "\n".join(out)


def _unsat(r) -> str:
    kind, gloss = KIND[r.mode]
    n = len(r.core)
    out = [
        _wrap(
            f"No {kind} over {r.voters} voters and {r.candidates} candidates satisfies "
            f"all of these at once ({gloss}):"
        ),
        "",
        _axiom_list(r.core),
        "",
    ]
    if len(r.core) < len(r.axioms):
        dropped = [a for a in r.axioms if a not in r.core]
        out += [
            _wrap(
                f"You asked for {len(r.axioms)}. The {COUNT.get(n, n)} above are enough "
                f"to rule it out on their own, so {_join(dropped)} never came into it."
            ),
            "",
        ]
    if r.core_minimal:
        out.append(
            _wrap(
                f"Those {COUNT.get(n, n)} are jointly unsatisfiable and none of them is "
                f"spare. Give up any one and a rule appears:"
            )
        )
        out.append("")
        width = max(len(a) for a in r.core)
        for name in r.core:
            w = r.witnesses.get(name)
            out.append(f"  without {name.ljust(width)}   {w.describe() if w else 'a rule exists'}")
    else:
        out.append(
            _wrap(
                "Minimisation did not finish inside the budget, so this set is known to "
                "be unsatisfiable but is not known to be minimal: some of it may be spare."
            )
        )
    out += ["", _wrap(_footer(r, found=False))]
    return "\n".join(out)


def _unknown(r) -> str:
    kind, _ = KIND[r.mode]
    out = [
        _wrap(
            f"Undecided. Whether a {kind} over {r.voters} voters and {r.candidates} "
            f"candidates satisfies {_join(r.axioms)} is not settled by this run."
        ),
        "",
        _wrap(r.note.strip().rstrip(".") + "."),
    ]
    if r.partial is not None:
        out += ["", _wrap("What did resolve, at the smaller size:"), "", _indent(render(r.partial))]
    return "\n".join(out)


# -- pieces ----------------------------------------------------------------


def _axiom_list(names) -> str:
    lib = library()
    width = max(len(n) for n in names)
    lines = []
    for name in names:
        english = lib[name].english if name in lib else ""
        body = textwrap.wrap(english, 78 - width - 4) or [""]
        lines.append(f"  {name.ljust(width)}  {body[0]}")
        lines += [" " * (width + 4) + extra for extra in body[1:]]
    return "\n".join(lines)


def _footer(r, found: bool) -> str:
    what = "Found" if found else "Established"
    checked = " Every rule above was re-checked against its axioms without the solver." if r.verified else ""
    return (
        f"{what} by searching all {r.profiles:,} profiles of this electorate, "
        f"{r.variables:,} variables, in {r.elapsed:.2f}s.{checked} "
        f"This is a statement about {r.voters} voters and {r.candidates} candidates: "
        f"a base-case lemma, not a result for every electorate."
    )


def _join(names) -> str:
    names = list(names)
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def _wrap(text: str) -> str:
    return textwrap.fill(" ".join(text.split()), 78)


def _indent(text: str) -> str:
    return "\n".join("  " + line if line else "" for line in text.splitlines())
