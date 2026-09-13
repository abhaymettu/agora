---
title: 'AGORA: deriving voting rules and impossibilities from axioms'
tags:
  - Python
  - social choice
  - voting
  - SAT solving
  - computational social choice
authors:
  - name: Abhay Mettu
    orcid: 0009-0001-2434-353X
    affiliation: 1
affiliations:
  - name: Independent researcher
    index: 1
date: 2026
bibliography: paper.bib
---

# Summary

AGORA takes a set of axioms for a voting rule and returns either a rule that provably
satisfies all of them or a proof that no such rule exists. For a fixed finite electorate
the question is decidable: every rule over that electorate is a boolean assignment, every
axiom is a constraint over those variables, and the conjunction goes to an SMT solver
[@demoura2008]. Satisfiable means a rule exists and the model *is* the rule.
Unsatisfiable means none does, and the unsatisfiable core names the minimal subset of the
axioms to blame.

Both branches return an object, not a verdict. A returned rule is a complete outcome table
that runs on any profile, is recognised by name when it coincides with a rule someone has
written down, and is re-checked against every axiom without the solver. A returned
impossibility has its core minimised and a witness rule for every proper subset, so "none
of these axioms is spare" arrives with the rule that appears when you drop each one.

The package also searches a whole library rather than one set. It enumerates minimal
inconsistent subsets level by level, asking every singleton, then every pair that is not
already a superset of a known impossibility, and so on; unsatisfiability is upward closed,
so anything that comes back unsatisfiable is minimal by construction. It enumerates every
rule satisfying a set, which turns a witness into a characterisation, and it computes the
implication order over the library, which separates a distinct impossibility from the same
theorem restated with a stronger hypothesis. One sweep asked 2,746 questions and returned
104 minimal impossibilities, reproducing Arrow [@arrow1963], Wilson [@wilson1972],
Muller-Satterthwaite [@satterthwaite1975] and Moulin's anonymity-neutrality condition
[@moulin1983]; the records are in `notes/DISCOVERY.md`.

# Statement of need

Social choice theory is full of results of the form "these axioms are incompatible" or
"these axioms characterise this rule", proved one at a time by hand. The proofs do not
compose. Knowing Arrow's theorem tells you nothing about the five properties you actually
care about, and getting an answer for those is usually a paper.

Computer-aided social choice has been answering such questions by SAT for over a decade:
Tang and Lin's reduction of Arrow to a finite base case [@tang2009], Geist and Endriss's
automated search over axiom sets [@geist2011], Brandt and Geist on strategyproofness
[@brandt2016], Brandt, Geist and Peters on the no-show paradox [@brandt2017], surveyed by
Geist and Peters [@geist2017]. Almost none of it shipped installable software. Each paper
is a hand-built encoding for one axiom family, and a reader with a different question
generally writes their own from scratch.

The maintained packages go the other way. `pref_voting` [@holliday2025], `abcvoting`
[@lackner2023] and `VoteKit` [@donnay2025] implement large catalogues of known rules and
check a given rule against axioms on given profiles. That answers "does this rule have
this property"; none searches the space of rules for one that does. The closest existing
tool is the justification work of Boixel and Endriss [@boixel2020], which explains why a
rule produced a particular outcome at a particular profile, quantifying over that profile
rather than over all rules. AGORA fills the gap: axioms in, a rule or an impossibility
out, from a Python API, a command line, or a local browser interface.

# Design and the axiom library

Fifteen axioms ship: `pareto`, `nondictatorial`, `surjective`, `strategyproof`,
`monotone`, `condorcet`, `iia`, `anonymous`, `neutral`, `unanimity`, `majority`,
`condorcetloser`, `topsonly`, `maskinmonotone` and `reversal`. Each declares whether it
applies to social choice functions, which elect one winner, or to social welfare
functions, which return a social ranking.

The axioms are data, not Python. They live in `core/axioms.agora`:

```
axiom topsonly
  modes scf
  english only first choices count; the rest of every ballot is ignored
  scf forall p:profile, q:profile, c:cand. sametops(p,q) -> (wins(p,c) <-> wins(q,c))
```

Quantifiers range over profiles, voters, candidates, ballots, and candidate and voter
permutations. Ground facts and profile transformations are settled in Python while the
quantifiers unroll, so a guard that comes out false takes its clause out of the formula
before the solver sees anything. Adding an axiom means adding a block; the grounder and
the renderer never learn its name. That trade is the central design choice: it costs a
grounding pass that is quadratic for axioms quantifying over pairs of profiles, and buys
an extensible library and a formula small enough to solve at the sizes where the classical
theorems bite.

# Example usage

```
$ pip install z3-solver
$ python -m core derive --mode swf pareto iia nondictatorial
```

reports that the three are jointly unsatisfiable over two voters and three candidates,
that none is spare, and what appears when each is dropped: the constant rule without
`pareto`, a rule with six distinct outcomes without `iia`, and a dictatorship without
`nondictatorial`. That is Arrow's theorem, derived rather than looked up.

```python
>>> from core import derive
>>> rule = derive(["condorcet", "monotone", "nondictatorial"], 3, 3, mode="scf").rule
>>> rule.matches()
['copeland with alphabetical tie-breaking']
>>> rule.show_outcome("A>B>C | B>C>A | C>A>B")
'A'
```

Five worked runs with verbatim output are in `examples/`, regenerable from the core.

# Scope and limitations

Ballots and social rankings are strict, rules are resolute, and there are no domain
restrictions. Electorates run from two to five voters and three to five candidates,
depending on the axioms; the ceiling is the grounder rather than the solver. Every result
is a statement about one electorate, and lifting it to all of them is a separate argument
AGORA does not make. A run that cannot finish says so and names the ceiling it hit.

# Testing

The suite is 85 tests under `unittest`, run with
`python -m unittest discover -s tests -t .`. Beyond unit coverage of the parser, grounder
and renderer, `tests/test_golden.py` pins the classical cases, including
Gibbard-Satterthwaite [@gibbard1973] and the Wilson case that would silently break Arrow
if the library dropped `pareto`. `tests/l3_reference.py` is a second, independent
implementation of the axiom library, written from the axiom file and importing z3 and
nothing else from `core/`; it uses a different variable encoding and a different
formulation of linearity, and `tests/test_l3_reproduce.py` checks the two against each
other.

# AI usage disclosure

The implementation, tests and documentation in this repository were written with the
assistance of a generative AI coding agent, directed and reviewed by the author. The
independent second implementation in `tests/l3_reference.py` and the solver-free
re-verification of every returned rule were built as checks on that process;
`notes/VERIFY-CORE.md` records what they cover and where that coverage stops.

# References
