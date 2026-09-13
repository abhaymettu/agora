"""Regenerate the worked examples in examples/.

    PYTHONPATH=. python examples/generate.py

Every number, table and verdict in the generated markdown comes from a live
call into `core`. Only the framing sentences are written by hand.
"""

from __future__ import annotations

from pathlib import Path

from core import derive, library

HERE = Path(__file__).parent


# Each example: a slug, a title, the question in prose, the axiom set, the
# electorate, and (for the satisfiable ones) profiles to run the rule on.
EXAMPLES = [
    {
        "slug": "01-arrow",
        "title": "Arrow's theorem, derived",
        "axioms": ["pareto", "iia", "nondictatorial"],
        "voters": 2,
        "candidates": 3,
        "mode": "swf",
        "intro": """
The most famous impossibility in the subject. Ask for a rule that produces a full
social ranking, respects unanimity, decides each pair using only how the voters rank
that pair, and is not one voter's ballot copied out. No such rule exists.
""",
        "outro": """
The three axioms are jointly unsatisfiable and the core is all three of them: drop any
one and a rule appears. The witnesses are the evidence for that. `without
nondictatorial` returning a dictatorship is the theorem's punchline stated as an
object rather than as a sentence.
""",
    },
    {
        "slug": "02-wilson",
        "title": "Drop unanimity and the impossibility goes away",
        "axioms": ["iia", "surjective", "nondictatorial"],
        "voters": 2,
        "candidates": 3,
        "mode": "swf",
        "profiles": ["A>B>C | C>B>A", "A>B>C | A>B>C", "B>A>C | C>A>B"],
        "intro": """
Arrow without Pareto, with surjectivity in its place. This is satisfiable, and the
rule it returns is the reason Pareto is not decoration: society ranks candidates in
the exact reverse of voter 1's ballot. Unanimous for A over B, and A comes last.
""",
        "outro": """
Wilson's theorem, in object form. Leave Pareto out of the axiom library and the
flagship result comes out wrong, because the inverse dictator satisfies everything
that is left.
""",
    },
    {
        "slug": "03-gibbard-satterthwaite",
        "title": "Strategyproofness forces a dictator",
        "axioms": ["strategyproof", "surjective"],
        "voters": 2,
        "candidates": 3,
        "mode": "scf",
        "profiles": ["A>B>C | C>B>A", "C>B>A | A>B>C", "B>C>A | A>B>C"],
        "intro": """
Elect a single winner. Ask that no voter ever gains by lying about their ranking, and
that every candidate can win under some profile. Both are satisfiable, and what comes
back is a dictatorship.
""",
        "outro": """
Adding `nondictatorial` to this set turns it unsatisfiable, which is
Gibbard-Satterthwaite. The satisfiable half is the more useful one to look at: it
hands you the rule, so you can check the claim by running it.
""",
    },
    {
        "slug": "04-copeland",
        "title": "Copeland, minted from three properties",
        "axioms": ["condorcet", "monotone", "nondictatorial"],
        "voters": 3,
        "candidates": 3,
        "mode": "scf",
        "profiles": [
            "A>B>C | B>C>A | C>A>B",
            "A>B>C | A>C>B | B>A>C",
            "C>B>A | C>A>B | A>B>C",
        ],
        "intro": """
Not every axiom set ends in an impossibility or a dictator. Ask for a winner-elects
rule that honours a Condorcet winner when there is one, never punishes a candidate for
being raised, and is not a dictatorship. The search returns a rule the literature
already has a name for.
""",
        "outro": """
The rule was recognised, not looked up: the search produced a table over all 216
profiles and the table happens to be identical to Copeland with alphabetical
tie-breaking. The first profile above is the Condorcet cycle, where no candidate beats
every other, and the rule still has to decide.
""",
    },
    {
        "slug": "05-anonymous-neutral",
        "title": "Anonymity and neutrality collide at three voters",
        "axioms": ["condorcet", "anonymous", "neutral"],
        "voters": 3,
        "candidates": 3,
        "mode": "scf",
        "intro": """
Three properties that each sound like a minimum: honour the Condorcet winner, ignore
who cast which ballot, and treat the candidates alike. There is no such rule, and the
reason is smaller than the question asked.
""",
        "outro": """
Two of the three are enough. Condorcet never came into it, and the core says so, which
is the difference between "these three are impossible" and knowing which of them to
argue about. A resolute rule has to break the symmetric cycle somehow, and anonymity
plus neutrality leave it nowhere to break it.
""",
    },
]


