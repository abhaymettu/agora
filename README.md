# AGORA

Name the properties you want a voting rule to have. AGORA either hands you a rule that
provably has all of them, or a proof that no such rule can exist.

```
$ python -m core derive --mode swf pareto iia nondictatorial

No social welfare function over 2 voters and 3 candidates satisfies all of
these at once (a rule that produces a ranking):

  pareto          if every voter ranks a above b, then so does society
  iia             how society ranks a against b depends only on how the voters
                  rank a against b
  nondictatorial  no one voter's ballot is always the outcome, whatever anyone
                  else says

Those three are jointly unsatisfiable and none of them is spare. Give up any
one and a rule appears:

  without pareto           the constant rule that always returns C > A > B
  without iia              no textbook match: 6 distinct outcomes over 36 profiles
  without nondictatorial   dictatorship of voter 2

Established by searching all 36 profiles of this electorate, 216 variables, in
0.11s. Every rule above was re-checked against its axioms without the solver.
This is a statement about 2 voters and 3 candidates: a base-case lemma, not a
result for every electorate.
```

That is Arrow's theorem, derived rather than looked up. Ask for a satisfiable set
instead and you get the other branch: a concrete rule, returned as an object you can
run on any profile you like.

```python
>>> from core import derive
>>> rule = derive(["condorcet", "monotone", "nondictatorial"], 3, 3, mode="scf").rule
>>> rule.matches()
['copeland with alphabetical tie-breaking']
>>> rule.show_outcome("A>B>C | B>C>A | C>A>B")
'A'
```

## Why

Social choice theory is full of results of the form "these axioms are incompatible" or
"these axioms characterise this rule". They are proved one at a time, by hand, and the
proofs do not compose: knowing Arrow tells you nothing about the set of axioms you
actually care about. If you want to know whether *your* five properties can hold
together, the literature usually has no answer, and deriving one is a paper.

For a fixed small electorate the question is decidable. Encode every rule over that
electorate as a boolean assignment, encode each axiom as a constraint over those
variables, and hand the conjunction to a SAT solver. Satisfiable means a rule exists,
and the model *is* the rule. Unsatisfiable means no rule exists, and the unsat core is
the minimal subset to blame.

So the loop that normally takes a paper takes a second, at the size where the classical
theorems bite. That is the useful part: not re-deriving Arrow, but asking the question
for an axiom set nobody has written about.

## Worked examples

Five runs with their output included verbatim, in [`examples/`](examples/):

