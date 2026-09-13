# Contributing

AGORA is a small research tool. Issues, questions and pull requests all go through the
GitHub repository at <https://github.com/abhaymettu/agora>.

## Getting support, or asking whether something is a bug

Open an issue. If the tool gave you an answer you think is wrong, include the exact
command or the `derive` call, the mode, the number of voters and candidates, and the
output. A wrong answer here means one of three things, and they need different fixes:

- **A rule came back that does not satisfy the axioms you asked for.** This should be
  impossible: every returned rule is re-checked against every axiom without the solver
  before it is shown to you, and `Result.verified` says whether that check ran. If you
  have one, it is a bug in the grounder or in the axiom, and it is the most serious kind.
  Say so in the title.
- **A core came back that is not minimal.** Check `Result.core_minimal` first. `False`
  means the tool already told you the set is unsatisfiable but some of it may be spare.
  That is documented behaviour, not a bug.
- **An axiom does not say what you think it says.** Read the block in
  `core/axioms.agora`. The formula is the definition; the English line next to it is a
  gloss and can be wrong on its own. If the two disagree, that is a bug worth reporting.

`unknown` is not a bug. It means the run hit the clause ceiling or the timeout, and the
output says which. Raise `--timeout`, or drop to a smaller electorate.

## Reporting a bug

Include the version (`git rev-parse HEAD` is fine), your Python version, your
`z3-solver` version, and a case small enough to run in a few seconds. Almost everything
reproduces at two or three voters and three candidates.

## Adding an axiom

This is the contribution the design is for, and it does not require touching Python.

1. Add a block to `core/axioms.agora`: the name, the `modes` it is defined for, an
   `english` gloss, and one formula per mode. Quantifiers range over `profile`, `voter`,
   `cand`, `ballot`, `cperm` and `vperm`; the ground facts and profile terms available
   are listed in the header comment of that file.
2. If your axiom needs a ground fact or a profile transformation that does not exist yet,
   add it to `core/ground.py`. Ground facts are decided in Python before the solver runs,
   so a guard that comes out false takes its clause out of the formula.
3. Write a second, deliberately different implementation in `tests/l3_reference.py` and a
   test that checks the two readings against each other on hand-built rules. Every axiom
   in the library has one. `tests/test_axioms_added.py` shows the pattern: pin the axiom
   against rules whose behaviour you already know, such as Borda satisfying
   `condorcetloser` and plurality failing it.
4. Add a golden test if the axiom lands you on a known theorem.

Axioms that are self-contradictory at the sizes the tool runs at do not ship. `noveto`
was written, swept, and dropped for exactly that reason; the reasoning is in
`notes/DISCOVERY.md`.

## Changing the core

Run the suite before and after:

```
python -m unittest discover -s tests -t .
```

`tests/l3_reference.py` is a second implementation of the axiom library. Keep it
independent: it imports z3 and the axiom file, and nothing else from `core/`. That is the
only reason `tests/test_l3_reproduce.py` is evidence rather than an echo, and
`notes/VERIFY-CORE.md` says where the independence stops.

New behaviour needs a test. Claims about what a rule does need a test that runs the rule.

## Pull requests

Branch, commit, open a PR against `main`. Keep the diff to one thing. If a change makes
the tool slower at a size that is in the README timing table, update the table and say
so in the PR.
