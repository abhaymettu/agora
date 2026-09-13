# L3: independent re-derivation of the core

Checked 2026-09-13. Python 3.14, z3-solver 5.1.0, macOS arm64. No network, no paid API.

**Verdict: INDEPENDENT REPRODUCTION PASS.** Every golden result in
`notes/BUILD-CORE.md` reproduces against a second implementation that shares no code with
`core/`. No blockers.

## What independence means here, and where it stops

`tests/l3_reference.py` is a second implementation of the axiom library, 568 lines, written
from `core/axioms.agora` (which is data, not implementation) and from the classical
statements of the theorems. It imports z3 and nothing else. What it does not import, and
what was never read while writing it, is `core/ground.py`, `core/solve.py`, `core/dsl.py`,
`core/domain.py`, `core/rules.py` or `core/render.py`. The only things read out of `core/`
were `__init__.py`, the axiom file, and two constructor signatures taken with
`inspect.signature`.

Three differences from the core were chosen on purpose, so agreement is evidence and not an
echo:

- Social rankings get one boolean per **unordered** pair, and `above(p, b, a)` is the
  syntactic negation of `above(p, a, b)`. Antisymmetry is a property of the representation.
  The core asserts `Xor` over two variables per pair instead. At 2 voters and 3 candidates
  that is 108 variables against the core's 216.
- Linearity is "no triple cycles", two clauses per unordered triple, rather than
  transitivity over every ordered triple.
- Exactly one winner is at-least-one plus pairwise at-most-one, not a pseudo-boolean count.

Each axiom is written once, as a Python generator of `(label, constraint)` pairs over a
swappable logic backend. The same generator runs against z3 expressions to search for a
rule and against Python booleans to check a decided rule, so the symbolic and the concrete
reading of an axiom cannot drift apart. The labels are what make a violation name the
profile that broke it.

Where the two implementations do meet: the reproduction is of the axiom **file**, so a
mistake in the English-to-formula step of the library itself would be reproduced faithfully
by both. That is the one class of error this lane does not catch, and no second
implementation of the same file could. It is also why `formalize/` being gated matters.

## The reproduction matrix

Regenerate with `PYTHONPATH=. .venv/bin/python notes/l3_matrix.py`.

"core said" is `derive(...)`. "L3 said" is my own encoding and my own solve. "checked" is
what was verified by hand afterwards: for a sat row the minted rule against every axiom
asked for, on every profile; for an unsat row every witness rule against the axioms it
claims, plus a full re-derivation of the minimal core.

### the eleven rows BUILD-CORE.md hands L3

| question | mode | size | expected | core said | L3 said | checked |
|---|---|---|---|---|---|---|
| pareto, iia, nondictatorial | swf | 2v3c | unsat, core all three | unsat, core all three | unsat | 3 rules, 36 profiles, 976 constraints, clean |
| pareto, iia, nondictatorial | swf | 3v3c | unsat, core all three | unsat, core all three | unsat | 3 rules, 216 profiles, 17,178 constraints, clean |
| pareto, iia | swf | 2v3c | sat, a dictatorship | sat, dictator v2 | sat | 1 rule, 36 profiles, 486 constraints, clean |
| iia, surjective, nondictatorial | swf | 2v3c | sat, an inverse dictatorship | sat, inverse dictator v1 | sat | 1 rule, 36 profiles, 440 constraints, clean |
| strategyproof, surjective, nondictatorial | scf | 2v3c | unsat, core all three | unsat, core all three | unsat | 3 rules, 36 profiles, 2,170 constraints, clean |
| strategyproof, surjective, nondictatorial | scf | 3v3c | unsat, core all three | unsat, core all three | unsat | 3 rules, 216 profiles, 19,452 constraints, clean |
| strategyproof, surjective | scf | 2v3c | sat, a dictatorship | sat, dictator v1 | sat | 1 rule, 36 profiles, 1,083 constraints, clean |
| anonymous, neutral | scf | 3v3c | unsat | unsat, core both | unsat | 2 rules, 216 profiles, 6,768 constraints, clean |
| anonymous, neutral | scf | 2v3c | sat | sat, no textbook shape | sat | 1 rule, 36 profiles, 738 constraints, clean |
| condorcet, strategyproof | scf | 3v3c | unsat, core both | unsat, core both | unsat | 2 rules, 216 profiles, 9,924 constraints, clean |
| condorcet, strategyproof, surjective | scf | 3v3c | unsat, surjective not in the core | unsat, core condorcet+strategyproof | unsat | 2 rules, 216 profiles, 9,924 constraints, clean |

