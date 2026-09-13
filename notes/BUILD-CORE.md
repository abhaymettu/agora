# L1: the derivation core

Built 2026-09-13. Python 3.14, z3-solver 5.1.0, macOS arm64.

You name the properties a fair voting rule should have. The core either hands you a rule
that provably has all of them, or hands you a proof that no such rule can exist.

This note is for L2 (web UI) and L3 (independent re-derivation). L2 needs the interface.
L3 needs the golden results to reproduce without reading the implementation.

## What was built

Nine files in `core/`, 1,550 lines, one runtime dependency (`z3-solver`).
No models, no network, no paid API. Deterministic: the same question gives the same
answer regardless of what the process asked before it.

| file | lines | job |
|---|---|---|
| `core/ground.py` | 332 | Expand an axiom tree over an electorate into Z3. The only place quantifiers unroll. |
| `core/dsl.py` | 298 | Tokeniser, syntax tree, recursive-descent parser. No Z3. |
| `core/solve.py` | 270 | Frame, selectors, minimal core, witnesses, budget. |
| `core/rules.py` | 164 | Rule object, textbook recogniser, solver-free re-check. |
| `core/domain.py` | 158 | Electorate: ballots, profiles, relabellings, ground facts. No Z3. |
| `core/render.py` | 147 | Result to English. |
| `core/axioms.agora` | 78 | The nine axioms, as data. |
| `core/cli.py` | 63 | `python -m core`, plus a 5-line `__main__.py`. |
| `core/__init__.py` | 35 | Public interface. |

Process artifacts: `.specify/memory/constitution.md` (five principles the core is held
to) and `specs/001-core/{spec,plan,tasks}.md`, written before any code.

## The axiom DSL

An axiom file is a sequence of blocks, one per axiom. Line-oriented, `#` to end of line
is a comment, a trailing `\` continues onto the next line.

```
axiom      := "axiom" NAME
              "modes" MODE+
              "english" TEXT
              (MODE formula)+                 one per declared mode

MODE       := "scf" | "swf"
SORT       := "profile" | "voter" | "cand" | "ballot" | "cperm" | "vperm"

formula    := iff
iff        := imp ("<->" imp)*
imp        := orx ("->" imp)?                 right associative
orx        := andx ("or" andx)*
andx       := unary ("and" unary)*
unary      := "not" unary | quant | "(" formula ")" | app
quant      := ("forall" | "exists") binding ("," binding)* "." formula
binding    := NAME ":" SORT
app        := NAME ("(" app ("," app)* ")")?
```

`app` covers formulas, ground facts and terms alike. Which one it is is settled by the
grounder, not the parser.

**Decision variables** (one family per mode):

| | mode | meaning |
|---|---|---|
| `wins(p, c)` | scf | candidate `c` wins at profile `p` |
| `prefers(p, a, b)` | swf | society ranks `a` above `b` at `p`; false when `a == b` |
| `ranks(p, r)` | swf | the social ranking at `p` is exactly ballot `r` (expands to a conjunction) |

**Ground facts**, evaluated in Python while quantifiers unroll:
`pref(p,i,a,b)`, `unanimous(p,a,b)`, `condorcet(p,c)`, `samepair(p,q,a,b)`, `neq(x,y)`.

**Terms**: `sub(p,i,r)`, `lift(p,i,c)`, `permc(p,s)`, `permv(p,t)`, `top(p,i)`, and
`s(a)` applying a bound candidate permutation.

`prefers(p,a,a)` is false because strict preference is irreflexive. An axiom that means
distinct candidates must say `neq(a,b)`. The parser does not silently fix this.

The whole library, for reference:

```
axiom condorcet
  modes swf scf
  english a candidate who beats every other head to head comes first
  swf forall p:profile, a:cand, b:cand. (condorcet(p,a) and neq(a,b)) -> prefers(p,a,b)
  scf forall p:profile, c:cand. condorcet(p,c) -> wins(p,c)
