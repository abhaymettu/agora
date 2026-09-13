# AGORA

You name the properties a fair voting rule should have. The machine either hands you a
rule that provably has all of them, or hands you a proof that no such rule can exist,
minted on the spot, under a minute.

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
instead and you get the other branch: a concrete rule, as an object you can run on any
profile you like.

```
$ python -m core derive --mode scf strategyproof surjective

A social choice function over 2 voters and 3 candidates satisfying all of
these exists (a rule that elects one winner):
  ...
One such rule: dictatorship of voter 1.
```

## What this is, said honestly

**Small electorates are base-case lemmas, and the output says so every time.** Two to
four voters, three to four candidates. That is where the classical theorems bite and
where exhaustive search finishes in seconds. An impossibility established at three
voters is a fact about three voters. Lifting it to every electorate is a separate
argument that this machine does not make, and it never pretends otherwise.

**The constructive branch is real, not a toy.** When a rule exists, you do not get a
yes. You get the rule: every profile of the electorate mapped to its outcome, runnable
on any profile you type, recognised by name if it happens to be a rule anyone has
written down, and re-checked against every axiom you asked for without going back
through the solver. You can stress-test it. That is the point of returning an object
instead of a verdict.

**This is the existence question, not the explanation question.** There is a line of
work out of the ILLC on justifying collective decisions: fix one profile, fix the
outcome a rule produced, and generate a human-readable explanation of why that outcome
follows from a chosen set of axioms in that profile. The justify demo answers "why this
result, here". AGORA answers a different question with a different quantifier: over
*all* profiles of the electorate, does any rule at all satisfy these axioms? One
explains a decision. The other synthesises a rule or refutes its existence.

**What it does not do.** Ties, indifference, and irresolute rules are out of scope:
ballots and social rankings are strict, and a voting rule elects exactly one winner.
There are no domain restrictions, so no single-peaked preferences. Nine axioms, listed
below, and no way to add a tenth except by writing it in the DSL, which is the
intended way.

## Running it

```
pip install z3-solver
python -m core axioms
python -m core derive --mode swf pareto iia nondictatorial
python -m core derive --mode scf --voters 3 condorcet strategyproof
python -m unittest discover -s tests -t .
```

z3-solver is the only dependency. Nothing here calls a network or a model.

## The axiom library

Nine axioms. Each one says which rule kinds it is defined for: `scf` elects a single
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

`pareto` is the ninth, and it is not decoration. Arrow's theorem needs it: ask for
`iia`, `surjective` and `nondictatorial` alone and the machine correctly returns a
*satisfying* rule, the inverse dictator, which is Wilson's theorem. Without pareto in
the library the flagship result would come out wrong. There is a test for exactly this.

## The axiom DSL

Axioms are data, not Python. `core/axioms.agora` holds all nine:

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
`lift`, `permc`, `permv`, `top`) are settled in Python while the quantifiers unroll,
so a guard that comes out false takes its clause out of the formula before the solver
sees anything.

Adding an axiom means adding a block. The grounder and the renderer never learn its
name.

## Using it from other code

```python
from core import derive

r = derive(["pareto", "iia", "nondictatorial"], voters=2, candidates=3, mode="swf")
r.status          # "sat", "unsat" or "unknown"
r.core            # the minimal set to blame, on unsat
r.witnesses       # {dropped axiom: a rule satisfying the rest}
r.rule            # the rule itself, on sat
print(r)          # the English above
r.as_dict()       # JSON-safe, for a UI

rule = derive(["strategyproof", "surjective"], 2, 3, mode="scf").rule
rule.winner("A>B>C | C>B>A")   # run it on anything
rule.matches()                 # ['dictatorship of voter 1']
```

`notes/BUILD-CORE.md` has the full interface, the grammar, the encoding, and measured
timings per electorate size.

## When it cannot answer

A run that does not finish says so and claims nothing. Grounding is Python and a
quantifier over pairs of profiles is quadratic, so the budget is enforced during
encoding as well as inside the solver. When a size is out of reach the machine walks
the electorate down and reports the largest one that did resolve, while stating plainly
that the smaller result is not shown to carry upward.

## Lineage

The encoding follows the computer-aided impossibility line: Tang and Lin's
reduction of Arrow to a finite base case, and Geist and Endriss's automated search over
axiom sets. The constructive half, returning the rule rather than only the verdict, and
the minimal core rendered as English with a witness for every proper subset, are what
this adds.

*Citations here were written offline. Check them before quoting.*