Eleven for eleven. The two rows the flagship claims rest on both hold: the Wilson row comes
back an inverse dictatorship of voter 1 and not a dictatorship, which is what justifies
pareto being in the library, and dropping nondictatorial from Gibbard-Satterthwaite gives a
dictatorship of voter 1.

### five rows L3 adds

The golden table does not claim these. The theory does, and they pull `monotone` and the
weaker combinations into the property tests, so every axiom in the library gets exercised
rather than the seven that the golden rows happen to name.

| question | mode | size | L3 expected | core said | L3 said | checked |
|---|---|---|---|---|---|---|
| pareto, monotone, anonymous, neutral | scf | 2v3c | unsat | unsat, core pareto+anonymous+neutral | unsat | 3 rules, 36 profiles, 1,584 constraints, clean |
| condorcet, monotone | scf | 3v3c | sat | sat, no textbook shape | sat | 1 rule, 216 profiles, 1,500 constraints, clean |
| pareto, monotone, surjective, nondictatorial | swf | 2v3c | sat | sat, no textbook shape | sat | 1 rule, 36 profiles, 350 constraints, clean |
| pareto, nondictatorial | scf | 3v3c | sat | sat, no textbook shape | sat | 1 rule, 216 profiles, 165 constraints, clean |
| iia, pareto, surjective | swf | 2v3c | sat, a dictatorship | sat, dictator v1 | sat | 1 rule, 36 profiles, 492 constraints, clean |

The first row is the one place this lane was wrong and the core was not. L3 predicted sat,
on the reasoning that two voters can always be handled anonymously. Both implementations
independently returned unsat, and the reason is the classical one: at
`A > B > C | B > A > C` pareto rules C out, and swapping the labels A and B leaves the
multiset of ballots alone, so anonymity says the winner does not move and neutrality says
it must. The row is now recorded as unsat with monotone spare. Two implementations agreeing
against my prediction is the outcome this lane is for.

That row also shows a minimal core is not unique. `pareto + anonymous + neutral` and
`monotone + anonymous + neutral` are both unsatisfiable and both minimal at two voters. The
core returns the first; `test_a_minimal_core_is_one_of_several` verifies both are genuine
minimal impossibilities and accepts either, rather than pinning the expected answer to
which way a solver leans.

## Exhaustive property tests on minted rules

No sampling anywhere. Electorates here have 36 or 216 profiles and every one of them is
enumerated.

| | count |
|---|---|
| rows in the matrix | 16 (11 golden, 5 added); 8 sat, 8 unsat |
| rules the core minted and L3 checked | 29 (8 from sat rows, 21 witness rules from unsat rows) |
| profiles enumerated across those rules | 3,564 rule-outcome rows, every profile of every electorate |
| axiom instances evaluated | 73,230 |
| **violations** | **0** |
| rules L3's own solver minted, checked the same way | 8 rules, 648 rule-outcome rows |
| hand-built rules checked against the whole library both ways | 4 rules, 32 (rule, axiom) pairs |

Three things get checked about each rule, not one:

1. **Every axiom asked for holds, on every profile.** A sat row's rule is read out of the
   core through `Rule.outcome`, one query per profile of L3's own electorate, so an
   electorate that did not line up would show as a `KeyError` rather than quietly agreeing.
   Then every axiom in the set is evaluated on it. Zero violations, 8 rules.
2. **Every witness rule does what the proof says it does.** An impossibility ships one rule
   per axiom in the core. All 21 satisfy the axioms they claim, and all 21 *fail* the axiom
   they were allowed to drop. The second half is the part that makes minimality
   demonstrated rather than asserted: a witness that satisfied the dropped axiom too would
   mean the axiom was never load-bearing.
3. **The rule is a function of the profile and nothing else.** Asking the same question
   twice, with an unrelated derivation in between, gives the same 36-row table, and a
   profile passed as a tuple and as the string `"A>B>C | C>B>A"` gives the same outcome.

The minimal cores are re-derived rather than accepted. For each of the 8 unsat rows,
`verify_minimal_unsat` re-solves the reported core in L3's own encoding, then drops each
member in turn, solves the rest, and checks the rule it gets back against those axioms with
no solver involved. 8 cores, 21 drop-one witnesses of L3's own, all satisfiable, all
verified by hand. The core's `core_minimal` and `verified` flags were True on all 8.