```

## The encoding

Tang-Lin / Geist-Endriss lineage: fix a finite electorate, make the rule's entire
outcome table the unknown, and let a SAT solver decide.

**Variables.** One boolean per (profile, candidate) for `scf`, per (profile, ordered pair
of distinct candidates) for `swf`. At 2 voters and 3 candidates that is 108 and 216.

**Frame constraints**, asserted unconditionally and never tracked, so they cannot land in
an unsat core and be reported as though transitivity were one of your axioms:

- `scf`: `PbEq([...], 1)` per profile. Exactly one winner.
- `swf`: `Xor(prefers(p,a,b), prefers(p,b,a))` per unordered pair, plus transitivity over
  every ordered triple. A strict linear order.

**Axioms as selectors.** Each axiom gets a boolean `sel!<name>`, and the solver is given
`Implies(sel!<name>, <grounded axiom>)`. Checking under those selectors as assumptions
returns an unsat core already in terms of axiom names, and dropping an axiom is dropping
an assumption, so minimisation needs no re-encoding.

**Grounding is eager and total.** Every quantifier expands over the finite domain at
encode time, and ground facts collapse to Python booleans during the expansion, so a
guard that comes out false removes its clause before Z3 sees it. That is what keeps the
formulas small: Arrow at 2 voters and 3 candidates is 216 variables and solves in 0.11s.

**Minimal core.** Deletion-based MUS, one pass over the returned core, each drop tested.
If a test comes back unknown the result says the core is unsatisfiable but not verified
minimal, rather than claiming minimality it does not have.

**Witnesses.** For every axiom in the minimal core, the solver is asked for a rule
satisfying the rest, and that rule is re-checked against those axioms *without the
solver* (`ConcreteContext` grounds the same tree against a decided table). So minimality
is demonstrated, not asserted.

**Two Z3 details that mattered.** Each `derive` call gets its own `z3.Context()`: Z3's
default context is global, and without isolation two identical calls in one process were
handed different AST ids by whatever ran between them and came back with different
(equally valid) models. `random_seed` is pinned to 0.

**Budget.** Three ceilings, because a solver timeout cannot interrupt Python:

1. `MAX_VARS = 300_000` in `solve.py`. Refused before anything is built.
2. A wall-clock deadline checked every 65,536 iterations inside quantifier expansion.
3. `MAX_CLAUSES = 2_000_000` in `ground.py`. Assembling a conjunction costs about seven
   seconds per million clauses, measured, and anything that large has no chance anyway.

On any of the three the result is `unknown` with a note saying which, and if `degrade` is
on the electorate is walked down a voter at a time until something resolves. The smaller
result is reported as a statement about the smaller electorate, explicitly not shown to
carry upward.

## Golden results

`python -m unittest discover -s tests -t .` — 24 tests, all passing, 14.1s.

```
test_base_case_is_impossible (tests.test_golden.Arrow.test_base_case_is_impossible) ... ok
test_dropping_nondictatorship_gives_a_dictator (tests.test_golden.Arrow.test_dropping_nondictatorship_gives_a_dictator) ... ok
test_every_axiom_in_the_core_is_load_bearing (tests.test_golden.Arrow.test_every_axiom_in_the_core_is_load_bearing) ... ok
test_pareto_is_what_makes_it_arrow (tests.test_golden.Arrow.test_pareto_is_what_makes_it_arrow)
IIA, surjectivity and nondictatorship alone are satisfiable. ... ok
test_still_impossible_with_three_voters (tests.test_golden.Arrow.test_still_impossible_with_three_voters) ... ok
test_a_budget_that_cannot_be_met_degrades_to_a_smaller_electorate (tests.test_golden.Budget.test_a_budget_that_cannot_be_met_degrades_to_a_smaller_electorate) ... ok
test_an_electorate_too_big_to_encode_is_refused_up_front (tests.test_golden.Budget.test_an_electorate_too_big_to_encode_is_refused_up_front) ... ok
test_every_profile_elects_exactly_one_candidate (tests.test_golden.Frame.test_every_profile_elects_exactly_one_candidate) ... ok
test_every_social_ranking_is_a_strict_linear_order (tests.test_golden.Frame.test_every_social_ranking_is_a_strict_linear_order) ... ok
test_frame_constraints_never_appear_in_a_core (tests.test_golden.Frame.test_frame_constraints_never_appear_in_a_core) ... ok
test_base_case_is_impossible (tests.test_golden.GibbardSatterthwaite.test_base_case_is_impossible) ... ok
test_dropping_nondictatorship_gives_a_dictator (tests.test_golden.GibbardSatterthwaite.test_dropping_nondictatorship_gives_a_dictator) ... ok
test_still_impossible_with_three_voters (tests.test_golden.GibbardSatterthwaite.test_still_impossible_with_three_voters) ... ok
test_the_witness_for_dropping_nondictatorship_is_a_dictator (tests.test_golden.GibbardSatterthwaite.test_the_witness_for_dropping_nondictatorship_is_a_dictator) ... ok
test_a_returned_rule_runs_on_any_profile_of_its_electorate (tests.test_golden.Interface.test_a_returned_rule_runs_on_any_profile_of_its_electorate) ... ok
test_an_axiom_used_in_the_wrong_mode_is_refused (tests.test_golden.Interface.test_an_axiom_used_in_the_wrong_mode_is_refused) ... ok
test_an_unknown_axiom_is_refused (tests.test_golden.Interface.test_an_unknown_axiom_is_refused) ... ok
test_every_axiom_in_the_library_grounds_in_every_mode_it_claims (tests.test_golden.Interface.test_every_axiom_in_the_library_grounds_in_every_mode_it_claims) ... ok
test_results_serialise (tests.test_golden.Interface.test_results_serialise) ... ok
test_the_same_question_gives_the_same_rule (tests.test_golden.Interface.test_the_same_question_gives_the_same_rule)
Including when unrelated work happens in between. ... ok
test_condorcet_rules_are_manipulable (tests.test_golden.SmallerTheorems.test_condorcet_rules_are_manipulable) ... ok
test_irrelevant_axioms_are_dropped_from_the_core (tests.test_golden.SmallerTheorems.test_irrelevant_axioms_are_dropped_from_the_core) ... ok
test_no_resolute_anonymous_neutral_rule_at_three_voters (tests.test_golden.SmallerTheorems.test_no_resolute_anonymous_neutral_rule_at_three_voters)
Three voters can produce a cycle that a candidate relabelling fixes. ... ok
test_a_dictatorship_has_exactly_the_properties_it_should (tests.test_golden.WithoutTheSolver.test_a_dictatorship_has_exactly_the_properties_it_should) ... ok

