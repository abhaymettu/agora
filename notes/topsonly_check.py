"""Why no tops-only rule can dodge the Condorcet loser, without a solver.

A tops-only rule sees only the vector of first choices, so it must return the
same winner at every profile sharing one. If some vector of first choices admits,
for each candidate in turn, a completion of the ballots that makes that candidate
the Condorcet loser, then whatever the rule returns there is the Condorcet loser
somewhere, and the two axioms cannot both hold. The proof is the profiles.

This reaches sizes the SAT encoding does not: the search is over completions of
one vector of first choices, not over rules.

    PYTHONPATH=. python notes/topsonly_check.py
"""

import json
from itertools import permutations, product
from pathlib import Path

from core.domain import CAND_NAMES

SIZES = [(2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3),
         (2, 4), (3, 4), (4, 4), (5, 4), (2, 5), (3, 5), (3, 6)]
OUT = Path(__file__).parent / "discovery" / "topsonly-condorcetloser.json"


def loses_to_everyone(profile, c, m, n):
    for d in range(m):
        if d == c:
            continue
        for_d = sum(1 for b in profile if b.index(d) < b.index(c))
        if 2 * for_d <= n:
            return False
    return True


def forcing_tops(n, m):
    """A vector of first choices at which every candidate can be made the loser."""
    completions = {
        c: [(c,) + r for r in permutations([d for d in range(m) if d != c])]
        for c in range(m)
    }
    for tops in product(range(m), repeat=n):
        found = {}
        for profile in product(*(completions[t] for t in tops)):
            for c in range(m):
                if c not in found and loses_to_everyone(profile, c, m, n):
                    found[c] = profile
            if len(found) == m:
                return tops, found
    return None, None


def show(profile):
    return " | ".join(" > ".join(CAND_NAMES[c] for c in b) for b in profile)


def main():
    out = []
    for n, m in SIZES:
        tops, found = forcing_tops(n, m)
        row = {"voters": n, "candidates": m, "impossible": tops is not None}
        if tops is not None:
            row["tops"] = "".join(CAND_NAMES[c] for c in tops)
            row["witness"] = {CAND_NAMES[c]: show(p) for c, p in sorted(found.items())}
        out.append(row)
        print(f"{n}v{m}c  " + (f"impossible; first choices {row['tops']}"
                               if tops else "no single vector of first choices forces it"),
              flush=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()