The sharpest single check is the hand-built one. Four rules that neither implementation
invented, a dictatorship and an inverse dictatorship as social welfare functions, a
dictatorship and a constant rule as social choice functions, are put to both
`Rule.satisfies` and L3's own checker against every axiom the library defines in that mode.
32 comparisons, 32 agree, 20 true and 12 false, so the agreement is not the vacuous kind
where everything passes. If L3 had read any axiom differently from the core, this is where
it would show, on a rule with no solver anywhere near it.

## Renderer cross-checks

For all 8 unsat rows the rendered English proof was parsed and compared against the
minimal core L3 verified independently:

| row | L3's verified minimal core | axioms the proof lists | escape clauses | asked but spare |
|---|---|---|---|---|
| swf 2v3c arrow | iia, nondictatorial, pareto | same | same | none |
| swf 3v3c arrow | iia, nondictatorial, pareto | same | same | none |
| scf 2v3c gs | nondictatorial, strategyproof, surjective | same | same | none |
| scf 3v3c gs | nondictatorial, strategyproof, surjective | same | same | none |
| scf 3v3c anonymous, neutral | anonymous, neutral | same | same | none |
| scf 3v3c condorcet, strategyproof | condorcet, strategyproof | same | same | none |
| scf 3v3c + surjective | condorcet, strategyproof | same | same | surjective, correctly absent |
| scf 2v3c pareto, monotone, anonymous, neutral | anonymous, neutral, pareto | same | same | monotone, correctly absent |

Exactly the axioms in the core, in the leading list and in the "give up any one" list, and
in both rows where the question named a spare axiom that axiom is kept out of the
load-bearing list and said to be spare in prose instead. `render(result)` and
`str(result)` return the same text.

Two more renderer checks that are about content rather than layout. The rows a rendered
existence prints are parsed back into profiles and outcomes and compared against the rule
object, so the printed table has to be the table the rule holds, checked for one scf and
one swf rule. And every proof states the electorate it is about, names the number of
profiles searched, and calls itself a base-case lemma, at 2v3c and at 3v3c.

## How to run it

```
PYTHONPATH=. .venv/bin/python -m unittest tests.test_l3_reproduce -v   # 21 tests, 27.7s
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -t .       # 65 tests, 51.8s, all lanes
PYTHONPATH=. .venv/bin/python notes/l3_matrix.py                       # the matrix above
```

L3's files are `tests/l3_reference.py` (the second implementation), `tests/test_l3_reproduce.py`
(21 tests) and `notes/l3_matrix.py` (the matrix generator). They are separate from
`tests/test_golden.py`, which is L1 checking its own work. They went to origin inside
commit `f6d17eb`, which another lane made while this one was mid-build.

Timing, for reference rather than for comparison: L3's encoding solves swf 3v3c in 0.20s
and scf 3v3c in 0.36s, measured here. The core's own sweep in `notes/timings.txt` puts the
same two rows at 2.53s and 0.57s. Half the variables and no
Xor clauses. That is a remark about two encodings of the same problem, not a claim that one
is better; the core's is the one that carries the selector machinery, the minimal cores and
the witnesses, and L3's does none of that.

## What this does not establish

Worth saying plainly, because a passing verification note is the easiest place in a project
to overclaim.

- **It is base cases only.** Every row is a statement about a fixed electorate at 2 or 3
  voters and 3 candidates. Nothing here carries to all electorates, and the core does not
  claim otherwise.
- **It checks the library as written.** Both implementations read the same axiom file. A
  formula in `core/axioms.agora` that is subtly not the axiom its English line describes
  would pass this lane twice over.
- **Nothing at four candidates was reproduced.** The golden table's four-candidate rows are
  timings and budget refusals, not results, and L3 added no rows there.
- **The budget and degradation paths were not re-derived.** `unknown`, the three ceilings
  and the walk down to a smaller electorate are L1's tests. L3 touched only rows that
  answer.
- **The recogniser was re-derived only for the shapes the theory predicts here**:
  dictatorships and inverse dictatorships. L3 has no independent check of plurality, borda
  or copeland, and does not need one, since no golden row turns on them.

Within those limits: 16 rows, 29 rules, 3,564 rule-outcome rows, 73,230 axiom instances,
8 minimal cores re-derived, 8 proofs cross-checked, 0 violations, 0 blockers.