----------------------------------------------------------------------
Ran 24 tests in 14.114s

OK
```

### What L3 has to reproduce

Written as claims, not as code, so L3 can derive them independently.

| question | mode | size | expected |
|---|---|---|---|
| pareto, iia, nondictatorial | swf | 2v3c | **unsat**, minimal core is all three |
| pareto, iia, nondictatorial | swf | 3v3c | **unsat**, minimal core is all three |
| pareto, iia | swf | 2v3c | **sat**, and the rule is a dictatorship |
| iia, surjective, nondictatorial | swf | 2v3c | **sat**, and the rule is an *inverse* dictatorship (Wilson) |
| strategyproof, surjective, nondictatorial | scf | 2v3c | **unsat**, minimal core is all three |
| strategyproof, surjective, nondictatorial | scf | 3v3c | **unsat**, minimal core is all three |
| strategyproof, surjective | scf | 2v3c | **sat**, and the rule is a dictatorship |
| anonymous, neutral | scf | 3v3c | **unsat** |
| anonymous, neutral | scf | 2v3c | **sat** |
| condorcet, strategyproof | scf | 3v3c | **unsat**, minimal core is both |
| condorcet, strategyproof, surjective | scf | 3v3c | **unsat**, surjective not in the core |

The Wilson row is the one that justifies a ninth axiom. The brief named eight, none of
them pareto. With only those eight, asking for Arrow gives `iia + surjective +
nondictatorial`, which is **satisfiable** (the inverse dictator survives it), and the
flagship theorem would come out wrong. Pareto is in the library for that reason and the
test says so.

The two dictatorship rows are the drop-an-axiom check: removing nondictatorial from
Gibbard-Satterthwaite yields a dictatorship, which is exactly the witness shape the
theorem predicts.

## Timings

`PYTHONPATH=. python notes/sweep.py > notes/timings.txt`, 120s budget per row,
degradation off so each row is that size alone. One machine, Python 3.14, z3 5.1.0.

```
mode  size    profiles  variables status     seconds  note
scf   2v3c         36        108 unsat         0.07
scf   3v3c        216        648 unsat         0.57
scf   4v3c      1,296      3,888 unsat         5.08
scf   2v4c        576      2,304 unsat         8.07
scf   3v4c     13,824     55,296 unknown      57.15  encoding budget, clauses
scf   4v4c    331,776  1,327,104 unknown       0.00  refused up front
swf   2v3c         36        216 unsat         0.11
swf   3v3c        216      1,296 unsat         2.53
swf   4v3c      1,296      7,776 unsat        77.08
swf   2v4c        576      6,912 unsat        48.75
swf   3v4c     13,824    165,888 unknown      53.71  encoding budget, clauses
swf   4v4c    331,776  3,981,312 unknown       0.00  refused up front
```

Read it honestly:

- **Three candidates is the comfortable range.** Everything at three candidates finishes,
  two of the four in under a second.
- **The pitch says under a minute. Two rows in scope miss it.** `swf 4v3c` takes 77s and
  `swf 2v4c` takes 49s with plenty of variance. Under the default 60s timeout, `swf 4v3c`
  comes back `unknown` rather than `unsat`. The under-a-minute claim holds for three
  candidates up to three voters, and for four candidates only at two voters. L2 should
  either default to those sizes or raise the timeout and say it is working.
- **Four candidates with three voters is the wall,** and it is the encoding, not the
  solver. IIA over pairs of 13,824 profiles, and strategyproofness over profile by voter
  by ballot by pair, both pass two million clauses before the solver is reached. Cutting
  that needs a smarter grounder (bucket profiles by pairwise signature), not a faster
  machine. Not done; the budget reports it honestly instead.
- **Four voters and four candidates is refused before anything is built,** at 1.3 million
  variables for `scf` and 4.0 million for `swf`.

## The interface L2 and L3 consume

Everything below is exported from `core/__init__.py`. Nothing else is public.

```python
derive(axioms, voters: int, candidates: int, mode: str = "scf",
       timeout: float = 60.0, minimise: bool = True,
       verify: bool = True, degrade: bool = True) -> Result