| | question | answer |
|---|---|---|
| [Arrow's theorem, derived](examples/01-arrow.md) | `pareto iia nondictatorial`, swf | impossible, core is all three |
| [Drop unanimity and the impossibility goes away](examples/02-wilson.md) | `iia surjective nondictatorial`, swf | the inverse dictator |
| [Strategyproofness forces a dictator](examples/03-gibbard-satterthwaite.md) | `strategyproof surjective`, scf | dictatorship of voter 1 |
| [Copeland, minted from three properties](examples/04-copeland.md) | `condorcet monotone nondictatorial`, scf | Copeland with alphabetical tie-breaking |
| [Anonymity and neutrality collide](examples/05-anonymous-neutral.md) | `condorcet anonymous neutral`, scf | impossible, and Condorcet is not to blame |

`PYTHONPATH=. python examples/generate.py` regenerates all five from the core.

## Scope

**Small electorates are base-case lemmas, and the output says so every time.** Two to
four voters, three to four candidates. An impossibility established at three voters is
a fact about three voters. Lifting it to every electorate is a separate argument, and
one that exists in the literature for several of these theorems, but AGORA does not
make it.

**The constructive branch returns the rule, not a verdict.** Every profile of the
electorate mapped to its outcome, runnable on any profile you type, recognised by name
if it happens to be a rule someone has written down, and re-checked against every axiom
you asked for without going back through the solver.

**This is the existence question, not the explanation question.** There is a line of
work on justifying collective decisions: fix one profile, fix the outcome a rule
produced, and generate a human-readable explanation of why that outcome follows from
some set of axioms in that profile. That answers "why this result, here". AGORA answers
a different question with a different quantifier: over *all* profiles of the
electorate, does any rule at all satisfy these axioms?

**Out of scope.** Ties, indifference and irresolute rules: ballots and social rankings
are strict, and a rule elects exactly one winner. No domain restrictions, so no
single-peaked preferences. Fifteen axioms, listed below; a sixteenth can be written in the
DSL.

## Sizes and timings

Measured on one machine, one run each. `unsat` and `sat` both mean the question was
answered; `unknown` means it was not, and the tool says which ceiling it hit.

| mode | size | profiles | variables | status | seconds |
|---|---|---|---|---|---|
| scf | 2v3c | 36 | 108 | unsat | 0.07 |
| scf | 3v3c | 216 | 648 | unsat | 0.57 |
| scf | 4v3c | 1,296 | 3,888 | unsat | 5.08 |
| scf | 2v4c | 576 | 2,304 | unsat | 8.07 |
| scf | 3v4c | 13,824 | 55,296 | unknown | 57.15 |
| scf | 4v4c | 331,776 | 1,327,104 | unknown | refused up front |
| swf | 2v3c | 36 | 216 | unsat | 0.11 |
| swf | 3v3c | 216 | 1,296 | unsat | 2.53 |
| swf | 4v3c | 1,296 | 7,776 | unsat | 77.08 |
| swf | 2v4c | 576 | 6,912 | unsat | 48.75 |
| swf | 3v4c | 13,824 | 165,888 | unknown | 53.71 |
| swf | 4v4c | 331,776 | 3,981,312 | unknown | refused up front |

Two rows need a word. `swf 4v3c` lands past the default 60 second budget, so it comes
back `unknown` unless you raise `--timeout`. Neither `3v4c` finishes at all: the
encoding passes two million clauses before the solver is reached.

## Running it

```
pip install z3-solver

python -m core axioms
python -m core derive --mode swf pareto iia nondictatorial
python -m core derive --mode scf --voters 3 condorcet monotone nondictatorial
python -m unittest discover -s tests -t .
```

z3-solver is the only dependency. The core calls no network.

There is also a local browser interface, if picking axioms from a list and running the
returned rule on profiles you type is easier than the CLI:

```
python -m web            # http://127.0.0.1:8000
```

## The axiom library

Fifteen axioms. Each says which rule kinds it is defined for: `scf` elects a single
winner, `swf` produces a social ranking.

| axiom | kinds | |
|---|---|---|
| `pareto` | swf, scf | if every voter ranks a above b, then so does society |
| `nondictatorial` | swf, scf | no one voter's ballot is always the outcome |
| `surjective` | swf, scf | every outcome is reachable: nothing is ruled out before the vote |
| `strategyproof` | scf | no voter ever does better by submitting a ballot other than their true one |
| `monotone` | swf, scf | raising a candidate on one ballot never costs that candidate ground |
| `condorcet` | swf, scf | a candidate who beats every other head to head comes first |
| `iia` | swf | how society ranks a against b depends only on how the voters rank a against b |
| `anonymous` | swf, scf | the outcome depends on which ballots were cast, not on who cast them |
| `neutral` | swf, scf | relabelling the candidates relabels the outcome and changes nothing else |
| `unanimity` | swf, scf | a candidate every voter puts first comes out on top |
| `majority` | swf, scf | a candidate put first by more than half the voters comes out on top |
| `condorcetloser` | swf, scf | a candidate who loses every head to head comes out last |
| `topsonly` | scf | only first choices count; the rest of every ballot is ignored |
| `maskinmonotone` | scf | a winner nobody has demoted against anyone is still the winner |
| `reversal` | scf | turning every ballot upside down never leaves the same candidate winning |

Pareto is load-bearing and not decoration. Ask for `iia`, `surjective` and
`nondictatorial` alone and the answer is a *satisfying* rule, the inverse dictator,
which is Wilson's theorem. Without Pareto in the library, Arrow would come out wrong.
There is a test for exactly this.

## The axiom DSL

Axioms are data, not Python. `core/axioms.agora` holds all fifteen:

```
axiom strategyproof
  modes scf
  english no voter ever does better by submitting a ballot other than their true one
  scf forall p:profile, i:voter, r:ballot, a:cand, b:cand. \
        pref(p,i,a,b) -> not (wins(p,b) and wins(sub(p,i,r),a))
```

Quantifiers range over six sorts (`profile`, `voter`, `cand`, `ballot`, `cperm`,
`vperm`). Connectives are `not`, `and`, `or`, `->`, `<->`. Two families of decision
variable, `wins(p,c)` and `prefers(p,a,b)`, one per rule kind. Ground facts (`pref`,
`unanimous`, `condorcet`, `samepair`, `neq`) and profile transformations (`sub`,
`lift`, `permc`, `permv`, `top`) are settled in Python while the quantifiers unroll, so
a guard that comes out false takes its clause out of the formula before the solver sees
anything.

Adding an axiom means adding a block. The grounder and the renderer never learn its
name.

## Using it from Python

Everything public is exported from `core/__init__.py`.

```python
derive(axioms, voters, candidates, mode="scf", timeout=60.0,
       minimise=True, verify=True, degrade=True) -> Result

axiom_names(mode=None) -> list[str]
library() -> dict[str, Axiom]
render(result) -> str
parse_axioms(text) -> dict
```

`derive` raises `ValueError` for an unknown axiom name, an empty axiom list, or an
axiom used in a mode it is not defined for (`iia` in `scf`). It does not raise on
timeout.

```python
Result.status        # "sat" | "unsat" | "unknown"
Result.rule          # Rule | None                set on sat
Result.core          # tuple[str, ...] | None     set on unsat
Result.core_minimal  # False means unsatisfiable but minimality unverified
Result.witnesses     # dropped axiom -> a rule satisfying the rest
Result.verified      # every rule here was re-checked without the solver
Result.note          # why, on unknown
Result.partial       # what resolved at a smaller electorate, on unknown
Result.profiles, .variables, .elapsed, .timeout_s
str(result), result.as_dict()
```

`core_minimal` and `verified` are the two fields not to ignore. `core_minimal == False`
means the set is unsatisfiable but some of it may be spare, so it is not a minimal
impossibility. `verified == False` means the solver-free re-check did not run or did
not cover everything.

```python
Rule.table                     # dict[Profile, int | Ballot]   the whole rule
Rule.winner(profile) -> int    # scf only
Rule.ranking(profile) -> Ballot  # swf only
Rule.outcome(profile)          # either, by mode
Rule.show_outcome(profile)     # "A", or "A > B > C"
Rule.rows()                    # (profile string, outcome string) pairs
Rule.matches() -> list[str]    # named rules this is identical to
Rule.describe() -> str
Rule.satisfies(axiom) -> bool  # re-check without the solver
Rule.as_dict() -> dict
```

Profiles are accepted as a tuple of ballots or as a string: `"A>B>C | C>B>A"`, or a
list like `["A>B>C", "C>B>A"]`. `matches()` compares against dictatorships, inverse
dictatorships, constant rules, and plurality, Borda and Copeland with alphabetical
tie-breaking.

```python
from core import derive, library

r = derive(["pareto", "iia", "nondictatorial"], voters=2, candidates=3, mode="swf")
r.status                                  # 'unsat'
r.core                                    # ('pareto', 'iia', 'nondictatorial')
r.witnesses["nondictatorial"].describe()  # 'dictatorship of voter 2'

rule = derive(["strategyproof", "surjective"], 2, 3, mode="scf").rule
rule.winner("A>B>C | C>B>A")              # 0, which is A
rule.matches()                            # ['dictatorship of voter 1']
rule.satisfies(library()["nondictatorial"])   # False
```

## When it cannot answer

A run that does not finish says so and claims nothing. Grounding is Python and a
quantifier over pairs of profiles is quadratic, so the budget is enforced during
encoding as well as inside the solver. When a size is out of reach the electorate is
walked down and the largest one that did resolve is reported, with the caveat that the
smaller result is not shown to carry upward.

The timeout is per electorate, not per call: if a run degrades, the smaller attempt
gets its own budget, so a 60 second call can take longer in total.

## Related work

The encoding follows the computer-aided impossibility line: Tang and Lin's reduction of
Arrow to a finite base case, and Geist and Endriss's automated search over axiom sets.
The additions here are the constructive half, returning the rule rather than only the
verdict, and the minimal core rendered as English with a witness rule for every proper
subset.
