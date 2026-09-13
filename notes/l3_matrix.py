"""Produce L3's verification matrix, for pasting into notes/VERIFY-CORE.md.

    PYTHONPATH=. .venv/bin/python notes/l3_matrix.py

Answers every row twice, once through the core and once through L3's own
re-derivation, and reports what each said and how much was checked by hand.
The unittest suite makes the same comparisons and fails on a mismatch; this
just prints the numbers.
"""

from core import derive, render

from tests import l3_reference as ref
from tests.test_l3_reproduce import EXTRA, MATRIX, first_block, table_of, without_block


def run(row):
    E = ref.Elec(row.voters, row.candidates)
    mine, _ = ref.solve(E, row.mode, list(row.axioms))
    theirs = derive(list(row.axioms), row.voters, row.candidates, mode=row.mode)
    rules = constraints = 0
    detail = ""
    if theirs.status == "sat":
        table = table_of(theirs.rule, E)
        violations, constraints = ref.violations(E, row.mode, table, list(row.axioms))
        rules = 1
        shapes = [f"dictator v{i}" for i in ref.dictators(E, row.mode, table)]
        shapes += [f"inverse dictator v{i}" for i in ref.inverse_dictators(E, row.mode, table)]
        detail = ", ".join(shapes) or "no textbook shape"
    else:
        violations = []
        for dropped, rule in theirs.witnesses.items():
            rest = [a for a in theirs.core if a != dropped]
            bad, n = ref.violations(E, row.mode, table_of(rule, E), rest)
            violations += bad
            rules += 1
            constraints += n
        check = ref.verify_minimal_unsat(E, row.mode, list(theirs.core))
        violations += check["problems"]
        named = first_block(render(theirs))
        detail = "core " + "+".join(theirs.core)
        if sorted(named) != sorted(theirs.core):
            violations.append(f"render names {named}")
        if sorted(without_block(render(theirs))) != sorted(theirs.core):
            violations.append("escape list differs from the core")
    return {
        "row": row,
        "mine": mine,
        "theirs": theirs.status,
        "detail": detail,
        "profiles": len(E.profiles),
        "rules": rules,
        "constraints": constraints,
        "violations": violations,
    }


def main():
    rules = constraints = 0
    problems = []
    for title, rows in [("golden table", MATRIX), ("rows L3 adds", EXTRA)]:
        print(f"\n### {title}\n")
        print("| question | mode | size | expected | core said | L3 said | checked | why |")
        print("|---|---|---|---|---|---|---|---|")
        for row in rows:
            r = run(row)
            rules += r["rules"]
            constraints += r["constraints"]
            verdict = "clean" if not r["violations"] else "VIOLATIONS " + "; ".join(r["violations"][:2])
            if r["violations"]:
                problems.append((row.label, r["violations"]))
            expected = row.expect + (f", core {'+'.join(row.core)}" if row.core else "")
            print(
                f"| {', '.join(row.axioms)} | {row.mode} | {row.voters}v{row.candidates}c "
                f"| {expected} | {r['theirs']}, {r['detail']} | {r['mine']} "
                f"| {r['rules']} rules, {r['profiles']} profiles, "
                f"{r['constraints']:,} constraints, {verdict} | {row.why} |"
            )
    print(f"\n{rules} rules checked by hand, {constraints:,} axiom instances, {len(problems)} problems")
    for label, why in problems:
        print(f"  {label}: {why}")


if __name__ == "__main__":
    main()