axiom_names(mode: str | None = None) -> list[str]
library() -> dict[str, Axiom]          # name -> Axiom(name, modes, english, bodies)
render(result) -> str                  # same as str(result)
parse_axioms(text: str) -> dict        # for a caller supplying its own axiom file
parse_formula(text: str, line: int = 0)
```

`derive` raises `ValueError` for an unknown axiom name, an empty axiom list, or an axiom
used in a mode it is not defined for (`iia` in `scf`). It does not raise on timeout.

### Result

```python
Result.status        # "sat" | "unsat" | "unknown"   the only three
Result.mode          # "scf" | "swf"
Result.voters        # int
Result.candidates    # int
Result.axioms        # tuple[str, ...]   what was asked
Result.profiles      # int   size of the search space
Result.variables     # int   size of the encoding
Result.timeout_s     # float
Result.elapsed       # float
Result.rule          # Rule | None       set on sat
Result.core          # tuple[str, ...] | None   set on unsat
Result.core_minimal  # bool   False means unsatisfiable but minimality unverified
Result.witnesses     # dict[str, Rule]   dropped axiom -> a rule satisfying the rest
Result.verified      # bool   every rule here was re-checked without the solver
Result.note          # str    why, on unknown
Result.partial       # Result | None     what resolved at a smaller electorate
str(result)          # the English rendering
result.as_dict()     # JSON-safe, nested, for a UI
```

`core_minimal` and `verified` are the two fields a UI must not ignore. `core_minimal ==
False` means the set is unsatisfiable but some of it may be spare; do not call it a
minimal impossibility. `verified == False` means the solver-free re-check did not run or
did not cover everything.

### Rule

```python
Rule.mode            # "scf" | "swf"
Rule.elec            # Electorate
Rule.table           # dict[Profile, int | Ballot]   the whole rule

Rule.winner(profile) -> int          # scf only; raises TypeError on a swf rule
Rule.ranking(profile) -> Ballot      # swf only
Rule.outcome(profile)                # either, by mode
Rule.show_outcome(profile) -> str    # "A", or "A > B > C"
Rule.rows()                          # iterator of (profile string, outcome string)
Rule.matches() -> list[str]          # textbook rules this is identical to
Rule.describe() -> str               # a name, or an honest description
Rule.satisfies(axiom) -> bool        # re-check without the solver
Rule.as_dict() -> dict               # JSON-safe
```

`winner`, `ranking`, `outcome` and `show_outcome` all accept a profile as a tuple of
ballots **or** as a string: `"A>B>C | C>B>A"`, or a list like `["A>B>C", "C>B>A"]`.
`ValueError` for the wrong number of ballots or a string that is not a ranking;
`KeyError` for a profile outside the electorate.

`matches()` compares against dictatorships, inverse dictatorships (swf), constant rules
(scf), and plurality, borda and copeland with alphabetical tie-breaking. Usually zero or
one match.

### Electorate

Useful to L2 for building and displaying profiles.

```python
Electorate(voters: int, candidates: int)
  .voters .candidates .cands .vs .ballots .profiles .cperms .vperms
  .parse_ballot("A > B > C") -> Ballot        # also "ABC", or a tuple
  .parse_profile("A>B>C | C>B>A") -> Profile  # also a list of ballots
  .show_ballot(b) -> "A > B > C"
  .show_profile(p) -> "v1: A > B > C | v2: C > B > A"
  .name(c) -> "A"
  .sub(p, i, r)  .lift(p, i, c)  .permc(p, s)  .permv(p, t)  .top(p, i)
  .pref(p, i, a, b)  .unanimous(p, a, b)  .beats(p, a, b)
  .condorcet(p, c)  .condorcet_winner(p) -> int | None  .samepair(p, q, a, b)