def fence(text: str, lang: str = "") -> str:
    return f"```{lang}\n{text.rstrip()}\n```"


def command(ex: dict) -> str:
    return (
        f"python -m core derive --mode {ex['mode']} --voters {ex['voters']} "
        f"--candidates {ex['candidates']} {' '.join(ex['axioms'])}"
    )


def trace(rule, profiles: list[str]) -> str:
    return "\n".join(
        f">>> rule.show_outcome({p!r})\n{rule.show_outcome(p)!r}" for p in profiles
    )


def checks(rule, asked: list[str], mode: str) -> str:
    lib = library()
    shown = list(asked)
    missing = next(
        (
            n
            for n, a in lib.items()
            if a.supports(mode) and n not in asked and not rule.satisfies(lib[n])
        ),
        None,
    )
    if missing:
        shown.append(missing)
    return "\n".join(
        f">>> rule.satisfies(library()[{n!r}])\n{rule.satisfies(lib[n])}" for n in shown
    )


def write_example(ex: dict) -> dict:
    result = derive(
        ex["axioms"], ex["voters"], ex["candidates"], mode=ex["mode"], timeout=120.0
    )

    body = [f"# {ex['title']}", "", ex["intro"].strip(), "", "## The question", ""]
    body.append(fence(command(ex)))
    body.extend(["", "## What comes back", "", fence(str(result)), ""])

    if result.rule is not None:
        rule = result.rule
        body.extend(["## Running the rule", ""])
        body.append(
            "The rule comes back as an object, so the claim is checkable by running it "
            "on profiles of your choosing."
        )
        body.extend(["", fence(trace(rule, ex["profiles"]), "python"), ""])
        body.append("Re-checked against each axiom without going back through the solver:")
        body.extend(["", fence(checks(rule, ex["axioms"], ex["mode"]), "python"), ""])
        body.extend([f"`rule.matches()` returns `{rule.matches()}`.", ""])
    else:
        body.extend(["## The core", ""])
        body.append(
            f"Asked for {len(result.axioms)}, blamed "
            f"{len(result.core)}: `{', '.join(result.core)}`."
            + (
                " Minimality was verified."
                if result.core_minimal
                else " Minimality was not verified."
            )
        )
        body.extend(["", "Each proper subset comes with a rule that satisfies it:", ""])
        for dropped, witness in result.witnesses.items():
            body.append(f"- without `{dropped}`: {witness.describe()}")
        body.append("")

    body.extend(["## Notes", "", ex["outro"].strip(), ""])
    body.append(
        f"Search space {result.profiles} profiles, {result.variables} variables, "
        f"solved in {result.elapsed:.2f}s."
    )
    body.append("")

    (HERE / f"{ex['slug']}.md").write_text("\n".join(body))

    return {
        "slug": ex["slug"],
        "title": ex["title"],
        "verdict": (
            result.rule.describe()
            if result.rule is not None
            else f"impossible; core {', '.join(result.core)}"
        ),
        "elapsed": result.elapsed,
    }


def write_index(rows: list[dict]) -> None:
    lines = [
        "# Worked examples",
        "",
        "Five runs against the derivation core, output included verbatim.",
        "Regenerate all of them with:",
        "",
        fence("PYTHONPATH=. python examples/generate.py"),
        "",
        "| example | what came back | time |",
        "|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| [{r['title']}]({r['slug']}.md) | {r['verdict']} | {r['elapsed']:.2f}s |"
        )
    lines.extend(
        [
            "",
            "Every one of these is a statement about the electorate it names. Small",
            "electorates are where the classical theorems bite and where exhaustive search",
            "finishes; carrying a result up to every electorate is a separate argument the",
            "core does not make.",
            "",
        ]
    )
    (HERE / "README.md").write_text("\n".join(lines))


if __name__ == "__main__":
    summary = [write_example(ex) for ex in EXAMPLES]
    write_index(summary)
    for row in summary:
        print(f"{row['slug']:24} {row['elapsed']:6.2f}s  {row['verdict']}")