```

Candidates are `0..m-1` and display as `A`, `B`, `C`, `D`. Voters are `0..n-1` and display
one-based (`v1`). A ballot is a tuple of candidates, best first. A profile is a tuple of
ballots, one per voter.

### Example calls

```python
from core import derive, axiom_names, Electorate

# the impossibility branch
r = derive(["pareto", "iia", "nondictatorial"], voters=2, candidates=3, mode="swf")
assert r.status == "unsat" and r.core_minimal
print(r)                                  # the English proof
r.witnesses["nondictatorial"].describe()  # 'dictatorship of voter 2'

# the constructive branch, and stress-testing what comes back
r = derive(["strategyproof", "surjective"], 2, 3, mode="scf")
rule = r.rule
rule.matches()                            # ['dictatorship of voter 1']
rule.winner("A>B>C | C>B>A")              # 0, which is A
rule.winner(["C>B>A", "A>B>C"])           # 2, which is C
len(list(rule.rows()))                    # 36

# check a claim without trusting the solver
from core import library
rule.satisfies(library()["strategyproof"])   # True
rule.satisfies(library()["nondictatorial"])  # False

# for a UI
r.as_dict()                               # nested, JSON-safe
axiom_names(mode="scf")                   # 8 of the 9; iia is swf only

# handling the third answer
r = derive(["pareto", "iia", "nondictatorial"], 4, 3, mode="swf", timeout=5)
if r.status == "unknown":
    print(r.note)                         # why
    if r.partial:
        print(r.partial.voters, r.partial.status)   # 3 unsat
```

### Command line

```
python -m core axioms [--mode scf|swf]
python -m core derive [--mode scf|swf] [--voters N] [--candidates N]
                      [--timeout S] [--json] [--table] AXIOM...
```

Exit code 0 when the question was answered, 1 on `unknown`, 2 on a bad axiom name.

## What L2 and L3 should know going in

- **Do not reach past the public interface.** `core.ground` and `core.solve` internals
  will move; `core/__init__.py` will not.
- **Sizes.** Default to three candidates. Four candidates is fine at two voters and dead
  at three. Anything at four candidates and four voters is refused instantly, which is a
  usable answer, not a hang.
- **The timeout is per electorate, not per call.** If a run degrades, the smaller attempt
  gets its own budget, so a 60s call can take longer in total. Documented on `derive`.
- **`unknown` is a real answer and must be shown as one.** The note says which of the
  three ceilings was hit. Reporting it as a failure or a spinner would misrepresent what
  the machine knows.
- **Every claim comes with an object.** An impossibility comes with a minimal core and a
  witness rule per proper subset; an existence comes with the rule itself. If a UI shows
  the verdict without the object it is throwing away the part that is checkable.

## Open, not done

- **The grounder is naive about quadratic quantifiers.** IIA ranges over pairs of
  profiles and is expanded pair by pair. Bucketing profiles by their pairwise signature
  would collapse it to near-linear and is what stands between the core and four
  candidates at three voters. Worth doing; the budget makes its absence honest in the
  meantime.
- **Resolute rules only.** No ties, no indifference, no choice sets. Several natural
  axioms (anonymity with neutrality, most obviously) are inconsistent at three voters
  *because* the rule must break a tie it has no way to break. That is a real theorem, but
  a reader may expect the irresolute version, which this does not do.
- **No lifting argument.** Everything is a base-case lemma over a fixed electorate. The
  induction that carries these to all electorates is the classical proof and lives
  outside this machine.
- **The recogniser is a short list.** Dictatorships, inverse dictatorships, constants,
  plurality, borda, copeland. An unnamed witness gets a description, not a name.
- **Citations in the README were written offline and should be checked before quoting.**
